# Second accuracy sample, 2026-09-26

Measured after the fixes the first sample (`2026-09-26-accuracy-sample.md`) led to.
40 findings drawn at random (`random.Random(20260927)`) from 262 reported findings in
articles that were not test fixtures, not in the first sample, and not read while
the fixes were being made. Judged by reading each sentence against its series.

**36 right, 4 wrong: 90%.** One of the four (the decimal comma) was fixed after this
measurement, which makes the current rules unmeasured again, and likely a little better.

| # | Kind | Article | Verdict |
| --- | --- | --- | --- |
| 1 | differs | Sudan | Right. |
| 2 | newer | Saudi Arabia | Right. |
| 3 | newer | Balkans | Right. |
| 4 | differs | Economy of Sudan | Right. |
| 5 | differs | Economy of Ecuador | Right. |
| 6 | differs | Economy of Ecuador | Right. |
| 7 | newer | Pahlavi Iran | **Wrong.** Pahlavi Iran is a former state; its 1978 figure is the right one. The former-state rule matches too few titles to catch it. |
| 8 | newer | Telecommunications in Timor-Leste | Right. |
| 9 | newer | Demographics of Albania | Right. |
| 10 | newer | Economy of the Gambia | Right. |
| 11 | differs | Economy of Burkina Faso | Right. |
| 12 | differs | Economy of Ethiopia | Right. |
| 13 | newer | Economy of Chile | Right. |
| 14 | differs | Morocco | Right. |
| 15 | differs | Economy of Ghana | Right. |
| 16 | differs | Iranian Revolution | Right: the source's constant-dollar base has moved; worth an editor's look. |
| 17 | differs | Economy of Bosnia and Herzegovina | Right: the sentence is an old forecast ("should go down to 18.3%"), and the source now has the actual. |
| 18 | differs | Health in Panama | **Wrong.** "14,9 per 1,000" is a decimal comma, read as 14. Fixed after this sample. |
| 19 | differs | Economy of Palestine | Right. |
| 20 | newer | Economy of Belarus | Right. |
| 21 | differs | Economy of Serbia | Right. |
| 22 | newer | Economy of Papua New Guinea | Right. |
| 23 | mislabeled | Romania | Right. |
| 24 | newer | List of Turkish provinces by life expectancy | Right. |
| 25 | differs | Health in Myanmar | Right. |
| 26 | newer | Economy of Armenia | Right. |
| 27 | differs | Climate change in Nicaragua | Right. |
| 28 | differs | Brazil | **Wrong.** "2.1 doctors and 2.5 hospital beds": judged on the beds figure, but the citation is the physicians series. |
| 29 | newer | Kenya | Right. |
| 30 | newer | Economy of Laos | Right. |
| 31 | differs | Economy of Angola | Right. |
| 32 | newer | Economy of Malawi | Right. |
| 33 | differs | Women in Iraq | Right. |
| 34 | newer | Economy of Hungary | Right. |
| 35 | newer | Russian Soviet Federative Socialist Republic | **Wrong.** The Russian SFSR is a former state; "Federative" gets past the former-state rule. |
| 36 | differs | Economy of Singapore | Right. |
| 37 | differs | Morocco | Right. |
| 38 | differs | Economy of Barbados | Right. |
| 39 | newer | Economy of Seychelles | Right. |
| 40 | newer | Education in Saudi Arabia | Right. |
