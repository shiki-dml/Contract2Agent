from __future__ import annotations

import json
from pathlib import Path

from contract2agent.evaluation.registry import (
    EvalCategoryRegistry,
    default_source_references,
)
from contract2agent.evaluation.schema import (
    AgentClassification,
    AgentProfile,
    EvidenceBundle,
    EvidenceSource,
    ExperimentSummary,
    evidence_source_from_dict,
    experiment_summary_from_dict,
)


_SOURCE_RELIABILITY = {
    "observed_experiment": 0.95,
    "imported_trace": 0.8,
    "inferred_from_tools": 0.55,
    "inferred_from_tasks": 0.5,
    "synthetic_sample": 0.35,
    "user_declared": 0.25,
    "benchmark_reference": 0.2,
    "curated_research_reference": 0.2,
    "missing": 0.0,
}


class ExperimentResultStore:
    def __init__(self, results: list[ExperimentSummary] | None = None) -> None:
        self._results = list(results or [])

    @classmethod
    def from_records(cls, records: list[dict]) -> "ExperimentResultStore":
        return cls([experiment_summary_from_dict(record) for record in records])

    @classmethod
    def from_json_path(cls, path: str | Path) -> "ExperimentResultStore":
        return cls(load_experiment_results(path))

    def add(self, result: ExperimentSummary) -> None:
        self._results.append(result)

    def all(self) -> list[ExperimentSummary]:
        return list(self._results)

    def for_agent(self, agent_id: str) -> list[ExperimentSummary]:
        return [
            result
            for result in self._results
            if result.agent_id == agent_id
        ]


