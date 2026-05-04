# Examples

The repository includes sample files that show the intended GitHub-facing workflow without requiring external services.

## Example Dashboard

Start with the [examples dashboard](https://github.com/shiki-dml/AgentDoctor/tree/main/examples).

## Paper Reader Agent

The [paper reader agent example](https://github.com/shiki-dml/AgentDoctor/tree/main/examples/paper-reader-agent) demonstrates:

- triage
- document reading
- tool-call order
- Markdown output
- missing-file handling
- source-grounding and hallucination risk

Files:

- [agent.yaml](https://github.com/shiki-dml/AgentDoctor/blob/main/examples/paper-reader-agent/agent.yaml)
- [expected-report.md](https://github.com/shiki-dml/AgentDoctor/blob/main/examples/paper-reader-agent/expected-report.md)

## Sample Reports

Sample reports are examples, not actual run outputs:

- [Quick report](https://github.com/shiki-dml/AgentDoctor/blob/main/examples/reports/quick-report.md)
- [Deep report](https://github.com/shiki-dml/AgentDoctor/blob/main/examples/reports/deep-report.md)
- [Auto report](https://github.com/shiki-dml/AgentDoctor/blob/main/examples/reports/auto-report.md)

Use them to understand report shape before running the CLI locally.

## Run the Built-In Offline Demo

AgentDoctor can also generate a deterministic demo project:

```bash
agentdoctor demo --out demo_project
agentdoctor counterexamples demo_project/agent_contract.yaml --out demo_project/traces/counterexamples
agentdoctor check-all --contract demo_project/agent_contract.yaml --traces demo_project/traces/counterexamples --diagnose
```

The generated demo writes reports under `demo_project/reports/`.
