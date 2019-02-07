import logging
import multiprocessing
import os
import time
from typing import Dict

from iris.config_service.aws.ec2_tags import EC2Tags
from iris.config_service.run import run_config_service  # noqa: E402
from iris.scheduler.run import run_scheduler  # noqa: E402


def run_iris(logger: logging.Logger, iris_main_settings: Dict, config_service_settings: Dict,
             scheduler_settings: Dict) -> None:
    try:
        iris_mode = iris_main_settings['iris_mode']
        iris_root_path = iris_main_settings['iris_root_path']
        iris_monitor_frequency = float(iris_main_settings['iris_monitor_frequency'])

        dev_mode = True if iris_mode == 'dev' else False  # run iris in dev env for testing or prod for deployment

        logger.info('Starting IRIS in {} mode\n'.format(iris_mode))

        # set path variables
        aws_credentials_path = os.path.join(iris_root_path, 'aws_credentials')
        s3_download_to_path = os.path.join(iris_root_path, 'downloads')
        local_config_file_path = os.path.join(iris_root_path, 'local_config.json')
        global_config_file_path = os.path.join(s3_download_to_path, 'global_config.json')
        prom_dir_path = os.path.join(iris_root_path, 'prom_files')

        # won't make dirs if they already exist
        os.makedirs(s3_download_to_path, exist_ok=True)
        os.makedirs(prom_dir_path, exist_ok=True)

        # run config_service process
        logger.info('Started the Config_Service child process')

        config_service_params = {
            'aws_creds_path': aws_credentials_path,
            's3_region_name': config_service_settings['s3_region_name'],
            's3_bucket_env': config_service_settings['s3_bucket_env'],
            's3_bucket_name': config_service_settings['s3_bucket_name'],
            's3_download_to_path': s3_download_to_path,
            'ec2_region_name': config_service_settings['ec2_region_name'],
            'ec2_dev_instance_id': config_service_settings['ec2_dev_instance_id'],
            'ec2_metadata_url': config_service_settings['ec2_metadata_url'],
            'local_config_path': local_config_file_path,
            'run_frequency': float(config_service_settings['run_frequency']),
            'dev_mode': dev_mode
        }

        config_service_process = multiprocessing.Process(
            target=run_config_service,
            name='config_service',
            kwargs=config_service_params
        )

        config_service_process.start()

        # run scheduler process
        logger.info('Started the Scheduler child process')

        scheduler_params = {
            'global_config_path': global_config_file_path,
            'local_config_path': local_config_file_path,
            'prom_dir_path': prom_dir_path,
            'run_frequency': float(scheduler_settings['run_frequency'])
        }

        scheduler_process = multiprocessing.Process(
            target=run_scheduler,
            name='scheduler',
            kwargs=scheduler_params
        )

        scheduler_process.start()

        # monitor the child processes (config_service, scheduler, etc.) & write to iris-{service}-up.prom files
        child_processes = [
            {'process': config_service_process, 'up': 1},
            {'process': scheduler_process, 'up': 1}]

        while True:
            child_process_names = [child['process'].name for child in child_processes]  # type: ignore
            logger.info('Monitoring {} child services: {}'.format(iris_mode, child_process_names))

            ec2 = EC2Tags(
                aws_creds_path=aws_credentials_path,
                region_name=config_service_settings['ec2_region_name'],
                ec2_metadata_url=config_service_settings['ec2_metadata_url'],
                dev_mode=dev_mode,
                dev_instance_id=config_service_settings['ec2_dev_instance_id'],
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

            logger.info('Sleeping for {}'.format(iris_monitor_frequency))

            time.sleep(iris_monitor_frequency)

    except Exception as e:
        logger.debug(e)
        raise
