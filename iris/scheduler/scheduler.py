import asyncio
import os
import time
from dataclasses import dataclass
from logging import Logger
from typing import List, Optional

import aiofiles

from iris.config_service.configs import Metric  # noqa: E402


@dataclass
class MetricResult:
    name: str
    pid: int
    return_code: int
    result: str

    def __str__(self) -> str:
        template_str = 'MetricResult for: \'{}\'. PID: {}. Return_Code: {}. Result_Output: \'{}\''
        return template_str.format(self.name, self.pid, self.return_code, self.result)

    def to_prom_format(self) -> str:
        return ''


@dataclass
class Scheduler:
    metrics: List[Metric]
    prom_output_path: str
    logger: Logger

    def run(self) -> List[MetricResult]:
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(self.gather_asyncio_metrics())

        self.logger.info('Finished writing to all prom files at: {}'.format(self.prom_output_path))

        return res

    async def gather_asyncio_metrics(self) -> List[MetricResult]:
        metrics_tasks = [self.run_asyncio_metric_task(metric) for metric in self.metrics if metric is not None]

        return await asyncio.gather(*metrics_tasks)  # type: ignore

    async def run_asyncio_metric_task(self, metric: Metric) -> Optional[MetricResult]:
        metric_prom_file_path = os.path.join(self.prom_output_path, metric.name)

        if os.path.isfile(metric_prom_file_path):
            prom_file_last_modified_time = os.stat(metric_prom_file_path).st_mtime
            if time.time() - prom_file_last_modified_time >= metric.execution_frequency:
                return await self._run_asyncio_metric_task(metric_prom_file_path, metric)
            else:
                self.logger.info('Not running metric: {} yet. Execution frequency not met.'.format(metric.name))
                return None
        else:
            self.logger.info('Creating the new prom file at: {}'.format(metric_prom_file_path))
            return await self._run_asyncio_metric_task(metric_prom_file_path, metric)

    async def _run_asyncio_metric_task(self, metric_prom_file_path: str, metric: Metric) -> MetricResult:
        metric_result = await self._create_asyncio_metric_task(metric)
        await self._write_asyncio_metric_result(metric_prom_file_path, metric_result)

        return metric_result

    async def _create_asyncio_metric_task(self, metric: Metric) -> MetricResult:
        pipe = asyncio.subprocess.PIPE
        proc = await asyncio.create_subprocess_shell(cmd=metric.bash_command, stdout=pipe, stderr=pipe)

        self.logger.info('Running metric: {}. pid: {}'.format(metric.name, proc.pid))
        task = asyncio.create_task(proc.communicate())

        _, pending = await asyncio.wait([task], timeout=metric.execution_timeout)

        if proc.returncode == 0:
            result = MetricResult(metric.name, proc.pid, proc.returncode, task.result()[0].decode('utf-8').strip())
            self.logger.info(result)
        else:
            if task in pending:
                result = MetricResult(metric.name, proc.pid, -1, 'TIMEOUT')
            else:
                result = MetricResult(metric.name, proc.pid, proc.returncode, task.result()[1].decode('utf-8').strip())
            self.logger.error(result)
            task.cancel()

        return result

    async def _write_asyncio_metric_result(self, prom_file_path: str, metric_result: MetricResult) -> None:
        async with aiofiles.open(prom_file_path, 'w') as prom_file:
            await prom_file.write(str(metric_result))
