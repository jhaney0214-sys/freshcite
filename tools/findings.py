"""Every figure a written piece quotes about a scan, printed from its findings.json.

    python tools/findings.py report/findings.json --articles 1270
    python tools/findings.py report/findings.json --articles 1270 --show "Economy of Laos"

Against the Source's page on this scan types none of its numbers; each comes
from this script's output, so when a scan is re-run the page is updated from
here rather than from memory.
"""

import argparse
import collections
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import freshcite  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("findings")
    parser.add_argument("--articles", type=int, required=True, help="how many articles the scan read")
    parser.add_argument("--show", action="append", default=[], help="print this article's findings")
    args = parser.parse_args(argv)
    rows = json.loads(pathlib.Path(args.findings).read_text(encoding="utf-8"))
    reported = [r for r in rows if r["kind"] in freshcite.REPORTED]
    kinds = collections.Counter(r["kind"] for r in rows)

    print("articles read            %6d" % args.articles)
    print("World Bank citations     %6d" % len(rows))
    print("reported                 %6d  (%.1f%% of citations)" % (
        len(reported), 100.0 * len(reported) / len(rows)))
    for kind in freshcite.REPORTED:
        print("  %-22s %6d" % (kind, kinds[kind]))
    print("articles with a finding  %6d" % len({r["article"] for r in reported}))
    print("silent, by reason:")
    for kind, n in kinds.most_common():
        if kind not in freshcite.REPORTED:
            print("  %-22s %6d" % (kind, n))

    behind = sorted(r["latest_year"] - r["matched_year"] for r in rows if r["kind"] == freshcite.NEWER)
    if behind:
        print("newer: years behind the latest, median %g, 5 or more %d of %d, most %d" % (
            statistics.median(behind), sum(1 for b in behind if b >= 5), len(behind), behind[-1]))
    series = collections.Counter(r["series"] for r in reported)
    print("series most often reported:")
    for name, n in series.most_common(6):
        print("  %3d  %s" % (n, name))
    for title in args.show:
        print("\n%s:" % title)
        for r in reported:
            if r["article"] == title:
                print("  %-10s %s | %s | %s" % (r["kind"], r["claim"][-110:], r["figure"], r["note"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
