import logging
import sys


def get_script_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    format = logging.Formatter(
        fmt='%(asctime)s %(name)-12s %(levelname)s %(process)-8d %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    script_stream_handler = logging.StreamHandler(sys.stdout)
    script_stream_handler.setFormatter(format)
    logger.addHandler(script_stream_handler)

    return logger
