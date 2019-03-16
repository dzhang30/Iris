from dataclasses import dataclass
from logging import Logger
from typing import List, Dict

from iris.utils import util


@dataclass
class GlobalConfig:
    """
    The GlobalConfig contains fields/values that determine the bounds that Metric fields must follow

    :param exec_timeout: the global execution timeout
    :param min_exec_freq: the global minimum execution frequency
    :param max_exec_freq: the global maximum execution frequency
    :param logger: logger for forensics
    """
    exec_timeout: int
    min_exec_freq: int
    max_exec_freq: int
    logger: Logger

    def __post_init__(self) -> None:
        """
        Check if the format of the GlobalConfig is correct

        :return: None, raises ValueError if the fields are not set correctly
        """
        if not 1 < self.min_exec_freq < self.max_exec_freq:
            err_fmt = 'Invalid GlobalConfig attributes: 1 sec <= min_exec_freq: {} < max_exec_freq: {}'
            err_msg = err_fmt.format(self.min_exec_freq, self.max_exec_freq)
            self.logger.error(err_msg)
            raise ValueError(err_msg)

    def __str__(self) -> str:
        """
        Retrieve string representation of a GlobalConfig. Useful for testing

        :return: The string representation of a GlobalConfig
        """
        template = 'GlobalConfig with exec_timeout: {}, min_exec_freq: {}, max_exec_freq: {}'
        return template.format(self.exec_timeout, self.min_exec_freq, self.max_exec_freq)


@dataclass
class Metric:
    """
    A Metric object that contains all of the metadata of the check/metric that needs to be executed/ran

    :param gc: the GlobalConfig object
    :param name: the metric name
    :param metric_type: the type of the metric, see valid_metric_types above
    :param execution_frequency: the metric_execution frequency
    :param export_method: the export method the metric uses to expose itself, see valid_export_methods above
    :param bash_command: the bash command that Iris actually runs to get the result of this metric
    :param help: the help string that describes what the metric does
    :param logger: logger for forensics
    """
    gc: GlobalConfig
    name: str
    metric_type: str
    execution_frequency: int
    export_method: str
    bash_command: str
    help: str
    logger: Logger

    valid_metric_types = frozenset({'counter', 'gauge', 'histogram', 'summary'})
    valid_export_methods = frozenset({'textfile', 'pushgateway'})

    def __post_init__(self) -> None:
        """
        Check if the format of the Metric is correct

        :return: None, raises ValueError if the fields are not set correctly
        """
        if self.metric_type not in self.valid_metric_types:
            err_fmt = 'Invalid metric: {}, metric_type: {} not one of valid types: {}'
            err_msg = err_fmt.format(self.name, self.metric_type, self.valid_metric_types)
            self.logger.error(err_msg)
            raise ValueError(err_msg)

        if self.export_method not in self.valid_export_methods:
            err_fmt = 'Invalid metric: {}, export_method: {} not in valid methods: {}'
            err_msg = err_fmt.format(self.name, self.export_method, self.valid_export_methods)
            self.logger.error(err_msg)
            raise ValueError(err_msg)

        if not self.gc.min_exec_freq <= self.execution_frequency <= self.gc.max_exec_freq:
            err_fmt = 'Invalid metric: {}, exec_freq: {} not between {} & {}'
            err_msg = err_fmt.format(self.name, self.execution_frequency, self.gc.min_exec_freq, self.gc.max_exec_freq)
            self.logger.error(err_msg)
            raise ValueError(err_msg)

        if self.execution_frequency <= self.gc.exec_timeout:
            self.execution_timeout = self.execution_frequency - 1
        else:
            self.execution_timeout = self.gc.exec_timeout

    def __str__(self) -> str:
        """
        Retrieve string representation of a Metric. Useful for testing

        :return: The string representation of a Metric
        """
        template = 'Metric {} of type {}. It runs every {} secs. The command is: {}'
        return template.format(self.name, self.metric_type, self.execution_frequency, self.bash_command)

    def to_json(self) -> Dict[str, str]:
        """
        Get the json format of this Metric. Used when we figure out which metrics the ec2 host must run and we need to
        create the local_config.json for the Scheduler to read and run.

        :return: a dict containing representation of the Metric and its fields
        """
        self.__dict__.pop('gc')
        self.__dict__.pop('logger')
        return self.__dict__


@dataclass
class Profile:
    """
    A Profile object that contains all of the metrics that the ec2 host needs to run

    :param name: the name of the profile
    :param metrics: a list of metric objects that the host needs to run
    :param logger: logger for forensics
    """
    name: str
    metrics: List[str]
    logger: Logger

    def __post_init__(self) -> None:
        """
        Check if the format of the Profile is correc

        :return: None, raises ValueError if the fields are not set correctly
        """
        util.detect_list_duplicates(self.metrics, '{} profile metrics'.format(self.name), self.logger)

    def __str__(self) -> str:
        """
        Retrieve string representation of a Profile. Useful for testing

        :return: The string representation of a Profile
        """
        return 'Profile {} containing the metrics: {}'.format(self.name, ', '.format(self.metrics))
