import os
from dataclasses import dataclass
from logging import Logger
from typing import Dict, Tuple, List

from iris.config_service.configs import Metric


@dataclass
class GarbageCollector():
    local_config_obj: Dict[str, Metric]
    internal_metrics_whitelist: Tuple
    prom_dir_path: str
    logger: Logger

    def delete_stale_prom_files(self) -> List[str]:
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
