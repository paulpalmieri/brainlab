# Project Brief

## Project Name

Brain Lab

## Goal

Brain Lab is a local-first notes CLI that will gradually become an agent lab. It starts as a tiny SQLite-backed notes app and grows step by step into a readable system for learning tools, agent loops, private inference, MCP, evals, and observability.

## Why This Exists

The project exists to learn agentic software engineering from first principles. Instead of hiding the important ideas behind a large framework, Brain Lab keeps each layer small enough to read, test, and explain.

## What This Project Should Teach

- Local CLI app structure
- SQLite persistence
- Typed data models
- Tool schemas
- Tool execution
- Manual agent loops
- Model and tool interaction
- Safety policies for tools
- MCP tools, resources, and prompts
- Basic agent evals
- Simple observability

## Portfolio Positioning

Brain Lab should become a portfolio project that demonstrates practical understanding of agentic systems. The value is not in feature count. The value is in clear, inspectable code that shows how each layer works.

## Core Features

- A local notes CLI
- SQLite-backed note storage
- A tool layer around note operations
- A hand-written agent loop
- Local LLM tool calling
- JSONL run logging
- A minimal MCP server
- MCP resources and prompts
- A small eval harness

## Non-Goals

- Production SaaS
- Complex application architecture
- Web app
- Authentication
- Docker setup
- Vector database
- Embeddings
- Agent frameworks such as LangChain, LlamaIndex, CrewAI, or AutoGen

## Success Criteria

- Each phase can be understood by reading a few short files.
- The CLI works locally without external services.
- Tests cover the behavior introduced in each phase.
- The agent layer is written manually before any provider SDK is introduced.
- Documentation stays accurate as the code changes.
