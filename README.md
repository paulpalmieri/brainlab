# Brain Lab

Brain Lab is my personal note-taking app and a test bench for agentic
experiments.

It is currently a local-first notes CLI with an explicit tool layer, a
hand-written agent loop, local Ollama inference, and JSONL run logs.

The project avoids agent frameworks and keeps the important boundaries visible:
SQLite persistence, note operations, tool schemas, model messages, tool
execution, and run observability each live in their own small module.

## What It Does

- Stores notes locally in SQLite.
- Adds, lists, reads, updates, deletes, and searches notes from the CLI.
- Exposes note operations as validated Pydantic-backed tools.
- Runs a manual model/tool loop without external agent frameworks.
- Connects to local Ollama for private inference.
- Logs agent runs to JSONL so tool calls and outcomes are inspectable.
- Includes tests for the note layer, tool layer, agent loop, model adapter, run
  logs, and CLI wiring.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Brain Lab expects an Ollama server at `http://localhost:11434` and uses
`qwen3:14b` by default.

## Notes CLI

Add a note:

```bash
brain note add "My note title" --body "Body text" --tags ai,mcp
```

List notes:

```bash
brain note list
```

Get one note by ID:

```bash
brain note get NOTE_ID
```

Update a note:

```bash
brain note update NOTE_ID --title "New title" --body "New body" --tags ai,mcp
```

Delete a note:

```bash
brain note delete NOTE_ID
```

Search notes:

```bash
brain note search "keyword"
```

## Agent CLI

Ask the agent to work with your notes:

```bash
brain ask "Create a note called Agent loop with the tag agent"
```

`brain ask` prints a compact progress trace to stderr while it runs, including
model steps, tool calls, tool result summaries, and the run ID. The final answer
is printed to stdout.

Hide progress output:

```bash
brain ask --quiet "Search notes for sqlite"
```

Hide Ollama thinking output while keeping the rest of the progress trace:

```bash
brain ask --no-thinking "Search notes for sqlite"
```

The Ollama endpoint and model are plain constants in `brain_lab/llm.py`.

## Run Logs

Each `brain ask` run is logged to `data/runs.jsonl`. Runtime data is ignored by
Git, so local notes, databases, and run logs stay out of the public repo.

List logged runs:

```bash
brain runs list
```

Show one run:

```bash
brain runs show RUN_ID
```

## Design

The core flow is intentionally direct:

```text
brain ask
  -> llm.py
  -> agent_loop.py
  -> tools.py
  -> notes.py
  -> db.py
  -> SQLite
```

Module responsibilities:

- `brain_lab/cli.py` defines the Typer command-line interface.
- `brain_lab/db.py` owns SQLite connection and schema setup.
- `brain_lab/models.py` contains typed data models.
- `brain_lab/notes.py` contains note business logic.
- `brain_lab/tools.py` wraps note operations as model-callable tools.
- `brain_lab/agent_loop.py` contains the manual model/tool loop.
- `brain_lab/llm.py` sends chat requests to local Ollama and adapts responses
  to Brain Lab's internal model protocol.
- `brain_lab/run_logs.py` writes and reads JSONL run records.

## Tests

Run the test suite:

```bash
.venv/bin/python -m pytest
```
