"""Tests for freshcite, against real pages and real series.

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
import freshcite  # noqa: E402

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
    found = freshcite.check_wikitext(title, wikitext(name or title.replace(" ", "_")), offline)
    return [f for f in found if f.kind in freshcite.REPORTED]


def series(values, indicator="SI.POV.GINI", country="XX"):
    return freshcite.Series(indicator, country, values, "Gini index", "Somewhere", "2026-07-13")


def cite(indicator="SI.POV.GINI", country="XX"):
    return freshcite.Citation(0, "https://data.worldbank.org/indicator/%s?locations=%s"
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
        self.assertEqual((f.kind, f.matched_year, f.series.latest), (freshcite.NEWER, 2019, 2025))
        self.assertIn("3.0%", f.note)

    def test_senegal_and_tanzania_employment_rates_are_a_decade_old(self):
        senegal, tanzania = self.one("Economy of Senegal"), self.one("Economy of Tanzania")
        self.assertEqual((senegal.kind, senegal.matched_year), (freshcite.NEWER, 2015))
        self.assertEqual((tanzania.kind, tanzania.matched_year), (freshcite.NEWER, 2014))

    def test_the_congo_gini_is_from_2012(self):
        f = self.one("Economy of the Democratic Republic of the Congo")
        self.assertEqual((f.kind, f.figure.raw, f.matched_year), (freshcite.NEWER, "42.1", 2012))

    def test_a_figure_under_the_wrong_year_is_mislabeled_not_stale(self):
        jamaica = self.one("Jamaica and the World Bank")
        self.assertEqual((jamaica.kind, jamaica.year, jamaica.matched_year),
                         (freshcite.MISLABELED, 2018, 2016))
        self.assertIn("5,610 for 2018", jamaica.note)
        kosovo = self.one("Economy of Kosovo")
        self.assertEqual((kosovo.kind, kosovo.year, kosovo.matched_year),
                         (freshcite.MISLABELED, 2017, 2012))

    def test_a_revised_value_for_the_stated_year_differs(self):
        bermuda = self.one("Economy of Bermuda")
        self.assertEqual((bermuda.kind, bermuda.figure.raw, bermuda.year),
                         (freshcite.DIFFERS, "-6.8%", 2020))
        self.assertIn("-7.0%", bermuda.note)
        # Paraguay's Gini "44.4 (2023)" is now 44.2: a 0.45% revision, under
        # the 2% at which a change is worth an editor's time.
        self.assertEqual(reported("Economy of Paraguay"), [])

    def test_an_exchange_rate_used_to_convert_a_gross_is_left_alone(self):
        """Film articles cite the rate to convert box office; there is no
        statistic in the sentence to check, and nothing may be reported."""
        self.assertEqual(reported("Super Mario Bros. (film)", "Super_Mario_Bros_film"), [])

    def test_every_archive_copy_is_ignored(self):
        text = wikitext("Economy_of_Romania")
        self.assertGreater(text.count("web.archive.org"), 0)
        urls = [c.url for c in freshcite.citations(text)]
        self.assertFalse([u for u in urls if "archive.org" in u])
        self.assertEqual(len(urls), len(set((c.ref_start for c in freshcite.citations(text)))))


class Links(unittest.TestCase):

    def test_one_place_is_checkable(self):
        self.assertEqual(freshcite.parse_url(
            "https://data.worldbank.org/indicator/SL.EMP.TOTL.SP.NE.ZS?locations=SN&name_desc=false"),
            ("SL.EMP.TOTL.SP.NE.ZS", "SN"))

    def test_several_places_or_none_are_not(self):
        self.assertEqual(freshcite.parse_url(
            "https://data.worldbank.org/indicator/NY.GDP.PCAP.CD?locations=HU-RO-BG"),
            ("NY.GDP.PCAP.CD", None))
        self.assertEqual(freshcite.parse_url(
            "https://data.worldbank.org/indicator/NY.GDP.PCAP.KD.ZG"), ("NY.GDP.PCAP.KD.ZG", None))

    def test_case_and_escaped_ampersands(self):
        self.assertEqual(freshcite.parse_url(
            "https://data.worldbank.org/indicator/sp.pop.totl?end=2020&amp;locations=ke"),
            ("SP.POP.TOTL", "KE"))

    def test_a_ref_without_a_worldbank_link_is_no_citation(self):
        self.assertEqual(freshcite.citations("x<ref>{{cite web|url=https://example.org}}</ref>"), [])

    def test_a_reused_named_ref_is_not_counted_twice(self):
        text = ('A 5%<ref name="a">https://data.worldbank.org/indicator/X.Y?locations=KE</ref>'
                ' and again<ref name="a"/>.')
        self.assertEqual(len(freshcite.citations(text)), 1)


class Claims(unittest.TestCase):

    def test_an_infobox_row_keeps_its_key(self):
        text = "| gini = {{decrease}} 42.1 {{color|red|x}} (2012)<ref>"
        key, claim, row = freshcite.claim_before(text, text.index("<ref>"))
        self.assertEqual((key, row), ("gini", True))
        self.assertIn("42.1", claim)
        self.assertIn("2012", claim)

    def test_the_claim_is_the_last_sentence_before_the_ref(self):
        text = ("Growth was 3% in 1999. Agriculture contributes about 4.3% of GDP."
                "<ref>x</ref>")
        _, claim, row = freshcite.claim_before(text, text.index("<ref>"))
        self.assertEqual((claim, row), ("Agriculture contributes about 4.3% of GDP", False))

    def test_a_list_item_is_a_row(self):
        text = "*42.4% employment rate (2015)<ref>x</ref>"
        self.assertTrue(freshcite.claim_before(text, text.index("<ref>"))[2])

    def test_the_claim_starts_after_an_earlier_ref(self):
        text = "First 10%.<ref>a</ref> Second 20%<ref>b</ref>"
        _, claim, _ = freshcite.claim_before(text, text.rindex("<ref>"))
        self.assertEqual(claim, "Second 20%")

    def test_flatten_keeps_what_a_reader_sees(self):
        self.assertEqual(freshcite.flatten("[[World Bank|the Bank]] gave {{US$|4,990}}&nbsp;(2018)"),
                         "the Bank gave US$ 4,990 (2018)")


class Figures(unittest.TestCase):

    def raws(self, text):
        return [f.raw for f in freshcite.figures(text)]

    def test_minus_signs_both_kinds(self):
        self.assertEqual([f.value for f in freshcite.figures("fell -6.8% and −2.5%")],
                         [-6.8, -2.5])

    def test_a_date_range_is_not_a_negative_number(self):
        self.assertEqual(self.raws("in 2019–2020 it rose"), [])

    def test_years_are_dates_not_figures(self):
        self.assertEqual(self.raws("as of 2023, 18,384,660 people"), ["18,384,660"])

    def test_scale_words_and_currency(self):
        found = freshcite.figures("$2.28 trillion and 57.5 million people and 38 per cent")
        self.assertEqual([f.value for f in found], [2.28e12, 57.5e6, 38.0])
        self.assertEqual(found[2].unit, "%")

    def test_tolerance_is_half_the_last_written_digit(self):
        figure = freshcite.figures("42.4%")[0]
        self.assertTrue(figure.matches(42.449))
        self.assertTrue(figure.matches(42.35))
        self.assertFalse(figure.matches(42.46))
        exact = freshcite.figures("57,532,493")[0]
        self.assertTrue(exact.matches(57532493))
        self.assertFalse(exact.matches(57532494))

    def test_a_value_is_rendered_the_way_the_text_writes_it(self):
        self.assertEqual(freshcite.figures("57.5 million")[0].render(58140000), "58.1 million")
        self.assertEqual(freshcite.figures("$4,990")[0].render(5610), "5,610")
        self.assertEqual(freshcite.figures("42.4%")[0].render(41.986), "42.0%")

    def test_the_stated_year_follows_the_figure(self):
        text = "In 2010 it was 5%, and 42.4% employment rate (2015)"
        figure = freshcite.figures(text)[-1]
        self.assertEqual(freshcite.stated_year(text, figure), 2015)

    def test_a_year_past_another_figure_is_that_figures_year(self):
        text = "In 2018 it was 4.5%, rising to 5.0% in 2020"
        first, second = freshcite.figures(text)
        self.assertEqual((freshcite.stated_year(text, first), freshcite.stated_year(text, second)),
                         (2018, 2020))

    def test_a_decade_is_not_a_year(self):
        """Fourth 2026-09-27 sample: Tonga's 71 was judged against 1960."""
        text = "Life expectancy in Tonga is 71 and has been steadily rising since the 1960s"
        self.assertIsNone(freshcite.stated_year(text, freshcite.figures(text)[0]))
        self.assertEqual([m.group(1) for m in freshcite.YEAR.finditer("in the 1990's, and in 2016")], ["2016"])

    def test_a_bare_sex_word_labels_the_figure(self):
        """Fourth sample: Niger's "30% female" judged against total literacy."""
        text = "and 38% (46% male and 30% female) according to the World Bank, both as of 2022"
        self.assertEqual([f.raw for f in freshcite.figures(text)], ["38%"])

    def test_a_rates_denominator_does_not_take_the_year(self):
        """Third 2026-09-26 sample: Bolivia's 21.2 was given 2006, not 2019."""
        text = "The infant mortality rate was 40.7 per 1000 in 2006 and was reduced to 21.2 per 1000 in 2019"
        found = freshcite.figures(text)
        self.assertEqual([f.raw for f in found], ["40.7", "21.2"])
        self.assertEqual([freshcite.stated_year(text, f) for f in found], [2006, 2019])

    def test_a_distant_year_beside_another_figure_is_that_figures(self):
        """Third 2026-09-26 sample: Montenegro's 2018 figure was given 2010."""
        text = ("As of 2018, mortality rate for adult males (per 1000 adults) was 125.094, which has "
                "decreased as can be seen through comparing to 2010 when it was at 147.104")
        first, second = freshcite.figures(text)
        self.assertEqual((freshcite.stated_year(text, first), freshcite.stated_year(text, second)),
                         (2018, 2010))
        text = "In 2018 it was 4.5%, rising to 5.0% in 2020"
        self.assertEqual(freshcite.stated_year(text, freshcite.figures(text)[0]), 2018)

    def test_a_year_before_the_figure_counts_when_none_follows(self):
        text = "In 2016, unsafe water accounted for 68.6 deaths per 100,000 people"
        self.assertEqual(freshcite.stated_year(text, freshcite.figures(text)[0]), 2016)


