from __future__ import annotations

import json
from pathlib import Path

from contract2agent.evaluation.file_reading.schema import (
    ReferenceResult,
    ReferenceSource,
    from_dict,
    to_dict,
)


CONTEXTUAL_LIMITATIONS = [
    "Contextual reference only; no target-agent score is implied.",
    "Use for task design or comparison notes unless a comparable observed run is imported.",
]


def curated_reference_sources() -> list[ReferenceSource]:
    """Return local metadata for public file-reading eval references."""
    return [
        ReferenceSource(
            source_id="openai_agent_evals_methodology",
            title="OpenAI agent evals methodology",
            source_type="methodology_reference",
            domain="agent_evaluation",
            source_url="https://platform.openai.com/docs/guides/evals",
            license="Documentation terms apply",
            provenance="Curated metadata from OpenAI evals documentation.",
            reliability=0.25,
            applicable_task_types=[
                "citation_required_qa",
                "summary_with_citations",
                "trace_completeness",
            ],
            metrics_available=[],
            notes=[
                "Useful context for traces, graders, datasets, and eval runs.",
                "The local file-reading adapter remains offline by default.",
            ],
            limitations=CONTEXTUAL_LIMITATIONS,
        ),
        ReferenceSource(
            source_id="qasper",
            title="QASPER: A Dataset of Information-Seeking Questions and Answers Anchored in Research Papers",
            source_type="benchmark_reference",
            domain="scientific_paper_qa",
            source_url="https://allenai.org/data/qasper",
            license="See upstream dataset license.",
            provenance="Curated metadata for paper-grounded question answering.",
            reliability=0.2,
            applicable_task_types=[
                "single_file_qa",
                "multi_file_qa",
                "citation_required_qa",
                "unanswerable_question",
            ],
            metrics_available=["answer_f1", "evidence_f1"],
            notes=["Relevant for paper-reading task design with evidence grounding."],
            limitations=CONTEXTUAL_LIMITATIONS,
        ),
        ReferenceSource(
            source_id="squad",
            title="SQuAD: Stanford Question Answering Dataset",
            source_type="benchmark_reference",
            domain="reading_comprehension",
            source_url="https://rajpurkar.github.io/SQuAD-explorer/",
            license="See upstream dataset license.",
            provenance="Curated metadata for span-based question answering.",
            reliability=0.2,
            applicable_task_types=["single_file_qa", "quote_lookup", "needle_in_file"],
            metrics_available=["exact_match", "f1"],
            notes=["Useful context for extractive answer correctness metrics."],
            limitations=CONTEXTUAL_LIMITATIONS,
        ),
        ReferenceSource(
            source_id="hotpotqa",
            title="HotpotQA: A Dataset for Diverse, Explainable Multi-hop Question Answering",
            source_type="benchmark_reference",
            domain="multi_hop_qa",
            source_url="https://hotpotqa.github.io/",
            license="See upstream dataset license.",
            provenance="Curated metadata for multi-hop supporting-fact evaluation.",
            reliability=0.2,
            applicable_task_types=[
                "multi_file_qa",
                "conflicting_evidence",
                "supporting_file_recall",
            ],
            metrics_available=["answer_f1", "supporting_fact_f1"],
            notes=["Relevant for multi-file evidence selection and reasoning tasks."],
            limitations=CONTEXTUAL_LIMITATIONS,
        ),
        ReferenceSource(
            source_id="docvqa",
            title="DocVQA: Document Visual Question Answering",
            source_type="benchmark_reference",
            domain="document_qa",
            source_url="https://www.docvqa.org/",
            license="See upstream dataset license.",
            provenance="Curated metadata for document question answering.",
            reliability=0.2,
            applicable_task_types=["single_file_qa", "key_value_lookup"],
            metrics_available=["answer_normalized_levenshtein_similarity"],
            notes=[
                "Visual/PDF-heavy tasks may require optional extraction outside this dependency-free core."
            ],
            limitations=[
                *CONTEXTUAL_LIMITATIONS,
                "This adapter does not claim visual document understanding without observed runs.",
            ],
        ),
        ReferenceSource(
            source_id="longbench",
            title="LongBench: A Bilingual, Multitask Benchmark for Long Context Understanding",
            source_type="benchmark_reference",
            domain="long_context",
            source_url="https://github.com/THUDM/LongBench",
            license="See upstream dataset license.",
            provenance="Curated metadata for long-context reading tasks.",
            reliability=0.2,
            applicable_task_types=[
                "needle_in_corpus",
                "summary_with_citations",
                "multi_file_qa",
            ],
            metrics_available=["task_specific"],
            notes=["Relevant for long-document and long-corpus robustness planning."],
            limitations=CONTEXTUAL_LIMITATIONS,
        ),
        ReferenceSource(
            source_id="paperqa2",
            title="PaperQA2 open-source file-reading agent reference",
            source_type="open_source_agent_reference",
            domain="scientific_document_rag",
            source_url="https://github.com/Future-House/paper-qa",
            license="Apache-2.0",
            provenance=(
                "Curated metadata from the Future-House/paper-qa GitHub repository, "
                "README, pyproject metadata, and public repository tree."
            ),
            reliability=0.22,
            applicable_task_types=[
                "citation_required_qa",
                "summary_with_citations",
                "multi_file_qa",
                "long_document_robustness",
                "table_or_key_value_lookup",
                "conflicting_evidence",
                "source_code_lookup",
            ],
            metrics_available=[],
            notes=[
                "Useful as an open-source reference for local document indexing, "
                "evidence retrieval, in-text citations, configurable source limits, "
                "reader packages, and agent adapter design.",
                "Treat upstream papers, demos, and published results as methodology "
                "context until a Contract2Agent run artifact exists.",
            ],
            limitations=[
                *CONTEXTUAL_LIMITATIONS,
                "No upstream benchmark claim or publication result is imported as "
                "target-agent performance.",
                "External metadata, LLM, and embedding calls require explicit local "
                "configuration outside this dependency-free adapter.",
                "Page-level or document-level citations need adapter mapping before "
                "they can satisfy Contract2Agent line-citation graders.",
            ],
        ),
    ]


