"""Tests for asof, against real pages and real series.

`fixtures/wikitext/` holds excerpts of English Wikipedia articles, and
`fixtures/worldbank/` the World Bank series their citations name, both captured
on 2026-09-26. `fixtures/linksearch.html` is a Special:LinkSearch page from the
same day. Testing against what the sites actually serve, rather than against
markup written to suit the parser, is what caught the `archive-url` duplicate
and the infobox row shape before either reached a report.

Nothing here touches the network.
"""

import io
import json
import pathlib
import re
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import asof  # noqa: E402

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"


def offline(url):
    """A fetch that answers World Bank URLs from the fixtures, like the API."""
    match = re.search(r"/country/([^/]+)/indicator/([^?]+)\?", url)
    if match:
        path = FIX / "worldbank" / ("%s_%s.json" % (
            urllib.parse.unquote(match.group(1)), urllib.parse.unquote(match.group(2))))
        if path.exists():
            return path.read_text(encoding="utf-8")
        return '[{"message":[{"id":"120","key":"Invalid value"}]}]'
    raise AssertionError("a test tried to fetch %s" % url)


def wikitext(name):
    return (FIX / "wikitext" / (name + ".wiki")).read_text(encoding="utf-8")


def reported(title, name=None):
    found = asof.check_wikitext(title, wikitext(name or title.replace(" ", "_")), offline)
    return [f for f in found if f.kind in asof.REPORTED]


def series(values, indicator="SI.POV.GINI", country="XX"):
    return asof.Series(indicator, country, values, "Gini index", "Somewhere", "2026-07-13")


def cite(indicator="SI.POV.GINI", country="XX"):
    return asof.Citation(0, "https://data.worldbank.org/indicator/%s?locations=%s"
                         % (indicator, country), indicator, country)


class TheRealArticles(unittest.TestCase):
    """The eight findings the 2026-09-26 probe and its follow-up produced,
    each checked by hand against the series before it became a test."""

    def one(self, title, name=None):
        found = reported(title, name)
        self.assertEqual(len(found), 1, [f.as_dict() for f in found])
        return found[0]

    def test_romania_agriculture_share_is_the_2019_figure(self):
        f = self.one("Economy of Romania")
        self.assertEqual((f.kind, f.matched_year, f.series.latest), (asof.NEWER, 2019, 2025))
        self.assertIn("3.0%", f.note)

    def test_senegal_and_tanzania_employment_rates_are_a_decade_old(self):
        senegal, tanzania = self.one("Economy of Senegal"), self.one("Economy of Tanzania")
        self.assertEqual((senegal.kind, senegal.matched_year), (asof.NEWER, 2015))
        self.assertEqual((tanzania.kind, tanzania.matched_year), (asof.NEWER, 2014))

    def test_the_congo_gini_is_from_2012(self):
        f = self.one("Economy of the Democratic Republic of the Congo")
        self.assertEqual((f.kind, f.figure.raw, f.matched_year), (asof.NEWER, "42.1", 2012))

    def test_a_figure_under_the_wrong_year_is_mislabeled_not_stale(self):
        jamaica = self.one("Jamaica and the World Bank")
        self.assertEqual((jamaica.kind, jamaica.year, jamaica.matched_year),
                         (asof.MISLABELED, 2018, 2016))
        self.assertIn("5,610 for 2018", jamaica.note)
        kosovo = self.one("Economy of Kosovo")
        self.assertEqual((kosovo.kind, kosovo.year, kosovo.matched_year),
                         (asof.MISLABELED, 2017, 2012))

    def test_a_revised_value_for_the_stated_year_differs(self):
        bermuda = self.one("Economy of Bermuda")
        self.assertEqual((bermuda.kind, bermuda.figure.raw, bermuda.year),
                         (asof.DIFFERS, "-6.8%", 2020))
        self.assertIn("-7.0%", bermuda.note)
        paraguay = self.one("Economy of Paraguay")
        self.assertEqual((paraguay.kind, paraguay.year), (asof.DIFFERS, 2023))

    def test_an_exchange_rate_used_to_convert_a_gross_is_left_alone(self):
        """Film articles cite the rate to convert box office; there is no
        statistic in the sentence to check, and nothing may be reported."""
        self.assertEqual(reported("Super Mario Bros. (film)", "Super_Mario_Bros_film"), [])

    def test_every_archive_copy_is_ignored(self):
        text = wikitext("Economy_of_Romania")
        self.assertGreater(text.count("web.archive.org"), 0)
        urls = [c.url for c in asof.citations(text)]
        self.assertFalse([u for u in urls if "archive.org" in u])
        self.assertEqual(len(urls), len(set((c.ref_start for c in asof.citations(text)))))


