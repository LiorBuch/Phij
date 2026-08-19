from __future__ import annotations

import json

import pytest

from dog_camera import Config, agent, ffmpeg_command
from dog_camera.agent import check_publisher_health, media_path_ready


def test_config_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("CAMERA_RTSP_URL", "rtsp://camera.test/ch2")
    monkeypatch.setenv("CAMERA_RTSP_TRANSPORT", "udp")
    monkeypatch.setenv("CAMERA_VIDEO_CODEC", "libx264")
    monkeypatch.setenv("CAMERA_RTSP_IO_TIMEOUT_SECONDS", "20")
    monkeypatch.setenv("MEDIA_MTX_API_URL", "http://mediamtx.test:9997")
    config = Config.from_env()
    assert config.source_rtsp_url == "rtsp://camera.test/ch2"
    assert config.source_rtsp_transport == "udp"
    assert config.video_codec == "libx264"
    assert config.rtsp_io_timeout == 20
    assert config.media_mtx_api_url == "http://mediamtx.test:9997"


def test_ffmpeg_command_copies_rtsp_video_and_publishes() -> None:
    config = Config(source_rtsp_url="rtsp://camera.test/ch2")
    command = ffmpeg_command(config)
    assert command[command.index("-i") + 1] == config.source_rtsp_url
    assert command[command.index("-c:v") + 1] == "copy"
    assert command[-1] == config.rtsp_url
    assert command[command.index("-c:a") + 1] == "libopus"
    assert command[command.index("-timeout") + 1] == "15000000"


def test_ffmpeg_command_can_transcode_video_and_disable_audio() -> None:
    config = Config(
        source_rtsp_url="rtsp://camera.test/ch2",
        video_codec="libx264",
        bitrate="2500k",
        audio_codec="none",
    )
    command = ffmpeg_command(config)
    assert command[command.index("-c:v") + 1] == "libx264"
    assert command[command.index("-b:v") + 1] == "2500k"
    assert "-an" in command
    assert "-c:a" not in command


def test_media_path_ready_reads_mediamtx_state(monkeypatch) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"ready": True}).encode()

    requested: list[tuple[str, int]] = []

    def urlopen(url: str, timeout: int):
        requested.append((url, timeout))
        return Response()

    monkeypatch.setattr("dog_camera.agent.urllib.request.urlopen", urlopen)
    config = Config(camera_id="dog cam", media_mtx_api_url="http://mediamtx:9997/")

    assert media_path_ready(config) is True
    assert requested == [("http://mediamtx:9997/v3/paths/get/dog%20cam", 3)]


def test_check_publisher_health_retries_before_giving_up(monkeypatch) -> None:
    attempts = 0

    def urlopen(_url: str, timeout: int):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise OSError("connection refused")
        return type("Response", (), {
            "__enter__": lambda self: self,
            "__exit__": lambda self, *_args: None,
            "read": lambda self: json.dumps({"ready": True}).encode(),
        })()

    sleeps: list[float] = []
    monkeypatch.setattr("dog_camera.agent.urllib.request.urlopen", urlopen)
    config = Config(
        source_rtsp_url="rtsp://camera.test/ch2",
        publisher_health_retries=3,
        publisher_health_retry_delay=0.5,
    )

    assert check_publisher_health(config, sleep=sleeps.append) is True
    assert attempts == 3
    assert sleeps == [0.5, 0.5]


def test_check_publisher_health_returns_none_when_api_stays_down(monkeypatch) -> None:
    monkeypatch.setattr(
        "dog_camera.agent.urllib.request.urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("connection refused")),
    )
    config = Config(
        source_rtsp_url="rtsp://camera.test/ch2",
        publisher_health_retries=2,
        publisher_health_retry_delay=0,
    )

    assert check_publisher_health(config, sleep=lambda _seconds: None) is None


def test_run_restarts_ffmpeg_when_publisher_stays_unavailable(monkeypatch) -> None:
    class StopRun(Exception):
        pass

    class Process:
        returncode: int | None = None
        terminated = False

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.terminated = True
            self.returncode = -15

        def wait(self, timeout=None) -> int:
            assert self.returncode is not None
            return self.returncode

        def kill(self) -> None:
            self.returncode = -9

    process = Process()
    starts = 0

    def popen(_command):
        nonlocal starts
        starts += 1
        if starts > 1:
            raise StopRun
        return process

    monkeypatch.setattr(agent, "media_path_ready", lambda _config: False)
    monkeypatch.setattr(agent, "send_heartbeat", lambda *_args: None)
    config = Config(
        source_rtsp_url="rtsp://camera.test/ch2",
        publisher_startup_grace=0,
        publisher_unready_checks=1,
    )

    with pytest.raises(StopRun):
        agent.run(config, popen=popen, sleep=lambda _seconds: None)

    assert process.terminated is True


def test_run_restarts_ffmpeg_when_health_checks_fail(monkeypatch) -> None:
    class StopRun(Exception):
        pass

    class Process:
        returncode: int | None = None
        terminated = False

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.terminated = True
            self.returncode = -15

        def wait(self, timeout=None) -> int:
            assert self.returncode is not None
            return self.returncode

        def kill(self) -> None:
            self.returncode = -9

    process = Process()
    starts = 0

    def popen(_command):
        nonlocal starts
        starts += 1
        if starts > 1:
            raise StopRun
        return process

    monkeypatch.setattr(
        agent,
        "check_publisher_health",
        lambda _config, sleep: None,
    )
    monkeypatch.setattr(agent, "send_heartbeat", lambda *_args: None)
    config = Config(
        source_rtsp_url="rtsp://camera.test/ch2",
        publisher_startup_grace=0,
        publisher_unready_checks=1,
    )

    with pytest.raises(StopRun):
        agent.run(config, popen=popen, sleep=lambda _seconds: None)

    assert process.terminated is True
