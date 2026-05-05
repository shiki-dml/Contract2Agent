from __future__ import annotations

import json
import sys


def main() -> int:
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    payload = json.loads(open(input_path, encoding="utf-8").read())
    task_id = payload.get("task_id", "")
    if "unanswerable" in task_id:
        answer = "Insufficient evidence in the allowed corpus."
        citations = []
        files_read = []
    elif task_id == "sample_refund_notice_period":
        answer = "Approved refunds require a written service-impact notice within 7 calendar days."
        citations = [
            {
                "file_id": "contract_policy.md",
                "line_start": 3,
                "line_end": 3,
                "quote": "Approved refunds require a written service-impact notice within 7 calendar days.",
            }
        ]
        files_read = ["contract_policy.md"]
    elif task_id == "sample_incident_severity":
        answer = "Support classified the issue as severity 2 because reports were delayed but login still worked."
        citations = [
            {
                "file_id": "incident_notes.md",
                "line_start": 4,
                "line_end": 4,
                "quote": "Support classified the issue as severity 2 because reports were delayed but login still worked.",
            }
        ]
        files_read = ["incident_notes.md"]
    elif task_id == "sample_invoice_due_date":
        answer = "Invoices are due net 30 after delivery of the synthetic invoice."
        citations = [
            {
                "file_id": "payment_terms.md",
                "line_start": 3,
                "line_end": 3,
                "quote": "Invoices are due net 30 after delivery of the synthetic invoice.",
            }
        ]
        files_read = ["payment_terms.md"]
    elif "release" in task_id:
        answer = "Version 2 adds offline export and stricter citation checks."
        citations = [
            {
                "file_id": "release_notes_v2.md",
                "line_start": 3,
                "line_end": 3,
                "quote": "Adds offline export and stricter citation checks.",
            }
        ]
        files_read = ["release_notes_v2.md"]
    else:
        answer = "Enterprise customers must retain audit logs for 90 days."
        citations = [
            {
                "file_id": "policy.md",
                "line_start": 3,
                "line_end": 3,
                "quote": "Enterprise customers must retain audit logs for 90 days.",
            }
        ]
        files_read = ["policy.md"]
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "answer": answer,
                "citations": citations,
                "confidence": 0.9,
                "files_read": files_read,
                "notes": "deterministic dummy",
            },
            handle,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
