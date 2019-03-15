import os
from dataclasses import dataclass
from logging import Logger
from typing import Dict, Tuple, List

from iris.config_service.configs import Metric


@dataclass
class GarbageCollector():
    """
    The GarbageCollector cleans up any stale prom files that shouldn't be scraped by prometheus anymore. These
    stale prom files can be the result of updating old metrics or accidental manual additions to the prom_dir

    :param local_config_obj: the local config object containing the current metrics that Iris should run
    :param internal_metrics_whitelist: the whitelist of internal metrics that the GarbageCollector shouldn't clean
    :param prom_dir_path: the path to the prom files directory where we look for stale prom files
    :param logger: logger for forensics
    """
    local_config_obj: Dict[str, Metric]
    internal_metrics_whitelist: Tuple
    prom_dir_path: str
    logger: Logger

    def delete_stale_prom_files(self) -> List[str]:
        """
        Remove the stale prom files in the prom_dir_path by looking at the current local_config object and internal
        metrics whitelist

        :return: a list of deleted stale prom file
        """
        deleted_files = []

        # remove stale custom metric prom files
        for prom_file_name in os.listdir(self.prom_dir_path):
            prom_name = prom_file_name.replace('.prom', '')
            if prom_name not in self.local_config_obj and prom_name not in self.internal_metrics_whitelist:
                prom_file_path = os.path.join(self.prom_dir_path, prom_file_name)
                try:
                    os.remove(prom_file_path)
                    deleted_files.append(prom_file_path)
                except Exception as e:
                    err_msg = 'Could not remove the stale prom file {}. Err: {}'.format(prom_file_path, e)
                    self.logger.warning(err_msg)

        log_msg = 'Deleted stale prom files: {}'.format(', '.join(deleted_files)) if deleted_files else 'No stale files'
        self.logger.info(log_msg)

        return deleted_files
