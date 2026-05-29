import logging
import subprocess
import sys

from src.core.config import get_settings
from src.core.logger import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


def main_prod():
    settings = get_settings()
    cmd = [
        "gunicorn",
        "-w", str(settings.workers),
        "-k", "uvicorn.workers.UvicornWorker",
        "--timeout", str(settings.timeout),
        "--graceful-timeout", str(settings.graceful_timeout),
        "-b", f"{settings.app_host}:{settings.app_port}",
        "src.main:app",
    ]
    subprocess.run(cmd, check=True)


def main_dev():
    settings = get_settings()
    cmd = [
        "uvicorn",
        "src.main:app",
        "--host", settings.app_host,
        "--port", str(settings.app_port),
        "--reload",
        "--reload-dir", "src",
        "--log-level", settings.log_level.lower(),
    ]
    subprocess.run(cmd, check=True)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        logger.info("Starting in development mode")
        main_dev()
    else:
        logger.info("Starting in production mode")
        main_prod()


if __name__ == "__main__":
    main()
