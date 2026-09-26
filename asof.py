"""asof - Wikipedia figures checked against the dataset their citation names.

A Wikipedia sentence that cites

    https://data.worldbank.org/indicator/SP.POP.TOTL?locations=KE

has already said, in a form a program can read, which series and which country
its number came from. So the number can be checked: fetch the series, find the
year the figure belongs to, and see whether the source has a newer year, or
now gives a different value for the year the sentence states.

It reports and never edits. Every finding carries the sentence, the figure as
written, the source's value, and a link to both, so an editor can decide in one
look. Where it cannot tell - no country in the link, no figure near the
citation, a figure that matches no year - it says nothing about that citation
and counts it, rather than guessing. A checker that is right about the things
it reports and silent about the rest is useful; one that is sometimes wrong is
noise an editor learns to skip.

    python asof.py check "Economy of Senegal"      # one article
    python asof.py scan --limit 200 --out report   # the articles citing the World Bank

Standard library only, Python 3.8 or later.
"""

import argparse
import datetime
import hashlib
import html
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

__version__ = "0.1.0"

#: Wikimedia's user-agent policy asks for a way to reach the operator.
USER_AGENT = "asof/%s (+https://github.com/jhaney0214-sys/placeholder1)" % __version__
WIKI = "https://en.wikipedia.org"
WORLDBANK_API = "https://api.worldbank.org/v2/country/%s/indicator/%s?format=json&per_page=200&page=%d"

#: Pages outside the article namespace link to the World Bank too - talk pages,
#: drafts, user sandboxes. Special:LinkSearch's namespace filter did not hold
#: when this was written, so titles are filtered here instead.
NON_ARTICLE = (
    "Talk", "User", "User talk", "Wikipedia", "Wikipedia talk", "File",
    "File talk", "MediaWiki", "MediaWiki talk", "Template", "Template talk",
    "Help", "Help talk", "Category", "Category talk", "Portal", "Portal talk",
    "Draft", "Draft talk", "TimedText", "TimedText talk", "Module",
    "Module talk", "Book", "Book talk", "Education Program",
)


# --------------------------------------------------------------- fetching

class Fetcher(object):
    """HTTP GET with a disk cache, a minimum interval per host, and patience
    with HTTP 429.

    Wikimedia rate-limits shared addresses hard (an `api.php` request from a
    cloud host was refused on the first try), so everything here goes through
    `index.php?action=raw` and Special:LinkSearch, which answered, one request
    at a time, honouring Retry-After.
    """

    def __init__(self, cache_dir=None, max_age=86400, interval=None, log=None):
        self.cache_dir = pathlib.Path(cache_dir) if cache_dir else None
        self.max_age = max_age
        self.interval = interval or {"en.wikipedia.org": 2.0, "api.worldbank.org": 0.3}
        self.last = {}
        self.log = log or (lambda message: None)

    def _cache_path(self, url):
        return self.cache_dir / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".txt")

    def __call__(self, url):
        if self.cache_dir:
            path = self._cache_path(url)
            if path.exists() and time.time() - path.stat().st_mtime < self.max_age:
                return path.read_text(encoding="utf-8")
        host = urllib.parse.urlsplit(url).netloc
        for attempt in range(6):
            wait = self.interval.get(host, 1.0) - (time.time() - self.last.get(host, 0))
            if wait > 0:
                time.sleep(wait)
            self.last[host] = time.time()
            try:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=30) as response:
                    body = response.read().decode("utf-8")
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt == 5:
                    raise
                pause = int(exc.headers.get("Retry-After") or 30) + 2
                self.log("rate limited by %s, waiting %ds" % (host, pause))
                time.sleep(pause)
            except (urllib.error.URLError, OSError) as exc:
                # A read that times out or a connection that drops is the
                # network, not the page. The first full scan died on one
                # timeout at article 10 of 1,270, which is why this exists.
                if attempt == 5:
                    raise
                pause = 5 * (attempt + 1)
                self.log("%s from %s, retrying in %ds" % (type(exc).__name__, host, pause))
                time.sleep(pause)
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache_path(url).write_text(body, encoding="utf-8")
        return body


