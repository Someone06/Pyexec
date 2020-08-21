import logging
from typing import Optional


def get_logger(name: str, filename: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if filename:
        log_file = logging.FileHandler(filename)
        log_file.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s](%(name)s:%(funcName)s:%(lineno)d): "
                "%(message)s"
            )
        )
        log_file.setLevel(logging.DEBUG)
        logger.addHandler(log_file)

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter("[%(levelname)s](%(name)s): %(message)s"))
    logger.addHandler(console)
    return logger
