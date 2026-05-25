"""Structured logging setup for FastAPI services."""

import logging
import os


def configure_logging(service_name: str) -> logging.Logger:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
    )
    logger = logging.getLogger(service_name)
    logger.info("Logging configured for %s at level %s", service_name, level)
    return logger