# --------------------------------------------------------------- citations

CITATION_URL = re.compile(
    r"(?P<prefix>archive-url\s*=\s*\S*?)?"
    r"https?://data\.worldbank\.org/indicator/(?P<indicator>[A-Za-z0-9_.]+)(?P<query>[^\s|}\]<]*)",
    re.I)
REF_BLOCK = re.compile(r"<ref\b[^>/]*>(?P<body>.*?)</ref\s*>", re.I | re.S)


class Citation(object):
    """One World Bank citation: where its ref starts, and what it names."""

    def __init__(self, ref_start, url, indicator, country):
        self.ref_start = ref_start
        self.url = url
        self.indicator = indicator
        self.country = country

    def __repr__(self):
        return "Citation(%s, %s)" % (self.indicator, self.country)


def parse_url(url):
    """(indicator, country) from a data.worldbank.org link.

    The country is None unless `locations=` names exactly one place: a link
    comparing Hungary, Romania and Bulgaria cannot say which figure the
    sentence took from it, so the citation is not checkable and is skipped.
    """
    match = re.search(r"/indicator/([A-Za-z0-9_.]+)", url, re.I)
    if not match:
        return None, None
    indicator = match.group(1).upper().rstrip(".")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(html.unescape(url)).query)
    places = [p for value in query.get("locations", []) for p in value.split("-") if p]
    country = places[0].upper() if len(places) == 1 else None
    return indicator, country


def citations(wikitext):
    """Every <ref> whose primary URL is a World Bank indicator page.

    A ref's `archive-url` usually repeats the same link through the Wayback
    Machine; only the first link that is not an archive copy counts, once per
    ref. Named refs reused elsewhere (`<ref name="x"/>`) are checked only
    where they are defined, since that is the only place the link appears.
    """
    found = []
    for block in REF_BLOCK.finditer(wikitext):
        for match in CITATION_URL.finditer(block.group("body")):
            if match.group("prefix"):
                continue
            url = match.group(0)
            indicator, country = parse_url(url)
            found.append(Citation(block.start(), url, indicator, country))
            break
    return found


# --------------------------------------------------------------- the claim

def flatten(text):
    """Wikitext reduced to what a reader sees, near enough to find figures in.

    Links keep their label, bold and italics go, templates are opened up so a
    number inside `{{US$|4,990}}` or a year inside `{{As of|2018}}` survives,
    and entities become characters.
    """
    text = re.sub(r"<ref\b[^>]*/>", " ", text, flags=re.I)
    text = re.sub(r"<ref\b.*?</ref\s*>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", text)
    text = text.replace("'''", "").replace("''", "")
    text = re.sub(r"[{}|]+", " ", text)
    text = html.unescape(text).replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def claim_before(wikitext, ref_start, reach=400):
    """The sentence, or infobox row, that the ref at `ref_start` supports.

    It runs back from the ref to the nearest of: the end of an earlier ref, the
    start of the line, or the end of the previous sentence. An infobox row
    keeps its key (`gini`, `population`) because the key says what the figure
    is when the row's own text does not.

    Returns (key, claim, row). `row` is true for an infobox field or a list
    item: those present a current value, so a newer year makes them stale,
    where a sentence of prose saying what happened in 1986 stays true.
    """
    start = max(0, ref_start - reach)
    window = wikitext[start:ref_start]
    ends = [window.rfind(mark) + len(mark) for mark in ("</ref>", "/>", "\n")
            if window.rfind(mark) >= 0]
    if ends:
        window = window[max(ends):]
    body = window.rstrip(" .,;:")
    sentence_end = None
    for match in re.finditer(r"[.!?](?:\s|&nbsp;)+(?=[A-Z\[\'\"])", body):
        sentence_end = match.end()
    if sentence_end is not None:
        body = body[sentence_end:]
    key = None
    is_row = bool(re.match(r"\s*[|*]", body))
    field = re.match(r"\s*[|*]\s*([a-z_ ]+?)\s*=\s*(.*)$", body, re.S)
    if field:
        key, body = field.group(1).strip(), field.group(2)
    return key, flatten(body.lstrip("*| ")), is_row


