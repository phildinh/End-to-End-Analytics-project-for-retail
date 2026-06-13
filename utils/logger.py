"""Project-wide logger configuration.

All pipeline scripts call get_logger(__name__) instead of using print().
Logs are written to logs/pipeline_YYYYMMDD.log, one file per calendar day.
"""

import logging
import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Return a logger writing to logs/pipeline_YYYYMMDD.log and stdout."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"pipeline_{datetime.now():%Y%m%d}.log")

    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(LOG_FORMAT)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
