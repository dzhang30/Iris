import logging
import os
import time

from iris.config_service.config_lint.linter import Linter  # noqa: E402
from iris.scheduler.scheduler import Scheduler  # noqa: E402

logger = logging.getLogger('iris.scheduler')


def run_scheduler(global_config_path: str, local_config_path: str, prom_dir_path: str, run_frequency: float) -> None:
    try:
        while True:
            logger.info('Starting Scheduler')

            sleep_total = 0  # the accumulated sleep time for checking the global_config and local_config
            sleep_increment = 5  # check for global_config and local_config every 5 seconds if they don't exist
            max_wait_time = 120  # max wait/sleep time that the scheduler will wait for these configs
            while not os.path.isfile(global_config_path) or not os.path.isfile(local_config_path):
                if sleep_total == max_wait_time:
                    err_msg = 'No global_config: {} or local_config: {}. The scheduler has waited for 2 mins'.format(
                        global_config_path, local_config_path)
                    logger.error(err_msg)
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

            logger.info('Reading local_config file with metrics {}'.format([metric.name for metric in metrics_list]))

            # run scheduler to asynchronously execute each metric and asynchronously write to the metric's prom file
            scheduler = Scheduler(metrics_list, prom_dir_path, logger=logger)
            scheduler.run()

            logger.info('Finished Scheduler\n')

            time.sleep(run_frequency)

    # will log twice for defined err logs in iris code, but will catch & log other unlogged errs in code (3rd party err)
    except Exception as e:
        logger.error(e)
        raise
