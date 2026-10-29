"""Static leakage scan for a time-cut prediction task.

Two modes over one rule table. `--diff` reads a unified diff on stdin and
scans the added lines (an attempt's own change, before its evaluation);
`--tree DIR` scans every Python file under a directory (a delivered
candidate, whole, for the final audit). Each hit is one JSON finding on
stdout: the file, the line, the rule, the concern and the line itself. A
violation exits 1; an advisory finding alone exits 0 and is prefixed
`verify:` because the pattern is legal for one chain (the test-predicting
model) and illegal for the other (the model that produces validation
predictions), so it is traced, not condemned.

    git diff main...HEAD | python3 scan.py --diff --regime frozen|seed-time|autocomplete
    python3 scan.py --tree . --regime frozen
"""
import argparse
import json
import re
import sys
from pathlib import Path

REGIMES = ("frozen", "seed-time", "autocomplete")

# (rule, pattern, concern, advisory)
RULES = [
    ("unmasked-test-table", r"mask_input_cols\s*=\s*False[^\n]*test|test[^\n]*mask_input_cols\s*=\s*False",
     "reads the test table with its input masks off (test labels)", False),
    ("unmasked-table", r"mask_input_cols\s*=\s*False",
     "reads a task table with its input masks off: legal on train and val, confirm which split", True),
    ("removed-columns", r"removed_cols", "reads the columns the sanitizer removed (the target and what derives it)", False),
    ("cache-location", r"RELBENCH_CACHE_DIR", "names the library's cache location: the prepared copy is the only cache", False),
    ("outside-snapshot", r"RELBENCH_ROLLING_ROOT|rolling_caches", "reaches outside the staged tick snapshot", False),
    ("task-stats", r"task\.stats\s*\(", "probes the task tables' statistics on a sanitized copy", False),
    ("download", r"download\s*=\s*True", "downloads the dataset: the prepared copy is complete and read-only", False),
    ("direct-fetch", r"relbench\.stanford\.edu|\bpooch\b", "fetches the benchmark's files directly", False),
    ("private-builder", r"_get_table\s*\(", "calls a private table builder", False),
    ("pristine-cache", r"\.cache[/\\]relbench", "touches the pristine library cache path", False),
    ("train-val-mixing",
     r"(concatenate|concat|hstack|vstack|np\.r_)[^\n]{0,80}(train[^\n]{0,30}val|val[^\n]{0,30}train)|train_?val_?(idx|index|indices|rows)",
     "train+val mixing: confirm the validation-prediction chain is pre-refit (the two-model contract)", True),
    ("fit-on-validation", r"\.fit\([^\n]{0,60}val_(y|label|labels|target|targets)",
     "a fit that names validation labels: confirm it is the test-predicting chain", True),
]
REGIME_RULES = {
    "frozen": ("untruncated-load", r"upto_test_timestamp\s*=\s*False",
               "requests the untruncated database under the frozen regime", False),
    "seed-time": ("re-truncated-load", r"upto_test_timestamp\s*=\s*True",
                  "truncates the per-tick snapshot at the static cutoff: the trap the temporal protocol names", False),
    "autocomplete": None,
}
FILE_HEADER = re.compile(r"^\+\+\+ (?:b/)?(.+)$")
HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def added_lines(diff):
    """Yield (file, line number, text) for every added line of a unified diff."""
    current = None
    number = 0
    for raw in diff.splitlines():
        header = FILE_HEADER.match(raw)
        if header:
            current = header.group(1)
            continue
        hunk = HUNK_HEADER.match(raw)
        if hunk:
            number = int(hunk.group(1))
            continue
        if current is None or raw.startswith("---"):
            continue
        if raw.startswith("+"):
            yield current, number, raw[1:]
            number += 1
        elif not raw.startswith("-"):
            number += 1


def tree_lines(root: Path):
    """Yield (file, line number, text) for every line of every Python file under `root`."""
    for path in sorted(root.rglob("*.py")):
        for number, text in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            yield str(path.relative_to(root)), number, text


def compiled_rules(regime):
    rules = list(RULES)
    if REGIME_RULES[regime] is not None:
        rules.append(REGIME_RULES[regime])
    return [(rule, re.compile(pattern), concern, advisory) for rule, pattern, concern, advisory in rules]


def scan(lines, regime):
    """The findings over (file, number, text) triples: the first rule that
    matches a line wins, so a test-table unmasking is reported once."""
    findings = []
    for file, number, text in lines:
        for rule, pattern, concern, advisory in compiled_rules(regime):
            if pattern.search(text):
                findings.append({
                    "file": file, "line": number, "rule": rule,
                    "concern": f"verify: {concern}" if advisory else concern,
                    "advisory": advisory, "text": text.strip(),
                })
                break
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--regime", required=True, choices=REGIMES, help="the regime the domain statement records")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--diff", action="store_true", help="scan the added lines of the unified diff on stdin")
    mode.add_argument("--tree", metavar="DIR", help="scan every Python file under this directory")
    args = parser.parse_args()
    lines = added_lines(sys.stdin.read()) if args.diff else tree_lines(Path(args.tree))
    findings = scan(lines, args.regime)
    for finding in findings:
        print(json.dumps(finding))
    sys.exit(1 if any(not finding["advisory"] for finding in findings) else 0)


if __name__ == "__main__":
    main()
