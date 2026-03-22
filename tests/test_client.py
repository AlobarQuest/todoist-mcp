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
async def test_api_request_500_raises_transient_error():
    """5xx raises TodoistTransientError.
    NOTE: This test will be updated in Task 6 when retry logic is added.
    After Task 6, a single 502 will be retried before raising.
    The test_retry_exhaustion_raises_transient test in Task 6 covers
    the equivalent behavior (502 after all retries exhausted).
    """
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
