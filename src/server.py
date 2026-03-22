#!/usr/bin/env python3
"""
Todoist MCP Server — Full CRUD for Tasks, Projects, Sections, Comments, and Labels.

Exposes the Todoist API v1 as MCP tools for use with Claude Desktop,
Claude Code, and any MCP-compatible client.
"""

import json
import os
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from src.client import (
    api_request,
    format_task_markdown,
    format_project_markdown,
)
from src.exceptions import TodoistAPIError

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "todoist_mcp",
    host=os.environ.get("MCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("MCP_PORT", "8000")),
)

@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "ok"})

# ---------------------------------------------------------------------------
# Shared enums / models
# ---------------------------------------------------------------------------

class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


# ===== TASKS ===============================================================

class TodoistListTasksInput(BaseModel):
    """Filter and list tasks."""
    model_config = ConfigDict(str_strip_whitespace=True)

    project_id: Optional[str] = Field(default=None, description="Filter by project ID")
    section_id: Optional[str] = Field(default=None, description="Filter by section ID")
    label: Optional[str] = Field(default=None, description="Filter by label name")
    filter: Optional[str] = Field(
        default=None,
        description="Todoist filter query (e.g. 'today', 'overdue', 'priority 1', '#Work')"
    )
    ids: Optional[str] = Field(default=None, description="Comma-separated task IDs")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class TodoistGetTaskInput(BaseModel):
    task_id: str = Field(..., description="Task ID to retrieve", min_length=1)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class TodoistCreateTaskInput(BaseModel):
    """Create a new task."""
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(..., description="Task title/content", min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, description="Task description", max_length=16383)
    project_id: Optional[str] = Field(default=None, description="Project ID to add task to")
    section_id: Optional[str] = Field(default=None, description="Section ID within the project")
    parent_id: Optional[str] = Field(default=None, description="Parent task ID (for subtasks)")
    order: Optional[int] = Field(default=None, description="Sort order in list")
    labels: Optional[List[str]] = Field(default=None, description="Label names to apply")
    priority: Optional[int] = Field(default=None, description="Priority: 1=normal, 2=medium, 3=high, 4=urgent", ge=1, le=4)
    due_string: Optional[str] = Field(default=None, description="Natural language due date (e.g. 'tomorrow at 3pm', 'every monday')")
    due_date: Optional[str] = Field(default=None, description="Due date in YYYY-MM-DD format")
    due_datetime: Optional[str] = Field(default=None, description="Due datetime in RFC3339 (e.g. 2026-03-20T15:00:00Z)")
    due_lang: Optional[str] = Field(default="en", description="Language for due_string parsing")
    assignee_id: Optional[str] = Field(default=None, description="User ID to assign task to (shared projects)")
    duration: Optional[int] = Field(default=None, description="Estimated duration in minutes", ge=1)
    duration_unit: Optional[str] = Field(default="minute", description="Duration unit: 'minute' or 'day'")


class TodoistUpdateTaskInput(BaseModel):
    """Update an existing task."""
    model_config = ConfigDict(str_strip_whitespace=True)

    task_id: str = Field(..., description="Task ID to update", min_length=1)
    content: Optional[str] = Field(default=None, description="New task title", max_length=500)
    description: Optional[str] = Field(default=None, description="New description", max_length=16383)
    labels: Optional[List[str]] = Field(default=None, description="Replace labels")
    priority: Optional[int] = Field(default=None, ge=1, le=4)
    due_string: Optional[str] = Field(default=None, description="New due date in natural language")
    due_date: Optional[str] = Field(default=None, description="New due date YYYY-MM-DD")
    due_datetime: Optional[str] = Field(default=None, description="New due datetime RFC3339")
    due_lang: Optional[str] = Field(default=None)
    assignee_id: Optional[str] = Field(default=None)
    duration: Optional[int] = Field(default=None, ge=1)
    duration_unit: Optional[str] = Field(default=None)