class Links(unittest.TestCase):

    def test_one_place_is_checkable(self):
        self.assertEqual(asof.parse_url(
            "https://data.worldbank.org/indicator/SL.EMP.TOTL.SP.NE.ZS?locations=SN&name_desc=false"),
            ("SL.EMP.TOTL.SP.NE.ZS", "SN"))

    def test_several_places_or_none_are_not(self):
        self.assertEqual(asof.parse_url(
            "https://data.worldbank.org/indicator/NY.GDP.PCAP.CD?locations=HU-RO-BG"),
            ("NY.GDP.PCAP.CD", None))
        self.assertEqual(asof.parse_url(
            "https://data.worldbank.org/indicator/NY.GDP.PCAP.KD.ZG"), ("NY.GDP.PCAP.KD.ZG", None))

    def test_case_and_escaped_ampersands(self):
        self.assertEqual(asof.parse_url(
            "https://data.worldbank.org/indicator/sp.pop.totl?end=2020&amp;locations=ke"),
            ("SP.POP.TOTL", "KE"))

    def test_a_ref_without_a_worldbank_link_is_no_citation(self):
        self.assertEqual(asof.citations("x<ref>{{cite web|url=https://example.org}}</ref>"), [])

    def test_a_reused_named_ref_is_not_counted_twice(self):
        text = ('A 5%<ref name="a">https://data.worldbank.org/indicator/X.Y?locations=KE</ref>'
                ' and again<ref name="a"/>.')
        self.assertEqual(len(asof.citations(text)), 1)


class Claims(unittest.TestCase):

    def test_an_infobox_row_keeps_its_key(self):
        text = "| gini = {{decrease}} 42.1 {{color|red|x}} (2012)<ref>"
        key, claim = asof.claim_before(text, text.index("<ref>"))
        self.assertEqual(key, "gini")
        self.assertIn("42.1", claim)
        self.assertIn("2012", claim)

    def test_the_claim_is_the_last_sentence_before_the_ref(self):
        text = ("Growth was 3% in 1999. Agriculture contributes about 4.3% of GDP."
                "<ref>x</ref>")
        _, claim = asof.claim_before(text, text.index("<ref>"))
        self.assertEqual(claim, "Agriculture contributes about 4.3% of GDP")

    def test_the_claim_starts_after_an_earlier_ref(self):
        text = "First 10%.<ref>a</ref> Second 20%<ref>b</ref>"
        _, claim = asof.claim_before(text, text.rindex("<ref>"))
        self.assertEqual(claim, "Second 20%")

    def test_flatten_keeps_what_a_reader_sees(self):
        self.assertEqual(asof.flatten("[[World Bank|the Bank]] gave {{US$|4,990}}&nbsp;(2018)"),
                         "the Bank gave US$ 4,990 (2018)")


