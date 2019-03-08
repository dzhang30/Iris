import logging
import os
import time
from typing import Tuple

from iris.config_service.config_lint.linter import Linter
from iris.scheduler.scheduler import Scheduler
from iris.utils.prom_helpers import PromStrBuilder, PromFileWriter

logger = logging.getLogger('iris.scheduler')


def run_scheduler(global_config_path: str, local_config_path: str, prom_dir_path: str, run_frequency: float,
                  internal_metrics_whitelist: Tuple[str]) -> None:
    error_flag = 0
    while True:
        try:
            logger.info('Resuming the Scheduler')

            sleep_total = 0  # the accumulated sleep time for checking the global_config and local_config
            sleep_increment = 10  # check for global_config and local_config every 5 seconds if they don't exist
            max_wait_time = 120  # max wait/sleep time that the scheduler will wait for these configs
            while not os.path.isfile(global_config_path) or not os.path.isfile(local_config_path):
                if sleep_total == max_wait_time:
                    err_msg = 'No global_config: {} or local_config: {}. The scheduler has waited for 2 mins'.format(
                        global_config_path, local_config_path)
                    logger.error('OSError: {}'.format(err_msg))
                    raise OSError(err_msg)
                else:
                    msg = 'The scheduler is still waiting on the config_service for the global_config/local_config file'
                    logger.warning(msg)
                    sleep_total += sleep_increment
                    time.sleep(sleep_increment)

            # run linter to transform the local_config file created by the config_service into objects for the scheduler
            logger.info('Starting linter to transform the config files created by the config_service into python objs')

            linter = Linter(logger)
            global_config_obj = linter.lint_global_config(global_config_path)
            local_config_obj = linter.lint_metrics_config(global_config_obj, local_config_path)
            metrics_list = list(local_config_obj.values())

            logger.info('Read local_config file metrics {}'.format(', '.join([metric.name for metric in metrics_list])))

            # run scheduler to asynchronously execute each metric and asynchronously write to the metric's prom file
            scheduler = Scheduler(metrics_list, prom_dir_path, logger=logger)
            scheduler.run()

            error_flag = 0

        # will log twice for defined err logs in iris, but will catch & log unlogged errs in code (3rd party err)
        except Exception as e:
            logger.error('Scheduler has an err: {}'.format(e))
            error_flag = 1

        finally:
            prom_writer = PromFileWriter(logger=logger)

            metric_name = 'iris_scheduler_error'
            prom_builder = PromStrBuilder(
                metric_name=metric_name,
                metric_result=error_flag,
                help_str='Indicate if an exception/error has occured in the Scheduler',
                type_str='gauge'
            )

            prom_string = prom_builder.create_prom_string()
            prom_file_path = os.path.join(prom_dir_path, '{}.prom'.format(metric_name))
            prom_writer.write_prom_file(prom_file_path, prom_string)

            # count how many custom metrics prom files are currently being exposed and create the prom file
            custom_metrics_count_result = 0
            for prom_file in os.listdir(prom_dir_path):
                metric_name = prom_file.replace('.prom', '')
                if metric_name not in internal_metrics_whitelist:
                    custom_metrics_count_result += 1

            metric_name = 'iris_custom_metrics_count'
            prom_builder = PromStrBuilder(
                metric_name=metric_name,
                metric_result=custom_metrics_count_result,
                help_str='Indicate how many custom metrics the Scheduler is exposing',
                type_str='gauge'
            )

            prom_string = prom_builder.create_prom_string()
            prom_file_path = os.path.join(prom_dir_path, '{}.prom'.format(metric_name))
            prom_writer.write_prom_file(prom_file_path, prom_string)

            logger.info('Sleeping the Scheduler for {} seconds\n'.format(run_frequency))

            time.sleep(run_frequency)
