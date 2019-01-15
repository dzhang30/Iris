import daemon
import inspect
import logging
import multiprocessing
import os
import sys

# Set python project directory paths for Iris
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
project_root_dir = os.path.dirname(current_dir)
sys.path.insert(0, project_root_dir)

from iris.config_service.run import run_config_service  # noqa: E402
from iris.scheduler.run import run_scheduler  # noqa: E402


def setup_iris_main_logger() -> logging.Logger:
    logger = logging.getLogger('iris')
    logger.setLevel(logging.DEBUG)

    iris_log_path = os.path.join(project_root_dir, 'logs/')
    if not os.path.exists(iris_log_path):
        os.makedirs(iris_log_path, exist_ok=True)

    format = logging.Formatter(fmt='%(asctime)s %(name)-12s %(levelname)s %(process)-8d %(message)s',
                               datefmt='%Y-%m-%d %H:%M:%S')

    config_service_file_handler = logging.FileHandler(os.path.join(iris_log_path, 'config_service.log'))
    config_service_file_handler.setFormatter(format)
    logging.getLogger('iris.config_service').addHandler(config_service_file_handler)

    scheduler_file_handler = logging.FileHandler(os.path.join(iris_log_path, 'scheduler.log'))
    scheduler_file_handler.setFormatter(format)
    logging.getLogger('iris.scheduler').addHandler(scheduler_file_handler)

    iris_main_logger = logging.getLogger('iris.main')
    iris_main_file_handler = logging.FileHandler(os.path.join(iris_log_path, 'iris_main.log'))
    iris_main_file_handler.setFormatter(format)
    iris_main_logger.addHandler(iris_main_file_handler)

    return iris_main_logger


def main() -> None:
    logger = setup_iris_main_logger()
    logger.info('Starting IRIS\n')

    upload_from_path = os.path.join(project_root_dir, 'configs')
    download_to_path = os.path.join(project_root_dir, 'downloads')
    local_config_path = os.path.join(current_dir, 'local_config.json')
    global_config_path = os.path.join(download_to_path, 'poc_global_config.json')
    prom_output_path = os.path.join(project_root_dir, 'prom_files')

    # Setup config_service process
    logger.info('Started the Config_Service')
    config_service_params = {
        'aws_profile': 'prod',
        'bucket_name': 'ihr-iris',
        'upload_from_path': upload_from_path,
        'download_to_path': download_to_path,
        'local_config_path': local_config_path
    }
    config_service_process = multiprocessing.Process(
        target=run_config_service,
        name='config_service',
        kwargs=config_service_params
    )
    config_service_process.start()

    #  Setup scheduler process
    logger.info('Started the Scheduler')
    scheduler_params = {
        'global_config_path': global_config_path,
        'local_config_path': local_config_path,
        'prom_output_path': prom_output_path
    }
    scheduler_process = multiprocessing.Process(
        target=run_scheduler,
        name='scheduler',
        kwargs=scheduler_params
    )
    scheduler_process.start()

    # Have this parent process monitor the child processes running the iris components (config_service, scheduler, etc.)
    child_processes = [config_service_process, scheduler_process]
    while True:
        for child_process in child_processes:
            if child_process.exitcode:
                logger.error('The child process ({}) running the {} has failed. Check the log file'.format(
                    child_process.pid, child_process.name))


if __name__ == '__main__':
    with daemon.DaemonContext(working_directory=current_dir):
        main()
