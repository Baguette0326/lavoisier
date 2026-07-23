import pytest

from carbonsense.ingestion import ApprovalStatus, UnitStatus, extract_csv, extract_structured_text
from carbonsense.ingestion.models import UnitMetadata


def test_extract_csv_builds_pending_candidates_with_provenance_and_units() -> None:
    text = "material_id,CO2 uptake (mmol/g),evidence_type\nMOF-1,4.2,computational\n"

    batch = extract_csv(text, "example.csv")

    assert batch.approval_status is ApprovalStatus.PENDING
    assert len(batch.records) == 1
    uptake = batch.records[0].candidates_for("co2_uptake_mmol_g")[0]
    assert uptake.parsed_value == 4.2
    assert uptake.confidence == 0.9
    assert uptake.unit.source_unit == "mmol/g"
    assert uptake.unit.status is UnitStatus.EXACT
    assert uptake.provenance.locator == "row 2, column 2"
    assert len(uptake.provenance.content_sha256) == 64
    assert uptake.approval_status is ApprovalStatus.PENDING


def test_extract_csv_retains_unknown_fields_instead_of_inventing_mapping() -> None:
    batch = extract_csv("material_id,mystery score\nMOF-1,high\n", "unknown.csv")

    unknown = batch.records[0].candidates[1]

    assert unknown.canonical_field is None
    assert unknown.parsed_value == "high"
    assert unknown.confidence == 0.0


def test_extract_csv_skips_malformed_rows_with_warning() -> None:
    batch = extract_csv("material_id,evidence_type\nMOF-1\nMOF-2,experimental\n", "rows.csv")

    assert len(batch.records) == 1
    assert "Row 2" in batch.warnings[0]


def test_extract_structured_text_separates_records_and_flags_duplicate_candidates() -> None:
    text = "material: MOF-1\nqst: 35 kJ/mol\nqst: 36 kJ/mol\n\nmaterial_id=MOF-2\nhumidity=yes\n"

    batch = extract_structured_text(text, "notes.txt")

    assert len(batch.records) == 2
    assert len(batch.records[0].candidates_for("heat_of_adsorption_kj_mol")) == 2
    assert any("multiple candidates" in warning for warning in batch.warnings)
    humidity = batch.records[1].candidates_for("humidity_flag")[0]
    assert humidity.parsed_value is True
    assert humidity.provenance.locator == "line 6"


def test_extract_structured_text_preserves_separators_inside_values() -> None:
    batch = extract_structured_text("source=https://example.test/material?id=1\n", "links.txt")

    source = batch.records[0].candidates_for("source")[0]

    assert source.raw_value == "https://example.test/material?id=1"
    assert source.parsed_value == "https://example.test/material?id=1"


def test_different_unit_is_preserved_for_human_review_without_conversion() -> None:
    batch = extract_csv("material_id,CO2 uptake (mol/kg)\nMOF-1,4.2\n", "units.csv")
    uptake = batch.records[0].candidates_for("co2_uptake_mmol_g")[0]

    assert uptake.parsed_value == 4.2
    assert uptake.unit.source_unit == "mol/kg"
    assert uptake.unit.canonical_unit == "mmol/g"
    assert uptake.unit.status is UnitStatus.REQUIRES_REVIEW
    assert not uptake.unit.conversion_applied
    assert any("no conversion" in note for note in uptake.notes)


def test_unit_metadata_rejects_implicit_conversion() -> None:
    with pytest.raises(ValueError, match="must not apply unit conversions"):
        UnitMetadata("mol/kg", "mmol/g", "specific_uptake", UnitStatus.EXACT, conversion_applied=True)


def test_extract_csv_requires_unique_nonblank_headers() -> None:
    with pytest.raises(ValueError, match="unique"):
        extract_csv("material_id,material_id\nMOF-1,MOF-2\n", "duplicate.csv")

    with pytest.raises(ValueError, match="blank"):
        extract_csv("material_id,\nMOF-1,value\n", "blank.csv")
