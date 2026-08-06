from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import CameraStore, Heartbeat, Settings, create_app


def test_camera_lifecycle() -> None:
    client = TestClient(create_app(Settings()))
    offline = client.get("/api/cameras/dog-cam")
    assert offline.status_code == 200
    assert offline.json()["state"] == "offline"

    accepted = client.post(
        "/api/cameras/heartbeat",
        json={"cameraId": "dog-cam", "state": "streaming"},
    )
    assert accepted.status_code == 202
    assert client.get("/api/cameras/dog-cam").json()["state"] == "streaming"


def test_unknown_camera_is_rejected() -> None:
    client = TestClient(create_app(Settings()))
    assert client.get("/api/cameras/other").status_code == 404


def test_stale_camera_is_offline() -> None:
    store = CameraStore("dog-cam", stale_after_seconds=1)
    store.update(Heartbeat(cameraId="dog-cam", state="streaming"))
    future = datetime.now(timezone.utc) + timedelta(seconds=2)
    assert store.status(future).state == "offline"
