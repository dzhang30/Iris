import daemon

from iris.run import run_iris
from iris.utils import main_helpers

# pyinstaller doesnt allow you to set commandline args before or after making the executable so we have to hard code
# this option. It can either be set to 'dev' for local testing or 'prod' for deploying and running on an ec2 host
IRIS_MODE = 'prod'

IRIS_ROOT_PATH = '/opt/iris'  # this is where iris will download and write all of its associated files


def main() -> None:
    logger = main_helpers.setup_iris_main_logger(IRIS_ROOT_PATH)  # logging for main iris process & its child processes
    iris_mode = main_helpers.check_iris_mode(IRIS_MODE, logger)  # make sure the IRIS_MODE variable is set correctly

    run_iris(logger, iris_mode, IRIS_ROOT_PATH)


if __name__ == '__main__':
    with daemon.DaemonContext():
        main()
