import os
import sys
from configparser import ConfigParser

import daemon

from iris.run import run_iris
from iris.utils.iris_logging import get_logger
from iris.utils.main_helpers import check_iris_dev_settings
from iris.utils.util import read_config_file

CONFIG_NAME = 'iris.cfg'


def main(iris_config: ConfigParser) -> None:
    iris_root_path = iris_config['main_settings']['iris_root_path']

    log_directory_path = os.path.join(iris_root_path, 'logs')
    os.makedirs(log_directory_path, exist_ok=True)

    iris_main_log_path = os.path.join(log_directory_path, 'iris_main.log')
    log_debug_file_path = os.path.join(iris_root_path, 'iris.debug')
    iris_main_logger = get_logger('iris.main', iris_main_log_path, log_debug_file_path)

    check_iris_dev_settings(iris_config, iris_main_logger)

    run_iris(logger=iris_main_logger, iris_config=iris_config)


if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        iris_config_path = os.path.join(sys._MEIPASS, CONFIG_NAME)  # type: ignore
    else:
        iris_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_NAME)

    iris_config = read_config_file(iris_config_path)

    with daemon.DaemonContext():
        main(iris_config)
