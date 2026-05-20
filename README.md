# Brain Lab

Brain Lab is a local-first notes CLI that will gradually become an agent lab. It starts with a tiny SQLite-backed notes app and grows step by step into a readable project for learning tool calls, manual agent loops, private inference, MCP servers, evals, and observability.

## Learning Goals

- Build a simple Python CLI
- Store local data in SQLite
- Model data with types
- Wrap business logic as tools
- Write a manual agent loop
- Connect local LLM tool calling
- Expose tools through MCP later
- Add basic evals and observability

## Learning Docs

- [Architecture diagrams](learning/diagrams.md)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Commands

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

Ask the agent with a local Ollama server:

```bash
brain ask "Create a note called Agent loop with the tag phase-4"
```

Override the model or Ollama URL:

```bash
brain ask --model llama3.2 --url http://localhost:11434 "Search notes for sqlite"
```

`brain ask` prints a compact progress trace to stderr while it runs, including
the selected model, model steps, tool calls, tool result summaries, and the run
ID. The final answer is still printed to stdout. Pass `--quiet` to hide the
progress trace, or `--no-thinking` to hide Ollama thinking output:

```bash
brain ask --quiet --no-thinking "Search notes for sqlite"
```

Provider calls include one-shot CLI guidance: the model is instructed not to ask
clarifying follow-up questions, because the command exits after one run. When a
request vaguely refers to "these files" or "these notes", the model should inspect
available Brain Lab notes with tools instead of asking which files you meant.

The default Ollama URL is `http://localhost:11434/api/chat`. To use a different
server, pass `--url` or set an environment variable:

```bash
export BRAIN_LAB_OLLAMA_URL="http://localhost:11434"
brain ask "Search notes for sqlite"
```

Each `brain ask` run is logged to `data/runs.jsonl`.

List logged runs:

```bash
brain runs list
```

Show one run:

```bash
brain runs show RUN_ID
```

Set the default model:

```bash
export BRAIN_LAB_OLLAMA_MODEL="llama3.2"
brain ask "Search notes for sqlite"
```

Run tests:

```bash
.venv/bin/python -m pytest
```

## Tool Layer

Phase 2 adds a small Python tool layer around the note operations. Tools have names,
descriptions, Pydantic input schemas, and execution functions.

```python
from brain_lab.tools import run_tool

note = run_tool(
    "create_note",
    {"title": "Tool layer", "body": "Wrap note operations.", "tags": ["tools"]},
)
```

## Agent Loop

Phase 3 adds a manual agent loop with a fake model. The loop accepts model responses
that either provide a final answer or request tool calls, then sends tool observations
back to the model until it reaches a final answer or `max_steps`.

```python
from brain_lab.agent_loop import FakeModel, ModelResponse, run_agent

model = FakeModel(
    [
        ModelResponse.call_tool("create_note", {"title": "Agent loop"}),
        ModelResponse.final("Created the note."),
    ]
)

result = run_agent("Create a note about the agent loop.", model)
print(result.final_answer)
```

## Ollama Adapter

Phase 4 adds a local Ollama adapter using its native `/api/chat` endpoint. Brain
Lab still owns the tool registry, tool schemas, tool execution, and manual loop.
The adapter only translates Brain Lab messages and tool schemas into the request
format Ollama expects.

Defaults:

- URL: `http://localhost:11434/api/chat`
- Model: `qwen3:14b`

You can set `BRAIN_LAB_OLLAMA_URL` or `BRAIN_LAB_OLLAMA_MODEL` to change those
defaults without passing CLI options.

## Public Repo Hygiene

Runtime data is ignored by default. Keep personal notes, local databases, JSONL
run logs, study notes, and scratch explanations out of commits. The tracked
`data/.gitkeep` file only keeps the runtime directory in place.

## Run Logs

Phase 5 adds simple JSONL observability. Each line in `data/runs.jsonl` records
one agent run with a run ID, timestamp, user task, model steps, tool calls, tool
arguments, short tool result summaries, final answer, and any errors. These logs
show observable agent behavior, not private model thinking.

## Current Status

Phase 1, Phase 2, Phase 3, Phase 4, and Phase 5 are implemented:

- SQLite database initialization
- `notes` table creation
- Note creation
- Note listing
- Note lookup by ID
- Note updates
- Note deletion
- Simple keyword search
- Minimal Typer CLI
- Pydantic tool input schemas
- Tool registry
- Direct tool execution for note operations
- Fake model for deterministic agent tests
- Manual agent loop
- Tool-call execution inside the loop
- Max-step enforcement
- Tool error observations
- Native Ollama chat adapter
- Ollama tool-schema conversion
- `brain ask` command
- JSONL run logging in `data/runs.jsonl`
- `brain runs list`
- `brain runs show RUN_ID`
- Mock tests for Ollama adapter behavior

Not implemented yet:

- MCP server
- Evals

## Roadmap Summary

1. Notes CLI
2. Tool layer
3. Manual agent loop
4. Real LLM tool calling
5. Observability
6. Safety policy
7. MCP server
8. MCP resources and prompts
9. Evals
10. Portfolio polish
