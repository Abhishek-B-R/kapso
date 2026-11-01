"""Stand the second machine's delivered churn campaign in for the
development box's, which delivered nothing in its hour, so the Codex
deploy step runs on a delivered build.

The box's own campaign is kept beside it; the machine's deployment and
its session records are removed so the Codex session's deploy is the
first; every file that names the machine's home names the box's work
directory instead (the campaign moved, nothing else changed).
"""
import shutil
import time
from pathlib import Path

SCRATCH = Path("/tmp/claude-1000/-home-ubuntu-kapso--claude-worktrees-kapso-plugin/5b2d9ebf-e9fa-4e9a-859e-c54e838342de/scratchpad/wp7")
SRC = SCRATCH / "machine-campaign" / "churn-campaign"
WORK = SCRATCH / "codex-proof" / "work"
DST = WORK / "churn-campaign"
OLD_HOME = b"/home/ubuntu/proof/work"
NEW_HOME = str(WORK).encode()

assert SRC.is_dir(), SRC
if DST.exists():
    kept = WORK / f"churn-campaign-devbox-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    DST.rename(kept)
    print(f"the box's own campaign kept at {kept.name}")
shutil.copytree(SRC, DST, symlinks=True)
for gone in (DST / ".kapso" / "deployments", DST / ".kapso" / "sessions" / "deployment"):
    if gone.exists():
        shutil.rmtree(gone)
rewritten = 0
for path in DST.rglob("*"):
    if not path.is_file() or ".git" in path.parts:
        continue
    data = path.read_bytes()
    if OLD_HOME in data:
        path.write_bytes(data.replace(OLD_HOME, NEW_HOME))
        rewritten += 1
print(f"restored at {DST}; {rewritten} files now name the box's work directory")
