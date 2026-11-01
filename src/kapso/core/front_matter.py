"""A Markdown file's front matter, read the one way: the harness check,
the staging and the deployment targets all read skills and agents by it."""

import io
from pathlib import Path
from typing import Any, Optional, Tuple

import yaml


def read_front_matter(file: Path) -> Tuple[Optional[Any], str]:
    """A Markdown file's front matter (the YAML between the opening `---`
    and the next `---`) and its body. None and the whole text when the
    file has no front matter; a block that is not valid YAML raises the
    parser's own error naming the file, with the block's line numbers
    on the file's (line 1 is the opening `---`)."""
    text = file.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---" not in text[4:]:
        return None, text
    end = 4 + text[4:].index("\n---")
    block = text[4:end]
    stream = io.StringIO("\n" + block)
    stream.name = str(file)
    data = yaml.safe_load(stream)
    body = text[end + 4:]
    if body.startswith("\n"):
        body = body[1:]
    return data, body
