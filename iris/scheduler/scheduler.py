import asyncio
import os
import time
from dataclasses import dataclass
from logging import Logger
from typing import List, Dict

from iris.config_service.configs import Metric
from iris.utils.prom_helpers import PromStrBuilder, PromFileWriter


@dataclass
class MetricResult:
    """
    A MetricResult object contains all of the metadata related to the actual execution of the Metric command

    :param metric: a Metric object that contains the metadata needed to run the metric
    :param pid: the pid of the subprocess running this metric
    :param timeout: a boolean value that states whether the metric timedout or not
    :param return_code: the return code of running the bash command
    :param shell_output: the string output of running the bash command. This is visible in logs in debug mode
    :param logger: logger for forensics
    """
    metric: Metric
    pid: int
    timeout: bool
    return_code: int
    shell_output: str
    logger: Logger

    err_msg_format = 'Metric {} must output a number via command {}. Current result {}'

    def __post_init__(self) -> None:
        """
        Check if the format of the MetricResult is correct

        :return: None, raises ValueError if the fields are not set correctly
        """
        if self.return_code != 0:
            self.prom_result_value = -1.0
        else:
            try:
                self.prom_result_value = float(self.shell_output)
            except ValueError:
                err_msg = self.err_msg_format.format(self.metric.name, self.metric.bash_command, self.shell_output)
                self.logger.error(err_msg)
                self.prom_result_value = -1.0

    def get_prom_strings(self) -> List[str]:
        """
        Get the MetricResult in the prom format for when we need to write these results to a .prom file

        :return: a list of strings that build up to the prom string we need to write
        """
        main_metric_builder = PromStrBuilder(
            metric_name=self.metric.name,
            metric_result=self.prom_result_value,
            help_str=self.metric.help,
            type_str=self.metric.metric_type,
            labels={'execution_frequency': self.metric.execution_frequency}
        )
        return_code_builder = PromStrBuilder(
            metric_name='iris_{}_returncode'.format(self.metric.name),
            metric_result=self.return_code,
            help_str='the execution return code',
            type_str='gauge',
        )

        return [main_metric_builder.create_prom_string(), return_code_builder.create_prom_string()]

    def __str__(self) -> str:
        """
        Retrieve string representation of a MetricResult. Useful for testing

        :return: The string representation of a MetricResult
        """
        template_str = 'MetricResult for: \'{}\'. PID: {}. Return_Code: {}. Result_Output: \'{}\''
        return template_str.format(self.metric.name, self.pid, self.return_code, self.shell_output)


@dataclass
class Scheduler:
    """
    The Scheduler asynchronously runs all of the metrics for this current ec2 host. These metrics are specified
    by the local_config_object (the metrics field in this class) created by the Config Service. The Config Service
    created this local_config by matching the ihr:iris:profile tag of the ec2 host to the correct profile json
    config pulled from S3

    :param metrics: the list of metrics/local_config_object the Scheduler needs to run
    :param prom_dir_path: the path to the prom files directory that we write metric results to
    :param logger: logger for forensics
    """
    metrics: List[Metric]
    prom_dir_path: str
    logger: Logger

    def run(self) -> List[MetricResult]:
        """
        Run the list of metrics specified in the local_config_file/object

        :return: a list of MetricResults. See MetricResult class above
        """
        prom_file_paths_and_metrics = self.get_prom_files_to_write().items()
        tasks = [self.run_metric_task(prom_path, metric) for prom_path, metric in prom_file_paths_and_metrics]

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(asyncio.gather(*tasks))

        self.logger.info('Finished writing to all prom files at: {}'.format(self.prom_dir_path))

        return result  # type: ignore

    def get_prom_files_to_write(self) -> Dict[str, Metric]:
        """
        Determine which metrics to run by checking if the last modified time of the metric's prom file is greater than
        or equal to the metric's execution frequency. This ensures that we don't always run every metric when the
        Scheduler wakes up

        :return: a dict with key: a Metric's prom_file_path, val: the actual Metric object
        """
        prom_files_to_write = {}
        for metric in self.metrics:
            prom_file_path = os.path.join(self.prom_dir_path, '{}.prom'.format(metric.name))

            if os.path.isfile(prom_file_path):
                prom_file_last_mod_time = os.stat(prom_file_path).st_mtime
                elapsed_time = time.time() - prom_file_last_mod_time

                if elapsed_time >= metric.execution_frequency:
                    prom_files_to_write[prom_file_path] = metric
                else:
                    self.logger.info('Not running metric: {} yet. Execution frequency not met.'.format(metric.name))
            else:
                self.logger.info('Creating the new prom file at: {}'.format(prom_file_path))
                prom_files_to_write[prom_file_path] = metric

        return prom_files_to_write

    async def run_metric_task(self, prom_file_path: str, metric: Metric) -> MetricResult:
        """
        Asynchronously run a single Metric by creating a coroutine for the Async EventLoop to execute.
        This function also asynchronously writes (using aiofiles library) a MetricResult to its associated prom file.
        See iris/utils/prom_helpers.py

        :param prom_file_path: the path to the prom file that we write the MetricResult to
        :param metric: the Metric we want to asynchronously schedule and run
        :return: the MetricResult after executing the Metric
        """
        metric_result = await self._create_metric_task(metric)
        result_prom_strings = metric_result.get_prom_strings()

        prom_writer = PromFileWriter(logger=self.logger)
        await prom_writer.write_prom_file(prom_file_path, *result_prom_strings, is_async=True)  # type: ignore

        return metric_result

    async def _create_metric_task(self, metric: Metric) -> MetricResult:
        """
        Helper method for run_metric_task. This actually creates the async coroutine that runs the metric by calling
        asyncio.create_subprocess_shell(cmd=metric.bash_command.....)

        If the Metric times out, then the return_code of the MetricResult is set to -1.

        Since bash commands that have pipes (ps aux | grep iris | grep -v grep | wc -l) spawn child processes for each
        sub command, we must ensure that each child process is cleaned up if the command times out. To do this, we set
        preexec_fn=os.setsid in create_subprocess shell(...) and call os.killpg(...) to guarantee no dangling child
        process.
        See https://stackoverflow.com/questions/4789837/how-to-terminate-a-python-subprocess-launched-with-shell-true

        THX PETE for finding this solution

        :param metric: the Metric we want to asynchronously run in the subprocess shell
        :return: the MetricResult after executing the Metric
        """
        pipe = asyncio.subprocess.PIPE
        proc = await asyncio.create_subprocess_shell(cmd=metric.bash_command, stdout=pipe, stderr=pipe)

        self.logger.info('Running metric: {}. pid: {}'.format(metric.name, proc.pid))
        task = asyncio.create_task(proc.communicate())

        try:
            result = await asyncio.wait_for(task, timeout=metric.execution_timeout)
            shell_output = result[0].decode('utf-8').strip() if result[0] else result[1].decode('utf-8').strip()

            metric_result = MetricResult(
                metric=metric,
                pid=proc.pid,
                timeout=False,
                return_code=proc.returncode,
                shell_output=shell_output,
                logger=self.logger
            )
            self.logger.info(metric_result)

        except asyncio.TimeoutError:
            metric_result = MetricResult(
                metric=metric,
                pid=proc.pid,
                timeout=True,
                return_code=-1,
                shell_output='TIMEOUT',
                logger=self.logger
            )
            self.logger.error(metric_result)

            proc.terminate()

        return metric_result
