import asyncio
import os
import time
from dataclasses import dataclass
from logging import Logger
from typing import List, Optional

from iris.config_service.configs import Metric  # noqa: E402
from iris.utils.prom_helpers import PromStrBuilder, PromFileWriter  # noqa: E402


@dataclass
class MetricResult:
    metric: Metric
    pid: int
    timeout: bool
    return_code: int
    shell_output: str
    logger: Logger

    err_msg_format = 'Metric {} must output a number via command {}. Current result {}'

    def __post_init__(self) -> None:
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
        template_str = 'MetricResult for: \'{}\'. PID: {}. Return_Code: {}. Result_Output: \'{}\''
        return template_str.format(self.metric.name, self.pid, self.return_code, self.shell_output)


@dataclass
class Scheduler:
    metrics: List[Metric]
    prom_dir_path: str
    logger: Logger

    def run(self) -> List[MetricResult]:
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(self.gather_asyncio_metrics())

        self.logger.info('Finished writing to all prom files at: {}'.format(self.prom_dir_path))

        return res

    async def gather_asyncio_metrics(self) -> List[MetricResult]:
        metrics_tasks = [self.run_asyncio_metric_task(metric) for metric in self.metrics if metric is not None]

        return await asyncio.gather(*metrics_tasks)  # type: ignore

    async def run_asyncio_metric_task(self, metric: Metric) -> Optional[MetricResult]:
        metric_prom_file_path = os.path.join(self.prom_dir_path, '{}.prom'.format(metric.name))

        if os.path.isfile(metric_prom_file_path):
            prom_file_last_mod_time = os.stat(metric_prom_file_path).st_mtime
            elapsed_time = time.time() - prom_file_last_mod_time

            if elapsed_time >= metric.execution_frequency:
                return await self._run_asyncio_metric_task(metric_prom_file_path, metric)
            else:
                self.logger.info('Not running metric: {} yet. Execution frequency not met.'.format(metric.name))
                return None
        else:
            self.logger.info('Creating the new prom file at: {}'.format(metric_prom_file_path))
            return await self._run_asyncio_metric_task(metric_prom_file_path, metric)

    async def _run_asyncio_metric_task(self, metric_prom_file_path: str, metric: Metric) -> MetricResult:
        metric_result = await self._create_asyncio_metric_task(metric)
        result_prom_strings = metric_result.get_prom_strings()

        prom_writer = PromFileWriter(logger=self.logger)
        await prom_writer.write_prom_file(True, metric_prom_file_path, *result_prom_strings)  # type: ignore

        return metric_result

    async def _create_asyncio_metric_task(self, metric: Metric) -> MetricResult:
        pipe = asyncio.subprocess.PIPE
        proc = await asyncio.create_subprocess_shell(cmd=metric.bash_command, stdout=pipe, stderr=pipe)

        self.logger.info('Running metric: {}. pid: {}'.format(metric.name, proc.pid))
        task = asyncio.create_task(proc.communicate())

        _, pending = await asyncio.wait([task], timeout=metric.execution_timeout)

        if proc.returncode == 0:
            result = MetricResult(
                metric=metric,
                pid=proc.pid,
                timeout=False,
                return_code=proc.returncode,
                shell_output=task.result()[0].decode('utf-8').strip(),
                logger=self.logger
            )
            self.logger.info(result)
        else:
            # a process object in a pending state will not have its return_code attribute set, so we default it to -1
            if task in pending:
                result = MetricResult(
                    metric=metric,
                    pid=proc.pid,
                    timeout=True,
                    return_code=-1,
                    shell_output='TIMEOUT',
                    logger=self.logger
                )
            else:
                result = MetricResult(
                    metric=metric,
                    pid=proc.pid,
                    timeout=False,
                    return_code=proc.returncode,
                    shell_output=task.result()[1].decode('utf-8').strip(),
                    logger=self.logger
                )
            self.logger.error(result)
            task.cancel()

        return result
