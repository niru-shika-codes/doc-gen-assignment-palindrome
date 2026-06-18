"""Centralised logging configuration for the pipeline."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


def setup_logging(level: int = logging.INFO) -> None:
    """Set up logging for the entire pipeline. Call once in generate.py."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )