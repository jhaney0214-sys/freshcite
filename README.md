# freshcite

[![numbers checked by docclaims](https://github.com/jhaney0214-sys/freshcite/actions/workflows/docclaims.yml/badge.svg)](https://github.com/jhaney0214-sys/docclaims)

**Wikipedia figures checked against the dataset their citation names.**

A Wikipedia sentence that cites

```
https://data.worldbank.org/indicator/SP.POP.TOTL?locations=KE
```

has already said, in a form a program can read, which series and which country
its number came from. `freshcite` reads the link, fetches that series from the World
Bank, finds the year the figure belongs to, and reports two things:

- **a newer figure is available**: the sentence gives the 2014 value and the
  source now has 2024;
- **the year does not belong to the figure**, or **the source now gives a
  different figure for the stated year**: the sentence says "(2018)" beside the
  2016 value, or the series has been revised since the sentence was written.

It never edits Wikipedia. Every finding carries the sentence, the figure as
written, the source's value written the same way, and links to both, so an
editor can decide in one look.

## What it found

**The first full scan, 2026-09-26:** every English Wikipedia article linking to
`data.worldbank.org/indicator`, **1,270 articles and 2,730 citations. With
the current rules it reports 358 findings in 206 articles**: 155 figures with
a newer year available, 196 where the source now gives a different value for
the stated year, and 7 where the year does not belong to the figure. (The first
run of the day reported 383; the difference is the fixes described below.)
Every article was read. The whole report is in
[`reports/2026-09-26-worldbank.md`](reports/2026-09-26-worldbank.md), the same
findings as a page for a Wikipedia userspace in
[`reports/2026-09-26-worldbank.wiki`](reports/2026-09-26-worldbank.wiki), and
every field of every citation in
[`reports/2026-09-26-worldbank.json`](reports/2026-09-26-worldbank.json).

| Article | As written | What the World Bank says now |
| --- | --- | --- |
| Colombia and the World Bank | extreme poverty "16.5 percent in 1996" | 24.8% for 1996, after the poverty line was revised |
| Economy of Laos | "15.7% on less than $3.00/day (2018)" | 7.1% in 2024 |
| Economy of Ethiopia | "78% employment rate (2023)" | 66% for 2023 |
| Liberia | life expectancy "64.4 years in 2020" | 61.3 for 2020 |
| Bangladesh | maternal mortality "123 per 100,000" as of 2020 | 152 for 2020 |
| Economy of Romania | agriculture "about 4.3% of GDP" | the 2019 value; 3.0% in 2025 |
| Economy of Moldova | poverty rate "26.8% (2020)" | 31.6% in 2023 |
| Jamaica and the World Bank | GNI per capita "$4,990 (2018)" | that is the 2016 value; 2018 was 5,610 |

**How often it is right.** Measured four times on 2026-09-26 and 27, each time on 40
findings drawn at random from articles that were not test fixtures and had not
been read while the rules were written:

| Sample | Rules | Right |
| --- | --- | --- |
| [first](reports/2026-09-26-accuracy-sample.md) | before this round of fixes | 33 of 40, 82.5% |
| [second](reports/2026-09-26-accuracy-sample-2.md) | after them, on unseen articles | **36 of 40, 90%** |
| [third](reports/2026-09-26-accuracy-sample-3.md) | after the second sample's fixes, on unseen articles | **36 of 40, 90%** |
| [fourth](reports/2026-09-27-accuracy-sample-4.md) | after the third sample's fixes, on unseen articles | **34 of 40, 85%** |

The first sample's seven errors fell into six patterns, and each now has a rule
and a test built from the real sentence. Re-scanning showed two of those rules
over-reaching, which were fixed before the second sample was drawn: a sex
breakdown must be kept when the citation is itself a series for one sex, and
"about" only reads as current when no year is stated. The second sample's four
errors are two former states the title rule did not recognise (Pahlavi Iran,
the Russian SFSR), a decimal comma ("14,9"), and a sentence giving two
statistics where the one nearest the citation is not the one it cites. All four
are fixed since: former states are now read from the article's infobox, and
two figures that each say what they count are judged by which one names the
series. Re-scanning with those fixes removed exactly the five rows they were
meant to (the two former states and the National Reorganization Process, whose
infobox also ends) and changed nothing else.

The third sample's four errors were two patterns, both about which year a
figure is given. In "21.2 per 1000 in 2019" the denominator was read as a
figure standing between 21.2 and its year; and in "As of 2018 ... was 125.094,
... comparing to 2010 when it was at 147.104", 2010 was given to the 2018
figure. Both are fixed. Re-scanning corrected all four and reported five more
true figures the denominator had hidden, 364 in all, and changed nothing else.
The fourth sample found five more patterns, each a figure that belongs to
something other than the cited series: a decade read as a year ("since the
1960s"), a bare "30% female" judged against the total, a figure "in Indonesia"
judged against the Philippines, a figure followed by a census citation, and a
figure in euros or of GNI judged against a dollar or GDP series. All are fixed;
re-scanning changed eight rows and left 358.

**Measured: 90%, 90% and 85% on the last three samples.** The latest fixes came
after the last of them, so the current rules are unmeasured; quote 85–90%.

Every rule that keeps a finding out of the report came from reading findings
like these, and each has a test built from the real sentence behind it.

## Running it

```bash
python freshcite.py check "Economy of Senegal"            # one article
python freshcite.py scan --limit 200 --out report         # articles citing the World Bank
```

`scan` finds the articles through Special:LinkSearch, checks each, and writes
`report/report.md` for people, `report/report.wiki` for a Wikipedia
userspace, and `report/findings.json` for anything else.
`python freshcite.py wiki findings.json --articles N --date YYYY-MM-DD` makes
the page again from an earlier scan, and `python tools/findings.py
findings.json --articles N` prints the summary figures a written piece quotes.
One file, standard library only, Python 3.8 or later. MIT licensed.

## When it says nothing

Most citations produce no finding, and that is deliberate. A checker that is
sometimes wrong is noise an editor learns to skip. **It stays silent, and counts
the citation in the report's last table, when:**

- the link names no country, or several (`locations=HU-RO-BG`): it cannot tell
  which figure the sentence took;
- no number near the citation matches any year of the series: the sentence
  converts a film's box office with an exchange rate, say, or quotes a figure
  from somewhere else;
- the World Bank has no data for the link's indicator and country;
- the figure is the latest year's, or the sentence already states the
  latest value;
- the sentence is prose about a past year ("dropped to 3.3% in 1986"), a
  change over a period ("from 12.07 to 10.9"), an average over a span of
  years, or a "respectively" list: all true of their period, or impossible
  to pin to one year;
- the figure is a bound ("exceeded 7%"), an age, a computed conversion
  (`#expr`), or an exchange rate, which converts an amount at a date and is
  never out of date, nor comparable with a year's average;
- the figure is one sex's ("77.7 for females") and the citation is the total,
  or the other sex's; or it is written with a decimal comma ("14,9");
- the article is about a state that no longer exists (a Soviet Socialist
  Republic, or a title with a year span such as "(1991–1995)"), whose figures
  the modern country's latest value does not make stale;
- the row is one year of a year-by-year table;
- the figure says "about" and the latest value is within 5% of it.

**How a figure is matched.** A number written as "42.4" matches anything that
rounds to it, so ±0.05; "57,532,493" must match exactly. The number nearest the
citation is judged first, because a sentence giving two statistics usually
cites the second. The year a figure belongs to is the first year after it
("42.4% (2015)") unless another figure stands between them, and otherwise the
nearest year before it ("In 2016, … 68.6 deaths").

**"Differs" is reported only** when the sentence states a year the series has,
and the figure is within a factor of two of the source's value for that year.
That keeps a poverty line of "$8.30 a day" from being read as a revision of a
16% poverty rate.

## What it does not do yet

- **World Bank only.** Census QuickFacts is next and the larger source: 11,299
  links from 5,983 articles, against 3,378 from 1,776 for the World Bank, counted
  2026-09-26.
- **Most citations cannot be checked, and it says so.** Of the 2,730 in the
  first scan, 984 link to no single country and 410 have no figure beside
  them. The report's last table counts each reason.
- **A named reference reused elsewhere** (`<ref name="x"/>`) is checked only
  where it is defined, since that is the only place the link appears.
- **A link without `locations=`** is skipped, even when the article's subject
  makes the country obvious. Guessing it would be right most of the time, and
  "most of the time" is the standard this tool exists to refuse.
- **Modelled series are revised every year.** A labour-force figure that was
  exactly right when written can stop matching any year. It lands in "differs"
  or in the silent count, never in "newer".

## Being a polite client

It sends a descriptive User-Agent, waits two seconds between requests to
Wikipedia and honours `Retry-After` on HTTP 429. It reads wikitext through
`index.php?action=raw` and keeps a day's cache on disk (`--cache`). Wikimedia
throttles some shared cloud addresses at the API, and this route kept working
when `api.php` did not.

## Development

```bash
python -m unittest discover -s tests       # 92 tests
docclaims verify . --scan "*.md" "reports/*.wiki"  # every number in this README
```

Every count this README states is pinned in `claims.json` and checked by
[docclaims](https://github.com/jhaney0214-sys/docclaims) on each push; the badge
at the top is that check. The tests run offline against real captured pages and series in
`tests/fixtures/`. Their licences are noted in `tests/fixtures/README.md`:
Wikipedia text is CC BY-SA 4.0 and World Bank data is CC BY 4.0.
