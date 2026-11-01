"""The harness manifest, `harness.yaml`: identity, environment, and which
module gets which attachments. Design: docs/research/harness-design.md
section 2; the plan: docs/plans/redesign/wp2-harness.md.

The file is read with its line numbers (the YAML composer's marks), so a
structural problem is a `Finding` that names `harness.yaml:<line>`;
`inspect_manifest` collects every finding so `check` can show them all,
and `read_manifest` raises them. A file that does not parse raises the
parser's own error, with its own position (CLAUDE.md rule 2).
"""

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

MANIFEST_FILE = "harness.yaml"
SCHEMA_VERSION = 1
MODULES = (
    "setup", "ideation", "implementation", "verification",
    "feedback", "learning", "deployment",
)
ATTACHMENT_KINDS = ("skills", "mcp_servers", "agents", "hooks")
_TOP_KEYS = ("schema_version", "name", "version", "description", "environment", "modules")
_REQUIRED_KEYS = ("schema_version", "name", "version", "description")
_ENVIRONMENT_KEYS = ("python", "commands", "gpu")
_NAME_FIRST = "abcdefghijklmnopqrstuvwxyz0123456789"
_NAME_REST = _NAME_FIRST + "-"


@dataclass(frozen=True)
class Finding:
    """One structural problem or warning: the file (relative to the harness
    root), the line when there is one, and the message."""
    file: str
    message: str
    line: Optional[int] = None

    def __str__(self) -> str:
        where = f"{self.file}:{self.line}" if self.line else self.file
        return f"{where}: {self.message}"


class ManifestError(ValueError):
    """The manifest's findings, raised by `read_manifest`."""

    def __init__(self, findings: List[Finding]):
        self.findings = list(findings)
        super().__init__("\n".join(str(f) for f in self.findings))


@dataclass(frozen=True)
class ModuleAttachments:
    """What one module's sessions get, by name; every list is complete and
    nothing is inherited between modules."""
    skills: Tuple[str, ...] = ()
    mcp_servers: Tuple[str, ...] = ()
    agents: Tuple[str, ...] = ()
    hooks: Tuple[str, ...] = ()

    def empty(self) -> bool:
        return not (self.skills or self.mcp_servers or self.agents or self.hooks)

    def names(self, kind: str) -> Tuple[str, ...]:
        return getattr(self, kind)


@dataclass(frozen=True)
class HarnessEnvironment:
    """The prerequisites a harness declares: a requirements file (resolved
    against the harness root), commands that must be on PATH, a GPU."""
    python: Optional[Path] = None
    commands: Tuple[str, ...] = ()
    gpu: bool = False


@dataclass(frozen=True)
class Manifest:
    name: str
    version: str
    description: str
    environment: HarnessEnvironment
    modules: Dict[str, ModuleAttachments] = field(default_factory=dict)

    def module(self, name: str) -> ModuleAttachments:
        """A module's attachments; a module the manifest leaves out has none
        (it still gets its pages)."""
        if name not in MODULES:
            raise ValueError(f"unknown module {name!r}; the modules are {', '.join(MODULES)}")
        return self.modules.get(name, ModuleAttachments())

    def listed(self, kind: str) -> Tuple[str, ...]:
        """Every name of one attachment kind any module lists, in manifest
        order, once each."""
        seen: List[str] = []
        for attachments in self.modules.values():
            for item in attachments.names(kind):
                if item not in seen:
                    seen.append(item)
        return tuple(seen)

    def modules_listing(self, kind: str, name: str) -> Tuple[str, ...]:
        """The modules that list one attachment."""
        return tuple(m for m, a in self.modules.items() if name in a.names(kind))


def valid_name(name: str) -> bool:
    """The bundled-name grammar: `[a-z0-9][a-z0-9-]*`."""
    return bool(name) and name[0] in _NAME_FIRST and all(c in _NAME_REST for c in name)


# The coordinate of a campaign that runs with no harness, which the
# experience package scopes lessons by (`harness:none`); no harness may
# take the name.
RESERVED_HARNESS_NAME = "none"


def read_manifest(root: Path) -> Manifest:
    """Read `<harness>/harness.yaml`; every finding is raised at once."""
    manifest, findings = inspect_manifest(root)
    if findings:
        raise ManifestError(findings)
    return manifest


def inspect_manifest(root: Path) -> Tuple[Optional[Manifest], List[Finding]]:
    """The manifest and its findings. The manifest is None when the file is
    missing, empty, or not a mapping; otherwise every rule is applied and
    the manifest is built from the parts that passed."""
    root = Path(root)
    file = root / MANIFEST_FILE
    if not file.is_file():
        return None, [Finding(MANIFEST_FILE, f"no {MANIFEST_FILE} in {root}")]
    stream = io.StringIO(file.read_text(encoding="utf-8"))
    stream.name = str(file)   # the parser's own error then names the file
    document = yaml.compose(stream)
    if document is None:
        return None, [Finding(MANIFEST_FILE, "the manifest is empty", 1)]
    inspector = _Inspector(root)
    manifest = inspector.manifest(document)
    # In file order for the reader; a finding with no line comes first.
    inspector.findings.sort(key=lambda f: (f.line is not None, f.line or 0))
    return manifest, inspector.findings


