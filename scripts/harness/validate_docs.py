from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DOCS = [
    "AGENTS.md",
    "docs/README.md",
    "docs/PROJECT_CONTEXT.md",
    "docs/ARCHITECTURE.md",
    "docs/CODEMAP.md",
    "docs/GOLDEN_PRINCIPLES.md",
    "docs/DECISIONS.md",
    "docs/AGENT_HANDOFF.md",
    "docs/harness/README.md",
    "docs/harness/FEATURE_REGISTRY.schema.json",
    "docs/harness/feature_registry.json",
    "docs/harness/PROGRESS.md",
    "docs/harness/QUALITY_GATES.md",
    "docs/harness/EVAL_MATRIX.md",
    "docs/harness/SPRINT_CONTRACT_TEMPLATE.md",
    "docs/harness/RUNBOOK.md",
]

MAJOR_READMES = [
    "contract2agent/README.md",
    "contract2agent/evaluation/README.md",
    "contract2agent/evaluation/file_reading/README.md",
    "contract2agent/cost_estimate/README.md",
    "contract2agent/patch_preview/README.md",
    "contract2agent/triage/README.md",
    "contract2agent/templates/README.md",
    "tests/README.md",
    "scripts/README.md",
    "scripts/harness/README.md",
]

VALID_STATUSES = {
    "inferred",
    "needs_verification",
    "implemented_pending_evaluation",
    "verified_pass",
    "blocked",
    "deprecated",
}

VALID_VISIBILITIES = {"user_visible", "developer_visible", "internal"}
VALID_CONFIDENCE = {"low", "medium", "high", "unknown"}
VALID_EVIDENCE_KINDS = {
    "source",
    "test",
    "command",
    "doc",
    "example",
    "artifact",
    "historical_record",
    "manual_annotation",
    "missing_evidence",
    "inferred",
}
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def main() -> int:
    failures: list[str] = []
    failures.extend(check_required_files(REQUIRED_DOCS, "required doc"))
    failures.extend(check_required_files(MAJOR_READMES, "module README"))
    failures.extend(check_agents_md())
    failures.extend(check_feature_registry())

    if failures:
        for failure in failures:
            print(failure)
        return 1

    print(
        "Validated "
        f"{len(REQUIRED_DOCS)} required docs, "
        f"{len(MAJOR_READMES)} module READMEs, "
        "AGENTS.md length, and feature registry shape."
    )
    return 0


def check_required_files(paths: list[str], label: str) -> list[str]:
    failures: list[str] = []
    for relative in paths:
        path = ROOT / relative
        if not path.exists():
            failures.append(f"Missing {label}: {relative}")
        elif path.is_file() and not path.read_text(encoding="utf-8").strip():
            failures.append(f"Empty {label}: {relative}")
    return failures


def check_agents_md() -> list[str]:
    path = ROOT / "AGENTS.md"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    failures: list[str] = []
    if len(lines) > 120:
        failures.append(f"AGENTS.md should stay under 120 lines; found {len(lines)}")
    required_links = [
        "docs/PROJECT_CONTEXT.md",
        "docs/ARCHITECTURE.md",
        "docs/CODEMAP.md",
        "docs/harness/feature_registry.json",
        "docs/AGENT_HANDOFF.md",
    ]
    text = "\n".join(lines)
    for link in required_links:
        if link not in text:
            failures.append(f"AGENTS.md missing source-of-truth pointer: {link}")
    return failures


def check_feature_registry() -> list[str]:
    path = ROOT / "docs/harness/feature_registry.json"
    if not path.exists():
        return []

    failures: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Invalid feature_registry.json: {exc}"]

    if data.get("registry_version") != "1.0":
        failures.append("feature_registry.json registry_version must be 1.0")
    if not DATE_RE.fullmatch(str(data.get("updated_at", ""))):
        failures.append("feature_registry.json updated_at must be YYYY-MM-DD")
    if not isinstance(data.get("source"), dict):
        failures.append("feature_registry.json source must be an object")
    if not isinstance(data.get("status_policy"), dict):
        failures.append("feature_registry.json status_policy must be an object")

    features = data.get("features")
    if not isinstance(features, list) or not features:
        failures.append("feature_registry.json features must be a non-empty list")
        return failures

    seen: set[str] = set()
    for index, feature in enumerate(features):
        prefix = f"feature[{index}]"
        if not isinstance(feature, dict):
            failures.append(f"{prefix} must be an object")
            continue
        feature_id = feature.get("id")
        if not isinstance(feature_id, str) or not re.fullmatch(r"[a-z0-9_]+", feature_id):
            failures.append(f"{prefix}.id must be snake_case")
        elif feature_id in seen:
            failures.append(f"Duplicate feature id: {feature_id}")
        else:
            seen.add(feature_id)

        required = [
            "id",
            "name",
            "summary",
            "visibility",
            "status",
            "confidence",
            "evidence",
            "tests",
            "docs",
            "risks",
            "notes",
            "last_updated",
        ]
        for key in required:
            if key not in feature:
                failures.append(f"{prefix}.{key} is required")

        if feature.get("visibility") not in VALID_VISIBILITIES:
            failures.append(f"{prefix}.visibility has invalid value: {feature.get('visibility')}")
        if feature.get("status") not in VALID_STATUSES:
            failures.append(f"{prefix}.status has invalid value: {feature.get('status')}")
        if feature.get("confidence") not in VALID_CONFIDENCE:
            failures.append(f"{prefix}.confidence has invalid value: {feature.get('confidence')}")

        evidence = feature.get("evidence")
        if not isinstance(evidence, list):
            failures.append(f"{prefix}.evidence must be a list")
            evidence = []
        for evidence_index, item in enumerate(evidence):
            item_prefix = f"{prefix}.evidence[{evidence_index}]"
            if not isinstance(item, dict):
                failures.append(f"{item_prefix} must be an object")
                continue
            if item.get("kind") not in VALID_EVIDENCE_KINDS:
                failures.append(f"{item_prefix}.kind has invalid value: {item.get('kind')}")
            for key in ["path", "detail"]:
                if not isinstance(item.get(key), str) or not item.get(key):
                    failures.append(f"{item_prefix}.{key} must be a non-empty string")
            date = item.get("date")
            if date is not None and not DATE_RE.fullmatch(str(date)):
                failures.append(f"{item_prefix}.date must be YYYY-MM-DD when present")

        for key in ["tests", "docs", "risks"]:
            if not isinstance(feature.get(key), list):
                failures.append(f"{prefix}.{key} must be a list")
        if not isinstance(feature.get("notes"), str):
            failures.append(f"{prefix}.notes must be a string")
        if not DATE_RE.fullmatch(str(feature.get("last_updated", ""))):
            failures.append(f"{prefix}.last_updated must be YYYY-MM-DD")
        if feature.get("status") == "verified_pass" and not feature.get("evidence"):
            failures.append(f"{prefix} is verified_pass without evidence")
        last_verified = feature.get("last_verified")
        if last_verified is not None and not DATE_RE.fullmatch(str(last_verified)):
            failures.append(f"{prefix}.last_verified must be YYYY-MM-DD or null")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
