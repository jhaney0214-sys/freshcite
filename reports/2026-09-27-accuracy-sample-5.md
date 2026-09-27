# Fifth accuracy sample, 2026-09-27

Measured on the rules that produced the 358-finding report, after the fourth sample's fixes.
40 findings drawn at random (`random.Random(20260930)`) from the 73 reported findings in
articles that were not test fixtures and not in any earlier sample. Judged by reading each
sentence in today's article against its series in the World Bank's API.

**38 right, 2 wrong: 95%**, the best of the five samples. The two are new patterns, each now a
rule with a test built from the real sentence. A full re-scan with the fixes (live pages and
series, 2026-09-27) removed exactly those two rows and changed no other reported row:
**356 findings in 204 articles**. Both removed rows are on the list posted to Wikipedia on
2026-09-27, which was made from the 358-finding scan.

| # | Kind | Article | Verdict |
| --- | --- | --- | --- |
| 1 | differs | Open defecation | Right. |
| 2 | differs | Economy of Afghanistan | Right: Afghanistan's labour force was revised down by a third. |
| 3 | differs | Nicaragua | Right. |
| 4 | newer | Demographics of the world | Right: the sentence gives Niger's rate as the current world high, 6.7; the series has 5.9 for 2024. |
| 5 | differs | Economy of the United Arab Emirates | Right. |
| 6 | differs | Health in Gabon | Right. |
| 7 | differs | Economy of Saint Lucia | Right. |
| 8 | differs | Economy of Iran | Right. |
| 9 | differs | Economy of Somalia | Right. |
| 10 | newer | Women in the United Arab Emirates | Right. |
| 11 | newer | Economy of Argentina | Right. |
| 12 | newer | Energy in Kenya | Right, and small: 76.5% at the end of 2021, 77.0% in 2024. |
| 13 | differs | Japan | Right. |
| 14 | differs | Economy of Somalia | Right. |
| 15 | differs | Cambodia | Right. |
| 16 | differs | Economy of Malta | Right. |
| 17 | newer | Internet in Thailand | Right. |
| 18 | newer | Economy of the United Arab Emirates | Right. |
| 19 | differs | Lesotho | Right. |
| 20 | differs | Economy of Lithuania | Right. |
| 21 | differs | Economy of Georgia (country) | Right. |
| 22 | differs | Telecommunications in Ukraine | Right. |
| 23 | newer | Health in Finland | **Wrong.** "Among males the life expectancy was 79" was judged against the total series, as current. Fixed after this sample: a sex that opens the clause ("among males ... 79") labels its figure, as one beside it already did. |
| 24 | differs | Education in Equatorial Guinea | Right. |
| 25 | newer | Sri Lanka | Right, and trivial: 98.8 against 98.87. |
| 26 | differs | Economy of Nauru | Right. |
| 27 | differs | Liberia | Right. |
| 28 | differs | Economy of Honduras | Right. |
| 29 | differs | Hurricane Norma (2023) | **Wrong.** "285 million pesos (US$16 million)" cites the DEC conversion factor in a footnote; US$16 million is the converted amount, not the factor, and it is right (285 / 17.76). Fixed: a figure cited to any conversion factor is an amount converted at it, as the official exchange rate already was. |
| 30 | newer | Economy of Oman | Right. |
| 31 | differs | Economy of Egypt | Right. |
| 32 | differs | Economy of Pakistan | Right. |
| 33 | differs | Health in Bangladesh | Right. |
| 34 | differs | Education in Benin | Right. |
| 35 | differs | Suicide in Romania | Right. |
| 36 | differs | Netherlands | Right. |
| 37 | differs | Economy of Palau | Right. |
| 38 | differs | Brazilian Americans | Right: the whole 1980s series has been revised; 1985 is now 1,556. |
| 39 | differs | Economy of the United Arab Emirates | Right. |
| 40 | newer | Economy of Georgia (country) | Right. |