class TodoistCloseTaskInput(BaseModel):
    task_id: str = Field(..., description="Task ID to complete/close", min_length=1)


class TodoistReopenTaskInput(BaseModel):
    task_id: str = Field(..., description="Task ID to reopen", min_length=1)


class TodoistDeleteTaskInput(BaseModel):
    task_id: str = Field(..., description="Task ID to permanently delete", min_length=1)


# ===== PROJECTS ============================================================

class TodoistListProjectsInput(BaseModel):
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class TodoistGetProjectInput(BaseModel):
    project_id: str = Field(..., description="Project ID", min_length=1)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class TodoistCreateProjectInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., description="Project name", min_length=1, max_length=200)
    parent_id: Optional[str] = Field(default=None, description="Parent project ID (for nesting)")
    color: Optional[str] = Field(default=None, description="Color name (e.g. 'berry_red', 'blue', 'green')")
    is_favorite: Optional[bool] = Field(default=None, description="Add to favorites")
    view_style: Optional[str] = Field(default=None, description="'list' or 'board'")


class TodoistUpdateProjectInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    project_id: str = Field(..., min_length=1)
    name: Optional[str] = Field(default=None, max_length=200)
    color: Optional[str] = Field(default=None)
    is_favorite: Optional[bool] = Field(default=None)
    view_style: Optional[str] = Field(default=None)


class TodoistDeleteProjectInput(BaseModel):
    project_id: str = Field(..., min_length=1, description="Project ID to permanently delete")


# ===== SECTIONS ============================================================

class TodoistListSectionsInput(BaseModel):
    project_id: str = Field(..., description="Project ID to list sections for", min_length=1)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class TodoistCreateSectionInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    project_id: str = Field(..., min_length=1)
    order: Optional[int] = Field(default=None)


class TodoistUpdateSectionInput(BaseModel):
    section_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=200)


class TodoistDeleteSectionInput(BaseModel):
    section_id: str = Field(..., min_length=1)


# ===== COMMENTS ============================================================

class TodoistListCommentsInput(BaseModel):
    task_id: Optional[str] = Field(default=None, description="Task ID (provide task_id OR project_id)")
    project_id: Optional[str] = Field(default=None, description="Project ID")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    @field_validator("project_id")
    @classmethod
    def check_one_id(cls, v: Optional[str], info) -> Optional[str]:
        task_id = info.data.get("task_id")
        if not v and not task_id:
            raise ValueError("Provide either task_id or project_id")
        return v


class TodoistCreateCommentInput(BaseModel):
    content: str = Field(..., min_length=1, max_length=16383, description="Comment text (Markdown supported)")
    task_id: Optional[str] = Field(default=None, description="Task to comment on")
    project_id: Optional[str] = Field(default=None, description="Project to comment on")

    @field_validator("project_id")
    @classmethod
    def check_one_id(cls, v: Optional[str], info) -> Optional[str]:
        task_id = info.data.get("task_id")
        if not v and not task_id:
            raise ValueError("Provide either task_id or project_id")
        return v


class TodoistUpdateCommentInput(BaseModel):
    comment_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1, max_length=16383)


class TodoistDeleteCommentInput(BaseModel):
    comment_id: str = Field(..., min_length=1)


# ===== LABELS ==============================================================

class TodoistListLabelsInput(BaseModel):
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class TodoistCreateLabelInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Label name")
    order: Optional[int] = Field(default=None)
    color: Optional[str] = Field(default=None)
    is_favorite: Optional[bool] = Field(default=None)


class TodoistUpdateLabelInput(BaseModel):
    label_id: str = Field(..., min_length=1)
    name: Optional[str] = Field(default=None, max_length=200)
    order: Optional[int] = Field(default=None)
    color: Optional[str] = Field(default=None)
    is_favorite: Optional[bool] = Field(default=None)


