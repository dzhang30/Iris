import os
from dataclasses import dataclass
from logging import Logger
from typing import Any, Tuple, Dict, List

from iris.config_service.configs import GlobalConfig, Metric, Profile
from iris.utils import util


@dataclass
class Linter:
    """
    The Linter class sanity checks the format and values of each iris config file pulled down from S3

    :param logger: logger for forensics
    """
    logger: Logger

    def lint_global_config(self, global_config_path: str) -> GlobalConfig:
        """
        Check if the global config is correctly formatted and populated

        :param global_config_path: the path to the global_config json
        :return: the GlobalConfig object containing the global restrictions/rules that each metric must follow
        """
        global_config_json = util.load_json_config(global_config_path, 'global_config', self.logger)
        global_config = self._json_to_global(global_config_json)

        self.logger.info('Linted global_config file & transformed it into a GlobalConfig object')

        return global_config

    def lint_metrics_config(self, global_config: GlobalConfig, metrics_config_path: str) -> Dict[str, Metric]:
        """
        Check if the metrics config is correctly formatted and populated by using fields/restrictions from global config

        :param global_config: the global config object (created from lint_global_config)
        :param metrics_config_path: the path to the metrics_config json
        :return: a dict with key: metric name, val: metric metadata
        """
        metrics_json = util.load_json_config(metrics_config_path, 'metrics', self.logger)
        metrics = {name: self._json_to_metric(global_config, name, content) for name, content in metrics_json.items()}

        self.logger.info('Linted metrics_config file & transformed it into a dict of Metrics objects')

        return metrics

    def lint_profile_configs(self, profile_configs_path: str) -> Dict[str, Profile]:
        """
        Check if the profile configs are correctly formatted and populated

        :param profile_configs_path: the path to the directory containing each profile_config json
        :return:  a dict with key: profile name, val: profile metadata
        """
        util.check_dir_exists(dir_path=profile_configs_path, dir_type='profile_configs', logger=self.logger)

        profile_config_files = os.listdir(profile_configs_path)

        util.detect_list_duplicates(profile_config_files, 'profile config filenames', self.logger)

        profiles = {}
        for profile_filename in profile_config_files:
            profile_filename_ = profile_filename.replace('.json', '')  # remove .json so we can use result dict later
            profiles[profile_filename_] = self._json_to_profile(os.path.join(profile_configs_path, profile_filename))

        self._detect_mismatch_profilename_filename(profiles)

        self.logger.info('Linted profile_configs files & transformed them into a dict of Profile objects')

        return profiles

    def _json_to_global(self, global_config_json: Dict[str, Any]) -> GlobalConfig:
        """
        Helper method to convert the global_config json file to a GlobalConfig object

        :param global_config_json: the path to the global_config json
        :return: the GlobalConfig object containing the global restrictions/rules that each metric must follow
        """
        return GlobalConfig(
            exec_timeout=global_config_json['execution_timeout'],
            min_exec_freq=global_config_json['min_execution_frequency'],
            max_exec_freq=global_config_json['max_execution_frequency'],
            logger=self.logger
        )

    def _json_to_metric(self, global_config: GlobalConfig, metric_name: str, metric_body: Dict[str, Any]) -> Metric:
        """
        Helper method to convert a single metric in the metrics_config json to a Metric object

        :param global_config: the GlobalConfig object needed to sanity check the Metric fields
        :param metric_name: name of the metric
        :param metric_body: metadata of the metric
        :return: a Metric object
        """
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
        """
        Helper method to convert a profile_config json to a Profile object

        :param profile_configs_path: the path to the directory containing each profile_config json
        :return: a Profile object
        """
        profile_config = util.load_json_config(profile_configs_path, 'profile', self.logger)
        return Profile(name=profile_config['profile_name'], metrics=profile_config['metrics'], logger=self.logger)

    def _detect_mismatch_profilename_filename(self, profiles: Dict[str, Profile]) -> List[Tuple[str, str]]:
        """
        Helper method for lint_profile_configs to determine whether there are duplicate profile filenames

        :param profiles: a dict of profiles with key: profile name, val: profile metadata
        :return: a list containing tuples of (profile_name, profile config json path) for each duplicate profile
        """
        diff_names = []
        for profile_key_name, profile in profiles.items():
            if profile_key_name != profile.name:
                diff_names.append((profile.name, '{}.json'.format(profile_key_name)))

        if diff_names:
            err_msg_format = 'There are mismatches between profile names & their containing filenames: {}'
            err_msg = err_msg_format.format(', '.format(diff_names))
            self.logger.error(err_msg)
            raise ValueError(err_msg)

        return diff_names
