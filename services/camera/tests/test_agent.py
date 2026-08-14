from dog_camera import Config, ffmpeg_command


def test_config_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("CAMERA_RTSP_URL", "rtsp://camera.test/ch2")
    monkeypatch.setenv("CAMERA_RTSP_TRANSPORT", "udp")
    monkeypatch.setenv("CAMERA_VIDEO_CODEC", "libx264")
    config = Config.from_env()
    assert config.source_rtsp_url == "rtsp://camera.test/ch2"
    assert config.source_rtsp_transport == "udp"
    assert config.video_codec == "libx264"


def test_ffmpeg_command_copies_rtsp_video_and_publishes() -> None:
    config = Config(source_rtsp_url="rtsp://camera.test/ch2")
    command = ffmpeg_command(config)
    assert command[command.index("-i") + 1] == config.source_rtsp_url
    assert command[command.index("-c:v") + 1] == "copy"
    assert command[-1] == config.rtsp_url
    assert command[command.index("-c:a") + 1] == "libopus"


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
