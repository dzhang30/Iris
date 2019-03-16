import os
import re
from configparser import SectionProxy
from dataclasses import dataclass
from logging import Logger
from typing import Union, Dict, Optional, Awaitable

import aiofiles

LabelTypes = Optional[Union[Dict, SectionProxy]]


@dataclass
class PromStrBuilder:
    """
    The PromStrBuilder is a class that helps transform a MetricResult into a string in .prom file format

    :param metric_name: the name of the Metric we want to build a prom string from
    :param metric_result: the MetricResult of the executed metric we want to build a prom string from
    :param help_str: the help string that describes the metric
    :param type_str: the type of the metric
    :param labels: the labels that describe more details of the metric
    """
    metric_name: str
    metric_result: float
    help_str: str
    type_str: str
    labels: LabelTypes = None

    def __post_init__(self) -> None:
        """
        Add the iris_ prefix to the metric if it is not in the metric name. Create the help_str and type_str

        :return: None
        """
        iris_prefix_found = re.search('^iris', self.metric_name, re.IGNORECASE)
        self.metric_name = self.metric_name if iris_prefix_found else 'iris_{}'.format(self.metric_name)

        self.help_str = '# HELP {} {}'.format(self.metric_name, self.help_str)
        self.type_str = '# TYPE {} {}'.format(self.metric_name, self.type_str)

    def create_prom_string(self) -> str:
        """
        Create the prom string from the metric we executed

        :return: the metric result string in prom format
        """
        labels_string = self.create_labels_string()
        prom_string = '{}{} {}'.format(self.metric_name, labels_string, self.metric_result)

        return '{}\n{}\n{}\n'.format(self.help_str, self.type_str, prom_string)

    def create_labels_string(self) -> str:
        """
        Create the labels that we want to add to the metric result prom string. Used by create_prom_string()

        :return: the string of labels we want to add to the metric result prom string
        """
        if self.labels:
            labels = ['{}="{}"'.format(name, value) for name, value in self.labels.items()]
            return '{{{}}}'.format(','.join(labels))

        return ''


@dataclass
class PromFileWriter:
    """
    The PromFileWriter class writes metric results to prom files. There is a synchronous option and an Asynchronous
    option (async option is used by the Scheduler since we can ensure that each metric is unique and will write to
    its own prom file)

    :param logger: logger for forensics
    """
    logger: Logger

    def write_prom_file(self, prom_file_path: str, *prom_strings: str, is_async: bool = False) -> Optional[Awaitable]:
        """
        Write to the specified prom file in sync or async mode

        :param prom_file_path: the path to the prom file that we want to write to
        :param prom_strings: the string in prom format that we want to write. Most likely created using PromStrBuilder
        :param is_async: Default False. set to True if you want to run in asynchronous mode (ie Scheduler)
        :return: None if running in synchronous, else returns the asynchronous write coroutine that is used by the
        Async EventLoop
        """
        if len(prom_strings) < 1:
            self.logger.error('Please pass in a prom_string or a list of them to write to {}'.format(prom_file_path))
            return None

        result_prom_string = prom_strings[0] if len(prom_strings) == 1 else '\n'.join(prom_strings)
        if is_async:
            return self.write_prom_file_async_helper(prom_file_path, result_prom_string)
        else:
            self.write_prom_file_sync_helper(prom_file_path, result_prom_string)
            return None

    def write_prom_file_sync_helper(self, prom_file_path: str, prom_string: str) -> None:
        """
        Helper method that writes to the specified prom file synchronously

        :param prom_file_path: the path to the prom file that we want to write to
        :param prom_string: the string in prom format that we want to write. Most likely created using PromStrBuilder
        :return: None
        """
        tmp_file_path = '{}.tmp'.format(prom_file_path)
        with open(tmp_file_path, 'w') as prom_file:
            prom_file.write(prom_string)
        os.rename(tmp_file_path, prom_file_path)  # Atomically update the prom file

        self.logger.info('Finished synchronous write to {}'.format(prom_file_path))

    async def write_prom_file_async_helper(self, prom_file_path: str, prom_string: str) -> None:
        """
        Helper method that writes to the specified prom file asynchronously

        :param prom_file_path: the path to the prom file that we want to write to
        :param prom_string: the string in prom format that we want to write. Most likely created using PromStrBuilder
        :return: None
        """
        tmp_file_path = '{}.tmp'.format(prom_file_path)
        async with aiofiles.open(tmp_file_path, 'w') as prom_file:
            await prom_file.write(prom_string)

        try:
            os.rename(tmp_file_path, prom_file_path)  # Atomically update the prom file
        except FileNotFoundError:
            # This should theoretically never happen when used in the Scheduler because there will always only be
            # a 1:1 mapping between an async task writer and a prom file
            err_msg = 'There is more than 1 async task trying to write to & rename the tmpfile {}. This results in ' \
                      'a FileNotFoundError because the first async task will rename the tmpfile while subsequent ' \
                      'async task(s) will try to rename the same, but now nonexistent, tmpfile'.format(tmp_file_path)
            self.logger.error(err_msg)
            raise FileNotFoundError(err_msg)

        self.logger.info('Finished asynchronous write to {}'.format(prom_file_path))
