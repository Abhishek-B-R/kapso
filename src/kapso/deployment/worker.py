"""The `function` run kind's worker (docs/plans/redesign/wp5-deploy.md):
one process per `Software` handle, started by it as

    <interpreter> -m kapso.deployment.worker <workspace> <module> <callable> [<env-file>]

in the workspace, the env file's values set before the import. It
imports `<workspace>/<module>.py` once and answers one JSON line per
request line: `{"ping": true}` with `{"pong": true}`, `{"inputs": …}`
with `{"output": <callable>(inputs)}`. The solution's own prints go to
stderr, so the reply channel stays clean. A call whose function raises
ends the worker with the traceback on stderr: the handle reports it as
the call's error and starts a worker again for the next call."""

import importlib
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main(argv) -> None:
    workspace, module_name, callable_name = argv[1:4]
    if len(argv) > 4:
        load_dotenv(argv[4], override=True)
    os.chdir(workspace)
    sys.path.insert(0, str(Path(workspace).resolve()))
    # The reply channel is the original stdout; the solution's prints go
    # to stderr.
    channel = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8")
    sys.stdout = sys.stderr
    function = getattr(importlib.import_module(module_name), callable_name)
    for line in sys.stdin:
        request = json.loads(line)
        reply = {"pong": True} if request.get("ping") else {"output": function(request["inputs"])}
        channel.write(json.dumps(reply) + "\n")
        channel.flush()


if __name__ == "__main__":
    main(sys.argv)
