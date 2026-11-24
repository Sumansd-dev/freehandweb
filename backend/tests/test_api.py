import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.mark.asyncio
async def test_root_and_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "VaaniWeb API"

        status_res = await ac.get("/api/status")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["status"] == "online"
        assert "engines" in status_data
        assert "bedrock" in status_data["engines"]
        assert "elevenlabs" in status_data["engines"]


@pytest.mark.asyncio
async def test_mock_portal_served():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/portal/")
        assert response.status_code == 200
        assert "BharatRail" in response.text
