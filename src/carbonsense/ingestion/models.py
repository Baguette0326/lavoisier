"""Review-first data models for deterministic ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeAlias


ScalarValue: TypeAlias = str | int | float | bool | None


class ApprovalStatus(StrEnum):
    """Human decision state for extracted data."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"


class UnitStatus(StrEnum):
    """How a source unit relates to Lavoisier's canonical unit."""

    EXACT = "exact"
    NOT_APPLICABLE = "not_applicable"
    MISSING = "missing"
    REQUIRES_REVIEW = "requires_review"


@dataclass(frozen=True)
class Provenance:
    """Stable source identity and the exact location of an extracted value."""

    source_name: str
    source_type: str
    content_sha256: str
    locator: str

    def __post_init__(self) -> None:
        if not self.source_name.strip():
            raise ValueError("source_name must not be empty")
        if len(self.content_sha256) != 64:
            raise ValueError("content_sha256 must be a SHA-256 hex digest")


@dataclass(frozen=True)
class UnitMetadata:
    """Unit information captured without performing implicit conversion."""

    source_unit: str | None
    canonical_unit: str | None
    quantity_kind: str | None
    status: UnitStatus
    conversion_applied: bool = False

    def __post_init__(self) -> None:
        if self.conversion_applied:
            raise ValueError("The first ingestion layer must not apply unit conversions")


@dataclass(frozen=True)
class ExtractionCandidate:
    """One source value proposed for a canonical Lavoisier field."""

    raw_field: str
    raw_value: str
    canonical_field: str | None
    parsed_value: ScalarValue
    confidence: float
    provenance: Provenance
    unit: UnitMetadata
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class IngestionRecord:
    """Candidates extracted from one source row or structured-text block."""

    record_number: int
    candidates: tuple[ExtractionCandidate, ...]
    approval_status: ApprovalStatus = ApprovalStatus.PENDING

    def candidates_for(self, canonical_field: str) -> tuple[ExtractionCandidate, ...]:
        """Return all candidates for a canonical field without resolving conflicts."""
        return tuple(candidate for candidate in self.candidates if candidate.canonical_field == canonical_field)


@dataclass(frozen=True)
class IngestionBatch:
    """Deterministic extraction output awaiting human review."""

    source_name: str
    source_type: str
    content_sha256: str
    records: tuple[IngestionRecord, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
