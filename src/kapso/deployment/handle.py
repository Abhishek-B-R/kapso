"""`Software`: the handle on a deployment, built from its record
(docs/plans/redesign/wp5-deploy.md, "The call" and "Run kinds"). It runs
the deployed software by the record's run kind (a worker process for a
function, an HTTP call, the target's `scripts/run.py`), and stops, starts,
checks and reads it through the target's scripts with the deployment's
values in their environment, writing the state back into the record so
another process sees it. `Software.open(campaign, number)` is the same
handle from any later process."""

import http.client
import json
import os
import select
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlsplit

from kapso.core.config import load_config
from kapso.deployment.errors import DeployError
from kapso.deployment.record import DeploymentRecord, RUNNING, STOPPED, open_record, read_record
from kapso.deployment.targets import RUN_SCRIPT, SCRIPTS_DIR

FUNCTION, HTTP, SCRIPT = "function", "http", "script"
RUN_KINDS = (FUNCTION, HTTP, SCRIPT)
START, STOP, HEALTH, LOGS = "start.sh", "stop.sh", "health.sh", "logs.sh"
# A lifecycle script's stdout lines that write back into the record.
ENDPOINT_LINE = "KAPSO_ENDPOINT="
VALUE_LINE = "KAPSO_VALUE_"
WORKER_LOG = "worker.log"
ENV_FILE = ".env"
_POLL_SECONDS = 0.05


def _communicate(process: subprocess.Popen, payload: Optional[str], deadline_seconds: float) -> Optional[Tuple[str, str]]:
    """The process's stdout and stderr once it ends, or None when it is
    still running at the deadline, killed then. Pumped in a thread so a
    large output never blocks it, and bounded without an exception."""
    collected: Dict[str, str] = {}

    def pump() -> None:
        collected["out"], collected["err"] = process.communicate(payload)

    thread = threading.Thread(target=pump, daemon=True)
    thread.start()
    thread.join(timeout=deadline_seconds)
    if thread.is_alive():
        process.kill()
        thread.join()
        return None
    return collected["out"], collected["err"]