class TodoistDeleteLabelInput(BaseModel):
    label_id: str = Field(..., min_length=1)


# ===========================================================================
# TOOL IMPLEMENTATIONS
# ===========================================================================

# ---------- TASKS ----------------------------------------------------------

@mcp.tool(
    name="todoist_list_tasks",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def todoist_list_tasks(params: TodoistListTasksInput) -> str:
    """List and filter active Todoist tasks.

    Supports filtering by project, section, label, or Todoist's powerful filter syntax
    (e.g. 'today', 'overdue', 'priority 1 & #Work', 'assigned to: me').
    """
    try:
        query_params = {}
        if params.project_id:
            query_params["project_id"] = params.project_id
        if params.section_id:
            query_params["section_id"] = params.section_id
        if params.label:
            query_params["label"] = params.label
        if params.filter:
            query_params["filter"] = params.filter
        if params.ids:
            query_params["ids"] = params.ids

        tasks = await api_request("tasks", params=query_params)

        if not tasks:
            return "No tasks found matching your criteria."

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(tasks, indent=2)

        lines = [f"# Todoist Tasks ({len(tasks)} results)", ""]
        for t in tasks:
            lines.append(format_task_markdown(t))
            lines.append("")
        return "\n".join(lines)
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_get_task",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def todoist_get_task(params: TodoistGetTaskInput) -> str:
    """Get full details for a single Todoist task by ID."""
    try:
        task = await api_request(f"tasks/{params.task_id}")
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(task, indent=2)
        return format_task_markdown(task)
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_create_task",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def todoist_create_task(params: TodoistCreateTaskInput) -> str:
    """Create a new Todoist task with optional due date, priority, labels, and project placement.

    Supports natural-language due dates via due_string (e.g. 'every weekday at 9am').
    """
    try:
        body: dict = {"content": params.content}
        for field in [
            "description", "project_id", "section_id", "parent_id",
            "order", "labels", "priority", "due_string", "due_date",
            "due_datetime", "due_lang", "assignee_id",
        ]:
            val = getattr(params, field)
            if val is not None:
                body[field] = val
        if params.duration is not None:
            body["duration"] = params.duration
            body["duration_unit"] = params.duration_unit or "minute"

        task = await api_request("tasks", method="POST", body=body)
        return f"Task created successfully!\n\n{format_task_markdown(task)}"
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_update_task",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def todoist_update_task(params: TodoistUpdateTaskInput) -> str:
    """Update an existing Todoist task's content, due date, priority, labels, or assignment."""
    try:
        body: dict = {}
        for field in [
            "content", "description", "labels", "priority",
            "due_string", "due_date", "due_datetime", "due_lang",
            "assignee_id",
        ]:
            val = getattr(params, field)
            if val is not None:
                body[field] = val
        if params.duration is not None:
            body["duration"] = params.duration
            body["duration_unit"] = params.duration_unit or "minute"

        if not body:
            raise ToolError("No fields provided to update.")

        task = await api_request(f"tasks/{params.task_id}", method="POST", body=body)
        return f"Task updated.\n\n{format_task_markdown(task)}"
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_close_task",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def todoist_close_task(params: TodoistCloseTaskInput) -> str:
    """Mark a Todoist task as complete. For recurring tasks, advances to the next occurrence."""
    try:
        await api_request(f"tasks/{params.task_id}/close", method="POST")
        return f"Task `{params.task_id}` marked complete."
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_reopen_task",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def todoist_reopen_task(params: TodoistReopenTaskInput) -> str:
    """Reopen a previously completed Todoist task."""
    try:
        await api_request(f"tasks/{params.task_id}/reopen", method="POST")
        return f"Task `{params.task_id}` reopened."
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_delete_task",
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": True},
)
async def todoist_delete_task(params: TodoistDeleteTaskInput) -> str:
    """Permanently delete a Todoist task. This cannot be undone."""
    try:
        await api_request(f"tasks/{params.task_id}", method="DELETE")
        return f"Task `{params.task_id}` permanently deleted."
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


