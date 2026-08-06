from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    camera_stale_after_seconds: float = 15
    stream_name: str = "dog-cam"
    whep_url: HttpUrl = HttpUrl("http://localhost:8889/dog-cam/whep")
    cors_origin: str = "*"


AgentState = Literal["starting", "streaming", "error"]
CameraState = Literal["starting", "streaming", "error", "offline"]


class Heartbeat(BaseModel):
    camera_id: str = Field(alias="cameraId", min_length=1)
    state: AgentState
    message: Optional[str] = Field(default=None, max_length=500)
    published_at: Optional[datetime] = Field(default=None, alias="publishedAt")


class CameraStatus(BaseModel):
    camera_id: str = Field(serialization_alias="cameraId")
    state: CameraState
    message: Optional[str] = None
    last_heartbeat_at: Optional[datetime] = Field(serialization_alias="lastHeartbeatAt")
    published_at: Optional[datetime] = Field(serialization_alias="publishedAt")


class CameraStore:
    def __init__(self, camera_id: str, stale_after_seconds: float) -> None:
        self.camera_id = camera_id
        self.stale_after_seconds = stale_after_seconds
        self._heartbeat: Optional[Heartbeat] = None
        self._received_at: Optional[datetime] = None
        self._lock = Lock()

    def update(self, heartbeat: Heartbeat) -> None:
        with self._lock:
            self._heartbeat = heartbeat
            self._received_at = datetime.now(timezone.utc)

    def status(self, now: Optional[datetime] = None) -> CameraStatus:
        with self._lock:
            current = now or datetime.now(timezone.utc)
            heartbeat, received_at = self._heartbeat, self._received_at
            if heartbeat is None or received_at is None:
                return CameraStatus(camera_id=self.camera_id, state="offline",
                                    message="No heartbeat received",
                                    last_heartbeat_at=None, published_at=None)
            age = (current - received_at).total_seconds()
            if age > self.stale_after_seconds:
                return CameraStatus(camera_id=self.camera_id, state="offline",
                                    message="Camera heartbeat is stale",
                                    last_heartbeat_at=received_at,
                                    published_at=heartbeat.published_at)
            return CameraStatus(camera_id=heartbeat.camera_id, state=heartbeat.state,
                                message=heartbeat.message, last_heartbeat_at=received_at,
                                published_at=heartbeat.published_at)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    config = settings or Settings()
    store = CameraStore(config.stream_name, config.camera_stale_after_seconds)
    application = FastAPI(title="Phij Dog Camera API", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if config.cors_origin == "*" else [config.cors_origin],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post("/api/cameras/heartbeat", status_code=status.HTTP_202_ACCEPTED)
    def heartbeat(payload: Heartbeat) -> dict[str, bool]:
        if payload.camera_id != config.stream_name:
            raise HTTPException(status_code=404, detail="Unknown camera")
        store.update(payload)
        return {"accepted": True}

    @application.get("/api/cameras/{camera_id}", response_model=CameraStatus,
                     response_model_by_alias=True)
    def camera_status(camera_id: str) -> CameraStatus:
        if camera_id != config.stream_name:
            raise HTTPException(status_code=404, detail="Unknown camera")
        return store.status()

    @application.get("/api/stream")
    def stream() -> dict[str, str]:
        return {"name": config.stream_name, "whepUrl": str(config.whep_url)}

    application.state.camera_store = store
    return application


app = create_app()
