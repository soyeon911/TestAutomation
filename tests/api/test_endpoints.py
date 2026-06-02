"""API 테스트 — TestClient + 인메모리 DB 오버라이드 (F0-7)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.db.repository import URLRepository
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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


# --- 커스텀 별칭 ---


def test_create_with_custom_alias_uses_it(client: TestClient):
    resp = client.post("/api/urls", json={"url": "https://example.com", "custom_alias": "mylink"})
    assert resp.status_code == 201
    assert resp.json()["short_code"] == "mylink"


def test_custom_alias_redirects(client: TestClient):
    client.post("/api/urls", json={"url": "https://example.com", "custom_alias": "promo01"})
    resp = client.get("/promo01", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"].startswith("https://example.com")


def test_duplicate_custom_alias_returns_409(client: TestClient):
    body = {"url": "https://example.com", "custom_alias": "dup123"}
    assert client.post("/api/urls", json=body).status_code == 201
    resp = client.post("/api/urls", json={"url": "https://other.com", "custom_alias": "dup123"})
    assert resp.status_code == 409


@pytest.mark.parametrize("alias", ["ab", "has space", "with-dash", "a" * 33])
def test_invalid_custom_alias_returns_400(client: TestClient, alias: str):
    resp = client.post("/api/urls", json={"url": "https://example.com", "custom_alias": alias})
    assert resp.status_code == 400


# --- 만료 (TTL) ---


def test_create_with_ttl_returns_expires_at(client: TestClient):
    resp = client.post("/api/urls", json={"url": "https://example.com", "expires_in_seconds": 3600})
    assert resp.status_code == 201
    assert resp.json()["expires_at"] is not None


def test_expired_link_redirect_returns_410(client: TestClient, db_session: Session):
    # 생성 후 DB의 expires_at을 과거로 당겨 만료를 재현한다(시간 경과 대기 없이 결정적).
    code = client.post(
        "/api/urls", json={"url": "https://example.com", "expires_in_seconds": 3600}
    ).json()["short_code"]

    repo = URLRepository(db_session)
    record = repo.get_by_code(code)
    assert record is not None
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()

    resp = client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 410

    # 만료된 링크는 클릭 수가 증가하지 않아야 한다.
    assert client.get(f"/api/urls/{code}").json()["clicks"] == 0


def test_unexpired_link_redirects_normally(client: TestClient):
    code = client.post(
        "/api/urls", json={"url": "https://example.com", "expires_in_seconds": 3600}
    ).json()["short_code"]
    resp = client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 307


# --- 삭제 ---


def test_delete_existing_returns_204_then_404(client: TestClient):
    code = client.post("/api/urls", json={"url": "https://example.com"}).json()["short_code"]

    assert client.delete(f"/api/urls/{code}").status_code == 204
    # 삭제 후 통계·리다이렉트 모두 404
    assert client.get(f"/api/urls/{code}").status_code == 404
    assert client.get(f"/{code}", follow_redirects=False).status_code == 404


def test_delete_unknown_returns_404(client: TestClient):
    assert client.delete("/api/urls/nope999").status_code == 404


# --- 목록 / 페이지네이션 ---


def test_list_returns_all_created_newest_first(client: TestClient):
    for i in range(3):
        client.post("/api/urls", json={"url": f"https://example.com/{i}"})

    resp = client.get("/api/urls")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    assert body[0]["original_url"].endswith("/2")  # 최신 우선


def test_list_pagination_limit_and_offset(client: TestClient):
    for i in range(5):
        client.post("/api/urls", json={"url": f"https://example.com/{i}"})

    resp = client.get("/api/urls", params={"limit": 2, "offset": 1})

    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_empty_returns_empty_array(client: TestClient):
    resp = client.get("/api/urls")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.parametrize(("params", "expected"), [({"limit": 0}, 422), ({"offset": -1}, 422)])
def test_list_invalid_pagination_returns_422(
    client: TestClient, params: dict[str, int], expected: int
):
    assert client.get("/api/urls", params=params).status_code == expected
