"""The `kapso …` command lines a page or a skill shows, for the tests that
parse them against the CLI's own parsers: the fenced bash lines (copied
by a reader or an agent) and the inline ones (mentioned in prose)."""
import re

PLACEHOLDER = re.compile(r"<[^>]+>")


def fenced_bash_lines(text: str):
    """The `kapso …` lines of the fenced bash blocks, continuation lines
    joined, comments and prompts stripped."""
    lines = []
    for block in re.findall(r"```(?:bash|sh)\n(.*?)```", text, re.S):
        joined = block.replace("\\\n", " ")
        for raw in joined.splitlines():
            line = raw.split("#", 1)[0].strip()
            if line.startswith("$ "):
                line = line[2:]
            if line.startswith("kapso "):
                lines.append(line)
    return lines


def inline_lines(text: str):
    """The `kapso …` lines written inline in backticks, when they are
    commands rather than mentions of a verb: a verb and a flag on the
    line, no placeholder in angle brackets, no ellipsis."""
    lines = []
    for line in re.findall(r"`(kapso [^`]+)`", text):
        if "--" in line and not line.split()[1].startswith("--") and "<" not in line and "…" not in line and line not in lines:
            lines.append(line)
    return lines