class Verdicts(unittest.TestCase):

    def judge(self, claim, values, row=False, indicator="SI.POV.GINI"):
        return freshcite.judge("A", cite(indicator), None, claim, series(values, indicator), row)

    def test_newer(self):
        f = self.judge("42.1 (2012)", {2012: 42.1, 2020: 44.7}, row=True)
        self.assertEqual((f.kind, f.matched_year), (freshcite.NEWER, 2012))

    def test_a_sentence_about_a_past_year_is_not_made_stale(self):
        """Found in the first scan: "the fertility rate dropped to 2.75" after
        1979, and "growth dropped to 3.3% in 1986", reported as "newer"."""
        f = self.judge("After the one-child policy in 1979, the fertility rate dropped to 2.75",
                       {1979: 2.75, 2024: 1.01})
        self.assertEqual((f.kind, f.matched_year), (freshcite.HISTORICAL, 1979))

    def test_a_sentence_that_says_as_of_is_current_and_can_be_stale(self):
        f = self.judge("As of 2015, 15.6% of GDP", {2015: 15.6, 2024: 17.3})
        self.assertEqual(f.kind, freshcite.NEWER)

    def test_a_sentence_with_no_year_can_be_stale(self):
        f = self.judge("Its youth literacy rate stands at 98.8%", {2022: 98.8, 2024: 98.9})
        self.assertEqual((f.kind, f.matched_year), (freshcite.NEWER, 2022))

    def test_an_exchange_rate_is_never_newer(self):
        """"4.76 Indian rupees per US dollar" converts a 1965 figure at the 1965 rate."""
        f = self.judge("4.76 Indian rupees per US dollar", {1965: 4.762, 2025: 87.158},
                       row=True, indicator="PA.NUS.FCRF")
        self.assertEqual(f.kind, freshcite.HISTORICAL)

    def test_a_computed_figure_is_left_alone(self):
        f = self.judge("INR #expr:(97.2*4.762)/10 round 1 million", {1965: 4.762, 2025: 87.158})
        self.assertEqual(f.kind, freshcite.COMPUTED)

    def test_a_bound_is_not_a_value(self):
        """"exceeded 7% every year from 2003" matched a 2024 value of 7."""
        f = self.judge("GDP growth exceeded 7% every year from 2003 to 2007",
                       {2003: 7.9, 2024: 7.0})
        self.assertEqual(f.kind, freshcite.UNMATCHED)

    def test_a_low_precision_figure_is_not_matched_to_another_year(self):
        """"1.6% (1987)" matched Switzerland's 2001 value."""
        f = self.judge("growth decreased to 1.6% in 1987", {1987: 3.4, 2001: 1.6})
        self.assertNotEqual(f.kind, freshcite.MISLABELED)

    def test_a_figure_close_to_its_own_year_is_a_revision_not_a_mislabel(self):
        """"57.4% employment rate (2016)": the 2016 value is now 57.1, and 57.4
        happens to be the 2000 value."""
        f = self.judge("57.4% employment rate (2016)", {2000: 57.4, 2016: 57.1}, row=True)
        self.assertNotEqual(f.kind, freshcite.MISLABELED)

    def test_figures_paired_with_years_by_order_are_not_read(self):
        f = self.judge("apart from 1986 and 1987 when growth decreased to 1.9% and 1.6% respectively",
                       {1986: 1.9, 1987: 3.4})
        self.assertEqual(f.kind, freshcite.UNMATCHED)

    def test_a_figure_over_a_span_of_years_is_not_read(self):
        """Two of twenty in a fresh sample: an average over 2004-2014 was
        compared with the 2004 value."""
        for claim in ("This growth rate was maintained, averaging 4.8% from 2004 to 2014",
                      "growth averaging 9.1% between 2007 and 2010",
                      "4.8% a year in 2004\u20132014"):
            self.assertEqual(self.judge(claim, {2004: 5.3, 2007: 9.3}).kind, freshcite.UNMATCHED, claim)

    def test_one_year_in_a_list_is_not_a_span(self):
        f = self.judge("output declining 0.9% in 2020 and rebounding 7.5% in 2021", {2021: 7.9})
        self.assertEqual(f.kind, freshcite.DIFFERS)

    def test_a_sentence_that_states_the_latest_value_is_current(self):
        """Full report: the male figure in a breakdown matched an old total."""
        f = self.judge("Australia's life expectancy of 83 years (81 years for males and 85 years for females)",
                       {2008: 81.0, 2024: 83.0}, indicator="SP.DYN.LE00.IN")
        self.assertEqual((f.kind, f.figure.raw), (freshcite.CURRENT, "83"))

    def test_a_breakdown_by_sex_is_not_the_total(self):
        """2026-09-26 sample: Peru's female 77.7 was judged against the total."""
        claim = ("Peru has a life expectancy of 75.0 years (72.4 for males and 77.7 for "
                 "females) according to the latest data for the year 2016 from the World Bank")
        self.assertEqual([f.raw for f in freshcite.figures(claim)], ["75.0"])
        f = self.judge(claim, {2016: 76.0, 2024: 77.9}, indicator="SP.DYN.LE00.IN")
        self.assertNotIn(f.kind, freshcite.REPORTED)

    def test_in_the_case_of_males_is_a_breakdown_too(self):
        """Re-scan: Benin's "67.1 percent in the case of males" against the total."""
        claim = ("from 21.8 percent in 2000 to 59 percent in 2016, 67.1 percent in the "
                 "case of males and 50.7 percent for females")
        self.assertEqual([f.raw for f in freshcite.figures(claim)],
                         ["21.8 percent", "59 percent"])

    def test_a_series_for_one_sex_keeps_the_breakdown(self):
        """Re-scan: Japan cites the male series, so "82 years for men" is the figure."""
        claim = ("In 2020, the overall life expectancy in Japan at birth was 85 years "
                 "(82 years for men and 88 years for women)")
        f = freshcite.judge("Japan", cite("SP.DYN.LE00.MA.IN", "JP"), None, claim,
                            series({2020: 81.6, 2023: 81.1}, "SP.DYN.LE00.MA.IN", "JP"))
        self.assertNotEqual(f.kind, freshcite.DIFFERS)

    def test_a_series_for_one_sex_ignores_the_other(self):
        """Re-scan: Micronesia cites the male series; 69 is the women's figure."""
        claim = "Life expectancy was 66 for men and 69 for women in 2018"
        self.assertEqual([f.raw for f in freshcite.figures(claim, by_sex="MA")], ["66"])
        f = freshcite.judge("FSM", cite("SP.DYN.LE00.MA.IN", "FM"), None, claim,
                            series({2018: 63.0, 2023: 64.0}, "SP.DYN.LE00.MA.IN", "FM"))
        self.assertNotEqual(f.figure.raw if f.figure else None, "69")

    def test_a_decimal_comma_is_not_read_as_an_integer(self):
        """Second 2026-09-26 sample: Panama's "14,9 per 1,000" was read as 14."""
        claim = "the under-five mortality rate was 14,9 per 1,000 live births"
        # Nothing: the 14,9 is skipped, and "per 1,000" is a denominator.
        self.assertEqual([f.raw for f in freshcite.figures(claim)], [])
        self.assertEqual([f.raw for f in freshcite.figures("12,345 people")], ["12,345"])

    def test_since_dates_another_clause(self):
        """2026-09-26 sample: 1998 is when Malaysia's surpluses began."""
        claim = ("total trade activities at 132% of its GDP, while recording "
                 "consistent trade surpluses since 1998")
        self.assertIsNone(freshcite.stated_year(claim, freshcite.figures(claim)[0]))
        self.assertEqual(freshcite.stated_year("3% in 2019, since 2010", freshcite.figures("3% in 2019, since 2010")[0]), 2019)

    def test_an_approximate_figure_near_the_latest_is_current(self):
        """2026-09-26 sample: "about 72 million" matched 2001; 2025 is 72.8M."""
        f = self.judge("It has a labour force of about 72 million", {2001: 72.1e6, 2025: 72.77e6},
                       indicator="SL.TLF.TOTL.IN")
        self.assertEqual(f.kind, freshcite.CURRENT)
        f = self.judge("It has a labour force of 72 million", {2001: 72.1e6, 2025: 72.77e6},
                       indicator="SL.TLF.TOTL.IN")
        self.assertEqual(f.kind, freshcite.NEWER, "without 'about' the precision stands")

    def test_about_with_a_stated_year_is_still_that_years(self):
        """Re-scan: "In 2021, about 23.4%" is a 2021 claim, not a current one."""
        f = self.judge("In 2021, about 23.4% of Nigeria's GDP was agriculture",
                       {1988: 23.4, 2021: 29.4, 2025: 23.5}, indicator="NV.AGR.TOTL.ZS")
        self.assertNotEqual(f.kind, freshcite.CURRENT)

    def test_a_row_keyed_by_its_year_is_that_years(self):
        """2026-09-26 sample: one row of Kazakhstan's arrivals-by-year table."""
        f = self.judge('"text-align:center;" 1996 increase 202,000', {1996: 202000.0, 2020: 2035000.0},
                       row=True, indicator="ST.INT.ARVL")
        self.assertEqual(f.kind, freshcite.HISTORICAL)
        f = self.judge("center 1995 increase 218,000", {1995: 233000.0, 1998: 380000.0},
                       row=True, indicator="ST.INT.ARVL")
        self.assertEqual(f.kind, freshcite.DIFFERS, "a revised year is still worth reporting")

    def test_a_former_state_is_not_held_to_the_modern_country(self):
        """2026-09-26 sample: the Ukrainian SSR's 1990 GDP reported as "newer"."""
        for title in ("Ukrainian Soviet Socialist Republic", "Republic of Belarus (1991\u20131995)"):
            f = freshcite.judge(title, cite("NY.GDP.MKTP.PP.CD"), "GDP_PPP", "~$395.12 billion",
                                series({1990: 395.12e9, 2025: 690.4e9}, "NY.GDP.MKTP.PP.CD"), True)
            self.assertEqual(f.kind, freshcite.HISTORICAL, title)

    def test_a_former_state_is_known_by_its_infobox(self):
        """Second 2026-09-26 sample: Pahlavi Iran and the Russian SFSR, missed by the title rule."""
        wikitext = ("{{Infobox former country\n| year_end = 1979\n| GDP_nominal = $77.99 billion"
                    "<ref>{{cite web |url=https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations=IR}}</ref>\n}}")
        values = {1978: 77.99e9, 2025: 362.68e9}
        fetch = lambda url: json.dumps([{"page": 1, "pages": 1, "lastupdated": "2026-07-13"}, [
            {"date": str(y), "value": v, "indicator": {"value": "GDP (current US$)"},
             "country": {"value": "Iran"}} for y, v in values.items()]])
        kinds = [f.kind for f in freshcite.check_wikitext("Pahlavi Iran", wikitext, fetch)]
        self.assertEqual(kinds, [freshcite.HISTORICAL])
        for infobox in ("{{Infobox country\n| year_end = 1983\n", "{{Infobox country\n| life_span = 1917–1991\n"):
            self.assertTrue(freshcite.ENDED_STATE.search(infobox), infobox)
        self.assertFalse(freshcite.ENDED_STATE.search("{{Infobox country\n| date_end = \n| established = 1963\n"))

    def test_two_figures_are_judged_by_what_they_count(self):
        """Second 2026-09-26 sample: Brazil's physicians judged on its hospital beds."""
        claim = "In 2021, Brazil had 2.1 doctors and 2.5 hospital beds for every 1,000 inhabitants"
        physicians = series({2021: 2.2, 2024: 2.3}, "SH.MED.PHYS.ZS")
        physicians.name = "Physicians (per 1,000 people)"
        f = freshcite.judge("Brazil", cite("SH.MED.PHYS.ZS", "BR"), None, claim, physicians)
        self.assertEqual((f.kind, f.figure.raw), (freshcite.DIFFERS, "2.1"))
        other = series({2021: 2.2}, "SH.XPD.CHEX.GD.ZS")
        other.name = "Current health expenditure (% of GDP)"
        f = freshcite.judge("Brazil", cite("SH.XPD.CHEX.GD.ZS", "BR"), None, claim, other)
        self.assertEqual(f.kind, freshcite.UNMATCHED, "neither figure names the series")

    def judged(self, claim, values, name, place, indicator="NY.GDP.PCAP.CD"):
        s = freshcite.Series(indicator, "XX", values, name, place, "2026-07-13")
        return freshcite.judge(place, cite(indicator), None, claim, s)

    def test_another_places_figure_is_not_judged(self):
        """Fourth sample: Indonesia's figure judged against the Philippines."""
        claim = ("the Philippine GDP per capita in 2021 was $3,548.8 compared to 3,694.0 in Vietnam, "
                 "and 4,291.8 in Indonesia")
        f = self.judged(claim, {2021: 3484.4, 2022: 3548.0}, "GDP per capita (current US$)", "Philippines")
        self.assertNotEqual(f.figure.raw if f.figure else None, "4,291.8")
        self.assertNotIn(f.kind, freshcite.REPORTED)

    def test_a_figure_cited_elsewhere_is_not_judged(self):
        """Fourth sample: Albania's census figure, then a World Bank link."""
        claim = ("the proportion of the urban demographic has consistently progressed from 47% in 2001 "
                 "to 65% in 2023. sfn 2023 Albanian census 2024 p=114")
        f = self.judged(claim, {2001: 42.0, 2023: 58.21}, "Urban population (% of total population)",
                        "Albania", "SP.URB.TOTL.IN.ZS")
        self.assertNotIn(f.kind, freshcite.REPORTED)

    def test_another_currency_or_aggregate_is_not_judged(self):
        """Fourth sample: the EU's euros against dollars, Norway's GNI against GDP."""
        f = self.judged("GNI amounted to EUR 44,778 per inhabitant in 2020", {2020: 47506.0},
                        "GNI per capita, PPP (current international $)", "European Union")
        self.assertNotIn(f.kind, freshcite.REPORTED)
        f = self.judged("Gross national income per capita was $81,807 (2018)", {2018: 85579.0},
                        "GDP per capita (current US$)", "Norway")
        self.assertEqual(f.kind, freshcite.UNMATCHED)
        f = self.judged("GDP per capita was $81,807 (2018)", {2018: 85579.0},
                        "GDP per capita (current US$)", "Norway")
        self.assertEqual(f.kind, freshcite.DIFFERS, "a GDP figure against a GDP series is still judged")

    def test_an_exchange_rate_is_never_a_revision_either(self):
        """2026-09-26 sample: "dropped to 165 yen per dollar in 1986" against the 1986 average."""
        f = self.judge("the exchange rate dropped to 165 yen per dollar in 1986",
                       {1986: 168.5, 2025: 149.7}, indicator="PA.NUS.FCRF")
        self.assertNotIn(f.kind, freshcite.REPORTED)

    def test_an_age_is_not_the_statistic(self):
        """Unseen sample: "estimated to be under the age of 15" was read as 15%."""
        claim = "A large share of the population is estimated to be under the age of 15"
        self.assertEqual(self.judge(claim, {2019: 30.0}).kind, freshcite.NO_FIGURE)
        self.assertEqual(freshcite.figures("children 5 years old and 12-year-olds"), [])

    def test_prose_that_names_any_year_is_dated(self):
        """Unseen sample: "$2.6 billion (28% of GDP) in 2022" was called newer
        because the 28% sat between the figure and its year."""
        f = self.judge("with service exports totalling $2.6 billion (28% of GDP) in 2022",
                       {2022: 2.6e9, 2025: 4.9e9})
        self.assertEqual(f.kind, freshcite.HISTORICAL)

    def test_a_change_from_one_value_to_another_is_dated(self):
        """Unseen sample: "decreased by 9.69%, from 12.07 to 10.9 per 1,000"."""
        f = self.judge("the birth rate decreased by 9.69%, from 12.07 to 10.9 per 1,000 people",
                       {2018: 10.9, 2024: 6.8})
        self.assertEqual(f.kind, freshcite.HISTORICAL)

    def test_an_estimate_is_not_called_a_revision(self):
        f = self.judge("with approximately 184,000 international arrivals in 2015", {2015: 199000.0})
        self.assertEqual(f.kind, freshcite.UNMATCHED)

    def test_trailing_zeros_are_rounding(self):
        f = self.judge("arable land was estimated at 119,000,000 hectares as of 2015",
                       {2015: 118700000.0, 2021: 114870800.0})
        self.assertEqual((f.kind, f.matched_year), (freshcite.NEWER, 2015))

    def test_a_later_year_with_the_same_value_is_current(self):
        self.assertEqual(self.judge("42.1", {2012: 42.1, 2020: 42.14}).kind, freshcite.CURRENT)

    def test_current(self):
        self.assertEqual(self.judge("44.7 (2020)", {2012: 42.1, 2020: 44.7}).kind, freshcite.CURRENT)

    def test_mislabeled(self):
        f = self.judge("29.0 (2017)", {2012: 29.0, 2017: 44.2, 2022: 38.3})
        self.assertEqual((f.kind, f.year, f.matched_year), (freshcite.MISLABELED, 2017, 2012))

    def test_differs_only_for_a_stated_year_the_source_has(self):
        self.assertEqual(self.judge("44.4 (2023)", {2023: 41.0}).kind, freshcite.DIFFERS)
        self.assertEqual(self.judge("44.4 (2019)", {2023: 41.0}).kind, freshcite.UNMATCHED)

    def test_a_revision_under_two_per_cent_is_not_reported(self):
        """"a 2.78% population growth in 1966" against 2.79: true to the reader."""
        self.assertEqual(self.judge("2.78% population growth in 1966", {1966: 2.79}).kind,
                         freshcite.UNMATCHED)

    def test_a_figure_of_another_size_is_not_a_disagreement(self):
        """"16% on less than $8.30/day (2023)": neither number is the source's
        value, and 8.30 is a threshold, not a revision of 16."""
        self.assertEqual(self.judge("8.30 a day (2023)", {2023: 44.2}).kind, freshcite.UNMATCHED)

    def test_the_figure_nearest_the_citation_is_the_one_judged(self):
        claim = "Agriculture employs about 26% and contributes about 4.3% of GDP"
        f = self.judge(claim, {1991: 26.0, 2019: 4.3, 2025: 3.0})
        self.assertEqual((f.figure.raw, f.matched_year), ("4.3%", 2019))

    def test_no_figure(self):
        self.assertEqual(self.judge("the World Bank reports", {2020: 1.0}).kind, freshcite.NO_FIGURE)

    def test_a_link_with_no_country_is_counted_not_fetched(self):
        text = "5%<ref>https://data.worldbank.org/indicator/NY.GDP.PCAP.KD.ZG</ref>"
        found = freshcite.check_wikitext("A", text, offline)
        self.assertEqual([f.kind for f in found], [freshcite.NO_COUNTRY])

    def test_an_indicator_the_api_does_not_have_is_no_data(self):
        text = "5%<ref>https://data.worldbank.org/indicator/NOT.REAL?locations=KE</ref>"
        self.assertEqual([f.kind for f in freshcite.check_wikitext("A", text, offline)], [freshcite.NO_DATA])