class Figures(unittest.TestCase):

    def raws(self, text):
        return [f.raw for f in asof.figures(text)]

    def test_minus_signs_both_kinds(self):
        self.assertEqual([f.value for f in asof.figures("fell -6.8% and −2.5%")],
                         [-6.8, -2.5])

    def test_a_date_range_is_not_a_negative_number(self):
        self.assertEqual(self.raws("in 2019–2020 it rose"), [])

    def test_years_are_dates_not_figures(self):
        self.assertEqual(self.raws("as of 2023, 18,384,660 people"), ["18,384,660"])

    def test_scale_words_and_currency(self):
        found = asof.figures("$2.28 trillion and 57.5 million people and 38 per cent")
        self.assertEqual([f.value for f in found], [2.28e12, 57.5e6, 38.0])
        self.assertEqual(found[2].unit, "%")

    def test_tolerance_is_half_the_last_written_digit(self):
        figure = asof.figures("42.4%")[0]
        self.assertTrue(figure.matches(42.449))
        self.assertTrue(figure.matches(42.35))
        self.assertFalse(figure.matches(42.46))
        exact = asof.figures("57,532,493")[0]
        self.assertTrue(exact.matches(57532493))
        self.assertFalse(exact.matches(57532494))

    def test_a_value_is_rendered_the_way_the_text_writes_it(self):
        self.assertEqual(asof.figures("57.5 million")[0].render(58140000), "58.1 million")
        self.assertEqual(asof.figures("$4,990")[0].render(5610), "5,610")
        self.assertEqual(asof.figures("42.4%")[0].render(41.986), "42.0%")

    def test_the_stated_year_follows_the_figure(self):
        text = "In 2010 it was 5%, and 42.4% employment rate (2015)"
        figure = asof.figures(text)[-1]
        self.assertEqual(asof.stated_year(text, figure), 2015)

    def test_a_year_past_another_figure_is_that_figures_year(self):
        text = "In 2018 it was 4.5%, rising to 5.0% in 2020"
        first, second = asof.figures(text)
        self.assertEqual((asof.stated_year(text, first), asof.stated_year(text, second)),
                         (2018, 2020))

    def test_a_year_before_the_figure_counts_when_none_follows(self):
        text = "In 2016, unsafe water accounted for 68.6 deaths per 100,000 people"
        self.assertEqual(asof.stated_year(text, asof.figures(text)[0]), 2016)


class Verdicts(unittest.TestCase):

    def judge(self, claim, values):
        return asof.judge("A", cite(), None, claim, series(values))

    def test_newer(self):
        f = self.judge("42.1 (2012)", {2012: 42.1, 2020: 44.7})
        self.assertEqual((f.kind, f.matched_year), (asof.NEWER, 2012))

    def test_a_later_year_with_the_same_value_is_current(self):
        self.assertEqual(self.judge("42.1", {2012: 42.1, 2020: 42.14}).kind, asof.CURRENT)

    def test_current(self):
        self.assertEqual(self.judge("44.7 (2020)", {2012: 42.1, 2020: 44.7}).kind, asof.CURRENT)

    def test_mislabeled(self):
        f = self.judge("29.0 (2017)", {2012: 29.0, 2017: 44.2, 2022: 38.3})
        self.assertEqual((f.kind, f.year, f.matched_year), (asof.MISLABELED, 2017, 2012))

    def test_differs_only_for_a_stated_year_the_source_has(self):
        self.assertEqual(self.judge("44.4 (2023)", {2023: 44.2}).kind, asof.DIFFERS)
        self.assertEqual(self.judge("44.4 (2019)", {2023: 44.2}).kind, asof.UNMATCHED)

    def test_a_figure_of_another_size_is_not_a_disagreement(self):
        """"16% on less than $8.30/day (2023)": neither number is the source's
        value, and 8.30 is a threshold, not a revision of 16."""
        self.assertEqual(self.judge("8.30 a day (2023)", {2023: 44.2}).kind, asof.UNMATCHED)

    def test_the_figure_nearest_the_citation_is_the_one_judged(self):
        claim = "Agriculture employs about 26% and contributes about 4.3% of GDP"
        f = self.judge(claim, {1991: 26.0, 2019: 4.3, 2025: 3.0})
        self.assertEqual((f.figure.raw, f.matched_year), ("4.3%", 2019))

    def test_no_figure(self):
        self.assertEqual(self.judge("the World Bank reports", {2020: 1.0}).kind, asof.NO_FIGURE)

    def test_a_link_with_no_country_is_counted_not_fetched(self):
        text = "5%<ref>https://data.worldbank.org/indicator/NY.GDP.PCAP.KD.ZG</ref>"
        found = asof.check_wikitext("A", text, offline)
        self.assertEqual([f.kind for f in found], [asof.NO_COUNTRY])

    def test_an_indicator_the_api_does_not_have_is_no_data(self):
        text = "5%<ref>https://data.worldbank.org/indicator/NOT.REAL?locations=KE</ref>"
        self.assertEqual([f.kind for f in asof.check_wikitext("A", text, offline)], [asof.NO_DATA])


