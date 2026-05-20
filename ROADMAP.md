# Roadmap

## Phase 1: Notes CLI

- SQLite database
- Add notes
- List notes
- Get notes
- Update notes
- Delete notes
- Simple keyword search

## Phase 2: Tool Layer

- Wrap note operations as tools
- Define Pydantic schemas
- Add a tool registry
- Test tools directly

## Phase 3: Manual Agent Loop

- Start with a fake model
- Write an explicit loop
- Support tool calls
- Enforce max steps
- Handle tool errors

## Phase 4: Local LLM Tool Calling

- Add an Ollama adapter
- Convert tools to Ollama format
- Add a `brain ask` command
- Use mock tests for model behavior

## Phase 5: Observability

- Write JSONL run logs
- Record tool-call traces
- Add `brain runs list`
- Add `brain runs show`

## Phase 6: Safety Policy

- Mark read-only tools
- Mark write tools
- Mark destructive tools
- Prevent destructive agent actions by default

## Phase 7: MCP Server

- Expose notes tools through MCP
- Reuse existing business logic

## Phase 8: MCP Resources and Prompts

- Add `notes://recent`
- Add `notes://note/{id}`
- Add `notes://tag/{tag}`
- Add a `weekly_review` prompt
- Add a `research_digest` prompt

## Phase 9: Evals

- Define simple eval cases
- Add `brain eval run`
- Log pass/fail results

## Phase 10: Portfolio Polish

- Polish the README
- Add examples
- Add an architecture diagram
- Add a terminal demo
