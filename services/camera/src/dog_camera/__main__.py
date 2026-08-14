import logging

from .agent import Config, run

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = Config.from_env()
    logger.info("starting RTSP relay for camera %s", config.camera_id)
    try:
        run(config)
    except KeyboardInterrupt:
        logger.info("camera agent stopped")


if __name__ == "__main__":
    main()
