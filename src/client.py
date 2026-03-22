"""Todoist API client with shared utilities."""

import os
import json
from typing import Any, Optional

import httpx

API_BASE_URL = "https://api.todoist.com/api/v1"
REQUEST_TIMEOUT = 30.0


def _get_token() -> str:
    """Retrieve Todoist API token from environment."""
    token = os.environ.get("TODOIST_API_TOKEN")
    if not token:
        raise RuntimeError(
            "TODOIST_API_TOKEN environment variable is not set. "
            "Get your token from Todoist → Settings → Integrations → Developer."
        )
    return token


def _headers() -> dict[str, str]:
    """Build authorization headers."""
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
    }


async def api_request(
    endpoint: str,
    method: str = "GET",
    params: Optional[dict[str, Any]] = None,
    body: Optional[dict[str, Any]] = None,
) -> Any:
    """Make an authenticated request to the Todoist REST API v2.

    Args:
        endpoint: API path relative to base URL (e.g. 'tasks', 'projects/123')
        method: HTTP method
        params: Query parameters
        body: JSON request body (for POST/PUT)

    Returns:
        Parsed JSON response, or None for 204 No Content.

    Raises:
        httpx.HTTPStatusError on non-2xx responses.
    """
    url = f"{API_BASE_URL}/{endpoint}"
    # Strip None values from params
    if params:
        params = {k: v for k, v in params.items() if v is not None}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.request(
            method,
            url,
            headers=_headers(),
            params=params if method == "GET" else None,
            json=body if method in ("POST", "PUT") else None,
        )
        response.raise_for_status()
        if response.status_code == 204:
            return None
        data = response.json()
        # API v1 wraps list responses in {"results": [...], "next_cursor": ...}
        if isinstance(data, dict) and "results" in data and "next_cursor" in data:
            return data["results"]
        return data


def handle_api_error(e: Exception) -> str:
    """Format API errors into actionable messages."""
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 400:
            return "Error: Bad request. Check your parameters are valid."
        if status == 401:
            return "Error: Invalid API token. Check TODOIST_API_TOKEN is correct."
        if status == 403:
            return "Error: Forbidden. You don't have access to this resource."
        if status == 404:
            return "Error: Resource not found. Check the ID is correct."
        if status == 429:
            return "Error: Rate limited. Todoist allows 1000 requests per 15 minutes. Wait and retry."
        return f"Error: API returned status {status}."
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Try again."
    if isinstance(e, RuntimeError) and "TODOIST_API_TOKEN" in str(e):
        return str(e)
    return f"Error: {type(e).__name__}: {e}"


def format_task_markdown(task: dict) -> str:
    """Format a single task as Markdown."""
    lines = []
    priority_map = {1: "⬜ Normal", 2: "🔵 Medium", 3: "🟠 High", 4: "🔴 Urgent"}
    priority = priority_map.get(task.get("priority", 1), "Normal")

    status = "✅" if task.get("checked") or task.get("is_completed") else "⬜"
    lines.append(f"### {status} {task['content']}")
    if task.get("description"):
        lines.append(f"_{task['description']}_")
    lines.append(f"- **ID**: `{task['id']}`")
    lines.append(f"- **Priority**: {priority}")
    if task.get("due"):
        due = task["due"]
        due_str = due.get("datetime") or due.get("date", "No date")
        lines.append(f"- **Due**: {due_str}")
        if due.get("is_recurring"):
            lines.append(f"- **Recurring**: {due.get('string', 'Yes')}")
    if task.get("labels"):
        lines.append(f"- **Labels**: {', '.join(task['labels'])}")
    if task.get("project_id"):
        lines.append(f"- **Project ID**: `{task['project_id']}`")
    if task.get("section_id"):
        lines.append(f"- **Section ID**: `{task['section_id']}`")
    if task.get("parent_id"):
        lines.append(f"- **Parent Task**: `{task['parent_id']}`")
    lines.append(f"- **URL**: {task.get('url', 'N/A')}")
    return "\n".join(lines)


def format_project_markdown(project: dict) -> str:
    """Format a single project as Markdown."""
    lines = []
    lines.append(f"### {project['name']}")
    lines.append(f"- **ID**: `{project['id']}`")
    comment_count = project.get("comment_count") or project.get("note_count")
    if comment_count:
        lines.append(f"- **Comments**: {comment_count}")
    if project.get("color"):
        lines.append(f"- **Color**: {project['color']}")
    lines.append(f"- **Shared**: {'Yes' if project.get('is_shared') else 'No'}")
    lines.append(f"- **Favorite**: {'Yes' if project.get('is_favorite') else 'No'}")
    if project.get("parent_id"):
        lines.append(f"- **Parent**: `{project['parent_id']}`")
    lines.append(f"- **URL**: {project.get('url', 'N/A')}")
    return "\n".join(lines)
