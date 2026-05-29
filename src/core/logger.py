from __future__ import annotations

import logging
import logging.config
import os

import yaml


class ExactLevelFilter(logging.Filter):
    def __init__(self, level: int):
        super().__init__()
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == self.level


_CONFIG_PATH = "src/config/logging.yaml"


def configure_logging() -> None:
    os.makedirs("logs", exist_ok=True)

    if os.path.exists(_CONFIG_PATH):
        with open(_CONFIG_PATH) as f:
            config = yaml.safe_load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        )
        logging.warning("Logging config not found at %s, using basicConfig", _CONFIG_PATH)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
