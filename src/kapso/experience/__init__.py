"""The experience package: what a campaign is served that was measured
before (a bank, the hosted gate, an ingested corpus), by one reference
grammar. Design: docs/research/onboarding.md section 2; plan:
docs/plans/redesign/wp3-experience.md."""

from kapso.experience.reference import (
    FORMS,
    HOSTED,
    MINE,
    RESERVED,
    ExperienceReference,
    ExperienceReferenceError,
    parse_experience_reference,
    recorded_reference,
    valid_index_name,
)
from kapso.experience.sources import (
    HOSTED_KEY,
    PROVENANCE_BANK,
    PROVENANCE_MINE,
    PROVENANCE_REPORTED,
    SCOPE_ALL,
    SCOPE_HARNESS,
    SCOPES,
    ExperienceError,
    ExperienceSource,
    bank_head,
    count_cards,
    has_origin,
    hosted_key_missing,
    hosted_key_present,
    pull_home,
    resolve_source,
)
from kapso.experience.ingest import IngestError
from kapso.experience.store import ExperienceStore, IndexRecord

__all__ = [
    "FORMS",
    "HOSTED",
    "HOSTED_KEY",
    "MINE",
    "PROVENANCE_BANK",
    "PROVENANCE_MINE",
    "PROVENANCE_REPORTED",
    "RESERVED",
    "SCOPE_ALL",
    "SCOPE_HARNESS",
    "SCOPES",
    "ExperienceError",
    "ExperienceReference",
    "ExperienceReferenceError",
    "ExperienceSource",
    "ExperienceStore",
    "IndexRecord",
    "IngestError",
    "bank_head",
    "count_cards",
    "has_origin",
    "hosted_key_missing",
    "hosted_key_present",
    "parse_experience_reference",
    "pull_home",
    "recorded_reference",
    "resolve_source",
    "valid_index_name",
]
