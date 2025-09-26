# Reliability API

This repository contains a minimal skeleton for the Reliability API runtime and
HTTP surface. The goal is to provide a starting point for building the
"Stripe-for-Agents" enforcement layer described in the product specification.

## Research-backed Motivation

Shome et al. (2025) review 102 commercial agent offerings and find that most
cluster around three marketed capabilities: orchestration (36 automation and 18
direct UI control products), creation (25 writing, 3 app/site builders, and 2
each for presentations and images), and insight (98 information retrieval,
44 recommendation, 31 data analysis, and 17 synthesis agents). Yet when 31
participants were asked to complete 62 representative tasks with two leading
commercial agents (Operator and Manus), five recurring usability pain points
blocked successful outcomes across all categories.

- Misaligned agent and user mental models: participants routinely “prompt
  gambled,” uncertain about what instructions would trigger or how to access
  essential capabilities.
- Presumed trust without demonstrated competence or security: users balked at
  handing over credentials or accepting outputs without verification, noting a
  lack of preference elicitation and provenance.
- Inflexible collaboration styles: participants wanted very different mixes of
  co-pilot versus autopilot control, but existing agents rarely exposed levers
  to pause, steer, or iteratively refine work.
- Overwhelming communication overhead: verbose action logs and dense outputs
  exceeded user bandwidth, making it hard to track progress or locate the
  deliverable.
- Metacognitive gaps: 14 of 31 participants encountered operational errors, and
  agents failed to detect or recover, often looping silently.

Reliability therefore emerges as the bottleneck for agentic app adoption: users
cannot trust, steer, or recover from failures even when the underlying models
are capable. The study argues for treating reliability as a first-class citizen
with explicit transparency, oversight, and error-handling affordances.

The Reliability API exists to close that gap. Its enforcement layer provides a
consistent runtime for applying policies, instrumenting tool use, and exposing
controllable integration patterns (gateway proxy, guards, decorators, CrewAI
metadata, full SDK loop). By externalizing reliability concerns into a focused
service, teams can align product promises with user expectations, deliver
auditable execution traces, and give operators the controls they need before
rolling agentic experiences into production.

> Shome, P., Krishnan, S., & Das, S. (2025). Why Johnny Can’t Use Agents:
> Industry Aspirations vs. User Realities with AI Agent Software. arXiv
> preprint arXiv:2509.14528.

## Getting started

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

2. Run the FastAPI application:

   ```bash
   uvicorn api.http.app:app --reload
   ```

3. Interact with the API using `curl` or the automatically generated Swagger UI
   at http://127.0.0.1:8000/docs.

## Project layout

The directory structure mirrors the high-level architecture outlined in the
product brief. Only the HTTP API and runtime skeleton contain executable code
at this stage; other packages act as placeholders for future components.

## Integration options

Reliability supports multiple integration surfaces so teams can adopt the
runtime incrementally. The repository contains skeletal helpers and samples for
each option described in the product brief:

| Option | Description | Reference |
| ------ | ----------- | --------- |
| A | OpenAI-compatible gateway proxy | `adapters.gateway.OpenAIGatewayProxy`, `examples/gateway_proxy` |
| B | Guard context manager | `examples/langchain_guard` |
| C | Reliable tool decorator | `samples/langchain/reliable_tool_decorator.py` |
| D | CrewAI policy metadata | `examples/crewai_policy`, `samples/crewai/metadata_policy.py` |
| E | Full SDK task loop | `adapters.sdk.py.ReliabilityClient`, `examples/full_sdk_runtime` |

The `samples/` directory provides runnable snippets for LangChain and CrewAI
integrations. Install the optional dependencies locally before running a
particular sample.
