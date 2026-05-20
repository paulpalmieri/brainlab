from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from brain_lab.db import DEFAULT_DB_PATH
from brain_lab.notes import (
    create_note,
    delete_note,
    get_note,
    list_notes,
    search_notes,
    update_note,
)


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateNoteInput(ToolInput):
    title: str = Field(description="Title for the new note.")
    body: str = Field(default="", description="Optional note body text.")
    tags: list[str] = Field(
        default_factory=list,
        description="Optional note tags.",
    )


class ListNotesInput(ToolInput):
    pass


class GetNoteInput(ToolInput):
    note_id: str = Field(description="ID of the note to fetch.")


class UpdateNoteInput(ToolInput):
    note_id: str = Field(description="ID of the note to update.")
    title: str | None = Field(default=None, description="Replacement note title.")
    body: str | None = Field(default=None, description="Replacement note body text.")
    tags: list[str] | None = Field(default=None, description="Replacement note tags.")

    @model_validator(mode="after")
    def require_update_value(self) -> Self:
        if self.title is None and self.body is None and self.tags is None:
            raise ValueError("At least one note field must be provided.")
        return self


class DeleteNoteInput(ToolInput):
    note_id: str = Field(description="ID of the note to delete.")


class SearchNotesInput(ToolInput):
    query: str = Field(description="Search text to match against title, body, or tags.")


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_model: type[ToolInput]
    run: Callable[[Any, str | Path], Any]

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.input_model.model_json_schema()


def _run_create_note(args: CreateNoteInput, db_path: str | Path) -> Any:
    return create_note(title=args.title, body=args.body, tags=args.tags, db_path=db_path)


def _run_list_notes(args: ListNotesInput, db_path: str | Path) -> Any:
    return list_notes(db_path=db_path)


def _run_get_note(args: GetNoteInput, db_path: str | Path) -> Any:
    return get_note(args.note_id, db_path=db_path)


def _run_update_note(args: UpdateNoteInput, db_path: str | Path) -> Any:
    return update_note(note_id=args.note_id, title=args.title, body=args.body, tags=args.tags, db_path=db_path)


def _run_delete_note(args: DeleteNoteInput, db_path: str | Path) -> Any:
    return delete_note(args.note_id, db_path=db_path)


def _run_search_notes(args: SearchNotesInput, db_path: str | Path) -> Any:
    return search_notes(args.query, db_path=db_path)


_TOOLS = [
    Tool(
        name="create_note",
        description="Create a new note.",
        input_model=CreateNoteInput,
        run=_run_create_note,
    ),
    Tool(
        name="list_notes",
        description="List all notes.",
        input_model=ListNotesInput,
        run=_run_list_notes,
    ),
    Tool(
        name="get_note",
        description="Fetch one note by ID.",
        input_model=GetNoteInput,
        run=_run_get_note,
    ),
    Tool(
        name="update_note",
        description="Update an existing note.",
        input_model=UpdateNoteInput,
        run=_run_update_note,
    ),
    Tool(
        name="delete_note",
        description="Delete a note by ID.",
        input_model=DeleteNoteInput,
        run=_run_delete_note,
    ),
    Tool(
        name="search_notes",
        description="Search notes by title, body, or tags.",
        input_model=SearchNotesInput,
        run=_run_search_notes,
    ),
]

TOOL_REGISTRY = {tool.name: tool for tool in _TOOLS}


def list_tools() -> list[Tool]:
    return list(TOOL_REGISTRY.values())


def get_tool(name: str) -> Tool:
    try:
        return TOOL_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unknown tool: {name}") from exc


def run_tool(
    name: str,
    arguments: Mapping[str, Any] | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> Any:
    tool = get_tool(name)
    validated_args = tool.input_model.model_validate(dict(arguments or {}))
    return tool.run(validated_args, db_path)