# --------------------------------------------------------------- figures

MULTIPLIERS = {"thousand": 1e3, "million": 1e6, "mn": 1e6, "billion": 1e9,
               "bn": 1e9, "trillion": 1e12}
FIGURE = re.compile(
    r"(?<![\w.,/-])(?P<sign>[-−])?\s?(?P<currency>US\$|\$)?\s?"
    r"(?P<number>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?:\s?(?P<unit>%|(?:per\s?cent|percent|thousand|million|mn|billion|bn|trillion)\b))?",
    re.I)
BOUND = re.compile(r"(?:exceed(?:s|ed|ing)?|over|more than|above|under|below|less than|fewer than|"
                   r"greater than|at least|at most|up to|nearly|almost)\s*(?:US\$|\$)?\s*$", re.I)
APPROXIMATE = re.compile(r"(?:about|around|approximately|roughly|circa|some|an estimated|estimated)"
                         r"\s*(?:US\$|\$)?\s*$", re.I)
YEAR = re.compile(r"(?<!\d)(?<!\d[.,])(19\d\d|20\d\d)(?![\d%]|[.,]\d)")


class Figure(object):
    """A number as a sentence writes it, with the precision it was written to."""

    def __init__(self, raw, value, tolerance, position, decimals, grouped, unit,
                 significant=3, bound=False, approximate=False):
        self.raw = raw
        self.value = value
        self.tolerance = tolerance
        self.position = position
        self.decimals = decimals
        self.grouped = grouped
        self.unit = unit
        #: How many digits the figure commits to. "7%" commits to one, and
        #: one digit matches too many years of a long series to mean anything.
        self.significant = significant
        #: "exceeded 7%", "under 450": a bound, not a value.
        self.bound = bound
        #: "about 184,000": a value, but not one to call a revision of.
        self.approximate = approximate

    def __repr__(self):
        return "Figure(%r)" % self.raw

    def matches(self, value):
        """Would this figure be the honest rounding of `value`?"""
        return abs(value - self.value) <= self.tolerance + 1e-9 * max(1.0, abs(value))

    def render(self, value):
        """`value` written the way this figure is written, for side-by-side reading."""
        scale = MULTIPLIERS.get((self.unit or "").lower(), 1.0)
        shown = value / scale
        if self.grouped and not self.decimals:
            text = "{:,.0f}".format(shown)
        elif self.grouped:
            text = "{:,.{}f}".format(shown, self.decimals)
        else:
            text = "{:.{}f}".format(shown, self.decimals)
        if self.unit:
            text += "%" if self.unit == "%" else " " + self.unit
        return text


def figures(text):
    """Every number in the claim that could be a statistic.

    Bare four-digit years are left out: they are dates, and they are what
    `years` reads. A number written as "42.4" carries a tolerance of 0.05,
    because a sentence that rounds honestly to one decimal place is correct
    for anything that rounds to it.
    """
    found = []
    for match in FIGURE.finditer(text):
        number, unit = match.group("number"), match.group("unit")
        if (not unit and not match.group("sign") and not match.group("currency")
                and re.fullmatch(r"(19|20)\d\d", number)):
            continue
        decimals = len(number.split(".")[1]) if "." in number else 0
        grouped = "," in number
        value = float(number.replace(",", ""))
        digits = number.replace(",", "")
        if "." in digits:
            significant = len(digits.replace(".", "").lstrip("0")) or 1
            trailing = 0
        else:
            significant = len(digits.strip("0")) or 1
            # "119,000,000 hectares" is rounded to the million, not exact.
            trailing = len(digits) - len(digits.rstrip("0")) if digits.strip("0") else 0
        if match.group("sign"):
            value = -value
        unit_key = (unit or "").lower().replace(" ", "")
        if unit_key == "percent":
            unit_key = "%"
        scale = MULTIPLIERS.get(unit_key, 1.0)
        tolerance = 0.5 * 10 ** (trailing - decimals) * scale
        before = text[max(0, match.start() - 25):match.start()]
        found.append(Figure(match.group(0).strip(), value * scale, tolerance,
                            match.start(), decimals, grouped, unit_key or None,
                            significant, bool(BOUND.search(before)),
                            bool(APPROXIMATE.search(before))))
    return found