def load_reference_results(path: str | Path) -> list[ReferenceResult]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("reference_results", [])
    if not isinstance(items, list):
        raise ValueError(f"Reference results must be a list or object with reference_results: {path}")
    return [from_dict(ReferenceResult, item) for item in items]


def write_reference_sources(sources: list[ReferenceSource], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps([to_dict(source) for source in sources], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def import_reference_source(
    source_id: str,
    out_dir: str | Path,
    *,
    allow_network: bool = False,
    limit: int | None = None,
) -> ReferenceSource:
    source = _source_by_id(source_id)
    if not allow_network:
        raise PermissionError(
            "Network reference import is disabled by default. Re-run with --allow-network "
            "only after reviewing the upstream source, license, and size."
        )
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    source.local_path = str(target / f"{source.source_id}_metadata.json")
    source.notes.append(
        f"Network fetch is not implemented in this dependency-free adapter; limit={limit!r} was recorded."
    )
    source.limitations.append(
        "No remote examples were downloaded by this command skeleton."
    )
    Path(source.local_path).write_text(
        json.dumps(to_dict(source), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return source


def import_local_reference_source(
    path: str | Path,
    *,
    title: str,
    source_type: str = "paper",
    license_name: str = "",
    provenance: str = "",
) -> ReferenceSource:
    local = Path(path)
    return ReferenceSource(
        source_id=f"local_{source_type}_{local.stem}",
        title=title or local.name,
        source_type=source_type,
        domain="file_reading_agent",
        local_path=str(local),
        license=license_name,
        provenance=provenance or "User-provided local reference file.",
        reliability=0.45,
        applicable_task_types=[],
        metrics_available=[],
        notes=[
            "User-provided reference material; use as contextual source or task seed.",
        ],
        limitations=CONTEXTUAL_LIMITATIONS,
    )


def _source_by_id(source_id: str) -> ReferenceSource:
    normalized = source_id.casefold()
    for source in curated_reference_sources():
        if source.source_id.casefold() == normalized:
            return source
    raise KeyError(f"Unknown reference source: {source_id}")
