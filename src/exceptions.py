"""Typed exceptions for the Todoist MCP client."""


class TodoistError(Exception):
    """Base exception for all Todoist client errors."""


class TodoistConfigError(TodoistError):
    """Raised when required configuration (e.g. API token) is missing."""


class TodoistAPIError(TodoistError):
    """Raised when Todoist returns a non-2xx response."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Todoist API error {status_code}: {message}")


class TodoistRateLimitError(TodoistAPIError):
    """Raised on 429 responses."""

    def __init__(self, message: str = "Rate limited. Todoist allows 1000 requests per 15 minutes."):
        super().__init__(status_code=429, message=message)


class TodoistTransientError(TodoistError):
    """Raised on transport errors, timeouts, or 5xx responses that may succeed on retry."""

    def __init__(self, message: str, cause: Exception | None = None):
        self.cause = cause
        super().__init__(message)
