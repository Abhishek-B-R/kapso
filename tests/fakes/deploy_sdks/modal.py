"""A fake Modal SDK for the target scripts' tests: the function looked up
by app name answers with what it was given."""

import os
from pathlib import Path


class _Function:
    def __init__(self, app, name):
        self.app = app
        self.name = name

    def hydrate(self):
        Path(os.environ["FAKE_LOG"]).open("a").write(f"sdk hydrate {self.app}/{self.name}\n")

    def remote(self, inputs):
        return {"app": self.app, "echo": inputs}


class Function:
    @staticmethod
    def from_name(app, name):
        return _Function(app, name)
