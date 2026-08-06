from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


@dataclass(frozen=True)
class Config:
    camera_id: str = "dog-cam"
    device: str = "/dev/video0"
    width: int = 1280
    height: int = 720
    fps: int = 25
    bitrate: str = "1800k"
    input_format: str = "mjpeg"
    rtsp_url: str = "rtsp://localhost:8554/dog-cam"
    api_url: str = "http://localhost:4000"
    heartbeat_interval: float = 5

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            camera_id=os.getenv("CAMERA_ID", "dog-cam"),
            device=os.getenv("CAMERA_DEVICE", "/dev/video0"),
            width=int(os.getenv("CAMERA_WIDTH", "1280")),
            height=int(os.getenv("CAMERA_HEIGHT", "720")),
            fps=int(os.getenv("CAMERA_FPS", "25")),
            bitrate=os.getenv("CAMERA_BITRATE", "1800k"),
            input_format=os.getenv("CAMERA_INPUT_FORMAT", "mjpeg"),
            rtsp_url=os.getenv("MEDIA_MTX_RTSP_URL", "rtsp://localhost:8554/dog-cam"),
            api_url=os.getenv("API_URL", "http://localhost:4000"),
            heartbeat_interval=float(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "5")),
        )


def ffmpeg_command(config: Config) -> list[str]:
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-f", "v4l2", "-input_format", config.input_format,
        "-video_size", f"{config.width}x{config.height}",
        "-framerate", str(config.fps), "-i", config.device,
        "-an", "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
        "-b:v", config.bitrate, "-pix_fmt", "yuv420p", "-g", str(config.fps * 2),
        "-f", "rtsp", "-rtsp_transport", "tcp", config.rtsp_url,
    ]


def send_heartbeat(config: Config, state: str, message: str | None = None) -> None:
    payload = {
        "cameraId": config.camera_id,
        "state": state,
        "message": message,
        "publishedAt": datetime.now(timezone.utc).isoformat(),
    }
    request = urllib.request.Request(
        f"{config.api_url.rstrip('/')}/api/cameras/heartbeat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=3):
        pass


def run(
    config: Config,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    backoff = 1.0
    while True:
        process = popen(ffmpeg_command(config))
        started = time.monotonic()
        while process.poll() is None:
            state = "streaming" if time.monotonic() - started >= 2 else "starting"
            try:
                send_heartbeat(config, state)
            except OSError:
                pass
            sleep(config.heartbeat_interval)
        try:
            send_heartbeat(config, "error", f"FFmpeg exited with code {process.returncode}")
        except OSError:
            pass
        sleep(backoff)
        backoff = min(backoff * 2, 30)
