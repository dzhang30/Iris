import os
import sys
from typing import Dict

import daemon

from iris.run import run_iris
from iris.utils import main_helpers
from iris.utils.util import read_config_file

CONFIG_NAME = 'iris.cfg'


def main(iris_config: Dict) -> None:
    iris_root_path = iris_config['main_settings']['iris_root_path']
    iris_mode = iris_config['main_settings']['iris_mode']

    iris_main_logger = main_helpers.setup_iris_logging(iris_root_path=iris_root_path)
    main_helpers.check_iris_mode(iris_mode=iris_mode, logger=iris_main_logger)

    run_iris(
        logger=iris_main_logger,
        iris_main_settings=iris_config['main_settings'],
        config_service_settings=iris_config['config_service_settings'],
        scheduler_settings=iris_config['scheduler_settings']
    )


if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        iris_config_path = os.path.join(sys._MEIPASS, CONFIG_NAME)  # type: ignore
    else:
        iris_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_NAME)

    iris_config = read_config_file(iris_config_path)

    with daemon.DaemonContext():
        main(iris_config)
