"""The engine's own refusal around a deployment."""


class DeployError(ValueError):
    """What a deployment refuses, in one line a person acts on: no such
    target, a campaign whose tracked files differ from the delivered
    commit, a result the engine cannot accept after the session's one
    resume, a session that failed or was cut, a script that exited
    non-zero, a deployment that cannot be opened, a call on one that is
    not running. The CLI prints it as its message, with the other engine
    errors."""
