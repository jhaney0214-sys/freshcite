# freshcite

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
`data.worldbank.org/indicator`, **1,270 articles and 2,730 citations. It
reported 383 findings**: 171 figures with a newer year available, 205 where the
source now gives a different value for the stated year, and 7 where the year
does not belong to the figure. Every article was read. The whole report is in
[`reports/2026-09-26-worldbank.md`](reports/2026-09-26-worldbank.md).

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

**How often it is right.** A random sample of 40 findings, drawn from articles
the rules had not been tuned on, was checked by hand: **37 were right, 3
wrong** (about 92%). The three were three patterns: an age read as a
statistic ("under the age of 15"), a dated sentence whose year sat past a
second figure, and a change "from 12.07 to 10.9" read as a current value.
All three are fixed, and so is a fourth pattern found by reading the report,
a male/female breakdown judged on the wrong figure. One of those fixes also
silenced a correct finding in the sample. **The fixed rules have not been
re-measured on a fresh sample**, so 92% is the measured figure, not the
current one.

Every rule that keeps a finding out of the report came from reading findings
like these, and each has a test built from the real sentence behind it.

## Running it

```bash
python freshcite.py check "Economy of Senegal"            # one article
python freshcite.py scan --limit 200 --out report         # articles citing the World Bank
```

`scan` finds the articles through Special:LinkSearch, checks each, and writes
`report/report.md` for people and `report/findings.json` for anything else.
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
  never out of date.

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
python -m unittest discover -s tests
```

The tests run offline against real captured pages and series in
`tests/fixtures/`. Their licences are noted in `tests/fixtures/README.md`:
Wikipedia text is CC BY-SA 4.0 and World Bank data is CC BY 4.0.
