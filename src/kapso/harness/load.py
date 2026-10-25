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
    settings: Dict[str, Any]      # the config's `harness` block it was loaded with

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

    def ref_dict(self) -> Dict[str, str]:
        """The identity as the launch record, the status file and the
        checkpoint write it."""
        return {"name": self.name, "version": self.version, "hash": self.hash, "source": self.source}

    def label(self) -> str:
        return f"{self.name} {self.version} ({short(self.hash)})"

    def has_content(self, module: str) -> bool:
        """Whether a module has a page of its own or any attachment: what
        decides that the engine runs the setup and verification sessions."""
        page = self.path / "instructions" / f"{module}.md"
        return page.is_file() or not self.manifest.module(module).empty()

    def sessions_added(self) -> Tuple[str, ...]:
        """The sessions a build runs because of this harness, for the
        launch print."""
        added = []
        if self.has_content("setup"):
            added.append("harness setup")
        if self.has_content("verification"):
            added.append("verification per attempt")
        return tuple(added)

    def restore_hint(self) -> str:
        """How to get the recorded content back, by the reference's form."""
        if self.reference.kind == "path":
            return (
                f"restore the recorded content (for instance `git checkout` in {self.path}) "
                "or start a new campaign with a new --output"
            )
        if self.reference.kind == "git":
            return (
                f"re-fetch the recorded revision with `kapso harness remove {self.reference.raw}` "
                f"then `kapso harness add {self.reference.raw}`, or start a new campaign"
            )
        return "reinstall the package version that shipped it, or start a new campaign"


def unmet_message(harness: Harness, rows: List[HarnessRequirement], verb: str) -> str:
    """Why a verb refuses: each unmet requirement of its modules, where it
    is read from, and the line that fixes it."""
    lines = [f"harness {harness.label()} cannot run a {verb} on this machine; it needs:"]
    for row in rows:
        lines.append(f"  - {row.label}: {row.fix}  [{', '.join(row.modules)}]")
    lines.append("Fix these and run again; prerequisites are checked at every call.")
    return "\n".join(lines)


def advisory_lines(harness: Harness, modules: Tuple[str, ...]) -> List[str]:
    """The unmet requirements a verb does not need, said but not refused."""
    needed = {id(row) for row in harness.missing_for(modules)}
    return [
        f"  advisory: {row.label}: {row.fix}  [{', '.join(row.modules)}]"
        for row in harness.missing if id(row) not in needed
    ]


def resume_refusal(recorded: Optional[Dict[str, str]], harness: Optional[Harness]) -> str:
    """Why a resume is refused when the harness is not the launch's; the
    message names both identities and the way out."""
    if recorded is None:
        return (
            f"this campaign was launched without a harness; a resume cannot add "
            f"{harness.label()} to it. Start a new campaign with --harness."
        )
    was = f"{recorded['name']} {recorded['version']} ({short(recorded['hash'])}) from {recorded['source']}"
    if harness is None:
        return (
            f"this campaign was launched with harness {was}, which is not loaded now: "
            f"pass --harness {recorded['source']} (or load it), or start a new campaign."
        )
    return (
        f"the harness changed since launch: {was} recorded, {harness.label()} now; "
        f"{harness.restore_hint()}."
    )


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
        settings=dict(settings),
    )


def reload_harness(harness: Harness, *, settings: Dict[str, Any], say: Callable[[str], None] = print) -> Harness:
    """The same directory read again: a verb's view at its own start."""
    return load_directory(harness.reference, harness.path, settings=settings, say=say)