class EvidenceResolver:
    def __init__(self, eval_category_registry: EvalCategoryRegistry | None = None) -> None:
        self.eval_category_registry = eval_category_registry or EvalCategoryRegistry.default()

    def resolve(
        self,
        profile: AgentProfile,
        classification: AgentClassification,
        experiment_results: list[ExperimentSummary] | ExperimentResultStore | None = None,
        benchmark_references: list[EvidenceSource] | None = None,
    ) -> EvidenceBundle:
        if isinstance(experiment_results, ExperimentResultStore):
            experiments = experiment_results.for_agent(profile.agent_id)
        else:
            experiments = [
                result
                for result in (experiment_results or [])
                if result.agent_id == profile.agent_id
            ]

        categories = self.eval_category_registry.select_for_classification(classification)
        references = self._applicable_references(
            classification,
            benchmark_references if benchmark_references is not None else default_source_references(),
        )
        data_sources = self._profile_sources(profile, classification)
        data_sources.extend(self._experiment_sources(experiments))
        data_sources.extend(references)

        missing = self._missing_evidence(classification, categories, experiments, references)
        quality = self._evidence_quality(data_sources, experiments)

        return EvidenceBundle(
            agent_id=profile.agent_id,
            classification=classification,
            applicable_eval_categories=categories,
            experiment_summaries=experiments,
            data_sources=sorted(data_sources, key=lambda source: source.source_id),
            missing_evidence=missing,
            evidence_quality_score=quality,
            coverage_by_type=self._coverage_by_type(classification, categories, experiments),
        )

    def _profile_sources(
        self,
        profile: AgentProfile,
        classification: AgentClassification,
    ) -> list[EvidenceSource]:
        sources = [
            EvidenceSource(
                source_id="profile_declared_capabilities",
                source_type="user_declared",
                title="Declared profile description and capabilities",
                reliability=_SOURCE_RELIABILITY["user_declared"],
                applies_to=[profile.agent_id],
                limitations=["User-declared capabilities are not performance evidence."],
                notes=[profile.description] if profile.description else [],
            )
        ]
        if any(classification.matched_signals.values()):
            sources.append(
                EvidenceSource(
                    source_id="profile_tool_and_task_inference",
                    source_type="inferred_from_tools",
                    title="Inferred from supplied tools, permissions, and sample tasks",
                    reliability=_SOURCE_RELIABILITY["inferred_from_tools"],
                    applies_to=[profile.agent_id],
                    limitations=["Inference from tools/tasks still needs observed traces."],
                    notes=[
                        "Matched signals are recorded in the classification trail."
                    ],
                )
            )
        if profile.sample_tasks:
            sources.append(
                EvidenceSource(
                    source_id="profile_sample_tasks",
                    source_type="inferred_from_tasks",
                    title="Representative sample tasks",
                    reliability=_SOURCE_RELIABILITY["inferred_from_tasks"],
                    applies_to=[profile.agent_id],
                    limitations=["Sample tasks describe intended use, not measured performance."],
                    notes=profile.sample_tasks[:3],
                )
            )
        return sources

    def _experiment_sources(
        self,
        experiments: list[ExperimentSummary],
    ) -> list[EvidenceSource]:
        sources: list[EvidenceSource] = []
        for result in experiments:
            source_type = _normalize_source_type(result.evidence_source)
            sources.append(
                EvidenceSource(
                    source_id=f"experiment:{result.result_id}",
                    source_type=source_type,
                    title=f"Experiment summary {result.result_id}",
                    reliability=_SOURCE_RELIABILITY[source_type],
                    applies_to=[result.agent_id, result.agent_type, result.eval_category],
                    limitations=result.limitations,
                    notes=[
                        f"verdict={result.verdict}",
                        f"trace_available={result.trace_available}",
                    ],
                )
            )
        return sources

    def _applicable_references(
        self,
        classification: AgentClassification,
        references: list[EvidenceSource],
    ) -> list[EvidenceSource]:
        type_ids = set(classification.primary_types) | set(classification.secondary_types)
        selected = [
            reference
            for reference in references
            if (
                "evaluation_methodology" in reference.applies_to
                or bool(type_ids.intersection(reference.applies_to))
            )
        ]
        return [
            EvidenceSource(
                source_id=reference.source_id,
                source_type=reference.source_type,
                title=reference.title,
                url=reference.url,
                local_path=reference.local_path,
                reliability=min(reference.reliability, 0.2),
                applies_to=reference.applies_to,
                limitations=[
                    *reference.limitations,
                    "Reference sources are contextual and never direct scores.",
                ],
                notes=reference.notes,
            )
            for reference in selected
        ]

    def _missing_evidence(
        self,
        classification: AgentClassification,
        categories,
        experiments: list[ExperimentSummary],
        references: list[EvidenceSource],
    ) -> list[str]:
        missing = list(classification.missing_evidence)
        if not experiments:
            missing.append("No observed experiment summary or imported trace is linked to this agent.")
        for category in categories:
            if not any(result.eval_category == category.category_id for result in experiments):
                missing.append(f"No experiment summary for eval category: {category.category_id}.")
        for result in experiments:
            if not result.trace_available:
                missing.append(f"Experiment {result.result_id} has no trace available.")
            if result.evidence_source in {"benchmark_reference", "curated_research_reference"}:
                missing.append(
                    f"Experiment {result.result_id} is reference metadata, not direct performance evidence."
                )
        if references and not experiments:
            missing.append("Reference sources are available only as context; no comparable run is present.")
        return sorted(set(missing))

    def _evidence_quality(
        self,
        data_sources: list[EvidenceSource],
        experiments: list[ExperimentSummary],
    ) -> float:
        direct_sources = [
            source
            for source in data_sources
            if source.source_type not in {"benchmark_reference", "curated_research_reference", "missing"}
        ]
        if not direct_sources:
            return 0.0
        best_experiment = max(
            (
                source.reliability
                for source in data_sources
                if source.source_type in {"observed_experiment", "imported_trace"}
            ),
            default=0.0,
        )
        inference_average = sum(source.reliability for source in direct_sources) / len(direct_sources)
        quality = max(best_experiment, min(0.6, inference_average))
        return round(quality, 3)

    def _coverage_by_type(
        self,
        classification: AgentClassification,
        categories,
        experiments: list[ExperimentSummary],
    ) -> dict[str, float]:
        type_ids = [
            type_id
            for type_id in [*classification.primary_types, *classification.secondary_types]
            if type_id != "unknown_agent"
        ] or ["unknown_agent"]
        coverage: dict[str, float] = {}
        result_categories = {result.eval_category for result in experiments}
        for type_id in type_ids:
            type_categories = [
                category
                for category in categories
                if type_id in category.applicable_agent_types
            ]
            if not type_categories:
                coverage[type_id] = 0.0
                continue
            covered = sum(
                1 for category in type_categories if category.category_id in result_categories
            )
            coverage[type_id] = round(covered / len(type_categories), 3)
        return coverage


def load_experiment_results(path: str | Path) -> list[ExperimentSummary]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    records = data.get("results", data.get("summaries", data)) if isinstance(data, dict) else data
    if not isinstance(records, list):
        raise ValueError(f"Experiment summary JSON must contain a list: {path}")
    return [experiment_summary_from_dict(record) for record in records]


def load_source_references(path: str | Path) -> list[EvidenceSource]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    records = data.get("sources", data.get("references", data)) if isinstance(data, dict) else data
    if not isinstance(records, list):
        raise ValueError(f"Source reference JSON must contain a list: {path}")
    return [evidence_source_from_dict(record) for record in records]


def load_benchmark_references(path: str | Path) -> list[EvidenceSource]:
    return load_source_references(path)


def _normalize_source_type(value: str) -> str:
    if value == "observed_run":
        return "observed_experiment"
    if value in _SOURCE_RELIABILITY:
        return value
    return "missing"
