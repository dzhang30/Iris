import logging
import os


def setup_iris_logging(iris_root_path: str) -> logging.Logger:
    logger = logging.getLogger('iris')
    logger.setLevel(logging.DEBUG)

    iris_log_path = os.path.join(iris_root_path, 'logs')
    os.makedirs(iris_log_path, exist_ok=True)

    format = logging.Formatter(
        fmt='%(asctime)s %(name)-12s %(levelname)s %(process)-8d %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    config_service_file_handler = logging.FileHandler(os.path.join(iris_log_path, 'config_service.log'))
    config_service_file_handler.setFormatter(format)
    logging.getLogger('iris.config_service').addHandler(config_service_file_handler)

    scheduler_file_handler = logging.FileHandler(os.path.join(iris_log_path, 'scheduler.log'))
    scheduler_file_handler.setFormatter(format)
    logging.getLogger('iris.scheduler').addHandler(scheduler_file_handler)

    iris_main_file_handler = logging.FileHandler(os.path.join(iris_log_path, 'iris_main.log'))
    iris_main_file_handler.setFormatter(format)
    iris_main_logger = logging.getLogger('iris.main')
    iris_main_logger.addHandler(iris_main_file_handler)

    return iris_main_logger


def check_iris_mode(iris_mode: str, logger: logging.Logger) -> str:
    iris_mode_lower = iris_mode.lower()

    if iris_mode_lower != 'dev' and iris_mode_lower != 'prod':
        err_msg = 'Please set IRIS_MODE to either dev or prod, not {}'.format(iris_mode)
        logger.error(err_msg)
        raise ValueError(err_msg)

    return iris_mode_lower
