# Brain Lab Architecture Diagrams

This document explains the current Brain Lab architecture using Mermaid diagrams.
It is meant to be read alongside `PROJECT_BRIEF.md`, `ROADMAP.md`, and
`ARCHITECTURE.md`.

Brain Lab is intentionally small. Each phase adds one concept at a time:

1. Store notes locally in SQLite.
2. Wrap note operations as tools.
3. Run a manual agent loop with a fake model.
4. Connect a local Ollama model to the same loop.

## System Map

```mermaid
flowchart TD
    User["User"]
    CLI["brain_lab/cli.py<br/>Typer commands"]
    ProviderModels["brain_lab/provider_models.py<br/>Ollama adapter"]
    AgentLoop["brain_lab/agent_loop.py<br/>manual loop"]
    Tools["brain_lab/tools.py<br/>tool registry and schemas"]
    Notes["brain_lab/notes.py<br/>note business logic"]
    DB["brain_lab/db.py<br/>SQLite connection and schema"]
    Models["brain_lab/models.py<br/>typed data models"]
    SQLite[("data/brain.db<br/>SQLite")]

    User --> CLI
    CLI --> Notes
    CLI --> ProviderModels
    CLI --> AgentLoop
    ProviderModels --> AgentLoop
    AgentLoop --> Tools
    Tools --> Notes
    Notes --> DB
    Notes --> Models
    DB --> SQLite
```

The CLI has two paths:

- `brain note ...` commands call `notes.py` directly.
- `brain ask ...` creates an Ollama model, then runs the manual agent loop.

The agent loop does not know about Ollama. It only knows that a model can return
either a final answer or tool calls.

## Module Responsibilities

```mermaid
flowchart LR
    CLI["cli.py"]
    ProviderModels["provider_models.py"]
    AgentLoop["agent_loop.py"]
    Tools["tools.py"]
    Notes["notes.py"]
    DB["db.py"]
    Models["models.py"]

    CLI -->|"Parse user commands"| Notes
    CLI -->|"Create Ollama model"| ProviderModels
    CLI -->|"Run ask command"| AgentLoop
    ProviderModels -->|"Return ModelResponse"| AgentLoop
    AgentLoop -->|"Execute requested tools"| Tools
    Tools -->|"Validate args and call functions"| Notes
    Notes -->|"Read and write notes"| DB
    Notes -->|"Return Note objects"| Models
    DB -->|"Open connection and init schema"| SQLite[("SQLite")]
```

### `cli.py`

`cli.py` is the application entry point. It should stay thin:

- Parse command-line input.
- Call the correct application layer.
- Print user-facing output.
- Exit with a non-zero code for command failures.

It has two kinds of commands:

- `brain note ...` for direct note operations.
- `brain ask ...` for model-driven note operations through the agent loop.

### `db.py`

`db.py` owns SQLite details:

- The default database path.
- Creating parent directories.
- Opening SQLite connections.
- Creating the `notes` table.

Other modules should not build SQLite schemas themselves.

### `models.py`

`models.py` contains typed data returned by the business layer. Right now the main
model is `Note`.

### `notes.py`

`notes.py` is the business logic layer. It knows how to:

- Create notes.
- List notes.
- Get a note by ID.
- Update notes.
- Delete notes.
- Search note text and tags.

It does not know about Typer, tools, model providers, or MCP.

### `tools.py`

`tools.py` wraps note operations in tool definitions. Each tool has:

- A stable tool name.
- A short description.
- A Pydantic input schema.
- A Python function that executes the tool.

The important design rule is that model-controlled arguments are separate from
runtime context. For example, the model can choose a note title, but it does not
choose the local `db_path`.

### `agent_loop.py`

`agent_loop.py` owns the manual loop:

- Send messages to a model.
- Receive a final answer or tool calls.
- Execute tool calls through `tools.py`.
- Send tool observations back to the model.
- Stop when the model gives a final answer or `max_steps` is reached.

The fake model in this file makes the loop testable without network calls.

### `provider_models.py`

`provider_models.py` adapts Ollama's native chat API to Brain Lab's internal
model protocol. It converts local tools into Ollama tool schemas and parses
Ollama tool calls back into Brain Lab `ToolCall` objects.

## Direct Notes CLI Flow

This is the simplest path. The user explicitly chooses the note operation.

