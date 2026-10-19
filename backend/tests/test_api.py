from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}


def test_create_and_redirect():
    with TestClient(app) as client:
        res = client.post("/api/links", json={"url": "https://example.com"})
        assert res.status_code == 201
        code = res.json()["code"]

        res = client.get(f"/r/{code}", follow_redirects=False)
        assert res.status_code == 307
        assert res.headers["location"].startswith("https://example.com")

        links = client.get("/api/links").json()
        assert next(link for link in links if link["code"] == code)["clicks"] == 1


def test_rejects_bad_url():
    with TestClient(app) as client:
        assert client.post("/api/links", json={"url": "not a url"}).status_code == 422


def test_unknown_code_is_404():
    with TestClient(app) as client:
        assert client.get("/r/nope00", follow_redirects=False).status_code == 404