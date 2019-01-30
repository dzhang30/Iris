import logging
import multiprocessing
import os
import time

from iris.config_service.aws.ec2_tags import EC2Tags
from iris.config_service.run import run_config_service  # noqa: E402
from iris.scheduler.run import run_scheduler  # noqa: E402


def run_iris(logger: logging.Logger, iris_mode: str, iris_root_path: str) -> None:
    # determine whether we want to run iris in dev env for testing or prod for deployment
    dev_mode = True if iris_mode == 'dev' else False

    logger.info('Starting IRIS in {} mode\n'.format(iris_mode))

    # set path variables
    iris_aws_creds_path = os.path.join(iris_root_path, 'aws_credentials')
    download_to_path = os.path.join(iris_root_path, 'downloads')
    local_config_file_path = os.path.join(iris_root_path, 'local_config.json')
    global_config_file_path = os.path.join(download_to_path, 'global_config.json')
    prom_dir_path = os.path.join(iris_root_path, 'prom_files')

    # won't make dirs if they already exist
    os.makedirs(download_to_path, exist_ok=True)
    os.makedirs(prom_dir_path, exist_ok=True)

    # setup config_service process
    logger.info('Started the Config_Service child process')

    config_service_params = {
        'aws_creds_path': iris_aws_creds_path,
        'aws_profile': 'prod',
        'bucket_name': 'ihr-iris',
        'download_to_path': download_to_path,
        'local_config_path': local_config_file_path,
        'interval': 25,
        'dev_mode': dev_mode
    }
    config_service_process = multiprocessing.Process(
        target=run_config_service,
        name='config_service',
        kwargs=config_service_params
    )

    config_service_process.start()

    # setup scheduler process
    logger.info('Started the Scheduler child process')

    scheduler_params = {
        'global_config_path': global_config_file_path,
        'local_config_path': local_config_file_path,
        'prom_dir_path': prom_dir_path,
        'interval': 20
    }
    scheduler_process = multiprocessing.Process(
        target=run_scheduler,
        name='scheduler',
        kwargs=scheduler_params
    )

    scheduler_process.start()

    # have this parent process monitor the child processes (config_service, scheduler, etc.)
    # write to iris-{service}-up.prom files for prometheus to monitor
    child_processes = [
        {'process': config_service_process, 'up': 1},
        {'process': scheduler_process, 'up': 1}]

    try:
        wait_time = 120  # The parent process will wait in 2 minute intervals to check if the child services exited
        while True:
            child_process_names = [child['process'].name for child in child_processes]  # type: ignore
            logger.info('Monitoring {} child services: {}'.format(iris_mode, child_process_names))

            ec2 = EC2Tags(
                aws_creds_path=iris_aws_creds_path,
                dev_mode=dev_mode,
                logger=logger
            )

            tags = ec2.get_iris_tags()
            host_name = tags['name']
            environment = tags['ihr:application:environment']
            iris_profile = tags['ihr:iris:profile']

            logger.info('Using iris tags as prom labels to generate iris_*_up.prom files for each child service')
            for child_process in child_processes:
                pid = child_process['process'].pid  # type: ignore
                name = child_process['process'].name  # type: ignore
                exit_code = child_process['process'].exitcode  # type: ignore

                if exit_code and child_process['up'] == 1:
                    err_msg = 'The child process ({0}) running the {1} has failed with code {2}. Check the {1} logfile'
                    logger.error(err_msg.format(pid, name, exit_code))
                    child_process['up'] = 0

                prom_format = 'iris_{}_up{{host_name="{}",environment="{}",iris_profile="{}"}} {}'
                prom_file_path = os.path.join(prom_dir_path, 'iris_{}_up.prom'.format(name))
                with open(prom_file_path, 'w') as prom_file:
                    prom_string = prom_format.format(name, host_name, environment, iris_profile, child_process['up'])
                    prom_file.write(prom_string)
                    logger.info('Finished writing to {}. The result is {}'.format(prom_file_path, prom_string))

            logger.info('Sleeping for {}'.format(wait_time))
            time.sleep(wait_time)

    except Exception as e:
        logger.debug(e)
        raise
