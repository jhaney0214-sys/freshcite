# Fixtures

Captured on 2026-09-26 from the live sites, so the tests run against what the
sites actually serve, except the three Nepal files (`wikitext/Nepal.wiki` and
the two `NP_` series), captured on 2026-10-09. Nothing in the suite touches
the network.

- `wikitext/` — excerpts of English Wikipedia articles: the lines around each
  World Bank citation. **Text is CC BY-SA 4.0 by Wikipedia contributors**; each
  file names its article, and the article's history names its authors.
- `worldbank/` — World Bank Open Data API responses, one indicator for one
  country per file. **World Bank data is CC BY 4.0**, © The World Bank.
- `linksearch.html` — one page of Special:LinkSearch for
  `https://data.worldbank.org/indicator`, the first 40 links.
