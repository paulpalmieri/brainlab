# AGENTS.md

Instructions for future coding agents working in Brain Lab.

## Working Principles

- This is a learning-first project, not a production SaaS.
- Before coding, read `PROJECT_BRIEF.md`, `ROADMAP.md`, and `ARCHITECTURE.md`.
- Implement the smallest correct next step from the roadmap.
- Keep code simple, explicit, and readable.
- Prefer boring functions over clever abstractions.
- List the files you plan to change before changing them.
- Update tests and `README.md` when behavior changes.
- Keep personal study notes, learning checklists, self-review answers, and scratch explanations out of tracked files.
- Use ignored local files under `.local/` for personal learning material.
- Do not add unrequested features.
- Do not use LangChain, LlamaIndex, CrewAI, AutoGen, or similar agent frameworks.
- Do not add a vector database, embeddings, auth, Docker, or a web app unless explicitly requested.

## Definition of Done

A change is done when:

- The requested behavior works manually.
- Relevant tests pass.
- New or changed behavior has tests.
- Documentation reflects the current state.
- The changed files are short enough to inspect line by line.
- The implementation matches the current roadmap phase.
