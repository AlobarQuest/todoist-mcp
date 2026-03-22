"""Tests for the exception hierarchy."""

from src.exceptions import (
    TodoistError,
    TodoistConfigError,
    TodoistAPIError,
    TodoistRateLimitError,
    TodoistTransientError,
)


def test_config_error_is_todoist_error():
    err = TodoistConfigError("missing token")
    assert isinstance(err, TodoistError)
    assert "missing token" in str(err)


def test_api_error_carries_status_code():
    err = TodoistAPIError(status_code=404, message="Not found")
    assert err.status_code == 404
    assert err.message == "Not found"
    assert isinstance(err, TodoistError)


def test_rate_limit_error_is_api_error_with_429():
    err = TodoistRateLimitError()
    assert err.status_code == 429
    assert isinstance(err, TodoistAPIError)
    assert isinstance(err, TodoistError)


def test_transient_error_carries_cause():
    cause = TimeoutError("connection timed out")
    err = TodoistTransientError("timeout", cause=cause)
    assert err.cause is cause
    assert isinstance(err, TodoistError)
