from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import quote

logger = logging.getLogger(__name__)


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
    media_mtx_api_url: str = "http://localhost:9997"
    api_url: str = "http://localhost:4000"
    heartbeat_interval: float = 5
    rtsp_io_timeout: float = 15
    publisher_startup_grace: float = 15
    publisher_unready_checks: int = 2
    publisher_health_retries: int = 5
    publisher_health_retry_delay: float = 1.0

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
            media_mtx_api_url=os.getenv("MEDIA_MTX_API_URL", "http://localhost:9997"),
            api_url=os.getenv("API_URL", "http://localhost:4000"),
            heartbeat_interval=float(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "5")),
            rtsp_io_timeout=float(os.getenv("CAMERA_RTSP_IO_TIMEOUT_SECONDS", "15")),
            publisher_startup_grace=float(os.getenv("PUBLISHER_STARTUP_GRACE_SECONDS", "15")),
            publisher_unready_checks=int(os.getenv("PUBLISHER_UNREADY_CHECKS", "2")),
            publisher_health_retries=int(os.getenv("PUBLISHER_HEALTH_RETRIES", "3")),
            publisher_health_retry_delay=float(os.getenv("PUBLISHER_HEALTH_RETRY_DELAY_SECONDS", "1")),
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
        "-timeout", str(int(config.rtsp_io_timeout * 1_000_000)),
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


def media_path_ready(config: Config) -> bool:
    path = quote(config.camera_id, safe="")
    url = f"{config.media_mtx_api_url.rstrip('/')}/v3/paths/get/{path}"
    with urllib.request.urlopen(url, timeout=3) as response:
        payload = json.load(response)
    return bool(payload.get("ready"))


def check_publisher_health(
    config: Config,
    sleep: Callable[[float], None] = time.sleep,
) -> bool | None:
    """Return True when the path is ready, False when not, None when the API is unreachable."""
    path = quote(config.camera_id, safe="")
    url = f"{config.media_mtx_api_url.rstrip('/')}/v3/paths/get/{path}"
    last_error: OSError | ValueError | None = None
    for attempt in range(config.publisher_health_retries):
        try:
            return media_path_ready(config)
        except (OSError, ValueError) as error:
            last_error = error
            if attempt + 1 < config.publisher_health_retries:
                sleep(config.publisher_health_retry_delay)
    logger.warning(
        "unable to check MediaMTX path readiness at %s after %d attempts: %s",
        url,
        config.publisher_health_retries,
        last_error,
    )
    return None


def stop_process(process: subprocess.Popen[bytes]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def run(
    config: Config,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    backoff = 1.0
    while True:
        process = popen(ffmpeg_command(config))
        started = time.monotonic()
        unready_checks = 0
        restart_reason: str | None = None
        while process.poll() is None:
            elapsed = time.monotonic() - started
            ready: bool | None = None
            if elapsed >= config.publisher_startup_grace:
                ready = check_publisher_health(config, sleep=sleep)
                if ready is True:
                    unready_checks = 0
                else:
                    unready_checks += 1
                    if unready_checks >= config.publisher_unready_checks:
                        if ready is False:
                            restart_reason = (
                                f"MediaMTX path {config.camera_id} remained unavailable; "
                                "restarting FFmpeg"
                            )
                        else:
                            restart_reason = (
                                f"MediaMTX health checks failed for {config.camera_id}; "
                                "restarting FFmpeg"
                            )
                        logger.warning(restart_reason)
                        stop_process(process)
                        break

            state = "streaming" if elapsed >= 2 and ready is True else "starting"
            try:
                send_heartbeat(config, state)
            except OSError:
                pass
            sleep(config.heartbeat_interval)
        runtime = time.monotonic() - started
        message = restart_reason or f"FFmpeg exited with code {process.returncode}"
        try:
            send_heartbeat(config, "error", message)
        except OSError:
            pass
        if runtime >= 60:
            backoff = 1.0
        sleep(backoff)
        backoff = min(backoff * 2, 30)
