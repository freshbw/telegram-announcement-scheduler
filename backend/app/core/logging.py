import logging
import sys


def setup_logging(name: str = "tg-scheduler") -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )
    return logging.getLogger(name)