```mermaid
sequenceDiagram
    actor User
    participant CLI as "cli.py"
    participant Notes as "notes.py"
    participant DB as "db.py"
    participant SQLite as "SQLite"

    User->>CLI: brain note add 'Title' --body 'Text'
    CLI->>Notes: create_note(title, body, tags)
    Notes->>DB: init_db(db_path)
    DB->>SQLite: CREATE TABLE IF NOT EXISTS notes
    Notes->>DB: get_connection(db_path)
    Notes->>SQLite: INSERT INTO notes
    SQLite-->>Notes: row written
    Notes-->>CLI: Note
    CLI-->>User: Created note NOTE_ID
```

The direct CLI path is useful because it proves the local data layer works before
the agent layer exists.

## Tool Layer Flow

Tools are a small adapter around `notes.py`. They make the note operations
available to models later.

```mermaid
flowchart TD
    Caller["Caller<br/>test, fake model, or agent loop"]
    RunTool["run_tool(name, arguments, db_path)"]
    Registry["TOOL_REGISTRY"]
    Schema["Pydantic input schema"]
    ToolFn["Tool run function"]
    Notes["notes.py function"]
    Result["Note, list[Note], bool, or None"]

    Caller --> RunTool
    RunTool --> Registry
    Registry --> ToolFn
    RunTool --> Schema
    Schema -->|"Validate arguments"| ToolFn
    ToolFn --> Notes
    Notes --> Result
```

Example:

```python
run_tool(
    "create_note",
    {"title": "Tool layer", "body": "Wrap note operations."},
    db_path=db_path,
)
```

The model will eventually produce the tool name and JSON arguments. The local app
still controls the database path.

## Manual Agent Loop

The manual loop is the core learning object in the project. It shows the agent
pattern without hiding it behind a framework.

```mermaid
stateDiagram-v2
    [*] --> UserPrompt
    UserPrompt --> ModelCall
    ModelCall --> FinalAnswer: "ModelResponse.final_answer"
    ModelCall --> ToolCalls: "ModelResponse.tool_calls"
    ToolCalls --> ExecuteTools
    ExecuteTools --> ToolObservations
    ToolObservations --> ModelCall: "append tool messages"
    ModelCall --> MaxSteps: "step count exhausted"
    FinalAnswer --> [*]
    MaxSteps --> [*]
```

The loop has only two model response types:

- Final answer: return to the user.
- Tool calls: execute tools and continue.

Tool errors are not thrown out of the loop. They are recorded as tool observations
and sent back to the model so it can recover or explain the failure.

## Fake Model Flow

The fake model is deterministic. It does not understand text. It returns scripted
responses so tests can verify loop behavior.

```mermaid
sequenceDiagram
    participant Test as "test_agent_loop.py"
    participant Fake as "FakeModel"
    participant Loop as "run_agent"
    participant Tools as "tools.py"

    Test->>Fake: scripted responses
    Test->>Loop: run_agent(prompt, FakeModel)
    Loop->>Fake: respond(messages)
    Fake-->>Loop: call create_note
    Loop->>Tools: run_tool("create_note", args)
    Tools-->>Loop: Note
    Loop->>Fake: respond(messages + tool result)
    Fake-->>Loop: final answer
    Loop-->>Test: AgentRun
```

This is why Phase 3 can be tested without network calls.

## Ollama Adapter Flow

`brain ask` connects a local Ollama model to the same manual loop.

```mermaid
sequenceDiagram
    actor User
    participant CLI as "cli.py"
    participant Adapter as "provider_models.py"
    participant Loop as "agent_loop.py"
    participant API as "Ollama API"
    participant Tools as "tools.py"
    participant Notes as "notes.py"

    User->>CLI: brain ask "Create a note"
    CLI->>Adapter: OllamaModel(url, model)
    CLI->>Loop: run_agent(prompt, ollama_model)
    Loop->>Adapter: respond(messages)
    Adapter->>API: messages + Ollama tool schemas
    API-->>Adapter: Ollama tool call
    Adapter-->>Loop: ModelResponse(tool_calls)
    Loop->>Tools: run_tool(name, arguments)
    Tools->>Notes: create_note(...)
    Notes-->>Tools: Note
    Tools-->>Loop: result
    Loop->>Adapter: respond(messages + tool observation)
    Adapter->>API: tool result
    API-->>Adapter: final text
    Adapter-->>Loop: ModelResponse(final_answer)
    Loop-->>CLI: AgentRun
    CLI-->>User: final answer
```

