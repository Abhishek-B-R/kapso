"""The bundled targets' scripts, run for real against fake executables on
PATH and fake SDK modules (docs/plans/redesign/wp5-deploy.md, Tests): what
each script does with the deployment's variables is what today's runners
did, and what `Software` relies on."""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

import kapso
from kapso.deployment.targets import BUNDLED_DIR

FAKE_SDKS = Path(__file__).resolve().parent / "fakes" / "deploy_sdks"
# The engine's own source, for the worker the local target's deploy
# script runs in `$KAPSO_INTERPRETER`.
ENGINE_SRC = Path(kapso.__file__).resolve().parent.parent
NAME = "churn-3f9a1c-2"

DOCKER_SHIM = """#!/usr/bin/env bash
echo "$*" >> "$FAKE_LOG"
case "$1" in
  build) exit 0 ;;
  run) touch "$FAKE_STATE"; echo containerid ;;
  rm) rm -f "$FAKE_STATE" ;;
  inspect) if [ -f "$FAKE_STATE" ]; then echo true; else exit 1; fi ;;
  logs) echo "line one"; echo "line two" ;;
esac
"""
LOGGING_SHIM = """#!/usr/bin/env bash
echo "$*" >> "$FAKE_LOG"
"""
BENTOML_SHIM = """#!/usr/bin/env bash
echo "$*" >> "$FAKE_LOG"
if [ "$1 $2" = "deployment get" ]; then
  echo '{"name": "'"$3"'", "status": "running", "endpoint_urls": ["https://'"$3"'.bentoml.cloud"]}'
fi
"""
MODAL_SHIM = """#!/usr/bin/env bash
echo "$*" >> "$FAKE_LOG"
if [ "$1 $2" = "app list" ]; then echo "kapso-churn-3f9a1c-2   deployed   2m ago"; fi
"""


class _Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200 if self.path == "/health" else 404)
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture
def health_server():
    server = HTTPServer(("127.0.0.1", 0), _Health)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_port
    server.shutdown()


