"""Shared test fixtures."""

import pytest


@pytest.fixture(autouse=True)
def fake_todoist_token(monkeypatch):
    """Ensure all tests have a fake token so _get_token() never fails unexpectedly."""
    monkeypatch.setenv("TODOIST_API_TOKEN", "test-token-fake-1234")


@pytest.fixture(autouse=True)
async def reset_shared_client():
    """Reset the shared httpx client before each test so respx can intercept.
    Also clean up after each test."""
    import src.client
    src.client._shared_client = None
    yield
    if hasattr(src.client, 'close_client'):
        await src.client.close_client()
    src.client._shared_client = None
