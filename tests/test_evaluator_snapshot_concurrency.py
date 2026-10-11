"""Parallel archivers must share a complete, immutable evaluator snapshot."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from kapso.execution.evaluation_archive_sandbox import (
    fingerprint_tree,
    snapshot_evaluator_tree,
)


def test_parallel_sessions_publish_one_complete_snapshot(tmp_path):
    source = tmp_path / "evaluation"
    source.mkdir()
    for index in range(100):
        (source / f"grader_{index}.py").write_text(f"SCORE = {index}\n")
    evaluator_id = fingerprint_tree(source)
    archive_root = tmp_path / "archive"
    workers = 8
    barrier = Barrier(workers)

    def snapshot():
        barrier.wait(timeout=10)
        return snapshot_evaluator_tree(archive_root, source, evaluator_id)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(snapshot) for _ in range(workers)]
        destinations = [future.result(timeout=10) for future in futures]

    expected = archive_root / "evaluators" / evaluator_id
    assert destinations == [expected] * workers
    assert fingerprint_tree(expected) == evaluator_id
    assert not expected.with_name(evaluator_id + ".partial").exists()
    again = snapshot_evaluator_tree(archive_root, source, evaluator_id)
    assert again == expected
    assert fingerprint_tree(expected) == evaluator_id
