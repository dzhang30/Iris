import logging
import multiprocessing
import os
import time
from configparser import ConfigParser

from iris.config_service.run import run_config_service  # noqa: E402
from iris.scheduler.run import run_scheduler  # noqa: E402
from iris.utils.prom_helpers import PromStrBuilder, PromFileWriter  # noqa: E402

# Version constants - these will be updated at build time.
IRIS_VERSION = 'n/a'
IRIS_REVISION = 'n/a'
IRIS_PYTHON_VERSION = 'n/a'
IRIS_BUILD_DATE = 'n/a'


def run_iris(logger: logging.Logger, iris_config: ConfigParser) -> None:
    try:
        iris_main_settings = iris_config['main_settings']

        iris_root_path = iris_main_settings['iris_root_path']
        textfile_collector_path = iris_main_settings['textfile_collector_path']
        iris_monitor_frequency = iris_main_settings.getfloat('iris_monitor_frequency')
        dev_mode = iris_main_settings.getboolean('dev_mode')

        logger.info('Starting IRIS in {} mode\n'.format('DEV' if dev_mode else 'PROD'))

        # set path variables
        aws_credentials_path = os.path.join(iris_root_path, 'aws_credentials')
        s3_download_to_path = os.path.join(iris_root_path, 'downloads')
        local_config_file_path = os.path.join(iris_root_path, 'local_config.json')
        global_config_file_path = os.path.join(s3_download_to_path, 'global_config.json')
        prom_dir_path = os.path.join(iris_root_path, 'prom_files')

        # won't make dirs if they already exist
        os.makedirs(s3_download_to_path, exist_ok=True)
        os.makedirs(textfile_collector_path, exist_ok=True)

        if not os.path.isdir(prom_dir_path):
            logger.info('Creating symlink from {} to {}'.format(textfile_collector_path, prom_dir_path))
            os.symlink(textfile_collector_path, prom_dir_path)

        # Expose Iris version metadata
        logger.info('Exposing Iris version metadata via prom file')
        iris_version_settings = {
            'iris_version': IRIS_VERSION,
            'iris_revision': IRIS_REVISION,
            'iris_python_version': IRIS_PYTHON_VERSION,
            'iris_build_date': IRIS_BUILD_DATE,
        }

        prom_builder = PromStrBuilder(
            metric_name='iris_build_info',
            metric_result=1,
            help_str='This gives us iris build metadata',
            type_str='gauge',
            labels=iris_version_settings
        )
        prom_string = prom_builder.create_prom_string()
        prom_file_path = os.path.join(prom_dir_path, '{}.prom'.format('iris_build_info'))
        prom_writer = PromFileWriter(logger=logger)
        prom_writer.write_prom_file(prom_file_path, prom_string)

        # run config_service process
        logger.info('Starting the Config_Service child process')

        config_service_settings = iris_config['config_service_settings']
        run_config_service_params = {
            'aws_creds_path': aws_credentials_path,
            's3_region_name': config_service_settings['s3_region_name'],
            's3_bucket_env': config_service_settings['s3_bucket_env'],
            's3_bucket_name': config_service_settings['s3_bucket_name'],
            's3_download_to_path': s3_download_to_path,
            'ec2_region_name': config_service_settings['ec2_region_name'],
            'ec2_dev_instance_id': config_service_settings['ec2_dev_instance_id'],
            'ec2_metadata_url': config_service_settings['ec2_metadata_url'],
            'local_config_path': local_config_file_path,
            'prom_dir_path': prom_dir_path,
            'run_frequency': config_service_settings.getfloat('run_frequency'),
            'dev_mode': dev_mode
        }
        config_service_process = multiprocessing.Process(
            target=run_config_service,
            name='config_service',
            kwargs=run_config_service_params
        )
        config_service_process.daemon = True  # cleanup config_service child process when main process exits
        config_service_process.start()

        # run scheduler process
        logger.info('Starting the Scheduler child process')

        scheduler_settings = iris_config['scheduler_settings']
        run_scheduler_params = {
            'global_config_path': global_config_file_path,
            'local_config_path': local_config_file_path,
            'prom_dir_path': prom_dir_path,
            'run_frequency': scheduler_settings.getfloat('run_frequency')
        }
        scheduler_process = multiprocessing.Process(
            target=run_scheduler,
            name='scheduler',
            kwargs=run_scheduler_params
        )
        scheduler_process.daemon = True  # cleanup scheduler child process when main process exits
        scheduler_process.start()

        # Indicate the parent is up
        prom_builder = PromStrBuilder(
            metric_name='iris_main_up',
            metric_result=1,
            help_str='Indicates if the Iris parent process is up',
            type_str='gauge'
        )
        prom_string = prom_builder.create_prom_string()
        prom_file_path = os.path.join(prom_dir_path, 'iris_main.prom')
        prom_writer = PromFileWriter(logger=logger)
        prom_writer.write_prom_file(prom_file_path, prom_string)

        # monitor the child processes (config_service, scheduler, etc.) & write to iris-{service}-up.prom files
        child_processes = [config_service_process, scheduler_process]
        while True:
            child_process_names = [child.name for child in child_processes]
            logger.info('Monitoring child services: {}'.format(child_process_names))

            for child_process in child_processes:
                pid = child_process.pid
                process_name = child_process.name
                exit_code = child_process.exitcode

                if exit_code:
                    err_msg = 'The child process ({0}) running the {1} has failed with code {2}. Check the {1} logfile'
                    logger.error(err_msg.format(pid, process_name, exit_code))

                metric_name = 'iris_{}_up'.format(process_name)
                prom_builder = PromStrBuilder(
                    metric_name=metric_name,
                    metric_result=1 if child_process.is_alive() else 0,
                    help_str='Indicate if the {} process is still up'.format(process_name),
                    type_str='gauge'
                )

                prom_string = prom_builder.create_prom_string()
                prom_file_path = os.path.join(prom_dir_path, 'iris_{}.prom'.format(process_name))
                prom_writer = PromFileWriter(logger=logger)
                prom_writer.write_prom_file(prom_file_path, prom_string)

            logger.info('Sleeping for {}'.format(iris_monitor_frequency))

            time.sleep(iris_monitor_frequency)

    except Exception as e:
        logger.debug(e)

        # Indicate the parent is down
        prom_builder = PromStrBuilder(
            metric_name='iris_main_up',
            metric_result=0,
            help_str='Indicates if the Iris parent process is up',
            type_str='gauge'
        )
        prom_string = prom_builder.create_prom_string()
        prom_file_path = os.path.join(prom_dir_path, 'iris_main.prom')
        prom_writer = PromFileWriter(logger=logger)
        prom_writer.write_prom_file(prom_file_path, prom_string)

        raise
