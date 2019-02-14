import logging
from unittest import mock

import aiofiles
import pytest

from iris.config_service.config_lint.linter import Linter
from iris.scheduler.scheduler import Scheduler

test_global_config_path = 'tests/scheduler/test_configs/global_config.json'
test_local_config_path = 'tests/scheduler/test_configs/local_config.json'
test_prom_output_path = 'tests/scheduler/test_prom_files'

test_local_config_incorrect_path = 'tests/scheduler/test_configs/local_config_incorrect.json'

logger = logging.getLogger('iris.test')

aiofiles.threadpool.wrap.register(mock.MagicMock)(
    lambda *args, **kwargs: aiofiles.threadpool.AsyncBufferedIOBase(*args, **kwargs)
)


@pytest.mark.asyncio
async def test_scheduler_success(mocker):
    linter = Linter(logger)
    global_config_obj = linter.lint_global_config(test_global_config_path)
    local_config_obj = linter.lint_metrics_config(global_config_obj, test_local_config_path)
    metrics_list = list(local_config_obj.values())

    scheduler = Scheduler(metrics_list, test_prom_output_path, logger)

    mock_file = mock.MagicMock()
    with mock.patch('aiofiles.threadpool.sync_open', return_value=mock_file):
        mocker.patch('os.rename')
        metric_result = await scheduler.gather_asyncio_metrics()

    assert metric_result[0].shell_output == '5'
    assert metric_result[0].prom_result_value == 5
    assert metric_result[0].return_code == 0


@pytest.mark.asyncio
async def test_scheduler_failure(mocker):
    linter = Linter(logger)
    global_config_obj = linter.lint_global_config(test_global_config_path)
    local_config_obj = linter.lint_metrics_config(global_config_obj, test_local_config_incorrect_path)
    metrics_list = list(local_config_obj.values())

    scheduler = Scheduler(metrics_list, test_prom_output_path, logger)

    mock_file = mock.MagicMock()
    with mock.patch('aiofiles.threadpool.sync_open', return_value=mock_file):
        mocker.patch('os.rename')
        metric_result = await scheduler.gather_asyncio_metrics()

    assert metric_result[0].shell_output == '/bin/sh: test_incorrect_metric: command not found'
    assert metric_result[0].prom_result_value == -1
    assert metric_result[0].return_code == 127
