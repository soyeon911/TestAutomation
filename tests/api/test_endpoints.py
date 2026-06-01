"""API 테스트 — TestClient + 인메모리 DB 오버라이드 (F0-7)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.api


def test_health_returns_ok(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_url_valid_returns_201_with_code(client: TestClient):
    resp = client.post("/api/urls", json={"url": "https://example.com"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["original_url"].startswith("https://example.com")
    assert len(body["short_code"]) >= 1
    assert body["short_url"].endswith("/" + body["short_code"])


@pytest.mark.parametrize("bad_url", ["not-a-url", "ftp://example.com", "", "  "])
def test_create_url_invalid_returns_422(client: TestClient, bad_url: str):
    resp = client.post("/api/urls", json={"url": bad_url})
    assert resp.status_code == 422


def test_redirect_known_code_returns_307_with_location(client: TestClient):
    code = client.post("/api/urls", json={"url": "https://example.com"}).json()["short_code"]

    resp = client.get(f"/{code}", follow_redirects=False)

    assert resp.status_code == 307
    assert resp.headers["location"].startswith("https://example.com")


def test_redirect_unknown_code_returns_404(client: TestClient):
    resp = client.get("/nope999", follow_redirects=False)
    assert resp.status_code == 404


def test_stats_after_one_redirect_reports_clicks_one(client: TestClient):
    code = client.post("/api/urls", json={"url": "https://example.com"}).json()["short_code"]
    client.get(f"/{code}", follow_redirects=False)

    resp = client.get(f"/api/urls/{code}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["short_code"] == code
    assert body["clicks"] == 1
    assert "created_at" in body


def test_stats_unknown_code_returns_404(client: TestClient):
    resp = client.get("/api/urls/nope999")
    assert resp.status_code == 404
