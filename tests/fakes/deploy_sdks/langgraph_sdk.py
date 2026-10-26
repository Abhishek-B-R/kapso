"""A fake LangGraph SDK for the target scripts' tests: threads are
numbered as they are created, runs echo their input on their thread."""

import os
from pathlib import Path


def _log(line):
    Path(os.environ["FAKE_LOG"]).open("a").write(line + "\n")


class _Threads:
    created = 0

    async def create(self):
        _Threads.created += 1
        _log(f"sdk threads.create {_Threads.created}")
        return {"thread_id": f"thread-{_Threads.created}"}

    async def delete(self, thread_id):
        _log(f"sdk threads.delete {thread_id}")


class _Runs:
    async def wait(self, thread_id, assistant_id, input):
        _log(f"sdk runs.wait {thread_id} {assistant_id}")
        return {"thread": thread_id, "assistant": assistant_id, "messages": input["messages"]}


class _Assistants:
    async def search(self):
        _log("sdk assistants.search")
        return [{"assistant_id": "agent"}]


class _Client:
    def __init__(self, url):
        self.url = url
        self.threads = _Threads()
        self.runs = _Runs()
        self.assistants = _Assistants()


def get_client(url):
    _log(f"sdk get_client {url}")
    return _Client(url)
