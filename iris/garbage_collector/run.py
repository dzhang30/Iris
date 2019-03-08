import logging
import os
import time
from typing import Tuple

from iris.config_service.config_lint.linter import Linter
from iris.garbage_collector.garbage_collector import GarbageCollector
from iris.utils.prom_helpers import PromStrBuilder, PromFileWriter

logger = logging.getLogger('iris.garbage_collector')


def run_garbage_collector(global_config_path: str, local_config_path: str, prom_dir_path: str, run_frequency: float,
                          internal_metrics_whitelist: Tuple[str]) -> None:
    general_error_flag = False
    prom_writer = PromFileWriter(logger=logger)
    while True:
        try:
            logger.info('Resuming the Garbage_Collector')

            logger.info('Starting linter to transform the configs created by the config_service into python objs')

            linter = Linter(logger=logger)
            global_config_obj = linter.lint_global_config(global_config_path)
            local_config_obj = linter.lint_metrics_config(global_config_obj, local_config_path)

            gc = GarbageCollector(
                local_config_obj=local_config_obj,
                internal_metrics_whitelist=internal_metrics_whitelist,
                prom_dir_path=prom_dir_path,
                logger=logger
            )

            logger.info('Running GC to detect stale prom files')

            deleted_files = gc.delete_stale_prom_files()

            metric_name = 'iris_garbage_collector_deleted_stale_files'
            prom_builder = PromStrBuilder(
                metric_name=metric_name,
                metric_result=len(deleted_files),
                help_str='Indicate how many stale prom files the Garbage Collector had to delete',
                type_str='gauge'
            )

            prom_string = prom_builder.create_prom_string()
            prom_file_path = os.path.join(prom_dir_path, '{}.prom'.format(metric_name))
            prom_writer.write_prom_file(prom_file_path, prom_string)

            general_error_flag = False

        except Exception as e:
            logger.error('Garbage Collector has an err: {}'.format(e))
            general_error_flag = True

        finally:
            metric_name = 'iris_garbage_collector_error'
            prom_builder = PromStrBuilder(
                metric_name=metric_name,
                metric_result=int(general_error_flag),
                help_str='Indicate if an exception/error has occurred in the Garbage Collector',
                type_str='gauge'
            )

            prom_string = prom_builder.create_prom_string()
            prom_file_path = os.path.join(prom_dir_path, '{}.prom'.format(metric_name))
            prom_writer.write_prom_file(prom_file_path, prom_string)

            logger.info('Sleeping the Garbage Collector for {} seconds\n'.format(run_frequency))

            time.sleep(run_frequency)
