"""What every benchmark runner on build() does the same way: the runtime
override file with the task's shared cache, the staged evaluation directory
with the task's settings beside the provided grader, the machine's compute
as a fact for the Brief, and a directory's layout as the Brief lists it."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from kapso.core.config import read_yaml

TASK_FILE = "task.json"
LAYOUT_ENTRIES_PER_DIRECTORY = 5
LAYOUT_DEPTH = 4


def write_runtime_config(config_path: Path, shared_cache_dir: Path, work_dir: Path,
                         archive_root: Optional[Path] = None) -> Path:
    """The per-run override file: the benchmark's own file with the task's
    shared cache over it and, for a benchmark whose grader keeps a durable
    archive, that task's own archive root in place of the file's layout
    glob (the engine labels the run of record there, and only there). The
    orchestrator loads config from disk, so a runtime value must live in a
    file; the file is an override over the packaged defaults, as the
    benchmark's own is."""
    config = read_yaml(str(config_path))
    config["search_strategy"]["params"]["shared_cache_dir"] = str(shared_cache_dir)
    if archive_root is not None:
        config["search_strategy"]["params"]["registered_evaluation_archive_glob"] = str(archive_root)
    runtime_dir = work_dir / ".kapso_runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    runtime_path = runtime_dir / "config.yaml"
    runtime_path.write_text(yaml.safe_dump(config, sort_keys=False))
    return runtime_path


def stage_evaluation(suite: Path, work_dir: Path, settings: Dict[str, object]) -> Path:
    """The provided grader with the task's settings beside it, under the
    archive root; written the same way every time, so a resume's fingerprint
    of the evaluation directory holds."""
    target = work_dir / "evaluation"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for item in sorted(suite.iterdir()):
        if item.is_file():
            shutil.copy2(item, target / item.name)
    (target / TASK_FILE).write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n")
    return target


def compute_facts() -> Dict[str, object]:
    """This machine: the GPU by name, the CPUs, the memory."""
    has_gpu = (
        shutil.which("nvidia-smi") is not None
        and subprocess.run(["nvidia-smi", "-L"], capture_output=True).returncode == 0
    )
    gpu_name = ""
    if has_gpu:
        probe = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True,
        )
        if probe.returncode == 0 and probe.stdout.strip():
            gpu_name = probe.stdout.strip().splitlines()[0].strip()
    mem_gb = 0
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemTotal"):
                mem_gb = int(line.split()[1]) // (1024 * 1024)
    return {"has_gpu": has_gpu, "gpu_name": gpu_name, "num_cpus": os.cpu_count() or 0, "mem_gb": mem_gb}


def resources(compute: Dict[str, object]) -> str:
    if compute["has_gpu"]:
        detail = f" ({compute['gpu_name']})" if compute["gpu_name"] else ""
        gpu = f"a dedicated CUDA GPU{detail}, pinned per lane through CUDA_VISIBLE_DEVICES"
    else:
        gpu = "no GPU"
    return f"Hardware: {gpu}; ~{compute['num_cpus']} CPUs; ~{compute['mem_gb']} GB RAM."


def _format_size(size_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}PB"


def _directory_size(directory: Path) -> int:
    return sum(item.stat().st_size for item in directory.rglob("*") if item.is_file())


def directory_layout(root: Path) -> str:
    """The directory's layout as the Brief lists it: every level down to a
    depth, a few entries per directory with their sizes and a count of the
    rest. A summary of a tree, written by us, not a clipped message."""
    lines: List[str] = [f"Data directory: {root}", "=" * 80, ""]
    _add_directory(lines, root, 0, "")
    return "\n".join(lines)


def _add_directory(lines: List[str], directory: Path, depth: int, prefix: str) -> None:
    if depth > LAYOUT_DEPTH:
        return
    items = sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name))
    dirs = [item for item in items if item.is_dir()]
    files = [item for item in items if item.is_file()]
    shown_files, shown_dirs = files[:LAYOUT_ENTRIES_PER_DIRECTORY], dirs[:LAYOUT_ENTRIES_PER_DIRECTORY]
    remaining_files, remaining_dirs = len(files) - len(shown_files), len(dirs) - len(shown_dirs)
    for index, item in enumerate(shown_files):
        last = index == len(shown_files) - 1 and not remaining_files and not shown_dirs
        lines.append(f"{prefix}{'└──' if last else '├──'} [{_format_size(item.stat().st_size)}] {item.name}")
    if remaining_files:
        lines.append(f"{prefix}{'├──' if shown_dirs else '└──'} ... ({remaining_files} more file{'s' if remaining_files > 1 else ''})")
    for index, item in enumerate(shown_dirs):
        last = index == len(shown_dirs) - 1 and not remaining_dirs
        lines.append(f"{prefix}{'└──' if last else '├──'} [{_format_size(_directory_size(item))}] {item.name}/")
        _add_directory(lines, item, depth + 1, prefix + ("    " if last else "│   "))
    if remaining_dirs:
        lines.append(f"{prefix}└── ... ({remaining_dirs} more director{'ies' if remaining_dirs > 1 else 'y'})")