class TheSource(unittest.TestCase):

    def test_a_real_series_reads_every_year(self):
        s = freshcite.worldbank_series(offline, "SP.POP.TOTL", "KE")
        self.assertEqual((s.latest, s.values[2025], s.updated), (2025, 57532493.0, "2026-07-13"))
        self.assertEqual((s.name, s.country_name), ("Population, total", "Kenya"))

    def test_pages_are_followed(self):
        pages = {1: [{"page": 1, "pages": 2, "lastupdated": "x"},
                     [{"date": "2020", "value": 1.0, "indicator": {"value": "I"}, "country": {"value": "C"}}]],
                 2: [{"page": 2, "pages": 2, "lastupdated": "x"},
                     [{"date": "2021", "value": 2.0, "indicator": {"value": "I"}, "country": {"value": "C"}}]]}
        fetch = lambda url: json.dumps(pages[int(re.search(r"&page=(\d+)", url).group(1))])
        self.assertEqual(freshcite.worldbank_series(fetch, "I", "C").values, {2020: 1.0, 2021: 2.0})

    def test_an_empty_answer_is_none(self):
        self.assertIsNone(freshcite.worldbank_series(lambda u: '[{"page":1,"pages":0},null]', "I", "C"))


class TheArticleList(unittest.TestCase):

    def test_only_articles_are_kept_and_each_once(self):
        html_text = (FIX / "linksearch.html").read_text(encoding="utf-8")
        titles = freshcite.linked_articles(lambda url: html_text, page_size=5000)
        self.assertIn("Economy of Serbia", titles)
        self.assertEqual(len(titles), len(set(titles)))
        self.assertFalse([t for t in titles if t.split(":")[0] in
                          ("Template", "Talk", "User", "User talk", "Wikipedia", "Wikipedia talk")])
        rows = freshcite.LINK_ROW.findall(html_text)
        self.assertEqual(len(rows), 40)

    def test_a_full_page_asks_for_the_next(self):
        calls = []
        row = ('<li><a rel="nofollow" class="external free" href="https://data.worldbank.org/'
               'indicator/X">u</a> is linked from <a href="/wiki/%s" title="%s">%s</a></li>')
        def fetch(url):
            offset = int(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["offset"][0])
            calls.append(offset)
            return "".join(row % ((("A%d" % (offset + i),) * 3)) for i in range(2 if offset == 0 else 1))
        self.assertEqual(freshcite.linked_articles(fetch, page_size=2), ["A0", "A1", "A2"])
        self.assertEqual(calls, [0, 2])


