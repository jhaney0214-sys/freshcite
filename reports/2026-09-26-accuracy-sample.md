# Accuracy sample, 2026-09-26

40 findings drawn at random (`random.Random(20260926)`) from the 366 reported findings
in articles that are not test fixtures, out of a scan re-run live on 2026-09-26 whose
report is byte-identical to `2026-09-26-worldbank.md`. Each was judged by reading the
sentence against the series the citation names.

**33 right, 7 wrong: 82.5%.** The 92% measured earlier was on the rules before their
last fixes; this is the first measurement of the current rules.

| # | Kind | Article | Verdict |
| --- | --- | --- | --- |
| 1 | newer | Economy of Kyrgyzstan | Right. |
| 2 | differs | Visa policy of Turkmenistan | Right. |
| 3 | newer | Economy of Moldova | Right. |
| 4 | differs | Economy of Malaysia | **Wrong.** The figure took the year of another clause: 1998 is when the trade surpluses began, and 132% carries no year. |
| 5 | differs | Economy of Niger | Right. |
| 6 | differs | Abortion in Yemen | Right. |
| 7 | newer | Economy of Bolivia | Right. |
| 8 | differs | Women in Egypt | Right. |
| 9 | newer | Demographics of Saudi Arabia | Right. |
| 10 | differs | Economy of Mauritius | Right. |
| 11 | newer | Kerala model | Right. |
| 12 | newer | Economy of Bangladesh | Right. |
| 13 | newer | Economy of the Maldives | Right. |
| 14 | differs | Economy of the Central African Republic | Right. |
| 15 | differs | Economy of Tunisia | Right. |
| 16 | newer | Economy of Tonga | Right. |
| 17 | newer | Aging of China | Right. |
| 18 | newer | Ukrainian Soviet Socialist Republic | **Wrong.** The article is about the Ukrainian SSR. Its 1990 figure is the right one, and the modern country's 2025 value does not apply. |
| 19 | newer | Visa policy of Kazakhstan | **Wrong.** One row of a year-by-year arrivals table. The row is a historical datum, so a newer year is not news. |
| 20 | differs | Health in Lesotho | Right. |
| 21 | differs | Economy of Zimbabwe | Right. |
| 22 | differs | Economy of Russia | Right. |
| 23 | differs | Economy of Jamaica | Right. |
| 24 | newer | Economy of Brunei | Right. |
| 25 | newer | Russia | **Wrong.** "About 72 million" matched the 2001 value by rounding, but the 2025 value, 72.8 million, is also about 72 million. The sentence is current. |
| 26 | differs | Economy of Botswana | Right. |
| 27 | newer | Republic of Belarus (1991–1995) | **Wrong.** The article is about the Republic of Belarus, 1991–1995. Its 1993 figure is the right one. |
| 28 | newer | Economy of Fiji | Right. |
| 29 | differs | Economy of Montenegro | Right. |
| 30 | newer | Economy of Ivory Coast | Right. |
| 31 | differs | Nepal | Right. |
| 32 | differs | Health in Bolivia | Right. |
| 33 | differs | Peru | **Wrong.** 77.7 is the female life expectancy, compared against the total series. The total, 75.0, is in the same sentence. |
| 34 | differs | Economy of Belize | Right. |
| 35 | newer | Economy of Uganda | Right. |
| 36 | differs | Nigeria | Right. |
| 37 | differs | Japanese asset price bubble | **Wrong.** A point-in-time exchange rate ("dropped to 165 yen") compared with an annual average. Exchange rates are meant to be skipped. |
| 38 | differs | Malaysia | Right. |
| 39 | newer | Economy of Costa Rica | Right. |
| 40 | differs | Healthcare in Pakistan | Right, with a note: the text says gross national income and the link points to GDP per capita. The mismatch is itself worth an editor's look. |

## The wrong ones, by cause

- **An article about a historical state** (18, 27). The link names the modern country's code, so the latest value is the modern country's. The scan's own report has two more, both for the Byelorussian SSR.
- **A row of a year-by-year table** (19). Each row is true of its year.
- **A year from another clause** (4).
- **An approximate figure matched by rounding to an old year** (25), when the latest value also rounds to it.
- **A sex breakdown** (33), a pattern a rule was written for; this phrasing gets past it.
- **An exchange rate** (37), which the README says is skipped; this series gets past it.

