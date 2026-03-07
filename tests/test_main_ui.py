import pytest


@pytest.mark.asyncio
async def test_index_serves_ui(async_client):
    r = await async_client.get("/")
    assert r.status_code == 200
    html = r.text.lower()
    # The editorial landing includes the burst-test playground
    assert "limitforge" in html
    assert "fire burst" in html or "fire-btn" in html