class TheFetcher(unittest.TestCase):

    def test_a_fresh_cache_entry_is_used_without_a_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            fetch = freshcite.Fetcher(cache_dir=tmp)
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
            self.assertEqual(freshcite.Fetcher(interval={"x.org": 0})("https://x.org/b"), "ok")
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
            fetch = freshcite.Fetcher(interval={"x.org": 2.0})
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
                freshcite.Fetcher(interval={"x.org": 0})("https://x.org/d")
        self.assertEqual(opened.call_count, 6)

    def test_a_missing_cache_directory_is_created(self):
        answer = mock.MagicMock()
        answer.__enter__.return_value.read.return_value = b"fresh"
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("urllib.request.urlopen", return_value=answer):
            fetch = freshcite.Fetcher(cache_dir=pathlib.Path(tmp) / "a" / "b", interval={"x.org": 0})
            self.assertEqual(fetch("https://x.org/e"), "fresh")
            self.assertEqual(fetch("https://x.org/f"), "fresh")
            self.assertEqual(fetch._cache_path("https://x.org/f").read_text(), "fresh")

    def test_a_timeout_is_retried(self):
        """The first full scan died on one read timeout at article 10."""
        answer = mock.MagicMock()
        answer.__enter__.return_value.read.return_value = b"ok"
        with mock.patch("urllib.request.urlopen", side_effect=[TimeoutError("read"), answer]), \
                mock.patch("time.sleep") as sleep:
            self.assertEqual(freshcite.Fetcher(interval={"x.org": 0})("https://x.org/g"), "ok")
        self.assertIn(mock.call(5), sleep.call_args_list)

    def test_a_network_that_stays_down_is_given_up_on(self):
        with mock.patch("urllib.request.urlopen", side_effect=[TimeoutError("read")] * 6), \
                mock.patch("time.sleep"):
            with self.assertRaises(TimeoutError):
                freshcite.Fetcher(interval={"x.org": 0})("https://x.org/h")

    def test_other_errors_are_not_retried(self):
        refused = urllib.error.HTTPError("u", 404, "Not Found", {}, io.BytesIO())
        with mock.patch("urllib.request.urlopen", side_effect=[refused]):
            with self.assertRaises(urllib.error.HTTPError):
                freshcite.Fetcher(interval={"x.org": 0})("https://x.org/c")


