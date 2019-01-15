import os
from dataclasses import dataclass
from logging import Logger
from typing import Any, Tuple, Dict, Optional

from iris.config_service.utils import util
from iris.config_service.configs import GlobalConfig, Metric, Profile


@dataclass
class Linter:
    logger: Logger

    def lint_global_config(self, global_config_path: str) -> GlobalConfig:
        global_config_json = util.load_json_config(global_config_path, self.logger)
        global_config = self._json_to_global(global_config_json)

        self.logger.info('Linted global_config file & transformed it into a GlobalConfig object')

        return global_config

    def lint_metrics_config(self, global_config: GlobalConfig, metrics_config_path: str) -> Dict[str, Metric]:
        metrics_json = util.load_json_config(metrics_config_path, self.logger)
        metrics = {name: self._json_to_metric(global_config, name, content) for name, content in metrics_json.items()}

        self.logger.info('Linted metrics_config file & transformed it into a dict of Metrics objects')

        return metrics

    def lint_profile_configs(self, profile_configs_path: str) -> Dict[str, Profile]:
        if not os.path.isdir(profile_configs_path):
            err_msg = '{0} is not a directory'.format(profile_configs_path)
            self.logger.error(err_msg)
            raise OSError(err_msg)

        profile_configs = os.listdir(profile_configs_path)

        duplicate_config = util.find_list_duplicate(profile_configs)
        if duplicate_config:
            err_msg = 'There are duplicate profile file names: {0}'.format(duplicate_config)
            self.logger.error(err_msg)
            raise ValueError(err_msg)

        profiles = {}
        for profile in profile_configs:
            profile_filename = profile.replace('.json', '')
            profiles[profile_filename] = self._json_to_profile(os.path.join(profile_configs_path, profile))

        diff_names = self._diff_profile_name_filename(profiles)
        if diff_names:
            err_msg = 'Profile name {0} must match containing filename {1}.json'.format(diff_names[0], diff_names[1])
            self.logger.error(err_msg)
            raise ValueError(err_msg)

        self.logger.info('Linted profile_configs files & transformed them into a dict of Profile objects')

        return profiles

    def _json_to_global(self, global_config_json: Dict[str, Any]) -> GlobalConfig:
        return GlobalConfig(
            config_service_pull_freq=global_config_json['config_service_pull_freq'],
            garbage_collector_run_freq=global_config_json['garbage_collector_run_freq'],
            exec_timeout=global_config_json['execution_timeout'],
            min_exec_freq=global_config_json['min_execution_frequency'],
            max_exec_freq=global_config_json['max_execution_frequency'],
            logger=self.logger
        )

    def _json_to_metric(self, global_config: GlobalConfig, metric_name: str, metric_body: Dict[str, Any]) -> Metric:
        return Metric(
            gc=global_config,
            name=metric_name,
            metric_type=metric_body['metric_type'],
            execution_frequency=metric_body['execution_frequency'],
            export_method=metric_body['export_method'],
            bash_command=metric_body['bash_command'], help=metric_body['help'],
            logger=self.logger
        )

    def _json_to_profile(self, profile_configs_path: str) -> Profile:
        profile_config = util.load_json_config(profile_configs_path, self.logger)
        return Profile(name=profile_config['profile_name'], metrics=profile_config['metrics'], logger=self.logger)

    def _diff_profile_name_filename(self, profiles: Dict[str, Profile]) -> Optional[Tuple[str, str]]:
        for filename, profile in profiles.items():
            if filename != profile.name:
                return (profile.name, filename)

        return None