class _Inspector:
    """Walks the composed document, collecting findings instead of raising."""

    def __init__(self, root: Path):
        self.root = root
        self.findings: List[Finding] = []

    def note(self, node: Optional[yaml.Node], message: str) -> None:
        self.findings.append(Finding(MANIFEST_FILE, message, _line(node) if node is not None else None))

    def manifest(self, document: yaml.Node) -> Optional[Manifest]:
        top = self.mapping(document, "the manifest", _TOP_KEYS)
        if top is None:
            return None
        for required in _REQUIRED_KEYS:
            if required not in top:
                self.note(document, f"`{required}` is required")
        # A key present with an empty value (`version:`) constructs to
        # None, which is as wrong as a bad value: each is a finding.
        schema = self.scalar(top.get("schema_version"), "schema_version")
        if self.present("schema_version", top) and schema != SCHEMA_VERSION:
            self.note(
                top["schema_version"],
                f"schema_version {schema!r} is not supported; this Kapso reads schema_version {SCHEMA_VERSION}",
            )
        name = self.scalar(top.get("name"), "name")
        if self.present("name", top) and (not isinstance(name, str) or not valid_name(name)):
            self.note(top["name"], f"name {name!r} must match [a-z0-9][a-z0-9-]*")
            name = None
        elif name == RESERVED_HARNESS_NAME:
            self.note(
                top["name"],
                f"name {name!r} is reserved: it is the coordinate of a campaign that runs with no harness",
            )
            name = None
        version = self.scalar(top.get("version"), "version")
        if isinstance(version, (int, float)) and not isinstance(version, bool):
            version = str(version)
        if self.present("version", top) and (not isinstance(version, str) or not version.strip()):
            self.note(top["version"], "version must be a non-empty string")
            version = None
        description = self.scalar(top.get("description"), "description")
        if self.present("description", top) and (not isinstance(description, str) or not description.strip()):
            self.note(top["description"], "description must be a non-empty string")
            description = None
        environment = self.environment(top["environment"]) if "environment" in top else HarnessEnvironment()
        modules: Dict[str, ModuleAttachments] = {}
        if "modules" in top:
            entries = self.mapping(top["modules"], "modules", MODULES)
            for module_name, node in (entries or {}).items():
                modules[module_name] = self.attachments(node, module_name)
        if name is None or version is None or description is None:
            return None
        return Manifest(
            name=name,
            version=version.strip(),
            description=description.strip(),
            environment=environment,
            modules=modules,
        )

    def mapping(self, node: yaml.Node, what: str, allowed: Tuple[str, ...]) -> Optional[Dict[str, yaml.Node]]:
        if not isinstance(node, yaml.MappingNode):
            self.note(node, f"{what} must be a mapping")
            return None
        children: Dict[str, yaml.Node] = {}
        for key_node, value_node in node.value:
            key = key_node.value
            if key not in allowed:
                self.note(key_node, f"unknown key `{key}` in {what}; the keys are {', '.join(allowed)}")
                continue
            if key in children:
                self.note(key_node, f"`{key}` appears twice in {what}")
                continue
            children[key] = value_node
        return children

    def scalar(self, node: Optional[yaml.Node], what: str) -> Any:
        if node is None:
            return None
        if not isinstance(node, yaml.ScalarNode):
            self.note(node, f"{what} must be a single value")
            return None
        return yaml.SafeLoader("").construct_object(node)

    @staticmethod
    def present(key: str, top: Dict[str, yaml.Node]) -> bool:
        """The key is there with a scalar: its value is checked, and a
        wrong one is a finding (a missing key, or one that is not a
        scalar, was noted already)."""
        return key in top and isinstance(top[key], yaml.ScalarNode)

    def names(self, node: yaml.Node, what: str) -> Tuple[str, ...]:
        if not isinstance(node, yaml.SequenceNode):
            self.note(node, f"{what} must be a list")
            return ()
        names: List[str] = []
        for item in node.value:
            value = self.scalar(item, what)
            if value is None:
                continue
            if not isinstance(value, str) or not value.strip():
                self.note(item, f"{what} holds a name that is not a string")
                continue
            if value in names:
                self.note(item, f"`{value}` is listed twice in {what}")
                continue
            names.append(value)
        return tuple(names)

    def environment(self, node: yaml.Node) -> HarnessEnvironment:
        fields = self.mapping(node, "environment", _ENVIRONMENT_KEYS)
        if fields is None:
            return HarnessEnvironment()
        python = None
        if "python" in fields:
            value = self.scalar(fields["python"], "environment.python")
            if value is not None and (not isinstance(value, str) or not value.strip()):
                self.note(fields["python"], "environment.python names a requirements file")
            elif value is not None:
                python = self.root / value
        commands: Tuple[str, ...] = ()
        if "commands" in fields:
            commands = self.names(fields["commands"], "environment.commands")
        gpu = False
        if "gpu" in fields:
            value = self.scalar(fields["gpu"], "environment.gpu")
            if value is not None and not isinstance(value, bool):
                self.note(fields["gpu"], "environment.gpu is true or false")
            elif value is not None:
                gpu = value
        return HarnessEnvironment(python=python, commands=commands, gpu=gpu)

    def attachments(self, node: yaml.Node, module_name: str) -> ModuleAttachments:
        if isinstance(node, yaml.ScalarNode) and node.value == "":
            return ModuleAttachments()   # `setup:` with nothing under it
        fields = self.mapping(node, f"modules.{module_name}", ATTACHMENT_KINDS)
        if fields is None:
            return ModuleAttachments()
        return ModuleAttachments(**{
            kind: self.names(fields[kind], f"modules.{module_name}.{kind}")
            for kind in ATTACHMENT_KINDS if kind in fields
        })


def _line(node: yaml.Node) -> int:
    return node.start_mark.line + 1
