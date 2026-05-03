from __future__ import annotations

import json
from collections import Counter
from typing import Any

from contract2agent.triage.models import EvalCoverage


STANDARD_AREAS = [
    "task_completion",
    "tool_use",
    "tool_order",
    "tool_arguments",
    "output_format",
    "output_schema",
    "error_handling",
    "safety",
    "hallucination",
    "regression",
    "stability",
    "permission_boundary",
    "human_review",
]


def analyze_eval_coverage(eval_cases: list[dict[str, Any]]) -> EvalCoverage:
    detected_tags: set[str] = set()
    area_counts: Counter[str] = Counter()

    for case in eval_cases:
        text = _case_text(case)
        tags = _extract_tags(case)
        detected_tags.update(tags)
        for tag in tags:
            if tag in STANDARD_AREAS:
                area_counts[tag] += 1
        for area in _areas_from_text_and_fields(text, case):
            area_counts[area] += 1

    if not eval_cases:
        return EvalCoverage(
            eval_case_count=0,
            detected_tags=[],
            covered_areas=[],
            missing_areas=list(STANDARD_AREAS),
            weak_areas=[],
            recommended_new_areas=list(STANDARD_AREAS[:8]),
        )

    covered = sorted(area for area, count in area_counts.items() if count > 0)
    weak = sorted(area for area, count in area_counts.items() if count == 1 and len(eval_cases) > 2)
    missing = [area for area in STANDARD_AREAS if area not in covered]
    recommended = _recommended_new_areas(missing)
    return EvalCoverage(
        eval_case_count=len(eval_cases),
        detected_tags=sorted(detected_tags),
        covered_areas=covered,
        missing_areas=missing,
        weak_areas=weak,
        recommended_new_areas=recommended,
    )


def _extract_tags(case: dict[str, Any]) -> list[str]:
    tags = case.get("tags", [])
    if isinstance(tags, str):
        return [_normalize_tag(tags)]
    if isinstance(tags, list):
        return [_normalize_tag(str(tag)) for tag in tags if str(tag).strip()]
    return []


def _case_text(case: dict[str, Any]) -> str:
    parts = []
    for key in ("name", "id", "description", "expected_behavior", "input"):
        value = case.get(key)
        if value is not None:
            parts.append(str(value))
    return " ".join(parts).casefold()


def _areas_from_text_and_fields(text: str, case: dict[str, Any]) -> set[str]:
    areas: set[str] = set()
    if any(phrase in text for phrase in ("missing_file", "missing file", "invalid_input", "invalid input", "tool_error", "tool error", "not found")):
        areas.add("error_handling")
    if any(phrase in text for phrase in ("hallucination", "source", "citation", "cite", "evidence")):
        areas.add("hallucination")
    if any(phrase in text for phrase in ("safety", "forbidden", "permission", "approval")):
        areas.add("safety")
    if any(phrase in text for phrase in ("regression", "baseline")):
        areas.add("regression")
    if any(phrase in text for phrase in ("stable", "stability", "repeat")):
        areas.add("stability")
    if any(phrase in text for phrase in ("tool order", "sequence", "before", "after")):
        areas.add("tool_order")
    if any(phrase in text for phrase in ("argument", "args", "parameter")):
        areas.add("tool_arguments")
    if any(phrase in text for phrase in ("output", "markdown", "yaml", "table", "format")):
        areas.add("output_format")

    if case.get("expected_tools"):
        areas.add("tool_use")
    if case.get("expected_output"):
        areas.add("output_format")

    serialized = json.dumps(case, sort_keys=True, default=str).casefold()
    if "json_schema" in serialized or "schema" in serialized:
        areas.add("output_schema")
    if "human_review" in serialized or "review" in serialized or "approval" in serialized:
        areas.add("human_review")
    if "permission_boundary" in serialized or "allowed_dir" in serialized or "forbidden_path" in serialized:
        areas.add("permission_boundary")
    if any(key in case for key in ("assertions", "scorers", "expected", "expected_behavior")):
        areas.add("task_completion")
    return areas


def _recommended_new_areas(missing: list[str]) -> list[str]:
    priority = [
        "task_completion",
        "tool_use",
        "tool_order",
        "tool_arguments",
        "output_format",
        "output_schema",
        "error_handling",
        "safety",
        "hallucination",
        "regression",
        "permission_boundary",
        "human_review",
        "stability",
    ]
    return [area for area in priority if area in missing]


def _normalize_tag(value: str) -> str:
    cleaned = []
    for char in value.casefold().strip():
        if char.isalnum():
            cleaned.append(char)
        elif cleaned and cleaned[-1] != "_":
            cleaned.append("_")
    return "".join(cleaned).strip("_")
