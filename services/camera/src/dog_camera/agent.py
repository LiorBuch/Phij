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
    source_rtsp_url: str = ""
    source_rtsp_transport: str = "tcp"
    video_codec: str = "copy"
    bitrate: str = "1800k"
    audio_codec: str = "libopus"
    audio_bitrate: str = "64k"
    rtsp_url: str = "rtsp://localhost:8554/dog-cam"
    api_url: str = "http://localhost:4000"
    heartbeat_interval: float = 5

    @classmethod
    def from_env(cls) -> Config:
        config = cls(
            camera_id=os.getenv("CAMERA_ID", "dog-cam"),
            source_rtsp_url=os.getenv("CAMERA_RTSP_URL", ""),
            source_rtsp_transport=os.getenv("CAMERA_RTSP_TRANSPORT", "tcp"),
            video_codec=os.getenv("CAMERA_VIDEO_CODEC", "copy"),
            bitrate=os.getenv("CAMERA_BITRATE", "1800k"),
            audio_codec=os.getenv("CAMERA_AUDIO_CODEC", "libopus"),
            audio_bitrate=os.getenv("CAMERA_AUDIO_BITRATE", "64k"),
            rtsp_url=os.getenv("MEDIA_MTX_RTSP_URL", "rtsp://localhost:8554/dog-cam"),
            api_url=os.getenv("API_URL", "http://localhost:4000"),
            heartbeat_interval=float(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "5")),
        )
        if not config.source_rtsp_url:
            raise ValueError("CAMERA_RTSP_URL must be set")
        if config.source_rtsp_transport not in {"tcp", "udp"}:
            raise ValueError("CAMERA_RTSP_TRANSPORT must be tcp or udp")
        return config


def ffmpeg_command(config: Config) -> list[str]:
    if not config.source_rtsp_url:
        raise ValueError("source_rtsp_url must be set")

    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-rtsp_transport", config.source_rtsp_transport,
        "-fflags", "nobuffer",
        "-flags", "low_delay",
        "-i", config.source_rtsp_url,
        "-map", "0:v:0",
        "-map", "0:a:0?",
    ]
    if config.video_codec == "copy":
        command.extend(["-c:v", "copy"])
    else:
        command.extend([
            "-c:v", config.video_codec,
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-b:v", config.bitrate,
            "-pix_fmt", "yuv420p",
        ])

    if config.audio_codec == "none":
        command.append("-an")
    else:
        command.extend([
            "-c:a", config.audio_codec, "-b:a", config.audio_bitrate,
            "-ar", "48000", "-ac", "1",
        ])

    command.extend([
        "-f", "rtsp", "-rtsp_transport", "tcp", config.rtsp_url,
    ])
    return command


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