def stated_year(text, figure):
    """The year the claim attaches to `figure`, or None.

    Wikipedia's convention is a year after the figure - "42.4% (2015)",
    "3% in 2019" - so the first year after it wins, unless another figure
    stands between them ("4.5% in 2018, rising to 5.0% in 2020" gives 4.5%
    its own year, not 5.0%'s). Otherwise the nearest year before it, as in
    "In 2016, unsafe water accounted for 68.6 deaths".
    """
    others = [f.position for f in figures(text) if f.position != figure.position]
    years = [(m.start(), int(m.group(1))) for m in YEAR.finditer(text)]
    for at, year in years:
        if at > figure.position and not [p for p in others if figure.position < p < at]:
            return year
    before = [(figure.position - at, year) for at, year in years if at < figure.position]
    return min(before)[1] if before else None


# --------------------------------------------------------------- the source

class Series(object):
    """One World Bank indicator for one country: every year with a value."""

    def __init__(self, indicator, country, values, name=None, country_name=None,
                 updated=None):
        self.indicator = indicator
        self.country = country
        self.values = values
        self.name = name
        self.country_name = country_name
        self.updated = updated

    @property
    def latest(self):
        return max(self.values) if self.values else None

    @property
    def url(self):
        return "https://data.worldbank.org/indicator/%s?locations=%s" % (
            self.indicator, self.country)


def worldbank_series(fetch, indicator, country):
    """Every non-empty year of `indicator` for `country`, or None if the API
    has nothing for the pair (a retired indicator, a code the link mistyped)."""
    values, name, country_name, updated, page, pages = {}, None, None, None, 1, 1
    while page <= pages:
        data = json.loads(fetch(WORLDBANK_API % (urllib.parse.quote(country),
                                                  urllib.parse.quote(indicator), page)))
        if not isinstance(data, list) or len(data) < 2 or not data[1]:
            return None
        meta, rows = data
        pages, updated = int(meta.get("pages") or 1), meta.get("lastupdated")
        for row in rows:
            if row.get("value") is not None and str(row.get("date", "")).isdigit():
                values[int(row["date"])] = float(row["value"])
            name = name or (row.get("indicator") or {}).get("value")
            country_name = country_name or (row.get("country") or {}).get("value")
        page += 1
    if not values:
        return None
    return Series(indicator, country, values, name, country_name, updated)


# --------------------------------------------------------------- the verdict

#: What a finding can say. The first three are reported; the rest are counted.
NEWER, MISLABELED, DIFFERS = "newer", "mislabeled", "differs"
CURRENT, HISTORICAL, UNMATCHED, NO_FIGURE, COMPUTED, NO_COUNTRY, NO_DATA = (
    "current", "historical", "unmatched", "no figure", "computed", "no country in link",
    "no data")

#: An exchange rate is cited to convert an amount at a date, so a newer rate
#: never makes the sentence stale. Found in the first scan: film articles
#: converting a 1965 box office at the 1965 rupee rate were reported as "newer".
DATED_BY_USE = ("PA.NUS.FCRF",)
#: A figure the page computes (`#expr`, `formatnum`) is not one a person wrote.
COMPUTED_MARK = re.compile(r"#expr|formatnum|\bround\s+\d", re.I)
RESPECTIVELY = re.compile(r"\brespectively\b", re.I)
#: Words that make a sentence with a year a statement of the current value.
CURRENT_WORDS = re.compile(r"\bas of\b|\bcurrently\b|\bstands at\b|\bis now\b|\bthe latest\b", re.I)
#: Smaller than this, a changed value is a revision nobody needs to act on.
DIFFERS_AT_LEAST = 0.02
#: Within this of the stated year's value, a mismatch is a revision of that
#: year, not a figure that belongs to another one.
SAME_YEAR_WITHIN = 0.05


def relative(a, b):
    return abs(a - b) / abs(a) if a else float("inf")