class TheSource(unittest.TestCase):

    def test_a_real_series_reads_every_year(self):
        s = asof.worldbank_series(offline, "SP.POP.TOTL", "KE")
        self.assertEqual((s.latest, s.values[2025], s.updated), (2025, 57532493.0, "2026-07-13"))
        self.assertEqual((s.name, s.country_name), ("Population, total", "Kenya"))

    def test_pages_are_followed(self):
        pages = {1: [{"page": 1, "pages": 2, "lastupdated": "x"},
                     [{"date": "2020", "value": 1.0, "indicator": {"value": "I"}, "country": {"value": "C"}}]],
                 2: [{"page": 2, "pages": 2, "lastupdated": "x"},
                     [{"date": "2021", "value": 2.0, "indicator": {"value": "I"}, "country": {"value": "C"}}]]}
        fetch = lambda url: json.dumps(pages[int(re.search(r"&page=(\d+)", url).group(1))])
        self.assertEqual(asof.worldbank_series(fetch, "I", "C").values, {2020: 1.0, 2021: 2.0})

    def test_an_empty_answer_is_none(self):
        self.assertIsNone(asof.worldbank_series(lambda u: '[{"page":1,"pages":0},null]', "I", "C"))


class TheArticleList(unittest.TestCase):

    def test_only_articles_are_kept_and_each_once(self):
        html_text = (FIX / "linksearch.html").read_text(encoding="utf-8")
        titles = asof.linked_articles(lambda url: html_text, page_size=5000)
        self.assertIn("Economy of Serbia", titles)
        self.assertEqual(len(titles), len(set(titles)))
        self.assertFalse([t for t in titles if t.split(":")[0] in
                          ("Template", "Talk", "User", "User talk", "Wikipedia", "Wikipedia talk")])
        rows = asof.LINK_ROW.findall(html_text)
        self.assertEqual(len(rows), 40)

    def test_a_full_page_asks_for_the_next(self):
        calls = []
        row = ('<li><a rel="nofollow" class="external free" href="https://data.worldbank.org/'
               'indicator/X">u</a> is linked from <a href="/wiki/%s" title="%s">%s</a></li>')
        def fetch(url):
            offset = int(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["offset"][0])
            calls.append(offset)
            return "".join(row % ((("A%d" % (offset + i),) * 3)) for i in range(2 if offset == 0 else 1))
        self.assertEqual(asof.linked_articles(fetch, page_size=2), ["A0", "A1", "A2"])
        self.assertEqual(calls, [0, 2])


