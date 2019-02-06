import os
import sys

import daemon

from iris.run import run_iris
from iris.utils import main_helpers
from iris.utils.util import read_config_file

CONFIG_NAME = 'iris.cfg'


def main(iris_config_path: str) -> None:
    iris_config = read_config_file(iris_config_path)
    iris_root_path = iris_config['settings']['iris_root_path']
    iris_mode = iris_config['settings']['iris_mode']

    logger = main_helpers.setup_iris_main_logger(iris_root_path)  # logging for main iris process & its child processes
    checked_iris_mode = main_helpers.check_iris_mode(iris_mode, logger)  # make sure the IRIS_MODE variable is set right

    run_iris(logger, checked_iris_mode, iris_root_path)


if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        iris_config_path = os.path.join(sys._MEIPASS, CONFIG_NAME)  # type: ignore
    else:
        iris_config_path = os.path.dirname(os.path.join(os.path.abspath(__file__), CONFIG_NAME))

    with daemon.DaemonContext():
        main(iris_config_path)
