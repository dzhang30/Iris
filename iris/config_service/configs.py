from dataclasses import dataclass
from logging import Logger
from typing import List, Dict

from iris.utils import util


@dataclass
class GlobalConfig:
    exec_timeout: int
    min_exec_freq: int
    max_exec_freq: int
    logger: Logger

    def __post_init__(self) -> None:
        if not 1 < self.min_exec_freq < self.max_exec_freq:
            err_fmt = 'Invalid GlobalConfig attributes: 1 sec <= min_exec_freq: {} < max_exec_freq: {}'
            err_msg = err_fmt.format(self.min_exec_freq, self.max_exec_freq)
            self.logger.error(err_msg)
            raise ValueError(err_msg)

    def __str__(self) -> str:
        template = 'GlobalConfig with exec_timeout: {}, min_exec_freq: {}, max_exec_freq: {}'
        return template.format(self.exec_timeout, self.min_exec_freq, self.max_exec_freq)


@dataclass
class Metric:
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
        template = 'Metric {} of type {}. It runs every {} secs. The command is: {}'
        return template.format(self.name, self.metric_type, self.execution_frequency, self.bash_command)

    def to_json(self) -> Dict[str, str]:
        self.__dict__.pop('gc')
        self.__dict__.pop('logger')
        return self.__dict__


@dataclass
class Profile:
    name: str
    metrics: List[str]
    logger: Logger

    def __post_init__(self) -> None:
        util.detect_list_duplicates(self.metrics, '{} profile metrics'.format(self.name), self.logger)

    def __str__(self) -> str:
        return 'Profile {} containing the metrics: {}'.format(self.name, ', '.format(self.metrics))