class TheScan(unittest.TestCase):

    def test_one_unreadable_article_does_not_end_the_scan(self):
        romania = wikitext("Economy_of_Romania")
        def fetch(url):
            if "LinkSearch" in url:
                return "".join('<li><a class="external" href="https://data.worldbank.org/indicator/X">u</a>'
                               ' is linked from <a href="/wiki/%s" title="%s">%s</a></li>' % (t, t, t)
                               for t in ("Broken", "Economy of Romania"))
            if "title=Broken" in url:
                raise TimeoutError("read")
            if "action=raw" in url:
                return romania
            return offline(url)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(freshcite, "Fetcher", return_value=fetch), \
                mock.patch("sys.stderr", io.StringIO()), mock.patch("sys.stdout", io.StringIO()):
            self.assertEqual(freshcite.main(["scan", "--out", tmp]), 0)
            report = (pathlib.Path(tmp) / "report.md").read_text(encoding="utf-8")
            findings = json.loads((pathlib.Path(tmp) / "findings.json").read_text(encoding="utf-8"))
        self.assertIn("## Articles that could not be read (1)", report)
        self.assertIn("TimeoutError", report)
        self.assertIn("## A newer figure is available (1)", report)
        self.assertIn("Generated", report)
        self.assertEqual([f["article"] for f in findings if f["kind"] == "newer"], ["Economy of Romania"])