The manual loop remains in charge. The Ollama adapter only translates between
Ollama API shapes and Brain Lab's internal `ModelResponse`.

## Ollama Adapter Shape

Brain Lab keeps one internal tool-call shape and translates at the Ollama
boundary.

```mermaid
flowchart TD
    LocalTools["Brain Lab Tool<br/>name, description, Pydantic schema"]
    OllamaSchema["Ollama tool schema<br/>type=function"]
    OllamaToolCall["Ollama tool call<br/>tool_calls[].function"]
    InternalCall["Brain Lab ToolCall<br/>name, arguments"]

    LocalTools --> OllamaSchema
    OllamaToolCall --> InternalCall
```

The adapter is intentionally small: HTTP transport, message formatting, tool
schema conversion, and response parsing live at the provider boundary.

## Data Model and Storage

```mermaid
erDiagram
    NOTES {
        TEXT id PK
        TEXT title
        TEXT body
        TEXT tags
        TEXT created_at
        TEXT updated_at
    }
```

SQLite stores tags as comma-separated text. `notes.py` converts that text back
into `list[str]` when returning a `Note`.

```mermaid
flowchart LR
    SQLiteRow["SQLite row<br/>tags='ai,mcp'"]
    RowToNote["_row_to_note(row)"]
    Note["Note<br/>tags=['ai', 'mcp']"]

    SQLiteRow --> RowToNote --> Note
```

## Testing Map

```mermaid
flowchart TD
    TestDB["tests/test_db.py"]
    TestNotes["tests/test_notes.py"]
    TestTools["tests/test_tools.py"]
    TestLoop["tests/test_agent_loop.py"]
    TestProviders["tests/test_provider_models.py"]
    TestCLI["tests/test_cli.py"]

    TestDB --> DB["db.py"]
    TestNotes --> Notes["notes.py"]
    TestTools --> Tools["tools.py"]
    TestLoop --> AgentLoop["agent_loop.py"]
    TestProviders --> ProviderModels["provider_models.py"]
    TestCLI --> CLI["cli.py"]

    AgentLoop --> Tools
    ProviderModels --> AgentLoop
    CLI --> ProviderModels
```

The tests mirror the architecture:

- Database tests prove the schema can be created.
- Notes tests prove local business behavior.
- Tool tests prove validation and registry behavior.
- Agent loop tests prove loop mechanics with a fake model.
- Adapter tests prove request and response translation without network calls.
- CLI tests prove command wiring and error handling.

## Current Phase Boundary

```mermaid
flowchart LR
    P1["Phase 1<br/>Notes CLI"]
    P2["Phase 2<br/>Tool layer"]
    P3["Phase 3<br/>Manual loop"]
    P4["Phase 4<br/>Local Ollama model"]
    P5["Phase 5<br/>Observability"]
    P6["Phase 6<br/>Safety policy"]
    P7["Phase 7<br/>MCP server"]

    P1 --> P2 --> P3 --> P4 --> P5 --> P6 --> P7

    classDef done fill:#d9f7be,stroke:#237804,color:#000;
    classDef next fill:#fff1b8,stroke:#ad8b00,color:#000;
    class P1,P2,P3,P4,P5 done;
    class P6 next;
```

The current implementation reaches Phase 5:

- The local notes app works.
- Notes are exposed as tools.
- A manual agent loop can execute tool calls.
- The Ollama adapter can drive the same loop.
- Agent runs are logged to JSONL for inspection.

The next architectural layer is safety policy. That should classify tools by
risk without changing the core note business logic.

## Key Design Rules

```mermaid
flowchart TD
    Rule1["Keep business logic provider-free"]
    Rule2["Keep provider APIs at the boundary"]
    Rule3["Keep model arguments separate from runtime context"]
    Rule4["Test the loop without network calls"]
    Rule5["Add phases one concept at a time"]

    Rule1 --> Notes["notes.py has no Typer, provider, or MCP imports"]
    Rule2 --> ProviderModels["provider_models.py translates provider shapes"]
    Rule3 --> Tools["Tool args exclude db_path"]
    Rule4 --> FakeModel["FakeModel scripts responses"]
    Rule5 --> Roadmap["ROADMAP.md controls scope"]
```

These rules are what keep Brain Lab readable as it grows.
