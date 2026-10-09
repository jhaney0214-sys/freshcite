"""What became of the posted rows, read from a fresh scan.

    python freshcite.py scan --out report
    python tools/rescan.py report/findings.json
    python tools/rescan.py report/findings.json --acted "Economy of Laos::SI.POV.DDAY" --rows

The baseline is `reports/2026-09-26-worldbank.json`: the 358 rows posted to
User:Jorn3333/World Bank figures on 2026-09-27, less the rows since found to be
the tool's errors. Rows are paired by article and citation URL, in
order where one article cites the same URL more than once.

A row counts as resolved only when the sentence itself was edited and its
figure is no longer listed. A row whose text is unchanged but drops out of the
report was moved by the World Bank revising its series, or by a rule change,
not by an editor, and is counted apart; so is a citation that disappeared,
which an editor may have fixed or simply deleted.
"""

import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import freshcite  # noqa: E402

BASELINE = ROOT / "reports" / "2026-09-26-worldbank.json"

#: Posted rows later found to be the tool's error, not the article's: the
#: text was right, so nothing an editor does to it says anything about the
#: delivery. The first two were found by the fifth sample and marked on the
#: page 2026-09-27. The last three were found 2026-10-09 by the rule that
#: reads a year stated before an earlier ref in the same sentence: each states
#: its year there, and each figure is that year's value.
TOOL_ERRORS = {("Health in Finland", "SP.DYN.LE00.IN"),
               ("Hurricane Norma (2023)", "PA.NUS.ATLS"),
               ("Nepal", "MS.MIL.XPND.GD.ZS"),
               ("Telecommunications in Timor-Leste", "IT.MLT.MAIN"),
               ("Telecommunications in Timor-Leste", "IT.MLT.MAIN.P2")}

#: How each posted row ended, in the order they are printed.
RESOLVED = "resolved by an edit"
UNREADABLE = "edited, tool cannot read it now"
STILL = "edited, still listed"
REMOVED = "citation gone"
GONE = "article gone from the scan"
DRIFTED = "unlisted with no edit (source or rule)"
UNCHANGED = "unchanged"
OUTCOMES = (RESOLVED, UNREADABLE, STILL, REMOVED, GONE, DRIFTED, UNCHANGED)
SILENT_BUT_READ = {freshcite.CURRENT, freshcite.HISTORICAL}


def posted(rows):
    return [r for r in rows if r["kind"] in freshcite.REPORTED
            and (r["article"], r["indicator"]) not in TOOL_ERRORS]


def outcome(old, new, article_read):
    if new is None:
        return REMOVED if article_read else GONE
    listed = new["kind"] in freshcite.REPORTED
    if new["claim"] == old["claim"]:
        return UNCHANGED if listed else DRIFTED
    if listed:
        return STILL
    if new["kind"] in SILENT_BUT_READ and new.get("figure") != old.get("figure"):
        return RESOLVED
    return UNREADABLE


def compare(baseline, fresh):
    """[(posted row, its row in the fresh scan or None, outcome)]."""
    by_key = collections.defaultdict(list)
    for r in fresh:
        by_key[(r["article"], r["citation"])].append(r)
    seen = collections.Counter()
    articles = {r["article"] for r in fresh}
    out = []
    for r in baseline:
        key = (r["article"], r["citation"])
        nth = seen[key]
        seen[key] += 1
        if r not in posted([r]):
            continue
        candidates = by_key.get(key, [])
        new = candidates[nth] if nth < len(candidates) else None
        out.append((r, new, outcome(r, new, r["article"] in articles)))
    return out


def acted_on(row, acted):
    """Whether `row` is one of `acted`: "Article", or "Article::INDICATOR" for one row's series."""
    return row["article"] in acted or "%s::%s" % (row["article"], row["indicator"]) in acted


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("findings", help="findings.json from a fresh scan")
    parser.add_argument("--baseline", default=str(BASELINE))
    parser.add_argument("--acted", action="append", default=[],
                        help='a row the author fixed or raised, as "Article::INDICATOR" '
                             '(or "Article" for all its rows); counted apart')
    parser.add_argument("--rows", action="store_true", help="print every row that moved")
    args = parser.parse_args(argv)
    baseline = json.loads(pathlib.Path(args.baseline).read_text(encoding="utf-8"))
    fresh = json.loads(pathlib.Path(args.findings).read_text(encoding="utf-8"))
    result = compare(baseline, fresh)
    acted = set(args.acted)
    missing = {a for a in acted if not any(acted_on(r, {a}) for r, _n, _o in result)}
    if missing:
        parser.error("not a posted row: %s" % ", ".join(sorted(missing)))

    groups = [("all posted rows", result)]
    if acted:
        groups += [("rows the author acted on", [x for x in result if acted_on(x[0], acted)]),
                   ("the rest", [x for x in result if not acted_on(x[0], acted)])]
    errors = sum(1 for r in baseline if r["kind"] in freshcite.REPORTED
                 and (r["article"], r["indicator"]) in TOOL_ERRORS)
    print("baseline  %s, %d rows (%d known tool errors left out)" % (
        pathlib.Path(args.baseline).name, len(result), errors))
    for name, rows in groups:
        counts = collections.Counter(o for _r, _n, o in rows)
        n = len(rows)
        print("\n%s: %d" % (name, n))
        for o in OUTCOMES:
            print("  %-42s %4d" % (o, counts[o]))
        if n:
            print("  resolved: %d of %d (%.1f%%); counting gone citations too, %d (%.1f%%)" % (
                counts[RESOLVED], n, 100.0 * counts[RESOLVED] / n,
                counts[RESOLVED] + counts[REMOVED], 100.0 * (counts[RESOLVED] + counts[REMOVED]) / n))
    if args.rows:
        print()
        for old, new, o in result:
            if o != UNCHANGED:
                print("%-30s %-10s %s | %s -> %s" % (
                    o[:30], old["kind"], old["article"], old["claim"][-70:],
                    "(none)" if new is None else "%s: %s" % (new["kind"], new["claim"][-70:])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
