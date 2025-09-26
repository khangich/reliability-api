# Reliability API

This repository contains a minimal skeleton for the Reliability API runtime and
HTTP surface. The goal is to provide a starting point for building the
"Stripe-for-Agents" enforcement layer described in the product specification.

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