class TheReport(unittest.TestCase):

    def test_findings_come_first_and_the_silence_is_counted(self):
        found = freshcite.check_wikitext("Economy of Romania", wikitext("Economy_of_Romania"), offline)
        text = freshcite.markdown(found, 1, "2026-09-26")
        self.assertIn("## A newer figure is available (1)", text)
        self.assertIn("[Economy of Romania](https://en.wikipedia.org/wiki/Economy_of_Romania)", text)
        self.assertLess(text.index("A newer figure"), text.index("Not reported, and why"))
        self.assertIn("| The link names no single country |", text)

    def test_the_wiki_page_shows_markup_rather_than_running_it(self):
        found = freshcite.check_wikitext("Economy of Romania", wikitext("Economy_of_Romania"), offline)
        rows = [f.as_dict() for f in found] * 2
        rows[-1] = dict(next(r for r in rows if r["kind"] == "newer"))
        rows[-1].update(kind="differs", key=None, claim="{{convert|1|km}} a || b [[x]]",
                       figure="4.3%", note="n")
        text = freshcite.wikitext(rows, "2026-09-26", 1)
        self.assertIn("== A newer figure is available (", text)
        self.assertIn("[[Economy of Romania]]", text)
        self.assertIn("<nowiki>{{convert|1|km}} a || b [[x]]</nowiki>", text)
        self.assertEqual(text.count("{|"), text.count("|}"))
        self.assertIn("read 1 articles and %d World Bank citations" % len(rows), text)

    def test_a_pipe_in_a_claim_cannot_break_the_table(self):
        f = freshcite.judge("A", cite(), None, "a | b 42.1 (2012)", series({2012: 42.1, 2020: 44.7}), True)
        row = [l for l in freshcite.markdown([f], 1, "d").splitlines() if l.startswith("| [A]")][0]
        self.assertEqual(row.count(" | "), 4)


class TheCommittedSummary(unittest.TestCase):

    def test_the_summary_is_what_the_findings_print(self):
        """README numbers are pinned to reports/*-summary.txt by docclaims, so
        that file must be exactly what tools/findings.py prints today."""
        root = FIX.parent.parent
        sys.path.insert(0, str(root / "tools"))
        import findings as summary  # noqa: E402
        for path in sorted((root / "reports").glob("*-summary.txt")):
            data = path.with_name(path.name.replace("-summary.txt", "-worldbank.json"))
            articles = re.search(r"^articles read\s+(\d+)", path.read_text(encoding="utf-8"), re.M).group(1)
            out = io.StringIO()
            with mock.patch("sys.stdout", out):
                summary.main([str(data), "--articles", articles])
            # read_text turns a Windows checkout's CRLF back into LF.
            self.assertEqual(out.getvalue(), path.read_text(encoding="utf-8"), path.name)


if __name__ == "__main__":
    unittest.main()
