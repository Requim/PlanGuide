from pathlib import Path

from fastapi.testclient import TestClient


def test_auth_template_instance_roundtrip(tmp_path, monkeypatch):
    _configure_test_db(tmp_path, monkeypatch)
    create_app = _fresh_app()

    with TestClient(create_app()) as client:
        _register_and_login(client)
        templates = client.get("/plan/api/templates").json()["templates"]
        assert templates

        book = client.post("/plan/api/instances", json={"template_id": templates[0]["id"], "title": "第一本"}).json()
        assert book["title"] == "第一本"

        shelf = client.get("/plan/api/bookshelf").json()["books"]
        assert any(row["title"] == "第一本" for row in shelf)


def test_revision_conflict(tmp_path, monkeypatch):
    _configure_test_db(tmp_path, monkeypatch)
    create_app = _fresh_app()

    with TestClient(create_app()) as client:
        _register_and_login(client, "api_user_2")
        template_id = client.get("/plan/api/templates").json()["templates"][0]["id"]
        book = client.post("/plan/api/instances", json={"template_id": template_id}).json()
        item_id = book["template"]["items"][0]["item_id"]
        book["state"]["item_state"][item_id]["status"] = "已完成"

        ok = client.put(f"/plan/api/instances/{book['id']}/state", json={"revision": 0, "state": book["state"]})
        assert ok.status_code == 200

        conflict = client.put(f"/plan/api/instances/{book['id']}/state", json={"revision": 0, "state": book["state"]})
        assert conflict.status_code == 409


def _configure_test_db(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("PLAN_INVITE_CODE", "invite-test")


def _fresh_app():
    import importlib
    import planguide.config
    import planguide.infrastructure.db
    import planguide.application.services
    import planguide.interface.routes
    import planguide.interface.app

    importlib.reload(planguide.config)
    importlib.reload(planguide.infrastructure.db)
    importlib.reload(planguide.application.services)
    importlib.reload(planguide.interface.routes)
    importlib.reload(planguide.interface.app)
    return planguide.interface.app.create_app


def _register_and_login(client, username="api_user_1"):
    client.post("/plan/api/auth/register", json={
        "username": username,
        "password": "secret123",
        "invite_code": "invite-test",
    })
    resp = client.post("/plan/api/auth/login", json={"username": username, "password": "secret123"})
    assert resp.status_code == 200
