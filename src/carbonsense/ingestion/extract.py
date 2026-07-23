"""Deterministic CSV and structured-text extraction."""

from __future__ import annotations

import csv
from hashlib import sha256
import io

from .fields import build_unit_metadata, match_field, parse_candidate_value
from .models import ExtractionCandidate, IngestionBatch, IngestionRecord, Provenance, UnitStatus


def extract_csv(text: str, source_name: str, column_mapping: dict[str, str] | None = None) -> IngestionBatch:
    """Extract review candidates from CSV text without approving or converting them."""
    digest = _digest(text)
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        headers = next(reader)
    except StopIteration:
        return IngestionBatch(source_name, "csv", digest, (), ("The CSV is empty.",))

    if any(not header.strip() for header in headers):
        raise ValueError("CSV headers must not be blank")
    if len(set(headers)) != len(headers):
        raise ValueError("CSV headers must be unique")

    records: list[IngestionRecord] = []
    warnings: list[str] = []
    for row_number, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != len(headers):
            warnings.append(f"Row {row_number} has {len(row)} value(s) for {len(headers)} header(s) and was skipped.")
            continue
        candidates = tuple(
            _candidate(raw_field, raw_value, source_name, "csv", digest, f"row {row_number}, column {column_number}", column_mapping)
            for column_number, (raw_field, raw_value) in enumerate(zip(headers, row, strict=True), start=1)
        )
        records.append(IngestionRecord(row_number, candidates))
    return IngestionBatch(source_name, "csv", digest, tuple(records), tuple(warnings))


def extract_structured_text(
    text: str,
    source_name: str,
    field_mapping: dict[str, str] | None = None,
) -> IngestionBatch:
    """Extract blank-line-separated `key: value` or `key=value` records."""
    digest = _digest(text)
    blocks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            current.append((line_number, line))
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)

    records: list[IngestionRecord] = []
    warnings: list[str] = []
    for record_number, block in enumerate(blocks, start=1):
        candidates: list[ExtractionCandidate] = []
        seen_fields: set[str] = set()
        for line_number, line in block:
            split_at = _first_separator_index(line)
            if split_at is None:
                warnings.append(f"Line {line_number} has no `:` or `=` separator and was skipped.")
                continue
            raw_field, raw_value = line[:split_at].strip(), line[split_at + 1 :].strip()
            if not raw_field:
                warnings.append(f"Line {line_number} has a blank field name and was skipped.")
                continue
            candidate = _candidate(raw_field, raw_value, source_name, "structured_text", digest, f"line {line_number}", field_mapping)
            if candidate.canonical_field and candidate.canonical_field in seen_fields:
                warnings.append(f"Record {record_number} has multiple candidates for `{candidate.canonical_field}`; human resolution is required.")
            if candidate.canonical_field:
                seen_fields.add(candidate.canonical_field)
            candidates.append(candidate)
        if candidates:
            records.append(IngestionRecord(record_number, tuple(candidates)))
    return IngestionBatch(source_name, "structured_text", digest, tuple(records), tuple(warnings))


def _candidate(
    raw_field: str,
    raw_value: str,
    source_name: str,
    source_type: str,
    digest: str,
    locator: str,
    mapping: dict[str, str] | None,
) -> ExtractionCandidate:
    definition, confidence = match_field(raw_field, mapping)
    parsed_value, value_unit, notes = parse_candidate_value(raw_value, definition)
    unit = build_unit_metadata(raw_field, definition, value_unit)
    if unit.status is UnitStatus.REQUIRES_REVIEW:
        notes += ("Source unit differs from the canonical unit; no conversion was applied.",)
    return ExtractionCandidate(
        raw_field=raw_field,
        raw_value=raw_value,
        canonical_field=definition.name if definition else None,
        parsed_value=parsed_value,
        confidence=confidence,
        provenance=Provenance(source_name, source_type, digest, locator),
        unit=unit,
        notes=notes,
    )


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _first_separator_index(line: str) -> int | None:
    positions = [position for separator in (":", "=") if (position := line.find(separator)) >= 0]
    return min(positions) if positions else None
