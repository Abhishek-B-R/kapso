"""A fake BentoML SDK for the target scripts' tests: the deployment's
client answers with what it was given."""

import os
from pathlib import Path


class _Client:
    def __init__(self, name):
        self.name = name

    def predict(self, inputs):
        Path(os.environ["FAKE_LOG"]).open("a").write(f"sdk predict {self.name}\n")
        return {"deployment": self.name, "echo": inputs}


class _Deployment:
    def __init__(self, name):
        self.name = name

    def get_client(self):
        return _Client(self.name)


class deployment:
    @staticmethod
    def get(name):
        return _Deployment(name)
