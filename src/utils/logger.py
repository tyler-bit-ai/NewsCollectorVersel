"""Runtime logger for local and Vercel execution."""

import logging


def setup_logger(debug_mode: bool = False) -> logging.Logger:
    """Configure a shared console logger without filesystem writes."""
    logger = logging.getLogger("news_collector")
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)

    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.propagate = False
    return logger
