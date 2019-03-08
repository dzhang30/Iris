import logging
import os
from configparser import ConfigParser


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

    garbage_collector_file_handler = logging.FileHandler(os.path.join(iris_log_path, 'garbage_collector.log'))
    garbage_collector_file_handler.setFormatter(format)
    logging.getLogger('iris.garbage_collector').addHandler(garbage_collector_file_handler)

    iris_main_file_handler = logging.FileHandler(os.path.join(iris_log_path, 'iris_main.log'))
    iris_main_file_handler.setFormatter(format)
    iris_main_logger = logging.getLogger('iris.main')
    iris_main_logger.addHandler(iris_main_file_handler)

    return iris_main_logger



def check_iris_dev_settings(iris_config: ConfigParser, logger: logging.Logger) -> None:
    try:
        dev_mode = iris_config.getboolean('main_settings', 'dev_mode')
    except ValueError as e:
        valid_boolean_values = ['true', 'false', 'yes', 'no', 'on', 'off', '1', '0', ]

        err_msg_format = '{}. Please set dev_mode in iris.cfg to a valid boolean value: {}'
        err_msg = err_msg_format.format(e, ', '.join(valid_boolean_values))
        logger.error(err_msg)

        raise ValueError(err_msg)

    test_ec2_instance_id = iris_config['config_service_settings']['ec2_dev_instance_id']
    if dev_mode and test_ec2_instance_id == '':
        err_msg = 'Please set the test_ec2_instance_id field in iris.cfg when running in dev mode'
        logger.error(err_msg)
        raise ValueError(err_msg)
