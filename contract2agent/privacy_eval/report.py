from __future__ import annotations

import json
from pathlib import Path

from contract2agent.privacy_eval.analyzer import analyze_privacy_profile
from contract2agent.privacy_eval.schema import (
    PrivacyEvalProfile,
    PrivacyEvalReport,
    PrivacyScorecard,
    to_dict,
)


def build_privacy_report(profile: PrivacyEvalProfile) -> PrivacyEvalReport:
    scorecard = analyze_privacy_profile(profile)
    data = {
        "profile": to_dict(profile),
        "scorecard": to_dict(scorecard),
    }
    markdown = render_privacy_markdown(profile, scorecard)
    return PrivacyEvalReport(
        profile=profile,
        scorecard=scorecard,
        markdown=markdown,
        json_report=data,
    )


def render_privacy_markdown(profile: PrivacyEvalProfile, scorecard: PrivacyScorecard) -> str:
    lines = [
        "# Privacy Evaluation Report",
        "",
        "## Profile",
        f"- Profile id: `{profile.profile_id}`",
        f"- Name: {profile.name}",
        f"- Domain: {profile.domain}",
        f"- Sensitive data: {', '.join(profile.sensitive_data) or 'none declared'}",
        "",
        "## Scorecard",
        f"- Overall privacy readiness: {scorecard.overall_privacy_readiness:.3f}",
        f"- Leakage risk score: {scorecard.leakage_risk_score:.3f}",
        f"- Channel coverage: {scorecard.channel_coverage:.3f}",
        f"- DP readiness: {scorecard.dp_readiness:.3f}",
        f"- Prompt-injection privacy resilience: {scorecard.prompt_injection_resilience:.3f}",
        f"- Auditability: {scorecard.auditability:.3f}",
        f"- Minimization: {scorecard.minimization:.3f}",
        f"- Approval safety: {scorecard.approval_safety:.3f}",
        "",
        "## Findings",
    ]
    if scorecard.findings:
        for finding in scorecard.findings:
            lines.append(f"- [{finding.severity.upper()}] `{finding.finding_id}`: {finding.summary}")
            if finding.evidence:
                lines.append(f"  - Evidence: {', '.join(finding.evidence)}")
            if finding.recommendation:
                lines.append(f"  - Recommendation: {finding.recommendation}")
            if finding.source_reference:
                lines.append(f"  - Reference: `{finding.source_reference}`")
    else:
        lines.append("- No findings from static profile checks.")
    lines.extend(["", "## Data Flows"])
    for flow in profile.data_flows:
        lines.append(
            f"- `{flow.flow_id}`: channel={flow.channel}, sensitive={flow.contains_sensitive_data}, "
            f"external={flow.external_destination}, untrusted={flow.untrusted_input}, controls={', '.join(flow.controls) or 'none'}"
        )
    if not profile.data_flows:
        lines.append("- No data flows declared.")
    lines.extend(["", "## Recommended Next Tests"])
    lines.extend(_plain_list(scorecard.recommended_next_tests, "No next tests recommended."))
    lines.extend(["", "## Source References"])
    for source in scorecard.source_references:
        lines.append(
            f"- `{source['source_id']}` [{source['source_type']}]: {source['title']} ({source['url']})"
        )
        limitations = source.get("limitations") or []
        if limitations:
            lines.append(f"  - Limitations: {'; '.join(str(item) for item in limitations)}")
    lines.extend(["", "## Limitations"])
    lines.extend(_plain_list(scorecard.limitations, "No limitations recorded."))
    lines.append("")
    return "\n".join(lines)


def write_privacy_report(
    report: PrivacyEvalReport,
    out: str | Path,
    *,
    output_format: str = "markdown",
) -> Path:
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized = output_format.casefold()
    if normalized == "json":
        target.write_text(json.dumps(report.json_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        target.write_text(report.markdown.rstrip() + "\n", encoding="utf-8")
    return target


def _plain_list(values: list[str], empty: str) -> list[str]:
    if not values:
        return [f"- {empty}"]
    return [f"- {value}" for value in values]
