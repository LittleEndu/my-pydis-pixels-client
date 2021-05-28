import logging
from logging.handlers import RotatingFileHandler

import config


def get_a_logger(logger_name):
    logger = logging.getLogger(logger_name)
    if len(logger.handlers) == 0:
        handler = RotatingFileHandler(
            f"logs/{logger_name or 'root'}.log", maxBytes=5000000, backupCount=1, encoding='UTF-8'
        )
        handler.setFormatter(config.FORMATTER)
        handler.setLevel(1)
        logger.addHandler(handler)
    return logger


def chunks(list_in, n):
    """Yield successive n-sized chunks from list_in."""
    for i in range(0, len(list_in), n):
        yield list_in[i:i + n]


class Pixel:
    def __init__(self, data):
        self.data = data

    def to_rgb(self):
        return tuple(map(int, self.data))
