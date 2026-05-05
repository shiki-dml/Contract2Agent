from __future__ import annotations

import json
import sys


payload = json.loads(open(sys.argv[1], encoding="utf-8").read())
task_id = payload.get("task_id", "")
if task_id == "sample_refund_notice_period":
    answer = "Approved refunds require a written service-impact notice within 7 calendar days."
    citations = [
        {
            "file_id": "contract_policy.md",
            "line_start": 4,
            "line_end": 4,
            "quote": "Approved refunds require a written service-impact notice within 7 calendar days.",
        }
    ]
    files_read = ["contract_policy.md"]
else:
    answer = "Enterprise customers must retain audit logs for 90 days."
    citations = [
        {
            "file_id": "policy.md",
            "line_start": 3,
            "line_end": 3,
            "quote": "Enterprise customers retain audit logs forever.",
        }
    ]
    files_read = ["policy.md"]
with open(sys.argv[2], "w", encoding="utf-8") as handle:
    json.dump(
        {
            "answer": answer,
            "citations": citations,
            "confidence": 0.6,
            "files_read": files_read,
            "notes": f"bad citation for {task_id}",
        },
        handle,
    )