REPORTED = (NEWER, MISLABELED, DIFFERS)


class Finding(object):

    def __init__(self, article, citation, kind, claim="", key=None, figure=None,
                 year=None, matched_year=None, series=None, note=""):
        self.article = article
        self.citation = citation
        self.kind = kind
        self.claim = claim
        self.key = key
        self.figure = figure
        self.year = year
        self.matched_year = matched_year
        self.series = series
        self.note = note

    def as_dict(self):
        out = {"article": self.article, "kind": self.kind, "claim": self.claim,
               "key": self.key, "citation": self.citation.url,
               "indicator": self.citation.indicator, "country": self.citation.country,
               "note": self.note}
        if self.figure is not None:
            out["figure"] = self.figure.raw
        if self.year is not None:
            out["stated_year"] = self.year
        if self.matched_year is not None:
            out["matched_year"] = self.matched_year
        if self.series is not None:
            s = self.series
            out.update({"series": s.name, "place": s.country_name,
                        "latest_year": s.latest, "latest_value": s.values[s.latest],
                        "source_updated": s.updated})
            if self.figure is not None:
                out["latest_as_written"] = self.figure.render(s.values[s.latest])
        return out


def judge(article, citation, key, claim, series, row=False):
    """What the source says about the figure beside `citation`.

    Figures are tried nearest-the-citation first, because the number a ref
    supports is almost always the last one before it; a sentence that gives
    two statistics and cites the second must not be judged on the first.

    Every rule below that keeps a finding out of the report was added after
    reading the first scan's findings by hand, and each names what it caught.
    """
    base = dict(article=article, citation=citation, claim=claim, key=key, series=series)
    if COMPUTED_MARK.search(claim):
        return Finding(kind=COMPUTED, **base)
    if RESPECTIVELY.search(claim):
        # "in 1986 and 1987 growth decreased to 1.9% and 1.6% respectively"
        # pairs figures with years by order, which reading figure by figure
        # gets wrong. Found in the first scan, where 1.9% was given 1987.
        return Finding(kind=UNMATCHED, **base)
    found = figures(claim)
    if not found:
        return Finding(kind=NO_FIGURE, **base)
    ordered = sorted(found, key=lambda f: -f.position)
    presents_current = row or bool(CURRENT_WORDS.search(claim))
    for figure in ordered:
        if figure.bound:
            continue
        stated = stated_year(claim, figure)
        years = [y for y, v in series.values.items() if figure.matches(v)]
        if not years:
            continue
        if stated in years:
            matched = stated
        elif stated is not None:
            # The figure is some other year's value. Say so only when it is
            # precise enough that the match is not a coincidence ("exceeded
            # 7%" matched a 2024 value), and the stated year's own value is
            # not close enough to make this a revision of that year instead.
            own = series.values.get(stated)
            if figure.significant >= 3 and (own is None or relative(own, figure.value) > SAME_YEAR_WITHIN):
                matched = max(years)
                note = "the text says %d; %s is the %d value" % (stated, figure.raw, matched)
                if own is not None:
                    note += ", and the source gives %s for %d" % (figure.render(own), stated)
                return Finding(kind=MISLABELED, figure=figure, year=stated,
                               matched_year=matched, note=note, **base)
            continue
        else:
            if figure.significant < 2:
                continue
            matched = max(years)
        latest = series.latest
        if latest > matched and not figure.matches(series.values[latest]):
            # "Dropped to 3.3% in 1986" is true forever. Only a figure that
            # presents itself as the current value is made stale by a newer
            # year: an infobox row, a sentence with no year, or one that
            # says "as of".
            if (citation.indicator not in DATED_BY_USE
                    and (presents_current or stated is None)):
                return Finding(kind=NEWER, figure=figure, year=stated, matched_year=matched,
                               note="%s is the %d value; the source has %d: %s" % (
                                   figure.raw, matched, latest,
                                   figure.render(series.values[latest])), **base)
            return Finding(kind=HISTORICAL, figure=figure, year=stated, matched_year=matched,
                           **base)
        return Finding(kind=CURRENT, figure=figure, year=stated, matched_year=matched, **base)
    # Nothing matched any year. Only when the claim states a year the source
    # also has, gives an exact figure rather than a bound or an estimate, and
    # the figure is the same order of size as the source's value for it but
    # at least 2% away, is that a disagreement worth an editor's time rather
    # than a figure from somewhere else or a revision too small to matter.
    for figure in ordered:
        if figure.bound or figure.approximate:
            continue
        stated = stated_year(claim, figure)
        if stated in series.values:
            source = series.values[stated]
            if (source and 0.5 <= figure.value / source <= 2.0
                    and relative(source, figure.value) >= DIFFERS_AT_LEAST):
                return Finding(kind=DIFFERS, figure=figure, year=stated,
                               note="the text gives %s for %d; the source now gives %s" % (
                                   figure.raw, stated, figure.render(source)), **base)
    return Finding(kind=UNMATCHED, **base)


