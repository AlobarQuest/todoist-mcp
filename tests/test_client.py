"""Tests for the Todoist API client."""

import pytest
import httpx
import respx

from src.client import api_request, API_BASE_URL
from src.exceptions import (
    TodoistConfigError,
    TodoistAPIError,
    TodoistRateLimitError,
    TodoistTransientError,
)


@pytest.mark.asyncio
@respx.mock
async def test_api_request_get_success():
    """Successful GET returns parsed JSON."""
    respx.get(f"{API_BASE_URL}/tasks").mock(
        return_value=httpx.Response(200, json=[{"id": "1", "content": "Test"}])
    )
    result = await api_request("tasks")
    assert result == [{"id": "1", "content": "Test"}]


@pytest.mark.asyncio
@respx.mock
async def test_api_request_post_success():
    """Successful POST returns parsed JSON."""
    respx.post(f"{API_BASE_URL}/tasks").mock(
        return_value=httpx.Response(200, json={"id": "1", "content": "New"})
    )
    result = await api_request("tasks", method="POST", body={"content": "New"})
    assert result == {"id": "1", "content": "New"}


@pytest.mark.asyncio
@respx.mock
async def test_api_request_204_returns_none():
    """204 No Content returns None."""
    respx.post(f"{API_BASE_URL}/tasks/1/close").mock(
        return_value=httpx.Response(204)
    )
    result = await api_request("tasks/1/close", method="POST")
    assert result is None


@pytest.mark.asyncio
@respx.mock
async def test_api_request_401_raises_api_error():
    """401 raises TodoistAPIError."""
    respx.get(f"{API_BASE_URL}/tasks").mock(
        return_value=httpx.Response(401, json={"error": "Unauthorized"})
    )
    with pytest.raises(TodoistAPIError) as exc_info:
        await api_request("tasks")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
@respx.mock
async def test_api_request_429_raises_rate_limit_error():
    """429 raises TodoistRateLimitError."""
    respx.get(f"{API_BASE_URL}/tasks").mock(
        return_value=httpx.Response(429, json={"error": "Too many requests"})
    )
    with pytest.raises(TodoistRateLimitError):
        await api_request("tasks")


@pytest.mark.asyncio
@respx.mock
async def test_api_request_500_raises_transient_after_retries():
    """5xx raises TodoistTransientError after exhausting retries."""
    respx.get(f"{API_BASE_URL}/tasks").mock(
        return_value=httpx.Response(502, json={"error": "Bad gateway"})
    )
    with pytest.raises(TodoistTransientError):
        await api_request("tasks")


@pytest.mark.asyncio
async def test_api_request_missing_token_raises_config_error(monkeypatch):
    """Missing token raises TodoistConfigError."""
    monkeypatch.delenv("TODOIST_API_TOKEN")
    with pytest.raises(TodoistConfigError):
        await api_request("tasks")


@pytest.mark.asyncio
@respx.mock
async def test_api_request_404_raises_api_error():
    """404 raises TodoistAPIError."""
    respx.get(f"{API_BASE_URL}/tasks/bad-id").mock(
        return_value=httpx.Response(404, json={"error": "Not found"})
    )
    with pytest.raises(TodoistAPIError) as exc_info:
        await api_request("tasks/bad-id")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_auto_pagination_follows_cursor():
    """api_request auto-pages through cursor-based responses."""
    respx.get(f"{API_BASE_URL}/tasks").mock(
        side_effect=[
            httpx.Response(200, json={
                "results": [{"id": "1"}],
                "next_cursor": "cursor-abc",
            }),
            httpx.Response(200, json={
                "results": [{"id": "2"}],
                "next_cursor": None,
            }),
        ]
    )
    result = await api_request("tasks")
    assert result == [{"id": "1"}, {"id": "2"}]


@pytest.mark.asyncio
@respx.mock
async def test_auto_pagination_caps_at_max_pages():
    """Auto-pagination stops at the safety cap (20 pages)."""
    responses = [
        httpx.Response(200, json={
            "results": [{"id": str(i)}],
            "next_cursor": f"cursor-{i+1}",
        })
        for i in range(25)
    ]
    respx.get(f"{API_BASE_URL}/tasks").mock(side_effect=responses)
    result = await api_request("tasks")
    # Should stop at MAX_PAGES (20), not exhaust all 25
    assert len(result) == 20


@pytest.mark.asyncio
@respx.mock
async def test_retry_on_transient_then_success():
    """Retries on 502 and succeeds on second attempt."""
    respx.get(f"{API_BASE_URL}/tasks").mock(
        side_effect=[
            httpx.Response(502, text="Bad Gateway"),
            httpx.Response(200, json=[{"id": "1"}]),
        ]
    )
    result = await api_request("tasks")
    assert result == [{"id": "1"}]


@pytest.mark.asyncio
@respx.mock
async def test_retry_exhaustion_raises_transient():
    """After max retries, raises TodoistTransientError."""
    respx.get(f"{API_BASE_URL}/tasks").mock(
        return_value=httpx.Response(502, text="Bad Gateway")
    )
    with pytest.raises(TodoistTransientError):
        await api_request("tasks")
