"""
Campaign Gate
=============

Three tools over the campaign verbs, for a host session only (the
engineer's own coding-agent session; docs/plans/redesign/wp7-plugin.md):
``kapso_build_start`` launches a campaign detached, ``kapso_status`` reads
one, ``kapso_stop`` ends one. Each runs the verb on the server's own
interpreter (``sys.executable -m kapso.cli``, never ``kapso`` from PATH)
as a subprocess with the server's working directory, so ``.env`` and every
relative path resolve as the person's shell would, outside the host's
shell sandbox. Outcomes are the verb's return code and output, returned
as data; a receipt that does not parse raises. The gate reads nothing
from the environment: the config path and the working directory reach
it through its ``GateConfig`` params (``config_path``, ``cwd``) from
``kapso-mcp``. A campaign session never gets this gate
(``GateDefinition.host_only``), and its tools refuse when the server runs
inside a campaign directory: a campaign never launches a campaign.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    Tool = None
    TextContent = None

from kapso.execution.inbox import launch_receipt_path
from kapso.execution.observability import OperationStatusView
from kapso.gated_mcp.gates.base import ToolGate

START_TOOL = "kapso_build_start"
STATUS_TOOL = "kapso_status"
STOP_TOOL = "kapso_stop"
EXPERIMENT_HISTORY_NAME = "experiment_history.json"
_RULES = (
    "Never inside a Kapso campaign session: a campaign does not launch, read or stop a campaign. "
    "One launch per request, never a second: the campaign outlives this session and is followed "
    "with kapso_status or `kapso watch <campaign> --follow`. A campaign that ends WAITING ON YOU "
    "has paused for something only a person can provide; it is answered with "
    "`kapso inbox reply <campaign> <id> \"<note>\"`, a note and never a value, not restarted."
)


def inside_campaign(start: Path) -> Optional[Path]:
    """The nearest ancestor of `start` (itself included) that is a
    campaign directory, else None."""
    for candidate in (start, *start.parents):
        if (candidate / ".kapso" / EXPERIMENT_HISTORY_NAME).is_file():
            return candidate
    return None


def _campaign_dir(cwd: Path, output: str) -> Path:
    """The campaign directory as the verb resolves it: `~` expanded first,
    then joined to the working directory (joining first would bury the
    tilde)."""
    return (cwd / Path(output).expanduser()).resolve()


class CampaignGate(ToolGate):
    """The campaign verbs as tools of a host session."""

    name = "campaign"
    description = "Launch, read and stop Kapso campaigns from this session"

    def get_tools(self) -> List["Tool"]:
        if not HAS_MCP:
            return []
        path = {"type": "string", "description": "The campaign directory (the launch's output)"}
        return [
            Tool(
                name=START_TOOL,
                description=(
                    "Launch a Kapso campaign in a session of its own and return at once with its "
                    "receipt (pid, log, status path, watch line). Pass `brief` (the path of a brief "
                    "file, kapso-build's) or `goal` (one line), `repo` and `output` (an empty directory "
                    "outside the repository). A harness or a bank not yet in the store is fetched before "
                    "the answer comes, which can take minutes the first time. " + _RULES
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "brief": {"type": "string", "description": "The brief file's path (objective, how it is measured, baseline, target, rules, budget)"},
                        "goal": {"type": "string", "description": "The objective in one line, when there is no brief file"},
                        "repo": {"type": "string", "description": "The repository to seed the campaign with: a directory or a GitHub URL"},
                        "output": {"type": "string", "description": "The campaign directory: empty, outside the repository"},
                        "evaluation": {"type": "string", "description": "The evaluation directory, copied and protected"},
                        "data": {"type": "string", "description": "The data directory, copied to kapso_datasets/"},
                        "budget_minutes": {"type": "number", "description": "The campaign's time budget, minutes"},
                        "budget_experiments": {"type": "integer", "description": "The number of experiments to run"},
                        "harness": {"type": "string", "description": "The harness to build with: a bundled name, a directory, a git reference"},
                        "experience": {"type": "array", "items": {"type": "string"}, "description": "The sources the build is served (mine, mine:all, leeroopedia, a bank reference, an index name); each must exist"},
                        "config": {"type": "string", "description": "A config file; default: the one this server runs with"},
                    },
                    "required": ["repo", "output"],
                },
            ),
            Tool(
                name=STATUS_TOOL,
                description=(
                    "How a campaign is doing, as data: `kapso watch <path> --json` (state, phase, best "
                    "score, budget left), or the launch state before the status exists (starting, "
                    "stopped, no_status). Read it before any stop or resume. " + _RULES
                ),
                inputSchema={"type": "object", "properties": {"path": path}, "required": ["path"]},
            ),
            Tool(
                name=STOP_TOOL,
                description=(
                    "End a running campaign: `kapso build --output <path> --stop`. Its checkpoint "
                    "stays; `kapso build --output <path> --resume --detach` continues it. A campaign "
                    "whose status is terminal or whose writer is gone is refused by state. " + _RULES
                ),
                inputSchema={"type": "object", "properties": {"path": path}, "required": ["path"]},
            ),
        ]

    async def handle_call(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[List["TextContent"]]:
        if not HAS_MCP or tool_name not in (START_TOOL, STATUS_TOOL, STOP_TOOL):
            return None
        cwd = Path(self.get_param("cwd"))
        campaign = inside_campaign(cwd)
        if campaign is not None:
            answer: Dict[str, Any] = {
                "error": (
                    f"this session runs inside the campaign at {campaign}: a campaign never launches, "
                    "reads or stops a campaign; run the verb from the project directory"
                ),
            }
            if tool_name == START_TOOL:
                answer["accepted"] = False
            if tool_name == STOP_TOOL:
                answer["stopped"] = False
        elif tool_name == START_TOOL:
            answer = self._start(arguments, cwd)
        elif tool_name == STATUS_TOOL:
            answer = self._status(arguments["path"], cwd)
        else:
            answer = self._stop(arguments["path"], cwd)
        return [TextContent(type="text", text=json.dumps(answer, indent=1))]

    def _start(self, arguments: Dict[str, Any], cwd: Path) -> Dict[str, Any]:
        if shutil.which("kapso") is None:
            return {
                "accepted": False, "exit": None,
                "error": "kapso is not on PATH: a campaign runs for hours and needs the CLI the person follows it with; run /kapso:setup first",
            }
        brief, goal = arguments.get("brief"), arguments.get("goal")
        if bool(brief) == bool(goal):
            return {"accepted": False, "exit": None, "error": "pass exactly one of `brief` (a file's path) and `goal` (one line)"}
        argv = ["build", "--brief", brief] if brief else ["build", "--goal", goal]
        argv += ["--repo", arguments["repo"], "--output", arguments["output"]]
        for key, flag in (("evaluation", "--evaluation"), ("data", "--data"), ("harness", "--harness")):
            if arguments.get(key):
                argv += [flag, arguments[key]]
        if arguments.get("budget_minutes") is not None:
            argv += ["--budget-minutes", str(arguments["budget_minutes"])]
        if arguments.get("budget_experiments") is not None:
            argv += ["--budget-experiments", str(arguments["budget_experiments"])]
        if arguments.get("experience"):
            argv += ["--experience", ",".join(arguments["experience"])]
        config = arguments.get("config") or self.get_param("config_path")
        if config:
            argv += ["--config", config]
        argv.append("--detach")
        run = self._verb(argv, cwd)
        if run.returncode != 0:
            return {"accepted": False, "exit": run.returncode, "error": run.stderr.strip() or run.stdout.strip()}
        campaign = _campaign_dir(cwd, arguments["output"])
        receipt = json.loads(launch_receipt_path(campaign).read_text(encoding="utf-8"))
        return {
            "accepted": True,
            "pid": receipt["pid"],
            "log": receipt["log"],
            "status": str(campaign / ".kapso" / "status.json"),
            "watch": f"kapso watch {campaign} --follow",
            "campaign": str(campaign),
            "started_at": receipt["started_at"],
        }

    def _status(self, path: str, cwd: Path) -> Dict[str, Any]:
        run = self._verb(["watch", path, "--json"], cwd)
        if run.returncode != 0 and not run.stdout.strip():
            return {"exit": run.returncode, "error": run.stderr.strip()}
        # The verb prints the status, or the launch state, as JSON; a dead
        # launch is printed and exits 1, so the exit code travels with it.
        return {**json.loads(run.stdout), "exit": run.returncode}

    def _stop(self, path: str, cwd: Path) -> Dict[str, Any]:
        campaign = _campaign_dir(cwd, path)
        status = campaign / ".kapso" / "status.json"
        # The writer's pid is the status file's; the verb's prose is not parsed.
        pid = OperationStatusView(status).data.get("pid") if status.is_file() else None
        argv = ["build", "--output", str(campaign), "--stop"]
        config = self.get_param("config_path")
        if config:
            argv += ["--config", config]
        run = self._verb(argv, cwd)
        if run.returncode != 0:
            return {"stopped": False, "exit": run.returncode, "error": run.stderr.strip() or run.stdout.strip()}
        return {"stopped": True, "pid": pid}

    @staticmethod
    def _verb(argv: List[str], cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "kapso.cli", *argv], cwd=str(cwd), capture_output=True, text=True,
        )