# --------------------------------------------------------------- articles

def raw_url(title):
    return WIKI + "/w/index.php?" + urllib.parse.urlencode({"title": title, "action": "raw"})


def check_wikitext(title, wikitext, fetch):
    """Every World Bank citation in one article, judged."""
    findings, cache = [], {}
    for citation in citations(wikitext):
        if not citation.country:
            findings.append(Finding(title, citation, NO_COUNTRY))
            continue
        key, claim, row = claim_before(wikitext, citation.ref_start)
        pair = (citation.indicator, citation.country)
        if pair not in cache:
            try:
                cache[pair] = worldbank_series(fetch, *pair)
            except (OSError, ValueError):
                cache[pair] = None
        if cache[pair] is None:
            findings.append(Finding(title, citation, NO_DATA, claim=claim, key=key))
            continue
        findings.append(judge(title, citation, key, claim, cache[pair], row))
    return findings


def check_article(title, fetch):
    return check_wikitext(title, fetch(raw_url(title)), fetch)


LINK_ROW = re.compile(
    r'<li><a[^>]*class="external[^"]*"[^>]*href="(?P<url>[^"]+)"[^>]*>.*?</a>'
    r' is linked from <a[^>]*title="(?P<title>[^"]+)"', re.S)


def is_article(title):
    prefix = title.split(":", 1)[0] if ":" in title else None
    return prefix not in NON_ARTICLE


def linked_articles(fetch, target="https://data.worldbank.org/indicator", page_size=5000,
                    most=None):
    """Article titles that link to `target`, from Special:LinkSearch, in order."""
    titles, offset = [], 0
    while True:
        query = urllib.parse.urlencode({"title": "Special:LinkSearch", "target": target,
                                        "limit": page_size, "offset": offset})
        rows = LINK_ROW.findall(fetch(WIKI + "/w/index.php?" + query))
        for _url, title in rows:
            title = html.unescape(title)
            if is_article(title) and title not in titles:
                titles.append(title)
        if len(rows) < page_size or (most and len(titles) >= most):
            return titles[:most] if most else titles
        offset += page_size


# --------------------------------------------------------------- reports

HEADINGS = {
    NEWER: "A newer figure is available",
    MISLABELED: "The year does not belong to the figure",
    DIFFERS: "The source now gives a different figure for the stated year",
}


def article_link(title):
    return "[%s](%s/wiki/%s)" % (title, WIKI, urllib.parse.quote(title.replace(" ", "_")))


