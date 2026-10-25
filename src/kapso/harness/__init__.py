"""The harness package: the domain layer the engine loads, checks, records
and stages. Design: docs/research/harness-design.md; plan:
docs/plans/redesign/wp2-harness.md."""

from kapso.harness.check import CheckReport, HarnessRequirement, check_harness
from kapso.harness.hash import harness_hash, short
from kapso.harness.load import (
    BUILD_MODULES,
    DEPLOY_MODULES,
    LEARN_MODULES,
    Harness,
    HarnessError,
    advisory_lines,
    load_directory,
    load_harness,
    reload_harness,
    resume_refusal,
    unmet_message,
)
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
from kapso.harness.reference import (
    BUNDLED_ROOT,
    HarnessReference,
    HarnessReferenceError,
    parse_reference,
)
from kapso.harness.staging import (
    GUIDANCE_HEADING,
    HARNESS_ROOT_VARIABLE,
    PREPARED_DIR,
    TASK_STATEMENT_FILE,
    StagedHarness,
    host_for,
    no_harness,
    stage_harness,
)
from kapso.harness.store import FetchedHarness, HarnessStore

__all__ = [
    "ATTACHMENT_KINDS",
    "BUILD_MODULES",
    "BUNDLED_ROOT",
    "DEPLOY_MODULES",
    "LEARN_MODULES",
    "MODULES",
    "CheckReport",
    "FetchedHarness",
    "GUIDANCE_HEADING",
    "HARNESS_ROOT_VARIABLE",
    "PREPARED_DIR",
    "TASK_STATEMENT_FILE",
    "StagedHarness",
    "Finding",
    "Harness",
    "HarnessEnvironment",
    "HarnessError",
    "HarnessReference",
    "HarnessReferenceError",
    "HarnessRequirement",
    "HarnessStore",
    "Manifest",
    "ManifestError",
    "ModuleAttachments",
    "advisory_lines",
    "check_harness",
    "harness_hash",
    "host_for",
    "inspect_manifest",
    "load_directory",
    "load_harness",
    "no_harness",
    "parse_reference",
    "read_manifest",
    "reload_harness",
    "resume_refusal",
    "short",
    "stage_harness",
    "unmet_message",
    "valid_name",
]
