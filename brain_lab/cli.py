import json

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner

from brain_lab.agent_loop import AgentProgress, run_agent
from brain_lab.notes import (
    create_note,
    delete_note,
    get_note,
    list_notes,
    search_notes,
    update_note,
)
from brain_lab.llm import LLM_MODEL, LLM_URL, LocalLLM
from brain_lab.run_logs import (
    DEFAULT_RUN_LOG_PATH,
    get_run_log,
    list_run_logs,
    write_run_log,
)


app = typer.Typer(help="Brain Lab notes CLI.")
note_app = typer.Typer(help="Work with notes.")
runs_app = typer.Typer(help="Inspect agent run logs.")
app.add_typer(note_app, name="note")
app.add_typer(runs_app, name="runs")


@note_app.command("add")
def add_note(
    title: str,
    body: str = typer.Option("", "--body", help="Note body text."),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags."),
) -> None:
    note = create_note(title=title, body=body, tags=tags)
    typer.echo(f"Created note {note.id}")


@note_app.command("list")
def show_notes() -> None:
    notes = list_notes()

    if not notes:
        typer.echo("No notes yet.")
        return

    for note in notes:
        typer.echo(f"- {note.id} | {note.title} | {','.join(note.tags)}")


@note_app.command("get")
def show_note(note_id: str) -> None:
    note = get_note(note_id)

    if note is None:
        typer.echo("Note not found.")
        raise typer.Exit(code=1)

    typer.echo(f"{note.id} | {note.title} | {','.join(note.tags)}")
    if note.body:
        typer.echo("")
        typer.echo(note.body)


@note_app.command("update")
def edit_note(
    note_id: str,
    title: str | None = typer.Option(None, "--title", help="New note title."),
    body: str | None = typer.Option(None, "--body", help="New note body text."),
    tags: str | None = typer.Option(None, "--tags", help="New comma-separated tags."),
) -> None:
    if title is None and body is None and tags is None:
        typer.echo("Nothing to update.")
        raise typer.Exit(code=1)

    note = update_note(note_id=note_id, title=title, body=body, tags=tags)

    if note is None:
        typer.echo("Note not found.")
        raise typer.Exit(code=1)

    typer.echo(f"Updated note {note.id}")


@note_app.command("delete")
def remove_note(note_id: str) -> None:
    deleted = delete_note(note_id)

    if not deleted:
        typer.echo("Note not found.")
        raise typer.Exit(code=1)

    typer.echo(f"Deleted note {note_id}")


@note_app.command("search")
def search_note_text(query: str) -> None:
    notes = search_notes(query)

    if not notes:
        typer.echo("No matching notes.")
        return

    for note in notes:
        typer.echo(f"- {note.id} | {note.title} | {','.join(note.tags)}")


@app.command("ask")
def ask_agent(
    prompt: str,
    max_steps: int = typer.Option(10, "--max-steps", min=1, help="Maximum agent steps."),
    verbose: bool = typer.Option(True, "--verbose/--quiet", help="Show agent progress."),
    thinking: bool = typer.Option(True, "--thinking/--no-thinking", help="Show model thinking."),
) -> None:
    err = Console(stderr=True)
    progress_ui: _ProgressUI | None = None
    try:
        agent_model = LocalLLM()
        if verbose:
            _show_agent_start(err, LLM_MODEL, LLM_URL)
        progress_ui = _ProgressUI(err, show_thinking=thinking) if verbose else None
        run = run_agent(prompt, agent_model, max_steps=max_steps, progress=progress_ui)
    except Exception as exc:
        write_run_log(
            user_task=prompt,
            error=f"{type(exc).__name__}: {exc}",
            log_path=DEFAULT_RUN_LOG_PATH,
        )
        err.print(f"[red]Error:[/] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        if progress_ui is not None:
            progress_ui.stop()

    record = write_run_log(user_task=prompt, run=run, log_path=DEFAULT_RUN_LOG_PATH)
    if verbose:
        err.print(f"[dim]Run logged: {record['run_id']}[/]")

    if run.final_answer is None:
        err.print(f"[red]Stopped after {max_steps} steps without a final answer.[/]")
        raise typer.Exit(code=1)

    typer.echo(run.final_answer)


@runs_app.command("list")
def list_runs() -> None:
    records = list_run_logs(DEFAULT_RUN_LOG_PATH)

    if not records:
        typer.echo("No runs logged.")
        return

    for record in records:
        typer.echo(
            " | ".join(
                [
                    record["timestamp"],
                    record["run_id"],
                    record["status"],
                    _shorten(record["user_task"]),
                ]
            )
        )


@runs_app.command("show")
def show_run(run_id: str) -> None:
    record = get_run_log(run_id, DEFAULT_RUN_LOG_PATH)

    if record is None:
        typer.echo("Run not found.", err=True)
        raise typer.Exit(code=1)

    typer.echo(json.dumps(record, indent=2, sort_keys=True))


class _ProgressUI:
    def __init__(self, console: Console, show_thinking: bool = True) -> None:
        self._con = console
        self._show_thinking = show_thinking
        self._live: Live | None = None

    def __call__(self, event: AgentProgress) -> None:
        if event.kind == "model_request":
            self._con.print(f"[bold]●[/] [dim]Step {event.step_number}[/]")
            self._live = Live(
                Spinner("dots", text="  thinking…"),
                console=self._con,
                refresh_per_second=10,
                transient=True,
            )
            self._live.start()
            return

        self._stop_live()

        if event.kind == "thinking" and event.thinking and self._show_thinking:
            self._con.print(
                Panel(event.thinking, title="[bold yellow]thinking[/]", border_style="yellow")
            )

        elif event.kind == "tool_call" and event.tool_call is not None:
            args = json.dumps(dict(event.tool_call.arguments), sort_keys=True)
            self._con.print(f"[cyan]→[/] [bold]{event.tool_call.name}[/]  [dim]{args}[/]")

        elif event.kind == "tool_result" and event.observation is not None:
            icon = "[green]✓[/]" if event.observation.ok else "[red]✗[/]"
            summary = _summarize_observation(event.observation)
            self._con.print(f"{icon} {event.observation.tool_name}  {summary}")

        elif event.kind == "final_answer":
            self._con.print("[green]✓[/] done")

        elif event.kind == "max_steps":
            self._con.print("[red bold]![/] max steps reached")

    def stop(self) -> None:
        self._stop_live()

    def _stop_live(self) -> None:
        if self._live is not None:
            self._live.stop()
            self._live = None


def _show_agent_start(err: Console, model: str, url: str) -> None:
    err.print(Rule(f"[bold]Brain Lab[/]  ·  [cyan]{model}[/]", style="dim"))
    err.print(f"[dim]{url}[/]")
    err.print()


def _shorten(value: str, limit: int = 80) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3]}..."


def _summarize_observation(observation: object) -> str:
    error = getattr(observation, "error", None)
    if error is not None:
        return f"[red]{error}[/]"

    content = getattr(observation, "content", "")
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        preview = content[:120].replace("\n", " ")
        return f"[dim]{preview}{'…' if len(content) > 120 else ''}[/]"

    if isinstance(value, list):
        return f"{len(value)} item(s)"
    if isinstance(value, dict):
        return f"{len(value)} field(s)"
    if value is None:
        return "null"

    return type(value).__name__


if __name__ == "__main__":
    app()