def markdown(findings, checked, when, unread=()):
    """The report an editor reads: findings first, then what was not checked."""
    counts = {}
    for f in findings:
        counts[f.kind] = counts.get(f.kind, 0) + 1
    out = ["# Figures checked against the World Bank", "",
           "Generated %s by asof %s. %d articles, %d World Bank citations." % (
               when, __version__, checked, len(findings)), "",
           "Each row gives the sentence as it reads now, the figure as written, and "
           "what the cited series says today. **Nothing here has been edited**; "
           "each row is for an editor to judge.", ""]
    for kind in REPORTED:
        rows = [f for f in findings if f.kind == kind]
        out += ["## %s (%d)" % (HEADINGS[kind], len(rows)), ""]
        if not rows:
            out += ["None.", ""]
            continue
        out += ["| Article | Where | As written | What the source says | Series |",
                "| --- | --- | --- | --- | --- |"]
        for f in sorted(rows, key=lambda f: f.article):
            where = f.key or f.claim[-90:]
            out.append("| %s | %s | %s | %s | [%s, %s](%s) (updated %s) |" % tuple(
                str(cell).replace("|", "\\|") for cell in (
                    article_link(f.article), where, f.figure.raw, f.note,
                    f.series.name, f.series.country_name, f.series.url,
                    f.series.updated)))
        out.append("")
    out += ["## Not reported, and why", "",
            "| Outcome | Citations |", "| --- | --- |"]
    for kind, label in ((CURRENT, "The figure matches the latest year"),
                        (HISTORICAL, "The figure is right for the year the sentence gives"),
                        (UNMATCHED, "No figure in the sentence matches any year of the series"),
                        (NO_FIGURE, "No figure in the sentence"),
                        (COMPUTED, "The figure is computed by the page"),
                        (NO_COUNTRY, "The link names no single country"),
                        (NO_DATA, "The World Bank has no data for the link's indicator and country")):
        out.append("| %s | %d |" % (label, counts.get(kind, 0)))
    out += ["", "A citation lands here when the tool cannot say something true about "
            "it. That is most of them, and it is the intended behaviour.", ""]
    if unread:
        out += ["## Articles that could not be read (%d)" % len(unread), "",
                "Their citations were not checked at all, so they are in no count "
                "above. A later run will pick them up.", ""]
        out += ["- %s: %s" % (article_link(title), why) for title, why in unread]
        out.append("")
    return "\n".join(out)


# --------------------------------------------------------------- command line

def print_findings(findings, stream=sys.stdout):
    for f in findings:
        if f.kind in REPORTED:
            stream.write("%-10s %s: %s\n           %s\n" % (
                f.kind.upper(), f.article, f.note, f.claim[-160:]))
        else:
            stream.write("%-10s %s: %s %s\n" % (
                f.kind, f.article, f.citation.indicator, f.citation.country or ""))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version="asof " + __version__)
    parser.add_argument("--cache", default=".asof-cache",
                        help="where fetched pages are kept (default .asof-cache)")
    sub = parser.add_subparsers(dest="command")
    one = sub.add_parser("check", help="check one article")
    one.add_argument("title")
    many = sub.add_parser("scan", help="check the articles that cite the World Bank")
    many.add_argument("--limit", type=int, default=None, help="stop after this many articles")
    many.add_argument("--out", default="report", help="directory for report.md and findings.json")
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2

    fetch = Fetcher(cache_dir=args.cache, log=lambda m: sys.stderr.write(m + "\n"))
    if args.command == "check":
        findings = check_article(args.title, fetch)
        print_findings(findings)
        return 0

    titles = linked_articles(fetch, most=args.limit)
    findings, unread = [], []
    for n, title in enumerate(titles, 1):
        try:
            found = check_article(title, fetch)
        except (OSError, ValueError) as exc:
            # One unreadable page must never end a scan of a thousand.
            why = "HTTP %s" % exc.code if isinstance(exc, urllib.error.HTTPError) else type(exc).__name__
            unread.append((title, why))
            sys.stderr.write("[%d/%d] %s: not read (%s)\n" % (n, len(titles), title, why))
            continue
        findings += found
        reported = sum(1 for f in found if f.kind in REPORTED)
        sys.stderr.write("[%d/%d] %s: %d citations, %d reported\n" % (
            n, len(titles), title, len(found), reported))
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    when = datetime.date.today().isoformat()
    (out / "report.md").write_text(markdown(findings, len(titles) - len(unread), when, unread),
                                   encoding="utf-8")
    (out / "findings.json").write_text(json.dumps(
        [f.as_dict() for f in findings], indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("%d articles read, %d not, %d citations, %d reported -> %s" % (
        len(titles) - len(unread), len(unread), len(findings),
        sum(1 for f in findings if f.kind in REPORTED), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
