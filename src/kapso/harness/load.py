"""Loading a harness: resolve the reference, run `check`, raise on a
failure, hash the directory, read what the machine lacks. The handle is
what `Kapso.load_harness` returns and what every verb reads. Design:
docs/research/harness-design.md section 8; the plan:
docs/plans/redesign/wp2-harness.md ("The handle").
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from kapso.handles import HarnessRef
from kapso.harness.check import CheckReport, HarnessRequirement, check_harness
from kapso.harness.hash import harness_hash, short
from kapso.harness.manifest import HarnessEnvironment, Manifest, ModuleAttachments
from kapso.harness.reference import HarnessReference, parse_reference
from kapso.harness.store import HarnessStore

# The modules each verb runs sessions for; a verb refuses on the unmet
# requirements of its own modules and prints the others as advisory.
BUILD_MODULES = ("setup", "ideation", "implementation", "verification", "feedback")
DEPLOY_MODULES = ("deployment",)
LEARN_MODULES = ("learning",)


class HarnessError(ValueError):
    """A harness that fails `check`; the message lists the failures."""


@dataclass(frozen=True)
class Harness:
    """A loaded harness: its identity, its directory, what each module
    gets, and what this machine lacks for it."""
    reference: HarnessReference
    path: Path
    manifest: Manifest
    hash: str
    report: CheckReport

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def version(self) -> str:
        return self.manifest.version

    @property
    def description(self) -> str:
        return self.manifest.description

    @property
    def source(self) -> str:
        """The reference as given, a path made absolute."""
        return str(self.path) if self.reference.kind == "path" else self.reference.raw

    @property
    def modules(self) -> Dict[str, ModuleAttachments]:
        return self.manifest.modules

    def module(self, name: str) -> ModuleAttachments:
        return self.manifest.module(name)

    @property
    def environment(self) -> HarnessEnvironment:
        return self.manifest.environment

    @property
    def missing(self) -> List[HarnessRequirement]:
        return list(self.report.missing)

    def missing_for(self, modules: Tuple[str, ...]) -> List[HarnessRequirement]:
        return self.report.missing_for(modules)

    def ref(self) -> HarnessRef:
        return HarnessRef(name=self.name, version=self.version, hash=self.hash, source=self.source)

    def label(self) -> str:
        return f"{self.name} {self.version} ({short(self.hash)})"


def load_harness(
    ref: str,
    *,
    settings: Dict[str, Any],
    cwd: Optional[Path] = None,
    say: Callable[[str], None] = print,
) -> Harness:
    """Resolve, fetch when needed (and say so), check, raise on failures,
    hash, read prerequisites. `settings` is the config's `harness` block."""
    reference = parse_reference(ref, cwd=cwd)
    store = HarnessStore(Path(settings["store"]))
    fetched_before = reference.kind != "git" or store.is_fetched(reference)
    path = store.resolve(reference)
    if not fetched_before:
        say(f"fetched {path}")
    return load_directory(reference, path, settings=settings, say=say)


def load_directory(
    reference: HarnessReference,
    path: Path,
    *,
    settings: Dict[str, Any],
    say: Callable[[str], None] = print,
) -> Harness:
    """The check, the hash and the handle for a resolved directory; also
    what a verb calls again at its start, so a change since the load
    and a prerequisite fixed since are both seen."""
    report = check_harness(path, page_warning_lines=int(settings["page_warning_lines"]))
    if not report.ok():
        raise HarnessError(
            f"harness at {path} fails check:\n"
            + "\n".join(f"  {finding}" for finding in report.failures)
        )
    for warning in report.warnings:
        say(f"warning: {warning}")
    return Harness(
        reference=reference,
        path=Path(path),
        manifest=report.manifest,
        hash=harness_hash(path),
        report=report,
    )


def reload_harness(harness: Harness, *, settings: Dict[str, Any], say: Callable[[str], None] = print) -> Harness:
    """The same directory read again: a verb's view at its own start."""
    return load_directory(harness.reference, harness.path, settings=settings, say=say)
