import pytest


@pytest.mark.asyncio
async def test_index_serves_ui(async_client):
    r = await async_client.get("/")
    assert r.status_code == 200
    html = r.text.lower()
    assert "try a decision" in html

