"""`check`: the structural rules a harness must meet before a run starts,
the warnings that make one weaker than it looks, and what this machine
lacks for it. Design: docs/research/harness-design.md section 8; the
plan: docs/plans/redesign/wp2-harness.md ("check").

A file that does not parse (YAML, JSON, front matter) raises the parser's
own error with its position (CLAUDE.md rule 2); the report holds the
structural problems of files that parsed. Nothing here reads a secret's
value: an environment reference is probed for presence by name, the
precedent being core/preflight.py's credential rows.
"""

import json
import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import dotenv_values, find_dotenv
from packaging.requirements import Requirement as Pin
from packaging.utils import canonicalize_name

from kapso.core.front_matter import read_front_matter
from kapso.core.preflight import Requirement
from kapso.harness.manifest import MODULES, Finding, Manifest, inspect_manifest

INSTRUCTIONS_DIR = "instructions"
GUARDRAILS_PAGE = "guardrails.md"
SKILLS_DIR = "skills"
SKILL_FILE = "SKILL.md"
AGENTS_DIR = "agents"
MCP_FILE = "mcp.json"
HOOKS_DIR = "hooks"
HOOK_FILE = "hook.json"
PLUGIN_ROOT = "${PLUGIN_ROOT}"
RESERVED_SERVER_NAMES = ("gated-knowledge",)
HOOK_EVENTS = (
    "SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "PermissionRequest", "Stop", "SubagentStart", "SubagentStop", "PreCompact", "PostCompact",
)
SECRET_NAME_WORDS = ("KEY", "TOKEN", "SECRET", "PASSWORD")
SECRET_PREFIXES = ("sk-", "kpsk_", "ghp_", "xoxb-")
HTTP_TYPES = ("streamable-http", "http")
# The interpreter a harness's own commands name: its servers, hooks and
# scripts run on it, so its requirements are checked there.
PYTHON_COMMAND = "python3"
# What that interpreter has installed, and the marker environment a pin's
# `; python_version < "3.12"` is read against: its own, not the engine's.
_INTERPRETER_REPORT = (
    "import importlib.metadata, json, os, platform, sys; "
    "print(json.dumps({"
    "'distributions': {d.metadata['Name']: d.version for d in importlib.metadata.distributions() if d.metadata['Name']}, "
    "'environment': {"
    "'implementation_name': sys.implementation.name, "
    "'implementation_version': '{}.{}.{}'.format(*sys.implementation.version[:3]), "
    "'os_name': os.name, 'platform_machine': platform.machine(), 'platform_release': platform.release(), "
    "'platform_system': platform.system(), 'platform_version': platform.version(), "
    "'python_full_version': platform.python_version(), 'platform_python_implementation': platform.python_implementation(), "
    "'python_version': '.'.join(platform.python_version_tuple()[:2]), 'sys_platform': sys.platform}}))"
)
_SERVER_NAME = re.compile(r"[A-Za-z0-9_-]+$")
_REFERENCE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
_OPAQUE = re.compile(r"^[A-Za-z0-9_-]{24,}$")
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_STDIO_KEYS = ("command", "args", "env", "cwd")
_HTTP_KEYS = ("type", "url", "headers")
_HOOK_ENTRY_KEYS = ("matcher", "hooks")
_HOOK_COMMAND_KEYS = ("type", "command", "timeout")


@dataclass(frozen=True)
class HarnessRequirement(Requirement):
    """A preflight row with the modules whose sessions need it, so a verb
    refuses on its own modules' rows and prints the rest as advisory."""
    modules: Tuple[str, ...] = ()


@dataclass
class CheckReport:
    failures: List[Finding] = field(default_factory=list)
    warnings: List[Finding] = field(default_factory=list)
    missing: List[HarnessRequirement] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)
    manifest: Optional[Manifest] = None

    def ok(self) -> bool:
        return not self.failures

    def missing_for(self, modules: Tuple[str, ...]) -> List[HarnessRequirement]:
        """The unmet rows any of `modules` needs."""
        return [row for row in self.missing if set(row.modules) & set(modules)]

    def summary(self) -> str:
        counts = ", ".join(
            f"{self.counts.get(kind, 0)} {kind}" for kind in ("skills", "agents", "servers", "hooks")
        )
        if self.ok():
            return f"check ok ({counts})"
        return f"check failed: {len(self.failures)} failure(s) ({counts})"

    def render(self) -> str:
        lines = [self.summary()]
        lines += [f"  fail   {finding}" for finding in self.failures]
        lines += [f"  warn   {finding}" for finding in self.warnings]
        for row in self.missing:
            modules = ", ".join(row.modules)
            lines.append(f"  needs  {row.label}: {row.fix}  [{modules}]")
        return "\n".join(lines)


