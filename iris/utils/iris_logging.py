import logging
import os


def get_logger(name: str, log_file_path: str, log_debug_file_path: str) -> logging.Logger:
    """
    Get the logger for the specific Iris service (ie Config Service, Scheduler, Garbage Collector, Main)

    If the log_debug_file_path (/opt/iris/iris.debug) exists, then we want to enable verbose logging for each Iris
    component. This essentially floods each log file with a very detailed step by step of what's going on. Iris will
    start logging everything from the DEBUG level and above. Use this when debugging/testing. You must create the
    iris.debug file first in the directory specified by the iris_root_path field (ie /opt/iris) set in iris.cfg.

    :param name: the name of the logger (ie iris.config_service, iris.scheduler, iris.garbage_collector)
    :param log_file_path: the path to Iris service's log file
    :param log_debug_file_path: the path to the iris.debug file that triggers when we want to enable verbose logging
    :return: the logger used for forensics
    """
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
