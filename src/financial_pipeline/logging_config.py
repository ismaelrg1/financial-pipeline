"""Application logging configuration."""

import logging

LOG_LEVELS: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def configure_logging(log_level: str) -> None:
    """Configure application logging for the command-line entry point."""
    try:
        level = LOG_LEVELS[log_level.upper()]
    except KeyError as error:
        raise ValueError(
            f"Unsupported log level: {log_level}",
        ) from error

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        force=True,
    )