# ---------- PROJECTS -------------------------------------------------------

@mcp.tool(
    name="todoist_list_projects",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def todoist_list_projects(params: TodoistListProjectsInput) -> str:
    """List all Todoist projects."""
    try:
        projects = await api_request("projects")
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(projects, indent=2)

        lines = [f"# Todoist Projects ({len(projects)})", ""]
        for p in projects:
            lines.append(format_project_markdown(p))
            lines.append("")
        return "\n".join(lines)
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_get_project",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def todoist_get_project(params: TodoistGetProjectInput) -> str:
    """Get details for a single Todoist project."""
    try:
        project = await api_request(f"projects/{params.project_id}")
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(project, indent=2)
        return format_project_markdown(project)
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_create_project",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def todoist_create_project(params: TodoistCreateProjectInput) -> str:
    """Create a new Todoist project with optional color, view style, and nesting."""
    try:
        body: dict = {"name": params.name}
        for field in ["parent_id", "color", "is_favorite", "view_style"]:
            val = getattr(params, field)
            if val is not None:
                body[field] = val
        project = await api_request("projects", method="POST", body=body)
        return f"Project created!\n\n{format_project_markdown(project)}"
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_update_project",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def todoist_update_project(params: TodoistUpdateProjectInput) -> str:
    """Update a Todoist project's name, color, or view style."""
    try:
        body: dict = {}
        for field in ["name", "color", "is_favorite", "view_style"]:
            val = getattr(params, field)
            if val is not None:
                body[field] = val
        if not body:
            raise ToolError("No fields provided to update.")
        project = await api_request(f"projects/{params.project_id}", method="POST", body=body)
        return f"Project updated.\n\n{format_project_markdown(project)}"
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_delete_project",
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": True},
)
async def todoist_delete_project(params: TodoistDeleteProjectInput) -> str:
    """Permanently delete a Todoist project and all its tasks. Cannot be undone."""
    try:
        await api_request(f"projects/{params.project_id}", method="DELETE")
        return f"Project `{params.project_id}` permanently deleted."
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


# ---------- SECTIONS -------------------------------------------------------

@mcp.tool(
    name="todoist_list_sections",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def todoist_list_sections(params: TodoistListSectionsInput) -> str:
    """List all sections within a Todoist project."""
    try:
        sections = await api_request("sections", params={"project_id": params.project_id})
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(sections, indent=2)

        if not sections:
            return f"No sections in project `{params.project_id}`."

        lines = [f"# Sections ({len(sections)})", ""]
        for s in sections:
            lines.append(f"### {s['name']}")
            lines.append(f"- **ID**: `{s['id']}`")
            lines.append(f"- **Order**: {s.get('order', 'N/A')}")
            lines.append("")
        return "\n".join(lines)
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_create_section",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def todoist_create_section(params: TodoistCreateSectionInput) -> str:
    """Create a new section within a Todoist project."""
    try:
        body: dict = {"name": params.name, "project_id": params.project_id}
        if params.order is not None:
            body["order"] = params.order
        section = await api_request("sections", method="POST", body=body)
        return f"Section created: **{section['name']}** (ID: `{section['id']}`)"
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_update_section",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def todoist_update_section(params: TodoistUpdateSectionInput) -> str:
    """Rename a Todoist section."""
    try:
        section = await api_request(
            f"sections/{params.section_id}", method="POST", body={"name": params.name}
        )
        return f"Section updated: **{section['name']}** (ID: `{section['id']}`)"
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_delete_section",
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": True},
)
async def todoist_delete_section(params: TodoistDeleteSectionInput) -> str:
    """Permanently delete a section and all its tasks."""
    try:
        await api_request(f"sections/{params.section_id}", method="DELETE")
        return f"Section `{params.section_id}` deleted."
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


# ---------- COMMENTS -------------------------------------------------------

@mcp.tool(
    name="todoist_list_comments",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def todoist_list_comments(params: TodoistListCommentsInput) -> str:
    """List comments on a task or project."""
    try:
        query_params = {}
        if params.task_id:
            query_params["task_id"] = params.task_id
        elif params.project_id:
            query_params["project_id"] = params.project_id

        comments = await api_request("comments", params=query_params)

        if not comments:
            return "No comments found."

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(comments, indent=2)

        lines = [f"# Comments ({len(comments)})", ""]
        for c in comments:
            lines.append(f"### Comment `{c['id']}` — {c.get('posted_at', '')}")
            lines.append(c["content"])
            lines.append("")
        return "\n".join(lines)
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_create_comment",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def todoist_create_comment(params: TodoistCreateCommentInput) -> str:
    """Add a comment to a Todoist task or project. Supports Markdown."""
    try:
        body: dict = {"content": params.content}
        if params.task_id:
            body["task_id"] = params.task_id
        elif params.project_id:
            body["project_id"] = params.project_id
        comment = await api_request("comments", method="POST", body=body)
        return f"Comment added (ID: `{comment['id']}`)."
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_update_comment",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def todoist_update_comment(params: TodoistUpdateCommentInput) -> str:
    """Update the text of a Todoist comment."""
    try:
        comment = await api_request(
            f"comments/{params.comment_id}", method="POST", body={"content": params.content}
        )
        return f"Comment `{comment['id']}` updated."
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_delete_comment",
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": True},
)
async def todoist_delete_comment(params: TodoistDeleteCommentInput) -> str:
    """Permanently delete a Todoist comment."""
    try:
        await api_request(f"comments/{params.comment_id}", method="DELETE")
        return f"Comment `{params.comment_id}` deleted."
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


# ---------- LABELS ---------------------------------------------------------

@mcp.tool(
    name="todoist_list_labels",
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def todoist_list_labels(params: TodoistListLabelsInput) -> str:
    """List all personal Todoist labels."""
    try:
        labels = await api_request("labels")
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(labels, indent=2)

        if not labels:
            return "No labels found."

        lines = [f"# Labels ({len(labels)})", ""]
        for l in labels:
            fav = " ⭐" if l.get("is_favorite") else ""
            lines.append(f"- **{l['name']}**{fav} — ID: `{l['id']}`, color: {l.get('color', 'default')}")
        return "\n".join(lines)
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_create_label",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def todoist_create_label(params: TodoistCreateLabelInput) -> str:
    """Create a new personal Todoist label."""
    try:
        body: dict = {"name": params.name}
        for field in ["order", "color", "is_favorite"]:
            val = getattr(params, field)
            if val is not None:
                body[field] = val
        label = await api_request("labels", method="POST", body=body)
        return f"Label created: **{label['name']}** (ID: `{label['id']}`)"
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_update_label",
    annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
)
async def todoist_update_label(params: TodoistUpdateLabelInput) -> str:
    """Update a Todoist label's name, color, or favorite status."""
    try:
        body: dict = {}
        for field in ["name", "order", "color", "is_favorite"]:
            val = getattr(params, field)
            if val is not None:
                body[field] = val
        if not body:
            raise ToolError("No fields provided to update.")
        label = await api_request(f"labels/{params.label_id}", method="POST", body=body)
        return f"Label updated: **{label['name']}** (ID: `{label['id']}`)"
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


@mcp.tool(
    name="todoist_delete_label",
    annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": True},
)
async def todoist_delete_label(params: TodoistDeleteLabelInput) -> str:
    """Permanently delete a Todoist label."""
    try:
        await api_request(f"labels/{params.label_id}", method="DELETE")
        return f"Label `{params.label_id}` deleted."
    except TodoistAPIError as e:
        raise ToolError(str(e)) from e


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "streamable_http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
