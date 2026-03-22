"""Todoist API client with shared utilities."""

import os
from typing import Any, Optional

import httpx

from src.exceptions import (
    TodoistConfigError,
    TodoistAPIError,
    TodoistRateLimitError,
    TodoistTransientError,
)

API_BASE_URL = "https://api.todoist.com/api/v1"
REQUEST_TIMEOUT = 30.0
MAX_PAGES = 20


def _get_token() -> str:
    """Retrieve Todoist API token from environment."""
    token = os.environ.get("TODOIST_API_TOKEN")
    if not token:
        raise TodoistConfigError(
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


async def _do_request(
    method: str,
    url: str,
    params: Optional[dict[str, Any]] = None,
    body: Optional[dict[str, Any]] = None,
) -> httpx.Response:
    """Execute a single HTTP request with error handling.

    Returns the response object for 2xx status codes.

    Raises:
        TodoistTransientError: on transport errors or 5xx responses.
        TodoistRateLimitError: on 429 responses.
        TodoistAPIError: on 4xx responses (except 429).
    """
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.request(
                method,
                url,
                headers=_headers(),
                params=params if method == "GET" else None,
                json=body if method in ("POST", "PUT") else None,
            )
    except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as exc:
        raise TodoistTransientError(str(exc), cause=exc) from exc

    if response.status_code == 429:
        raise TodoistRateLimitError()

    if response.status_code >= 500:
        raise TodoistTransientError(
            f"Todoist returned {response.status_code}"
        )

    if response.status_code >= 400:
        detail = ""
        try:
            detail = response.json().get("error", response.text)
        except Exception:
            detail = response.text
        raise TodoistAPIError(response.status_code, detail)

    return response


async def api_request(
    endpoint: str,
    method: str = "GET",
    params: Optional[dict[str, Any]] = None,
    body: Optional[dict[str, Any]] = None,
) -> Any:
    """Make an authenticated request to the Todoist REST API v1.

    For GET requests, automatically follows cursor-based pagination up to
    MAX_PAGES. Non-GET requests are executed as a single call.

    Args:
        endpoint: API path relative to base URL (e.g. 'tasks', 'projects/123')
        method: HTTP method
        params: Query parameters
        body: JSON request body (for POST/PUT)

    Returns:
        Parsed JSON response, or None for 204 No Content.
        For paginated list endpoints, returns the accumulated results list.

    Raises:
        TodoistConfigError: if TODOIST_API_TOKEN is not set.
        TodoistAPIError: on 4xx responses (except 429).
        TodoistRateLimitError: on 429 responses.
        TodoistTransientError: on 5xx responses or transport errors.
    """
    url = f"{API_BASE_URL}/{endpoint}"
    # Strip None values from params
    if params:
        params = {k: v for k, v in params.items() if v is not None}

    # Non-GET: single request, no pagination
    if method != "GET":
        response = await _do_request(method, url, params=None, body=body)
        if response.status_code == 204:
            return None
        return response.json()

    # GET: may need pagination
    all_results: list[Any] = []
    current_params = dict(params) if params else {}

    for _ in range(MAX_PAGES):
        response = await _do_request("GET", url, params=current_params)
        data = response.json()

        if isinstance(data, dict) and "results" in data and "next_cursor" in data:
            all_results.extend(data["results"])
            if not data["next_cursor"]:
                break
            current_params["cursor"] = data["next_cursor"]
        else:
            # Non-paginated response — return as-is
            return data

    return all_results


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
