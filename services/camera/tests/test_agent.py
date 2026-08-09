from dog_camera import Config, ffmpeg_command


def test_config_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("CAMERA_WIDTH", "640")
    monkeypatch.setenv("CAMERA_DEVICE", "/dev/video2")
    monkeypatch.setenv("CAMERA_AUDIO_DEVICE", "plughw:2,0")
    config = Config.from_env()
    assert config.width == 640
    assert config.device == "/dev/video2"
    assert config.audio_device == "plughw:2,0"


def test_ffmpeg_command_contains_capture_and_publish_settings() -> None:
    config = Config(width=1920, height=1080, fps=30, bitrate="2500k")
    command = ffmpeg_command(config)
    assert "1920x1080" in command
    assert "2500k" in command
    assert command[-1] == config.rtsp_url
    assert command[command.index("-g") + 1] == "60"
    assert "-an" in command


def test_ffmpeg_command_adds_opus_microphone() -> None:
    config = Config(audio_device="plughw:1,0", audio_bitrate="96k")
    command = ffmpeg_command(config)
    assert "plughw:1,0" in command
    assert command[command.index("-c:a") + 1] == "libopus"
    assert command[command.index("-b:a") + 1] == "96k"
    assert "-an" not in command
