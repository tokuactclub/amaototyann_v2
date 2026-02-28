"""Pytest configuration and shared fixtures for the test suite.

Design principles:
- All external I/O (Google Sheets, Discord, aiohttp sessions) is mocked.
- The real lifespan is replaced with a null context so no background tasks
  or network connections are created during tests.
- Environment variables are isolated per test via monkeypatch.
- get_settings() lru_cache is cleared before every test so env overrides
  take effect cleanly.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from unittest.mock import patch

import httpx
import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from fastapi import FastAPI

from amaototyann.config import get_settings
from amaototyann.store.memory import BotStore, GroupStore

# ---------------------------------------------------------------------------
# Environment / settings isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def settings_override(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Clear the get_settings lru_cache and inject dummy env vars before every test.

    This fixture is autouse so it always runs, ensuring no test accidentally
    inherits real credentials from a .env file or the parent process environment.
    """
    # Optional fields — set to empty/dummy values to prevent accidental real usage
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "")
    monkeypatch.setenv("SERVER_URL", "")
    monkeypatch.setenv("IS_RENDER_SERVER", "false")

    # Bust the lru_cache so the patched env is picked up by get_settings()
    get_settings.cache_clear()

    yield

    # Always clear again on teardown so the next test starts fresh
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------


@pytest.fixture
def bot_store() -> BotStore:
    """Return a fresh, empty BotStore for each test."""
    return BotStore()


@pytest.fixture
def group_store() -> GroupStore:
    """Return a fresh, empty GroupStore for each test."""
    return GroupStore()


# ---------------------------------------------------------------------------
# FastAPI test client (null lifespan)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _null_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """No-op lifespan that skips all startup/shutdown side-effects.

    Replaces the real lifespan so tests never attempt Sheets fetches, Discord
    bot startup, or background task creation.
    """
    yield


@pytest.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Return an httpx.AsyncClient wired to the FastAPI app via ASGITransport.

    The real lifespan is swapped out for _null_lifespan before the app is
    created, preventing any network activity during the client's lifetime.
    """
    # Patch the lifespan used by create_app() before importing/calling it
    with patch("amaototyann.server.app.lifespan", new=_null_lifespan):
        from amaototyann.server.app import create_app

        app = create_app()

        transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            yield client
