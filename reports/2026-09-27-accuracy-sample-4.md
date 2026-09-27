# Fourth accuracy sample, 2026-09-27

Measured on the rules that produced the 364-finding report, after the third sample's fixes.
40 findings drawn at random (`random.Random(20260929)`) from the 118 reported findings in
articles that were not test fixtures and not in any earlier sample. Judged by reading each
sentence against its series.

**34 right, 6 wrong: 85%**, below the second and third samples' 90%. The six are five new
patterns, each now a rule with a test built from the real sentence. A re-scan from the same
cached pages changed eight rows: the six, plus Pakistan's GNI sentence (a GDP series; now
silent) and the Iranian Revolution's "GDP per capita" sentence citing a GNI series (now silent;
the second sample had called it right for another reason). Two of the six are now reported
correctly rather than silenced. **358 findings**, and the current rules unmeasured again.

| # | Kind | Article | Verdict |
| --- | --- | --- | --- |
| 1 | differs | Health in Syria | Right. |
| 2 | differs | Economy of Cyprus | Right. |
| 3 | differs | Colombia | Right. |
| 4 | newer | Education in Peru | Right. |
| 5 | differs | Demographics of Ethiopia | Right. |
| 6 | differs | Gross national income in the European Union | **Wrong.** "EUR 44,778 per inhabitant" is a Eurostat figure in euros, judged against a series in PPP dollars. Fixed after this sample: a figure in another currency is not judged against a dollar series. |
| 7 | newer | Economy of Greenland | Right, and trivial: five people between 2024 and 2025. |
| 8 | newer | People's Bank of China | Right. |
| 9 | newer | Economy of Estonia | Right. |
| 10 | differs | Women in Namibia | Right. |
| 11 | differs | Phantom aid in Afghanistan | Right: a 2% revision, at the reporting threshold. |
| 12 | differs | Albania | **Wrong.** "65% in 2023" is cited to Albania's census (an sfn sits between the figure and the World Bank link). Fixed: a figure followed by another citation belongs to that source. |
| 13 | newer | Vietnamese two-child policy | Right. |
| 14 | differs | Colombia and the World Bank | Right: the sentence says constant 2010 dollars and the series is now constant 2015, which an editor should update. |
| 15 | differs | Demographics of Cambodia | Right. |
| 16 | newer | Economy of Kuwait | Right. |
| 17 | differs | Health in Norway | **Wrong.** The sentence gives *gross national income* per capita; the cited series is GDP per capita. Fixed: a claim naming GNI is not judged against a GDP series, or the reverse. |
| 18 | newer | Africa | Right. |
| 19 | newer | Economy of Bhutan | Right. |
| 20 | differs | Poverty in the Philippines | **Wrong.** "4,291.8 in Indonesia" was judged against the Philippines series. Fixed: in a sentence with several figures, one followed by another named place is not judged. |
| 21 | differs | Puerto Rico | Right. |
| 22 | differs | Obesity in the Pacific | **Wrong.** "since the 1960s" was read as the year 1960. Fixed: a decade is not a year. (The re-scan now reports it correctly as newer: 71 then, 73 in 2024.) |
| 23 | differs | Armed Forces of the Argentine Republic | Right. |
| 24 | differs | Georgia (country) | Right. |
| 25 | newer | Sudan Memory | Right. |
| 26 | differs | Mali | Right. |
| 27 | newer | Economy of Venezuela | Right. |
| 28 | newer | List of companies of Iraq | Right. |
| 29 | differs | Colombia and the World Bank | Right: the sentence gives the old $1.90 line and the cited indicator is now the $3.00 line. |
| 30 | differs | Economy of Guatemala | Right. |
| 31 | differs | Bosnia and Herzegovina | Right. |
| 32 | differs | Economy of Rwanda | Right. |
| 33 | differs | Economy of Azerbaijan | Right. |
| 34 | differs | Economy of Macau | Right. |
| 35 | newer | Economy of Bahrain | Right. |
| 36 | differs | Women in Syria | Right. |
| 37 | differs | Oman | Right. |
| 38 | differs | Demographics of Cambodia | Right. |
| 39 | differs | Niger | **Wrong.** "30% female" was judged against the total series; the sex filter needed "for females". Fixed: a bare sex word labels the figure. (The re-scan now judges the 38% total instead.) |
| 40 | differs | Healthcare in Madagascar | Right. |
