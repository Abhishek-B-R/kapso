"""The look-ahead patterns, shared by the skill's diff scan and the harness's write hook."""
import re

RULES = [
    (re.compile(r"\.shift\(\s*-\d"), "a negative shift moves future values onto the current timestamp"),
    (re.compile(r"rolling\([^)]*center\s*=\s*True"), "a centred window reads bars after t"),
    (re.compile(r"\.bfill\(|method\s*=\s*['\"]bfill['\"]"), "backward fill copies a later value into an earlier bar"),
    (re.compile(r"\.iloc\[\s*i\s*\+\s*1\s*\]"), "indexing i + 1 inside a bar loop reads the next bar"),
    (re.compile(r"merge_asof\([^)]*direction\s*=\s*['\"](forward|nearest)['\"]"), "an as-of join looking forward or nearest matches a future row"),
]


def scan_lines(lines) -> list[dict]:
    """Findings for an iterable of (where, text) pairs, one per rule a line matches."""
    findings = []
    for where, text in lines:
        for pattern, rule in RULES:
            if pattern.search(text):
                findings.append({"rule": rule, "where": where, "line": text.strip()})
    return findings
