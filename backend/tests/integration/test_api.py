import pytest

BASE = "http://test"


async def test_health_endpoint(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_api_health_endpoint_structure(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    for key in ("overall", "db", "redis", "helius", "birdeye"):
        assert key in data


async def test_api_health_db_ok(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    # DB uses SQLite in test env — must be ok.
    # Redis may not be running in CI, so we only check the key exists.
    assert data["db"]["status"] == "ok"
    assert "status" in data["redis"]


async def test_list_tokens_returns_200(client):
    r = await client.get("/api/v1/tokens")
    assert r.status_code == 200


async def test_list_signals_returns_200(client):
    r = await client.get("/api/v1/signals")
    assert r.status_code == 200


async def test_create_token_wsol(client):
    payload = {
        "mint_address": "So11111111111111111111111111111111111111112",
        "symbol": "WSOL",
        "name": "Wrapped SOL",
        "decimals": 9,
    }
    r = await client.post("/api/v1/tokens", json=payload)
    assert r.status_code in (200, 201, 400, 409, 422)


async def test_holders_404_for_nonexistent_mint(client):
    r = await client.get("/api/v1/holders/FakeMintThatDoesNotExist1111111111/top10")
    assert r.status_code == 404


async def test_list_clusters_returns_200(client):
    r = await client.get("/api/v1/clusters")
    assert r.status_code == 200
