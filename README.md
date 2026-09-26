# asof

**Wikipedia figures checked against the dataset their citation names.**

A Wikipedia sentence that cites

```
https://data.worldbank.org/indicator/SP.POP.TOTL?locations=KE
```

has already said, in a form a program can read, which series and which country
its number came from. `asof` reads the link, fetches that series from the World
Bank, finds the year the figure belongs to, and reports two things:

- **a newer figure is available**: the sentence gives the 2014 value and the
  source now has 2024;
- **the year does not belong to the figure**, or **the source now gives a
  different figure for the stated year**: the sentence says "(2018)" beside the
  2016 value, or the series has been revised since the sentence was written.

It never edits Wikipedia. Every finding carries the sentence, the figure as
written, the source's value written the same way, and links to both, so an
editor can decide in one look.

## What it found on its first test

Forty randomly chosen World Bank citations, checked by hand after the tool
flagged them (34 were in articles; the other six were talk pages and user
sandboxes, which it now skips):

| Article | As written | What the World Bank says |
| --- | --- | --- |
| Economy of Romania | agriculture "about 4.3% of GDP" | that is the 2019 value; 2025 is 3.0% |
| Economy of Senegal | "42.4% employment rate (2015)" | 2024 is 42.0% |
| Economy of Tanzania | "82.2% employment rate (2014)" | 2024 is 83.2% |
| Economy of the Democratic Republic of the Congo | Gini "42.1 (2012)" | 2020 is 44.7 |
| Jamaica and the World Bank | GNI per capita "$4,990 (2018)" | that is the 2016 value; 2018 was 5,610 |
| Economy of Kosovo | Gini "29.0 (2017)" | that is the 2012 value; 2017 was 44.2 |

Every one of the six was a real finding, and nothing it reported was wrong. That
is six of 34 articles, which is a small sample; a full scan is in progress.

## Running it

```bash
python asof.py check "Economy of Senegal"            # one article
python asof.py scan --limit 200 --out report         # articles citing the World Bank
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
- the figure is the latest year's.

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