class TheFetcher(unittest.TestCase):

    def test_a_fresh_cache_entry_is_used_without_a_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            fetch = asof.Fetcher(cache_dir=tmp)
            fetch._cache_path("https://x.org/a").parent.mkdir(parents=True, exist_ok=True)
            fetch._cache_path("https://x.org/a").write_text("cached", encoding="utf-8")
            with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")):
                self.assertEqual(fetch("https://x.org/a"), "cached")

    def test_a_429_is_waited_out_and_retried(self):
        answer = mock.MagicMock()
        answer.__enter__.return_value.read.return_value = b"ok"
        refused = urllib.error.HTTPError("u", 429, "Too Many", {"Retry-After": "0"}, io.BytesIO())
        with mock.patch("urllib.request.urlopen", side_effect=[refused, answer]), \
                mock.patch("time.sleep") as sleep:
            self.assertEqual(asof.Fetcher(interval={"x.org": 0})("https://x.org/b"), "ok")
        self.assertIn(mock.call(2), sleep.call_args_list)

    def test_requests_to_one_host_are_spaced_and_the_first_is_not_delayed(self):
        """The pacing is what keeps a scan polite to Wikipedia. Found by
        mutation testing: nothing checked it, and a broken wait passed."""
        answer = mock.MagicMock()
        answer.__enter__.return_value.read.return_value = b"ok"
        clock = iter([100.0, 100.0, 101.5, 101.5, 101.5])
        with mock.patch("urllib.request.urlopen", return_value=answer), \
                mock.patch("time.time", side_effect=lambda: next(clock)), \
                mock.patch("time.sleep") as sleep:
            fetch = asof.Fetcher(interval={"x.org": 2.0})
            fetch("https://x.org/1")
            self.assertEqual(sleep.call_args_list, [])
            fetch("https://x.org/2")
        self.assertEqual(len(sleep.call_args_list), 1)
        self.assertAlmostEqual(sleep.call_args_list[0][0][0], 0.5)

    def test_a_host_that_keeps_refusing_is_given_up_on(self):
        refusals = [urllib.error.HTTPError("u", 429, "Too Many", {"Retry-After": "0"}, io.BytesIO())
                    for _ in range(6)]
        with mock.patch("urllib.request.urlopen", side_effect=refusals) as opened, \
                mock.patch("time.sleep"):
            with self.assertRaises(urllib.error.HTTPError):
                asof.Fetcher(interval={"x.org": 0})("https://x.org/d")
        self.assertEqual(opened.call_count, 6)

    def test_a_missing_cache_directory_is_created(self):
        answer = mock.MagicMock()
        answer.__enter__.return_value.read.return_value = b"fresh"
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("urllib.request.urlopen", return_value=answer):
            fetch = asof.Fetcher(cache_dir=pathlib.Path(tmp) / "a" / "b", interval={"x.org": 0})
            self.assertEqual(fetch("https://x.org/e"), "fresh")
            self.assertEqual(fetch("https://x.org/f"), "fresh")
            self.assertEqual(fetch._cache_path("https://x.org/f").read_text(), "fresh")

    def test_other_errors_are_not_retried(self):
        refused = urllib.error.HTTPError("u", 404, "Not Found", {}, io.BytesIO())
        with mock.patch("urllib.request.urlopen", side_effect=[refused]):
            with self.assertRaises(urllib.error.HTTPError):
                asof.Fetcher(interval={"x.org": 0})("https://x.org/c")


class TheReport(unittest.TestCase):

    def test_findings_come_first_and_the_silence_is_counted(self):
        found = asof.check_wikitext("Economy of Romania", wikitext("Economy_of_Romania"), offline)
        text = asof.markdown(found, 1, "2026-09-26")
        self.assertIn("## A newer figure is available (1)", text)
        self.assertIn("[Economy of Romania](https://en.wikipedia.org/wiki/Economy_of_Romania)", text)
        self.assertLess(text.index("A newer figure"), text.index("Not reported, and why"))
        self.assertIn("| The link names no single country |", text)

    def test_a_pipe_in_a_claim_cannot_break_the_table(self):
        f = asof.judge("A", cite(), None, "a | b 42.1 (2012)", series({2012: 42.1, 2020: 44.7}))
        row = [l for l in asof.markdown([f], 1, "d").splitlines() if l.startswith("| [A]")][0]
        self.assertEqual(row.count(" | "), 4)


if __name__ == "__main__":
    unittest.main()