@pytest.fixture
def rig(tmp_path):
    """A workspace, a record directory, the shims on PATH and the fake SDKs
    on PYTHONPATH; `run(target, script, **values)` runs one script as the
    engine does, from the workspace, and `log()` is what the shims saw."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    record = tmp_path / "record"
    record.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, text in (("docker", DOCKER_SHIM), ("modal", MODAL_SHIM), ("bentoml", BENTOML_SHIM), ("langgraph", LOGGING_SHIM)):
        shim = bin_dir / name
        shim.write_text(text)
        shim.chmod(0o755)
    log = tmp_path / "shims.log"
    env_file = workspace / ".env"
    env_file.write_text("GREETING=hello\n")

    class Rig:
        def run(self, target, script, *, port=0, check=True, stdin=None, options=None, **values):
            env = {
                **{k: v for k, v in os.environ.items() if k in ("HOME", "LANG")},
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "PYTHONPATH": f"{FAKE_SDKS}:{ENGINE_SRC}",
                "FAKE_LOG": str(log),
                "FAKE_STATE": str(tmp_path / "container.state"),
                "KAPSO_DEPLOYMENT_NAME": NAME,
                "KAPSO_PORT": str(port),
                "KAPSO_NUMBER": "2",
                "KAPSO_WORKSPACE": str(workspace),
                "KAPSO_RECORD_DIR": str(record),
                "KAPSO_TARGET_DIR": str(target if isinstance(target, Path) else BUNDLED_DIR / target),
                "KAPSO_INTERPRETER": sys.executable,
                "KAPSO_ENV_FILE": str(env_file),
                **{f"KAPSO_VALUE_{key.upper()}": value for key, value in values.items()},
                **{f"KAPSO_OPTION_{key.upper()}": value for key, value in (options or {}).items()},
            }
            root = target if isinstance(target, Path) else BUNDLED_DIR / target
            path = root / "scripts" / script
            command = ["bash", str(path)] if script.endswith(".sh") else [sys.executable, str(path)]
            return subprocess.run(command, cwd=workspace, env=env, input=stdin, capture_output=True, text=True, check=check, timeout=60)

        def log(self):
            return log.read_text().splitlines() if log.exists() else []

        workspace_dir = workspace
        record_dir = record

    return Rig()


# -------------------------------------------------------------------- local

def test_local_deploy_proves_the_entry_point_through_the_worker_with_the_callers_variables(rig):
    (rig.workspace_dir / "main.py").write_text("import os\nGREETING = os.environ['GREETING']\n\ndef predict(inputs):\n    return {'greeting': GREETING}\n")
    assert rig.run("local", "deploy.sh").stdout.strip() == "main.predict imports in the engine's worker"
    (rig.workspace_dir / "main.py").write_text("def other(inputs):\n    return inputs\n")
    failed = rig.run("local", "deploy.sh", check=False)
    assert failed.returncode == 1 and "main.py has no module-level callable predict" in failed.stderr
    (rig.workspace_dir / "main.py").write_text("import nothing_of_the_kind\n")
    failed = rig.run("local", "deploy.sh", check=False)
    assert failed.returncode == 1 and "No module named 'nothing_of_the_kind'" in failed.stderr


# ------------------------------------------------------------------- docker

def test_docker_builds_runs_with_the_env_file_port_and_gpu_then_waits_for_health(rig, health_server):
    (rig.workspace_dir / ".dockerignore").write_text("*.md\n")
    out = rig.run("docker", "deploy.sh", port=health_server, container_port="9000", gpu="all")
    assert out.stdout.strip().endswith(f"answers on port {health_server}")
    assert rig.log() == [
        f"rm -f kapso-{NAME}",
        f"build -t kapso-{NAME} .",
        f"run -d --name kapso-{NAME} -p {health_server}:9000 --restart unless-stopped --env-file {rig.workspace_dir / '.env'} --gpus all kapso-{NAME}",
    ]
    # The engine's own files and the env file stay out of the image; the
    # person's lines stay.
    lines = (rig.workspace_dir / ".dockerignore").read_text().splitlines()
    assert lines[0] == "*.md" and {".env", ".git", ".claude", ".agents", ".codex", ".kapso*", "__pycache__", "*.pyc", "kapso_evaluation", "prepared"} <= set(lines)
    assert rig.run("docker", "health.sh", port=health_server, check=False).returncode == 0
    assert rig.run("docker", "logs.sh", port=health_server).stdout == "line one\nline two\n"


def test_docker_stop_saves_the_logs_and_start_recreates_the_same_container(rig, health_server):
    rig.run("docker", "deploy.sh", port=health_server, container_port="8000", gpu="none")
    rig.run("docker", "stop.sh", port=health_server, container_port="8000", gpu="none")
    assert (rig.record_dir / "container.log").read_text() == "line one\nline two\n"
    assert rig.log()[-2:] == [f"logs --tail 200 kapso-{NAME}", f"rm -f kapso-{NAME}"]
    assert rig.run("docker", "health.sh", port=health_server, check=False).returncode == 1
    # Without the container, the logs are what the stop saved.
    assert rig.run("docker", "logs.sh", port=health_server).stdout == "line one\nline two\n"
    rig.run("docker", "start.sh", port=health_server, container_port="8000", gpu="none")
    assert rig.log()[-1] == (
        f"run -d --name kapso-{NAME} -p {health_server}:8000 --restart unless-stopped --env-file {rig.workspace_dir / '.env'} kapso-{NAME}"
    )
    assert rig.run("docker", "health.sh", port=health_server, check=False).returncode == 0


# -------------------------------------------------------------------- modal

def test_modal_deploys_looks_the_function_up_calls_it_and_stops_without_a_tty(rig):
    app = f"kapso-{NAME}"
    rig.run("modal", "deploy.sh", app=app)
    assert rig.log() == ["deploy modal_app.py", f"sdk hydrate {app}/predict"]
    answer = rig.run("modal", "run.py", app=app, stdin=json.dumps({"x": 1}))
    assert json.loads(answer.stdout) == {"app": app, "echo": {"x": 1}}
    rig.run("modal", "stop.sh", app=app)
    assert rig.log()[-1] == f"app stop {app} --yes"
    assert rig.run("modal", "logs.sh", app=app).stdout.splitlines() == [
        f"{app}   deployed   2m ago", f"stream its logs with: modal app logs {app}",
    ]
    rig.run("modal", "start.sh", app=app)
    assert rig.log()[-2:] == ["deploy modal_app.py", f"sdk hydrate {app}/predict"]


# ------------------------------------------------------------------ bentoml

def test_bentoml_deploys_through_the_workspace_script_and_a_start_reports_the_new_endpoint(rig):
    name = f"kapso-{NAME}"
    (rig.workspace_dir / "deploy.py").write_text("print('deploying')\n")
    out = rig.run("bentoml", "deploy.sh", deployment=name)
    assert out.stdout.startswith("deploying\n{") and f"deployment get {name} -o json" in rig.log()
    assert rig.run("bentoml", "health.sh", deployment=name, check=False).returncode == 0
    answer = rig.run("bentoml", "run.py", deployment=name, stdin=json.dumps({"x": 2}))
    assert json.loads(answer.stdout) == {"deployment": name, "echo": {"x": 2}}
    rig.run("bentoml", "stop.sh", deployment=name)
    assert rig.log()[-1] == f"deployment terminate {name} --wait"
    started = rig.run("bentoml", "start.sh", deployment=name)
    assert rig.log()[-2] == f"deployment start {name}" and rig.log()[-1] == f"deployment get {name} -o json"
    assert started.stdout.splitlines()[-1] == f"KAPSO_ENDPOINT=https://{name}.bentoml.cloud"


# ---------------------------------------------------------------- langgraph

def test_langgraph_keeps_one_thread_across_calls_and_deletes_it_on_stop(rig):
    url = "https://graph.example"
    rig.run("langgraph", "deploy.sh", deployment_url=url, assistant="agent")
    assert rig.log() == [f"deploy --name kapso-{NAME}"]
    first = json.loads(rig.run("langgraph", "run.py", deployment_url=url, assistant="agent", stdin=json.dumps({"text": "hi"})).stdout)
    second = json.loads(rig.run("langgraph", "run.py", deployment_url=url, assistant="agent", stdin=json.dumps({"messages": [{"role": "user", "content": "again"}]})).stdout)
    assert first == {"thread": "thread-1", "assistant": "agent", "messages": [{"role": "user", "content": "hi"}]}
    assert second["thread"] == "thread-1" and (rig.workspace_dir / ".kapso_langgraph_thread").read_text().strip() == "thread-1"
    assert rig.run("langgraph", "health.sh", deployment_url=url, check=False).returncode == 0
    assert rig.run("langgraph", "logs.sh", deployment_url=url, assistant="agent").stdout.splitlines() == [
        f"deployment: {url} (assistant agent)", "thread: thread-1",
    ]
    assert rig.log()[-1] == f"deploy logs --name kapso-{NAME}"
    stopped = rig.run("langgraph", "stop.sh", deployment_url=url)
    assert rig.log()[-1] == "sdk threads.delete thread-1" and not (rig.workspace_dir / ".kapso_langgraph_thread").exists()
    assert stopped.stdout.splitlines() == [
        "thread thread-1 deleted",
        f"the platform deployment kapso-{NAME} stays on LangSmith; to delete it: langgraph deploy list, then langgraph deploy delete <its id> --force",
    ]


# ------------------------------------------------------------ paper-trading

PAPER = Path(__file__).resolve().parent.parent / "examples" / "harnesses" / "trading" / "skills" / "paper-trading"
# What a session writes for the target: a runner with the two modes the
# target's scripts drive.
RUN_PAPER = """import json
import os
import sys
import time