class Software:
    """A deployment, running or not: `run(inputs)`, `stop()`, `start()`,
    `is_healthy()`, `logs()`, and the record's facts."""

    def __init__(self, record: DeploymentRecord, *, call_timeout: float, script_timeout: float):
        self._record = record
        self._call_timeout = float(call_timeout)
        self._script_timeout = float(script_timeout)
        self._lines: List[str] = []
        self._worker: Optional[subprocess.Popen] = None

    @classmethod
    def open(cls, campaign: Union[str, Path], number: Optional[int] = None, config: Optional[str] = None) -> "Software":
        """The campaign's deployment of that number, or its highest; the
        timeouts from the config file (the packaged defaults without one)."""
        deployment = load_config(config)["deployment"]
        software = cls(
            open_record(Path(campaign), number),
            call_timeout=deployment["call_timeout"], script_timeout=deployment["script_timeout"],
        )
        software._check_files()
        return software

    # ------------------------------------------------------------- facts

    @property
    def number(self) -> int:
        return self._record.number

    @property
    def campaign(self) -> Path:
        return self._record.campaign

    @property
    def state(self) -> str:
        """Read from the record each time: a stop from another process shows."""
        self._record = read_record(self._record.directory)
        return self._record.state

    @property
    def target(self) -> str:
        return self._record.data["target"]

    @property
    def endpoint(self) -> Optional[str]:
        return self._record.data["endpoint"]

    @property
    def workspace(self) -> Path:
        return self._record.workspace

    @property
    def record(self) -> Path:
        return self._record.path

    @property
    def target_dir(self) -> Path:
        """The target's skill directory copied beside the record: the scripts every call runs."""
        return self._record.target_dir

    @property
    def values(self) -> Dict[str, str]:
        return dict(self._record.data["values"])

    @property
    def run_kind(self) -> str:
        return self._record.data["result"]["run"]["kind"]

    @property
    def proof(self) -> Optional[Dict[str, Any]]:
        """The call the session proved: what `run()` takes, and what it answered."""
        result = self._record.data["result"]
        return None if result is None else result["proof"]

    def __repr__(self) -> str:
        return f"Software(deployment {self.number} of {self.campaign}, {self.target}, {self.state})"

    # -------------------------------------------------------------- calls

    def run(self, inputs: Union[Dict[str, Any], str, bytes]) -> Dict[str, Any]:
        """One call: `{"status": "success", "output": …}` or
        `{"status": "error", "error": …}`; refused while the deployment is
        not running."""
        state = self.state
        if state != RUNNING:
            way_out = "start() it" if state == STOPPED else (self._record.data["error"] or "it never ran")
            raise DeployError(f"deployment {self.number} is {state}; {way_out}")
        kind = self.run_kind
        if kind == FUNCTION:
            return self._run_function(inputs)
        if kind == HTTP:
            return self._run_http(inputs)
        if not self._script(RUN_SCRIPT):
            raise DeployError(f"the {self.target} target has no {SCRIPTS_DIR}/{RUN_SCRIPT}; see logs()")
        return self._run_script(inputs)

    def run_batch(self, inputs_list: List[Any]) -> List[Dict[str, Any]]:
        return [self.run(inputs) for inputs in inputs_list]

    def __call__(self, inputs: Union[Dict[str, Any], str, bytes]) -> Dict[str, Any]:
        return self.run(inputs)

    def _run_http(self, inputs: Any) -> Dict[str, Any]:
        run = self._record.data["result"]["run"]
        url = urlsplit(run["url"])
        connection_class = http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
        connection = connection_class(url.hostname, url.port, timeout=self._call_timeout)
        connection.request(
            "POST", run["path"], body=json.dumps(inputs), headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        connection.close()
        if 200 <= response.status < 300:
            return {"status": "success", "output": json.loads(body)}
        return {"status": "error", "error": f"{response.status} from {run['url']}{run['path']}: {body}"}

    def _run_script(self, inputs: Any) -> Dict[str, Any]:
        process = subprocess.Popen(
            [self._record.data["interpreter"], str(self._script(RUN_SCRIPT))],
            cwd=self.workspace, env=self._environment(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        ended = _communicate(process, json.dumps(inputs), self._call_timeout)
        if ended is None:
            return {"status": "error", "error": f"{RUN_SCRIPT} did not answer within {self._call_timeout:g} s and was killed"}
        out, err = ended
        if process.returncode != 0:
            return {"status": "error", "error": err.strip() or f"{RUN_SCRIPT} exited {process.returncode}"}
        return {"status": "success", "output": json.loads(out)}

    # ------------------------------------------------------------- worker

    def _worker_log(self) -> Path:
        return self._record.directory / WORKER_LOG

    def _ensure_worker(self) -> Optional[str]:
        """A worker answering pings, started when there is none; the
        reason (its log's tail) when it cannot start."""
        if self._worker is not None and self._worker.poll() is None:
            return None
        run = self._record.data["result"]["run"]
        command = [
            self._record.data["interpreter"], "-m", "kapso.deployment.worker",
            str(self.workspace), run["module"], run["callable"],
        ]
        env_file = self.workspace / ENV_FILE
        if env_file.is_file():
            command.append(str(env_file))
        with self._worker_log().open("a", encoding="utf-8") as log:
            self._worker = subprocess.Popen(
                command, cwd=self.workspace, env=self._environment(), stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=log, text=True,
            )
        reply = self._ask_worker({"ping": True})
        return None if reply == {"pong": True} else reply["error"]

    def _ask_worker(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """One request line to the worker and its reply line, bounded by
        the call timeout; a worker that ends (its function raised, its
        import failed) answers with the error from its log."""
        worker = self._worker
        worker.stdin.write(json.dumps(request) + "\n")
        worker.stdin.flush()
        deadline = time.monotonic() + self._call_timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                worker.kill()
                worker.wait()
                self._worker = None
                return {"error": f"the function did not answer within {self._call_timeout:g} s; its worker was ended"}
            readable, _, _ = select.select([worker.stdout], [], [], min(remaining, _POLL_SECONDS))
            if readable:
                line = worker.stdout.readline()
                if line:
                    return json.loads(line)
                worker.wait()
                self._worker = None
                return {"error": self._worker_log_tail()}
            if worker.poll() is not None:
                self._worker = None
                return {"error": self._worker_log_tail()}

    def _worker_log_tail(self) -> str:
        log = self._worker_log()
        lines = log.read_text(encoding="utf-8").splitlines() if log.is_file() else []
        return "\n".join(lines[-30:]) or "the worker ended without a message"

    def _end_worker(self) -> None:
        if self._worker is not None and self._worker.poll() is None:
            self._worker.kill()
            self._worker.wait()
        self._worker = None

    def _run_function(self, inputs: Any) -> Dict[str, Any]:
        failure = self._ensure_worker()
        if failure is not None:
            return {"status": "error", "error": failure}
        reply = self._ask_worker({"inputs": inputs})
        if "error" in reply:
            return {"status": "error", "error": reply["error"]}
        return {"status": "success", "output": reply["output"]}

    # ---------------------------------------------------------- lifecycle

    def stop(self) -> None:
        """The target's stop script (its failure noted, never raised), the
        worker ended, the state `stopped`."""
        if self._script(STOP):
            code, _out, err = self._lifecycle(STOP)
            if code != 0:
                self._lines.append(f"{STOP} exited {code}: {err.strip()}")
        self._end_worker()
        self._record.set_state(STOPPED)
        self._lines.append(f"stopped deployment {self.number}")

    def start(self) -> None:
        """The target's start script (its failure raised), the worker
        started, the state `running`."""
        if self._script(START):
            code, _out, err = self._lifecycle(START)
            if code != 0:
                raise DeployError(f"deployment {self.number}: {START} exited {code}: {err.strip()}")
        if self.run_kind == FUNCTION:
            failure = self._ensure_worker()
            if failure is not None:
                raise DeployError(f"deployment {self.number}: the function's worker did not start: {failure}")
        self._record.set_state(RUNNING)
        self._lines.append(f"started deployment {self.number}")

    def is_healthy(self) -> bool:
        """Running by the record, answering by the target's health script
        (the state alone without one), and the worker answering a ping
        for a function."""
        if self.state != RUNNING:
            return False
        if self._script(HEALTH):
            code, _out, _err = self._lifecycle(HEALTH)
            if code != 0:
                return False
        if self.run_kind == FUNCTION:
            return self._ensure_worker() is None
        return True

    def logs(self) -> str:
        """The engine's own lines, the target's logs script's output, and a
        function's worker log."""
        parts = list(self._lines)
        if self._script(LOGS):
            _code, out, _err = self._lifecycle(LOGS)
            parts.append(out.rstrip("\n"))
        if self.run_kind == FUNCTION and self._worker_log().is_file():
            parts.append(self._worker_log().read_text(encoding="utf-8").rstrip("\n"))
        return "\n".join(part for part in parts if part)

    def __enter__(self) -> "Software":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.stop()
        return False

    # ------------------------------------------------------------ scripts

    def _script(self, name: str) -> Optional[Path]:
        path = self._record.target_dir / SCRIPTS_DIR / name
        return path if path.is_file() else None

    def _environment(self) -> Dict[str, str]:
        """The deployment's values, as every script and the worker see them."""
        data = self._record.data
        env = {
            **os.environ,
            "KAPSO_DEPLOYMENT_NAME": data["deployment_name"],
            "KAPSO_PORT": str(data["port"]),
            "KAPSO_NUMBER": str(data["number"]),
            "KAPSO_WORKSPACE": str(self.workspace),
            "KAPSO_RECORD_DIR": str(self._record.directory),
            "KAPSO_TARGET_DIR": str(self._record.target_dir),
            "KAPSO_INTERPRETER": data["interpreter"],
        }
        if data["endpoint"]:
            env["KAPSO_ENDPOINT"] = data["endpoint"]
        if (self.workspace / ENV_FILE).is_file():
            env["KAPSO_ENV_FILE"] = str(self.workspace / ENV_FILE)
        if data["harness_root"]:
            env["KAPSO_HARNESS_ROOT"] = data["harness_root"]
        for name, value in data["options"].items():
            env[f"KAPSO_OPTION_{name.upper()}"] = str(value)
        for name, value in data["values"].items():
            env[f"{VALUE_LINE}{name.upper()}"] = str(value)
        return env

    def _lifecycle(self, name: str) -> Tuple[int, str, str]:
        """One lifecycle script from the record's target directory, the
        workspace as its working directory; its update lines written into
        the record when it succeeds. A script still running at the
        timeout is killed and counts as failed."""
        process = subprocess.Popen(
            ["bash", str(self._script(name))], cwd=self.workspace, env=self._environment(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        ended = _communicate(process, None, self._script_timeout)
        if ended is None:
            return 1, "", f"{name} did not end within {self._script_timeout:g} s and was killed"
        out, err = ended
        if process.returncode == 0:
            self._take_updates(out)
        return process.returncode, out, err

    def _take_updates(self, out: str) -> None:
        changed = False
        for line in out.splitlines():
            if line.startswith(ENDPOINT_LINE):
                self._record.data["endpoint"] = line[len(ENDPOINT_LINE):].strip()
                changed = True
            elif line.startswith(VALUE_LINE) and "=" in line:
                key, value = line[len(VALUE_LINE):].split("=", 1)
                self._record.data["values"][key.lower()] = value.strip()
                changed = True
        if changed:
            self._record.write()

    def _check_files(self) -> None:
        for label, path in (("workspace", self.workspace), ("target directory", self._record.target_dir)):
            if not path.is_dir():
                raise DeployError(f"deployment {self.number} of {self.campaign}: its {label} is gone ({path})")
        root = self._record.data["harness_root"]
        if root and not Path(root).is_dir():
            raise DeployError(f"deployment {self.number} of {self.campaign}: its harness is gone ({root})")
