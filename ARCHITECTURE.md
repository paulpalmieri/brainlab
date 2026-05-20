# Architecture

Brain Lab is intentionally small. Each layer should stay easy to read before the next layer is added.

## Current Shape

```text
CLI
  -> notes.py
  -> db.py
  -> SQLite
```

```text
tools.py
  -> notes.py
  -> db.py
  -> SQLite
```

```text
agent_loop.py
  -> tools.py
  -> notes.py
  -> db.py
  -> SQLite
```

```text
brain ask
  -> provider_models.py
  -> agent_loop.py
  -> tools.py
  -> notes.py
  -> db.py
```

## Future Shape

```text
MCP server
  -> mcp_server.py
  -> tools.py
  -> notes.py
  -> db.py
```

```text
Eval runner
  -> evals
  -> agent_loop.py/tools.py
```

## Module Responsibilities

`brain_lab/cli.py` defines the command-line interface. It should parse command input and call business logic.

`brain_lab/db.py` owns SQLite connections and database initialization.

`brain_lab/models.py` contains typed data models.

`brain_lab/notes.py` contains note business logic. It should not know about Typer, tools, model providers, or MCP.

`brain_lab/tools.py` wraps note business logic as tool definitions with names, descriptions, Pydantic input schemas, and execution functions. Tool arguments describe caller-provided data. Runtime context, such as `db_path`, is passed separately so future model calls do not choose local database files.

`brain_lab/agent_loop.py` contains a hand-written loop for model responses, tool calls, and final answers. It starts with a deterministic fake model so the loop can be tested without network calls.

`brain_lab/provider_models.py` contains model adapters. The current adapter sends native Ollama `/api/chat` requests, converts local tool definitions into Ollama tool schemas, parses Ollama tool calls, and returns the same `ModelResponse` shape used by the fake model.

Future `brain_lab/mcp_server.py` will expose the existing tool layer through MCP without duplicating note logic.

Future `evals` code will run small behavior checks against tools and the agent loop.
