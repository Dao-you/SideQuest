"""Pytest Fixtures and Test Clients."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.firestore_service import get_firestore_service


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    """Ensure in-memory mock data is seeded before running tests."""
    firestore_service = get_firestore_service()
    await firestore_service.initialize()
    yield


@pytest_asyncio.fixture
async def async_client():
    """Create an AsyncClient for FastAPI endpoint testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
