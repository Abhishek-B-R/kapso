import re
from pathlib import Path
from typing import Any, Callable, List

import pytest

from kapso.execution.memories.repo_memory.builders import (
    _read_numbered_text,
    infer_repo_model_update,
    infer_repo_model_with_retry,
)
from tests.test_repo_memory_resilience import VALID_MODEL, VALID_UPDATE, SequenceLLM

BIG_FILE = "big_module.py"
BIG_FILE_LINES = 3000  # ~45k characters, longer than the old read caps
NUMBERED_ROW = re.compile(r"^\s*(\d+)\| line_(\d{4}) = \d+$", re.M)


def _big_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    repo_root.joinpath(BIG_FILE).write_text(
        "".join(f"line_{n:04d} = {n}\n" for n in range(1, BIG_FILE_LINES + 1))
    )
    return repo_root


def _infer_initial(llm: SequenceLLM, repo_root: Path) -> None:
    infer_repo_model_with_retry(
        llm=llm,
        repo_root=str(repo_root),
        repo_map={"files": [BIG_FILE], "key_files": [BIG_FILE], "entrypoints": []},
    )


def _infer_update(llm: SequenceLLM, repo_root: Path) -> None:
    infer_repo_model_update(
        llm=llm,
        repo_root=str(repo_root),
        repo_map={"files": [BIG_FILE]},
        previous_model={"summary": "Old", "sections": {}},
        diff_summary="big_module.py changed",
        changed_files=[BIG_FILE],
    )


@pytest.mark.parametrize(
    "infer, responses",
    [
        (_infer_initial, ['{"files_to_read": []}', VALID_MODEL]),
        (_infer_update, [VALID_UPDATE]),
    ],
    ids=["initial", "update"],
)
def test_large_file_reaches_the_prompt_whole_with_real_line_numbers(
    tmp_path: Path,
    infer: Callable[[SequenceLLM, Path], None],
    responses: List[Any],
) -> None:
    llm = SequenceLLM(responses)

    infer(llm, _big_repo(tmp_path))

    prompt = llm.calls[-1]["messages"][0]["content"]
    rows = [(int(shown), int(real)) for shown, real in NUMBERED_ROW.findall(prompt)]
    assert [(shown, real) for shown, real in rows if shown != real] == []
    assert [real for _, real in rows] == list(range(1, BIG_FILE_LINES + 1))
    assert "omitted" not in prompt


def test_numbers_only_the_files_real_lines(tmp_path: Path) -> None:
    path = tmp_path / "small.txt"
    path.write_text("alpha\nbeta\n")

    assert _read_numbered_text(str(path)) == "1| alpha\n2| beta"


def test_unreadable_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _read_numbered_text(str(tmp_path / "missing.txt"))
