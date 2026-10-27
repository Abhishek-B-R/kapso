"""The timeline of a campaign (docs/plans/redesign/wp9-semantic-suite.md,
change 8): the status file sampled at the engine config's heartbeat
cadence into `timeline.jsonl`, each row the stored state beside the
observed liveness (the writer's process in the process table, the
heartbeat's age), so S5 can tell within one heartbeat whether the stored
state was truthful and S6 can read both builds on one elapsed grid.

    python3 status_timeline.py <campaign> <timeline.jsonl> --every <seconds> [--until-terminal]
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

TERMINAL = ("done", "failed")


def installed_python() -> Path:
    """The interpreter of the installed package (a uv tool's, a venv's, a
    conda env's): the `kapso` script's shebang, so the config read below is
    the engine's own."""
    kapso = shutil.which("kapso")
    if not kapso:
        raise RuntimeError("kapso is not on PATH")
    first = Path(kapso).resolve().read_text(encoding="utf-8", errors="replace").splitlines()[0]
    if not first.startswith("#!"):
        raise RuntimeError(f"{kapso} has no shebang to read the interpreter from")
    return Path(first[2:].split()[0])


def heartbeat_seconds() -> float:
    """The engine config's `budget.checkpoint_heartbeat_seconds`, read from
    the installed package: the one cadence the sampler and the grids use."""
    run = subprocess.run([str(installed_python()), "-c", "from kapso.core.config import load_config; print(load_config()['budget']['checkpoint_heartbeat_seconds'])"], capture_output=True, text=True, check=True)
    return float(run.stdout.strip())


def sample(campaign: Path) -> Dict[str, Any]:
    status_path = campaign / ".kapso" / "status.json"
    now = datetime.now(timezone.utc)
    row: Dict[str, Any] = {"ts": now.isoformat(timespec="seconds"), "stored": None, "pid_alive": None, "heartbeat_age_s": None}
    if not status_path.is_file():
        return row
    text = status_path.read_text(encoding="utf-8")
    if not text.strip():
        return row
    status = json.loads(text)
    row["stored"] = {key: status.get(key) for key in ("state", "phase", "iteration", "best", "stopped_reason", "heartbeat_at", "pid", "error")}
    pid = status.get("pid")
    row["pid_alive"] = isinstance(pid, int) and Path(f"/proc/{pid}").exists()
    heartbeat = status.get("heartbeat_at")
    if heartbeat:
        row["heartbeat_age_s"] = round((now - datetime.fromisoformat(heartbeat)).total_seconds(), 1)
    return row


def run(campaign: Path, timeline: Path, every: float, until_terminal: bool) -> None:
    while True:
        row = sample(campaign)
        with open(timeline, "a", encoding="utf-8") as out:
            out.write(json.dumps(row) + "\n")
        if until_terminal and row["stored"] and row["stored"]["state"] in TERMINAL:
            return
        time.sleep(every)


def rows(timeline: Path):
    return [json.loads(line) for line in timeline.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("campaign")
    parser.add_argument("timeline")
    parser.add_argument("--every", type=float, required=True, help="the cadence in seconds: the engine config's budget.checkpoint_heartbeat_seconds, read by the runner")
    parser.add_argument("--until-terminal", action="store_true")
    args = parser.parse_args(argv)
    run(Path(args.campaign), Path(args.timeline), args.every, args.until_terminal)
    return 0


if __name__ == "__main__":
    sys.exit(main())
