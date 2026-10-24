"""The harness package: the domain layer the engine loads, checks, records
and stages. Design: docs/research/harness-design.md; plan:
docs/plans/redesign/wp2-harness.md."""

from kapso.harness.check import CheckReport, HarnessRequirement, check_harness
from kapso.harness.hash import harness_hash, short
from kapso.harness.manifest import (
    ATTACHMENT_KINDS,
    MODULES,
    Finding,
    HarnessEnvironment,
    Manifest,
    ManifestError,
    ModuleAttachments,
    inspect_manifest,
    read_manifest,
    valid_name,
)

__all__ = [
    "ATTACHMENT_KINDS",
    "MODULES",
    "CheckReport",
    "HarnessRequirement",
    "check_harness",
    "Finding",
    "HarnessEnvironment",
    "Manifest",
    "ManifestError",
    "ModuleAttachments",
    "harness_hash",
    "inspect_manifest",
    "read_manifest",
    "short",
    "valid_name",
]
