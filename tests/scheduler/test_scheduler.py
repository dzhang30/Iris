import logging
import os
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
    scheduler = get_test_scheduler_instance(
        global_config_path=test_global_config_path,
        local_config_path=test_local_config_path,
        prom_output_path=test_prom_output_path
    )

    mock_file = mock.MagicMock()
    with mock.patch('aiofiles.threadpool.sync_open', return_value=mock_file):
        mocker.patch('os.rename')
        metric_result = await scheduler.run_metric_task(test_prom_output_path, scheduler.metrics[0])

    assert metric_result.shell_output == '5'
    assert metric_result.prom_result_value == 5
    assert metric_result.return_code == 0


@pytest.mark.asyncio
async def test_scheduler_failure(mocker):
    scheduler = get_test_scheduler_instance(
        global_config_path=test_global_config_path,
        local_config_path=test_local_config_incorrect_path,
        prom_output_path=test_prom_output_path
    )

    mock_file = mock.MagicMock()
    with mock.patch('aiofiles.threadpool.sync_open', return_value=mock_file):
        mocker.patch('os.rename')
        metric_result = await scheduler.run_metric_task(test_prom_output_path, scheduler.metrics[0])

    assert metric_result.shell_output == '/bin/sh: test_incorrect_metric: command not found'
    assert metric_result.prom_result_value == -1
    assert metric_result.return_code == 127


def test_get_prom_files_to_write():
    scheduler = get_test_scheduler_instance(
        global_config_path=test_global_config_path,
        local_config_path=test_local_config_path,
        prom_output_path=test_prom_output_path
    )

    expected_prom_file_path = os.path.join(test_prom_output_path, 'test_list_iris_root_dir_count.prom')
    expected_result = {expected_prom_file_path: scheduler.metrics[0]}
    assert scheduler.get_prom_files_to_write() == expected_result


def get_test_scheduler_instance(global_config_path: str, local_config_path: str, prom_output_path: str):
    linter = Linter(logger)
    global_config_obj = linter.lint_global_config(global_config_path)
    local_config_obj = linter.lint_metrics_config(global_config_obj, local_config_path)
    metrics_list = list(local_config_obj.values())

    return Scheduler(metrics_list, prom_output_path, logger)