at = sys.argv[sys.argv.index("--at") + 1] if "--at" in sys.argv else "latest"
cycle = {"bar": at, "orders": [], "equity": float(os.environ.get("KAPSO_OPTION_CASH", "100000"))}
if "--once" in sys.argv:
    print(json.dumps(cycle))
    sys.exit(0)
while True:
    print(json.dumps(cycle), flush=True)
    time.sleep(0.2)
"""


@pytest.fixture
def paper_runner(rig):
    """The runner in the workspace, and whatever loop is left ended."""
    (rig.workspace_dir / "deploy").mkdir()
    (rig.workspace_dir / "deploy" / "run_paper.py").write_text(RUN_PAPER)
    yield rig
    rig.run(PAPER, "stop.sh", check=False)


def test_paper_trading_runs_the_workspaces_runner_as_a_loop_and_one_cycle_on_demand(paper_runner):
    rig = paper_runner
    started = rig.run(PAPER, "deploy.sh")
    assert started.stdout.startswith("the paper runner runs (pid ") and started.stdout.strip().endswith("its log at deploy/paper.log")
    assert (rig.workspace_dir / "deploy" / "paper.pid").is_file()
    assert rig.run(PAPER, "health.sh", check=False).returncode == 0
    # One cycle on demand, as of a bar, with the call's cash option.
    answer = rig.run(PAPER, "run.py", stdin=json.dumps({"at": "2024-01-03"}), options={"cash": "5000"})
    assert json.loads(answer.stdout) == {"bar": "2024-01-03", "orders": [], "equity": 5000.0}
    assert '"bar": "latest"' in rig.run(PAPER, "logs.sh").stdout
    pid = int((rig.workspace_dir / "deploy" / "paper.pid").read_text())
    assert rig.run(PAPER, "stop.sh").stdout.strip() == f"the paper runner (pid {pid}) ended"
    assert rig.run(PAPER, "health.sh", check=False).returncode == 1 and not (rig.workspace_dir / "deploy" / "paper.pid").exists()
    # A pid file naming another process (a pid reused after a reboot) is
    # not the runner.
    (rig.workspace_dir / "deploy" / "paper.pid").write_text(f"{os.getpid()}\n")
    assert rig.run(PAPER, "health.sh", check=False).returncode == 1
    (rig.workspace_dir / "deploy" / "paper.pid").unlink()
    assert rig.run(PAPER, "start.sh").stdout.startswith("the paper runner runs (pid ")
    assert rig.run(PAPER, "health.sh", check=False).returncode == 0


def test_paper_trading_refuses_to_start_without_the_runner(rig):
    failed = rig.run(PAPER, "deploy.sh", check=False)
    assert failed.returncode == 1 and "no deploy/run_paper.py in the workspace" in failed.stderr
