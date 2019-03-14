import logging
import os


def get_logger(name: str, log_file_path: str, log_debug_file_path: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if os.path.isfile(log_debug_file_path):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)

    format = logging.Formatter(
        fmt='%(asctime)s %(name)-12s %(levelname)s %(process)-8d %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    iris_service_file_handler = logging.FileHandler(log_file_path)
    iris_service_file_handler.setFormatter(format)
    logger.addHandler(iris_service_file_handler)

    return logger
