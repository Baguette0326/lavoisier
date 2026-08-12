"""Cautious virtual-lab assessment synthesis for unfamiliar MOF candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class CandidateAssessmentResult:
    """Final review synthesis across similarity, benchmark, and prediction evidence."""

    assessment_summary: dict[str, object]


def _property_statuses(property_summary: Mapping[str, object]) -> dict[str, str]:
    raw = property_summary.get("supplied_prediction_comparison", {})
    if not isinstance(raw, Mapping):
        return {}
    statuses: dict[str, str] = {}
    for target, detail in raw.items():
        if isinstance(detail, Mapping):
            statuses[str(target)] = str(detail.get("status", ""))
    return statuses


def _has_missing_prediction(property_summary: Mapping[str, object]) -> bool:
    target_summaries = property_summary.get("target_summaries", {})
    if not isinstance(target_summaries, Mapping):
        return True
    if not target_summaries:
        return True
    return any(
        isinstance(detail, Mapping) and detail.get("status") != "predicted"
        for detail in target_summaries.values()
    )


def _review_confidence(similarity_summary: Mapping[str, object], property_summary: Mapping[str, object]) -> str:
    warnings = list(similarity_summary.get("warnings", [])) + list(property_summary.get("warnings", []))
    nearest_distance = float(similarity_summary.get("nearest_distance", 999.0) or 999.0)
    prediction_confidence = float(similarity_summary.get("prediction_confidence", 0.0) or 0.0)
    statuses = _property_statuses(property_summary).values()
    if warnings or nearest_distance > 3 or any(status == "large_supplied_prediction_gap" for status in statuses):
        return "low"
    if prediction_confidence >= 0.75 and not any(status == "moderate_supplied_prediction_gap" for status in statuses):
        return "medium"
    return "low"


def synthesize_candidate_assessment(
    similarity_summary: Mapping[str, object],
    property_summary: Mapping[str, object],
) -> CandidateAssessmentResult:
    """Combine review outputs into one cautious virtual-lab assessment."""
    warnings = list(similarity_summary.get("warnings", [])) + list(property_summary.get("warnings", []))
    statuses = _property_statuses(property_summary)
    has_large_gap = any(status == "large_supplied_prediction_gap" for status in statuses.values())
    has_moderate_gap = any(status == "moderate_supplied_prediction_gap" for status in statuses.values())
    missing_prediction = _has_missing_prediction(property_summary)
    benchmark_verdict = str(similarity_summary.get("benchmark_verdict", ""))
    neighbor_verdict = str(similarity_summary.get("neighbor_advantage_verdict", ""))
    rd_recommendation = str(similarity_summary.get("rd_recommendation", ""))
    predicted_class = str(similarity_summary.get("predicted_candidate_class", ""))

    reasons: list[str] = []
    flags: list[str] = []

    if missing_prediction:
        final_decision = "complete_required_inputs"
        viability_read = "incomplete_evidence"
        better_than_known_reference = "insufficient_evidence"
        reasons.append("descriptor-based property prediction is incomplete")
        flags.append("missing_prediction")
    elif has_large_gap:
        final_decision = "investigate_assumption_gap"
        viability_read = "potential_but_unresolved"
        better_than_known_reference = "unresolved_due_to_prediction_gap"
        reasons.append("one or more supplied metrics strongly disagree with descriptor-based prediction")
        flags.append("large_supplied_prediction_gap")
    elif warnings:
        final_decision = "review_with_caution"
        viability_read = "potential_but_unresolved"
        better_than_known_reference = "uncertain"
        reasons.append("similarity or prediction warnings reduce confidence")
        flags.append("review_warning")
    elif rd_recommendation == "deprioritize_until_new_evidence" or benchmark_verdict == "below_reference_or_risky":
        final_decision = "deprioritize_until_new_evidence"
        viability_read = "weak_candidate"
        better_than_known_reference = "unlikely_better"
        reasons.append("candidate resembles records with first-pass screening limitations")
        flags.append("screening_limitation")
    elif (
        rd_recommendation == "prioritize_deeper_review"
        and benchmark_verdict == "above_reference_candidate"
        and neighbor_verdict in {"candidate_advantage_over_neighbors", "candidate_mixed_advantage_over_neighbors"}
    ):
        final_decision = "prioritize_deeper_review"
        viability_read = "viable_candidate_for_deeper_review"
        better_than_known_reference = "possibly_better_than_nearest_known_records"
        reasons.append("candidate is benchmark-competitive and compares favorably with nearest known records")
    elif rd_recommendation in {"prioritize_deeper_review", "consider_for_deeper_review"}:
        final_decision = "consider_for_deeper_review"
        viability_read = "plausible_candidate"
        better_than_known_reference = "not_clearly_better"
        reasons.append("candidate resembles usable known records but does not clearly dominate nearest alternatives")
    else:
        final_decision = "manual_review_required"
        viability_read = "incomplete_or_mixed_evidence"
        better_than_known_reference = "uncertain"
        reasons.append("combined evidence does not support an automatic R&D triage decision")

    if has_moderate_gap and not has_large_gap:
        flags.append("moderate_supplied_prediction_gap")
        reasons.append("at least one supplied metric moderately differs from descriptor-based prediction")
    if predicted_class:
        reasons.append(f"similarity triage class is {predicted_class}")

    return CandidateAssessmentResult(
        assessment_summary={
            "method": "rule_based_virtual_lab_assessment",
            "final_decision": final_decision,
            "viability_read": viability_read,
            "better_than_known_reference": better_than_known_reference,
            "review_confidence": _review_confidence(similarity_summary, property_summary),
            "decision_reasons": reasons,
            "evidence_flags": flags,
            "source_summaries": {
                "similarity_method": similarity_summary.get("method"),
                "property_prediction_method": property_summary.get("method"),
                "rd_recommendation": rd_recommendation,
                "benchmark_verdict": benchmark_verdict,
                "neighbor_advantage_verdict": neighbor_verdict,
            },
            "official_use_policy": "This assessment is a triage synthesis for deeper review, not proof of experimental viability.",
        }
    )