def check_harness(root: Path, *, page_warning_lines: int, dotenv_path: Optional[str] = None) -> CheckReport:
    """Every rule of the Interface, against the directory as it is now."""
    root = Path(root).resolve()
    manifest, findings = inspect_manifest(root)
    report = CheckReport(failures=list(findings), manifest=manifest)
    if manifest is None:
        if not findings:
            report.failures.append(Finding(MANIFEST_FILE, "no manifest could be read, and no finding says why", None))
        return report
    checker = _Checker(root, manifest, report, page_warning_lines, dotenv_path)
    checker.pages()
    checker.skills()
    checker.agents()
    checker.servers()
    checker.hooks()
    checker.environment()
    return report


class _Checker:
    def __init__(self, root: Path, manifest: Manifest, report: CheckReport,
                 page_warning_lines: int, dotenv_path: Optional[str]):
        self.root = root
        self.manifest = manifest
        self.report = report
        self.page_warning_lines = page_warning_lines
        self.dotenv_names = _dotenv_names(dotenv_path)
        self.origin = f"harness {manifest.name} {manifest.version}"

    # ------------------------------------------------------------ helpers

    def fail(self, file: str, message: str, line: Optional[int] = None) -> None:
        self.report.failures.append(Finding(file, message, line))

    def warn(self, file: str, message: str, line: Optional[int] = None) -> None:
        self.report.warnings.append(Finding(file, message, line))

    def need(self, label: str, fix: str, modules: Tuple[str, ...], detail: str = "") -> None:
        self.report.missing.append(HarnessRequirement(
            label=label, ok=False, fix=fix, origin=self.origin, detail=detail, modules=modules,
        ))

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def page_for(self, module: str) -> Optional[Path]:
        """The page a module's sessions read first for a skill's situation:
        its own page, else the guardrails."""
        own = self.root / INSTRUCTIONS_DIR / f"{module}.md"
        if own.is_file():
            return own
        guardrails = self.root / INSTRUCTIONS_DIR / GUARDRAILS_PAGE
        return guardrails if guardrails.is_file() else None

    # -------------------------------------------------------------- pages

    def pages(self) -> None:
        directory = self.root / INSTRUCTIONS_DIR
        pages = sorted(directory.glob("*.md")) if directory.is_dir() else []
        if not pages:
            self.fail(
                f"{INSTRUCTIONS_DIR}/{GUARDRAILS_PAGE}",
                "no instruction page: a harness attaches nothing without one; "
                "guardrails.md (every module) is the minimum",
            )
            return
        for page in pages:
            if page.name != GUARDRAILS_PAGE and page.stem not in MODULES:
                self.warn(
                    self.relative(page),
                    f"a page no module reads; the pages are {GUARDRAILS_PAGE} and <module>.md "
                    f"for {', '.join(MODULES)}",
                )
                continue
            lines = page.read_text(encoding="utf-8").count("\n")
            if lines > self.page_warning_lines:
                self.warn(
                    self.relative(page),
                    f"{lines} lines on an always-on page (over {self.page_warning_lines}); "
                    "every word is paid for on every session; move the situational part to a skill",
                )

    # ------------------------------------------------------------- skills

    def skills(self) -> None:
        directory = self.root / SKILLS_DIR
        defined = sorted(p.name for p in directory.iterdir() if p.is_dir()) if directory.is_dir() else []
        self.report.counts["skills"] = len(defined)
        listed = self.manifest.listed("skills")
        for name in listed:
            file = directory / name / SKILL_FILE
            modules = self.manifest.modules_listing("skills", name)
            if not file.is_file():
                self.fail(
                    "harness.yaml",
                    f"modules.{modules[0]} lists skill `{name}`, and {SKILLS_DIR}/{name}/{SKILL_FILE} does not exist",
                )
                continue
            self.front_matter(file, name)
            for module in modules:
                page = self.page_for(module)
                if page is not None and name not in page.read_text(encoding="utf-8"):
                    self.warn(
                        self.relative(page),
                        f"skill `{name}` is listed on {module} and never named here; "
                        "a skill the page does not mention is rarely opened",
                    )
        for name in defined:
            if name not in listed:
                self.warn(f"{SKILLS_DIR}/{name}/", "defined, and no module lists it")

    def agents(self) -> None:
        directory = self.root / AGENTS_DIR
        defined = sorted(p.stem for p in directory.glob("*.md")) if directory.is_dir() else []
        self.report.counts["agents"] = len(defined)
        listed = self.manifest.listed("agents")
        for name in listed:
            file = directory / f"{name}.md"
            modules = self.manifest.modules_listing("agents", name)
            if not file.is_file():
                self.fail(
                    "harness.yaml",
                    f"modules.{modules[0]} lists agent `{name}`, and {AGENTS_DIR}/{name}.md does not exist",
                )
                continue
            self.front_matter(file, name)
        for name in defined:
            if name not in listed:
                self.warn(f"{AGENTS_DIR}/{name}.md", "defined, and no module lists it")

    def front_matter(self, file: Path, expected_name: str) -> None:
        """`name` (the directory or file name) and `description` are what
        both hosts show the agent before it opens the file."""
        where = self.relative(file)
        data, _body = read_front_matter(file)
        if data is None:
            self.fail(where, "no front matter: the file must open with `---`, name, description, `---`", 1)
            return
        if not isinstance(data, dict):
            self.fail(where, "the front matter is not a mapping", 1)
            return
        name = data.get("name")
        if name != expected_name:
            self.fail(where, f"front matter name {name!r} must be `{expected_name}`, the directory or file name", 2)
        description = data.get("description")
        if not isinstance(description, str) or not description.strip():
            self.fail(where, "front matter needs a non-empty description: what it does, then `Use when ...`", 2)

    # ------------------------------------------------------------ servers

    def servers(self) -> None:
        file = self.root / MCP_FILE
        listed = self.manifest.listed("mcp_servers")
        if not file.is_file():
            self.report.counts["servers"] = 0
            if listed:
                modules = self.manifest.modules_listing("mcp_servers", listed[0])
                self.fail(
                    "harness.yaml",
                    f"modules.{modules[0]} lists server `{listed[0]}`, and there is no {MCP_FILE}",
                )
            return
        data = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"mcpServers"} or not isinstance(data["mcpServers"], dict):
            self.fail(MCP_FILE, 'must be an object with one key, "mcpServers", holding the servers by name')
            self.report.counts["servers"] = 0
            return
        servers = data["mcpServers"]
        self.report.counts["servers"] = len(servers)
        for name in listed:
            if name not in servers:
                modules = self.manifest.modules_listing("mcp_servers", name)
                self.fail("harness.yaml", f"modules.{modules[0]} lists server `{name}`, and {MCP_FILE} has no such key")
        for name, entry in servers.items():
            self.server(name, entry)
            if name not in listed:
                self.warn(MCP_FILE, f"server `{name}` is defined, and no module lists it")

    def server(self, name: str, entry: Any) -> None:
        modules = self.manifest.modules_listing("mcp_servers", name) or MODULES
        if not _SERVER_NAME.match(name):
            self.fail(MCP_FILE, f"server name `{name}` must match [A-Za-z0-9_-]+ (both hosts' configuration needs it)")
        if name in RESERVED_SERVER_NAMES:
            self.fail(MCP_FILE, f"server name `{name}` is the engine's own knowledge server; choose another")
        if not isinstance(entry, dict):
            self.fail(MCP_FILE, f"server `{name}` must be an object")
            return
        if "command" in entry:
            self.stdio_server(name, entry, modules)
        elif "url" in entry:
            self.http_server(name, entry)
        else:
            self.fail(MCP_FILE, f"server `{name}` has neither `command` (stdio) nor `url` (streamable-http)")
            return
        env = entry.get("env")
        if isinstance(env, dict):   # a wrong shape was reported by stdio_server
            for key, value in env.items():
                self.env_value(name, key, value, modules)

    def stdio_server(self, name: str, entry: Dict[str, Any], modules: Tuple[str, ...]) -> None:
        unknown = sorted(set(entry) - set(_STDIO_KEYS))
        if unknown:
            self.fail(MCP_FILE, f"server `{name}`: unknown key(s) {', '.join(unknown)}; a stdio server has {', '.join(_STDIO_KEYS)}")
        if not isinstance(entry["command"], str) or not entry["command"].strip():
            self.fail(MCP_FILE, f"server `{name}`: `command` must be a non-empty string")
            return
        args = entry.get("args", [])
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            self.fail(MCP_FILE, f"server `{name}`: `args` must be a list of strings")
            args = []
        env = entry.get("env", {})
        if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
            self.fail(MCP_FILE, f"server `{name}`: `env` must map names to strings")
        cwd = entry.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            self.fail(MCP_FILE, f"server `{name}`: `cwd` must be a string")
        for token in [entry["command"], *args, *([cwd] if isinstance(cwd, str) else [])]:
            self.plugin_path(MCP_FILE, f"server `{name}`", token)
        self.program(MCP_FILE, f"the {name} server", entry["command"], modules)

    def http_server(self, name: str, entry: Dict[str, Any]) -> None:
        unknown = sorted(set(entry) - set(_HTTP_KEYS))
        if unknown:
            self.fail(MCP_FILE, f"server `{name}`: unknown key(s) {', '.join(unknown)}; a streamable-http server has {', '.join(_HTTP_KEYS)}")
        if not isinstance(entry["url"], str) or not entry["url"].startswith(("http://", "https://")):
            self.fail(MCP_FILE, f"server `{name}`: `url` must be an http(s) URL")
        if "type" in entry and entry["type"] not in HTTP_TYPES:
            self.fail(MCP_FILE, f"server `{name}`: `type` must be one of {', '.join(HTTP_TYPES)}")
        headers = entry.get("headers", {})
        if not isinstance(headers, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in headers.items()):
            self.fail(MCP_FILE, f"server `{name}`: `headers` must map names to strings")
            return
        for key, value in headers.items():
            self.env_value(name, key, value, self.manifest.modules_listing("mcp_servers", name) or MODULES, where="headers")

    def env_value(self, server: str, key: str, value: Any, modules: Tuple[str, ...], where: str = "env") -> None:
        """A secret is referenced by name, never written; the host or the
        engine forwards the variable, whose presence is a prerequisite."""
        if not isinstance(value, str):
            return
        reference = _REFERENCE.match(value)
        if reference:
            variable = reference.group(1)
            if where == "env" and variable != key:
                # Codex forwards a variable by name, so the server reads the
                # key only when the key is the variable.
                self.fail(MCP_FILE, f"server `{server}`: env.{key} references ${{{variable}}}; an env entry names the variable it forwards, so write \"${{{key}}}\" and set {key} in .env")
                return
            if not (os.environ.get(variable) or variable in self.dotenv_names):
                self.need(
                    label=f"{variable} (env, for the {server} server)",
                    fix=f"add {variable}=... to .env",
                    modules=modules,
                )
            return
        if "${" in value:
            # Neither host expands a reference inside a longer value.
            self.fail(MCP_FILE, f"server `{server}`: {where}.{key} embeds a reference in a longer value; write the whole value as one \"${{NAME}}\" reference (prefix included) and put it in .env")
            return
        upper = key.upper()
        if any(word in upper for word in SECRET_NAME_WORDS):
            self.fail(MCP_FILE, f"server `{server}`: {where}.{key} is a literal where a reference is expected; write \"${{{key}}}\" and put the value in .env")
        elif value.startswith(SECRET_PREFIXES):
            self.fail(MCP_FILE, f"server `{server}`: {where}.{key} looks like a credential; write a \"${{NAME}}\" reference and put the value in .env")
        elif _OPAQUE.match(value):
            self.warn(MCP_FILE, f"server `{server}`: {where}.{key} is a long opaque value; if it is a credential, write a \"${{NAME}}\" reference")

    # -------------------------------------------------------------- hooks

    def hooks(self) -> None:
        directory = self.root / HOOKS_DIR
        defined = sorted(p.name for p in directory.iterdir() if p.is_dir()) if directory.is_dir() else []
        self.report.counts["hooks"] = len(defined)
        listed = self.manifest.listed("hooks")
        for name in listed:
            file = directory / name / HOOK_FILE
            modules = self.manifest.modules_listing("hooks", name)
            if not file.is_file():
                self.fail("harness.yaml", f"modules.{modules[0]} lists hook `{name}`, and {HOOKS_DIR}/{name}/{HOOK_FILE} does not exist")
                continue
            self.hook(file, name, modules)
        for name in defined:
            if name not in listed:
                self.warn(f"{HOOKS_DIR}/{name}/", "defined, and no module lists it")

    def hook(self, file: Path, name: str, modules: Tuple[str, ...]) -> None:
        where = self.relative(file)
        data = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"hooks"} or not isinstance(data["hooks"], dict):
            self.fail(where, 'must be an object with one key, "hooks", mapping events to entries')
            return
        for event, entries in data["hooks"].items():
            if event not in HOOK_EVENTS:
                self.fail(where, f"unknown event `{event}`; the events are {', '.join(HOOK_EVENTS)}")
                continue
            if not isinstance(entries, list):
                self.fail(where, f"{event} must be a list of entries")
                continue
            for entry in entries:
                self.hook_entry(where, event, entry, modules)

    def hook_entry(self, where: str, event: str, entry: Any, modules: Tuple[str, ...]) -> None:
        if not isinstance(entry, dict) or set(entry) - set(_HOOK_ENTRY_KEYS) or "hooks" not in entry:
            self.fail(where, f"{event}: each entry is an object with an optional `matcher` and a `hooks` list")
            return
        if "matcher" in entry and not isinstance(entry["matcher"], str):
            self.fail(where, f"{event}: `matcher` must be a string")
        if not isinstance(entry["hooks"], list):
            self.fail(where, f"{event}: `hooks` must be a list")
            return
        for command in entry["hooks"]:
            if (
                not isinstance(command, dict)
                or set(command) - set(_HOOK_COMMAND_KEYS)
                or command.get("type") != "command"
                or not isinstance(command.get("command"), str)
            ):
                self.fail(where, f'{event}: each hook is {{"type": "command", "command": "..."}} (an optional `timeout`)')
                continue
            words = shlex.split(command["command"])
            for word in words:
                self.plugin_path(where, f"{event} command", word)
            program = next((w for w in words if not _ASSIGNMENT.match(w)), None)
            if program is None:
                self.fail(where, f"{event}: the command has no program to run")
                continue
            self.program(where, f"the {event} hook", program, modules)

    # -------------------------------------------------------- environment

    def environment(self) -> None:
        env = self.manifest.environment
        for command in env.commands:
            if shutil.which(command) is None:
                self.need(label=f"{command} (command)", fix=f"install {command} and put it on PATH", modules=MODULES)
        if env.python is not None:
            if not env.python.is_file():
                self.fail("harness.yaml", f"environment.python names {self.relative(env.python)}, which does not exist")
            else:
                self.requirements(env.python)
        if env.gpu:
            smi = shutil.which("nvidia-smi")
            usable = smi is not None and subprocess.run([smi, "-L"], capture_output=True).returncode == 0
            if not usable:
                self.need(label="a GPU (environment.gpu)", fix="run on a machine with an NVIDIA GPU and its driver", modules=MODULES)

    def requirements(self, file: Path) -> None:
        """Each pin against `python3` on PATH, the interpreter the harness's
        own commands name (its servers, hooks and scripts run there, not in
        the engine's interpreter); a malformed line raises the packaging
        library's own error."""
        interpreter = shutil.which(PYTHON_COMMAND)
        if interpreter is None:
            self.need(
                label=f"{PYTHON_COMMAND} (command, for environment.python)",
                fix=f"install {PYTHON_COMMAND} and put it on PATH", modules=MODULES,
            )
            return
        listing = subprocess.run([interpreter, "-c", _INTERPRETER_REPORT], capture_output=True, text=True, check=True)
        report = json.loads(listing.stdout)
        installed = {canonicalize_name(name): version for name, version in report["distributions"].items()}
        for raw in file.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            pin = Pin(line)
            if pin.marker is not None and not pin.marker.evaluate(environment=report["environment"]):
                continue
            name = canonicalize_name(pin.name)
            fix = f"{PYTHON_COMMAND} -m pip install -r {file}"
            if name not in installed:
                self.need(label=f"python: {pin.name}", fix=fix, modules=MODULES)
            elif pin.specifier and not pin.specifier.contains(installed[name], prereleases=True):
                self.need(label=f"python: {pin} (installed {installed[name]})", fix=fix, modules=MODULES)

    # ------------------------------------------------------------ commands

    def plugin_path(self, where: str, what: str, token: str) -> None:
        """A `${PLUGIN_ROOT}/...` path in a command must exist in the harness."""
        if PLUGIN_ROOT not in token:
            return
        tail = token[token.index(PLUGIN_ROOT) + len(PLUGIN_ROOT):]
        target = self.root / tail.lstrip("/")
        if not target.exists():
            self.fail(where, f"{what} names {PLUGIN_ROOT}{tail}, and {self.relative(target)} does not exist")

    def program(self, where: str, what: str, program: str, modules: Tuple[str, ...]) -> None:
        """The program a command runs must be reachable, else the hook fails
        open and the server never starts."""
        if PLUGIN_ROOT in program:
            return
        if "/" in program:
            if not Path(program).exists():
                self.need(label=f"{program} (for {what})", fix=f"install it at {program}", modules=modules)
            return
        if shutil.which(program) is None:
            hint = "; on a stock Ubuntu `python` is absent and `python3` is not" if program == "python" else ""
            self.need(label=f"{program} (command, for {what})", fix=f"install {program} and put it on PATH{hint}", modules=modules)


def _dotenv_names(dotenv_path: Optional[str]) -> Tuple[str, ...]:
    path = dotenv_path if dotenv_path is not None else find_dotenv(usecwd=True)
    if not path:
        return ()
    return tuple(name for name, value in dotenv_values(path).items() if value)
