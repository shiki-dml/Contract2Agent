# Sample Reports

These reports are illustrative examples, not actual run outputs from this repository checkout.

| Report | Use it to understand |
|---|---|
| [Quick report](quick-report.md) | Smoke diagnosis output and review items. |
| [Deep report](deep-report.md) | Multi-round diagnosis, taxonomy summary, baseline comparison, and time cost. |
| [Auto report](auto-report.md) | Target confidence, patch summary, overfitting warning, efficiency warning, and human review recommendation. |

To generate real local reports:

```bash
agentdoctor quick
agentdoctor deep --rounds 3 --review on-fail
agentdoctor auto --target-confidence 0.85 --max-rounds 6 --review on-fail
```

Real reports are written under `reports/` by default.
