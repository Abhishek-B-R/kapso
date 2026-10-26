"""One call of the deployed graph through the LangGraph SDK, on the one
thread this deployment keeps in the workspace (`.kapso_langgraph_thread`):
the inputs as JSON on stdin (`messages`, or `text` for one user message),
the final state as JSON on stdout. The SDK reads its own credentials
(LANGSMITH_API_KEY)."""

import asyncio
import json
import os
import sys
from pathlib import Path

from langgraph_sdk import get_client

THREAD_FILE = Path(".kapso_langgraph_thread")


def messages_of(inputs):
    if isinstance(inputs, dict) and "messages" in inputs:
        return inputs["messages"]
    if isinstance(inputs, dict) and "text" in inputs:
        return [{"role": "user", "content": inputs["text"]}]
    return [{"role": "user", "content": json.dumps(inputs)}]


async def main(inputs):
    client = get_client(url=os.environ["KAPSO_VALUE_DEPLOYMENT_URL"])
    if THREAD_FILE.is_file():
        thread_id = THREAD_FILE.read_text(encoding="utf-8").strip()
    else:
        thread_id = (await client.threads.create())["thread_id"]
        THREAD_FILE.write_text(thread_id + "\n", encoding="utf-8")
    result = await client.runs.wait(
        thread_id, os.environ.get("KAPSO_VALUE_ASSISTANT", "agent"), input={"messages": messages_of(inputs)},
    )
    print(json.dumps(result))


asyncio.run(main(json.load(sys.stdin)))
