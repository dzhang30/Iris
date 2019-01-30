import logging

import pytest

from iris.utils import util

test_metric_path = 'tests/config_service/test_configs/correct_configs/metrics.json'
test_configs_dir = 'tests/config_service/test_configs'
dup_metrics_path = 'tests/config_service/test_configs/incorrect_configs/metrics.json'

test_invalid_file = 'tests/config_service/test_configs/invalid.json'
test_invalid_dir = 'tests/config_service/test_configs/invalid/'

test_logger = logging.getLogger('iris.test')


def test_check_file_exists():
    assert util.check_file_exists(test_metric_path, 'metrics', test_logger)

    with pytest.raises(OSError) as file_doesnt_exist:
        util.check_file_exists(test_invalid_file, 'test', test_logger)
    expected_res = 'The test file path {} does not exist or is incorrect. Check the path'.format(test_invalid_file)
    assert str(file_doesnt_exist.value) == expected_res


def test_check_dir_exists():
    assert util.check_dir_exists(test_configs_dir, 'test_configs', test_logger)

    with pytest.raises(OSError) as dir_doesnt_exist:
        util.check_dir_exists(test_invalid_dir, 'test', test_logger)
    expected_res = 'The test directory path {} does not exist or is incorrect. Check the path'.format(test_invalid_dir)
    assert str(dir_doesnt_exist.value) == expected_res


def test_find_list_duplicate():
    duplicate_list = [
        'test0',
        'test1',
        'test1'
    ]
    assert util.find_list_duplicate(duplicate_list) == 'test1'

    non_duplicate_list = [
        'test0',
        'test1',
        'test2'
    ]
    assert util.find_list_duplicate(non_duplicate_list) is None


def test_load_json_config():
    expected_config = {
        "node_logged_in_users": {
            "help": "The number of users currently logged into the node",
            "metric_type": "gauge",
            "execution_frequency": 30, "execution_timeout": 30,
            "bash_command": "who | wc -l",
            "export_method": "textfile"
        }
    }

    assert util.load_json_config(test_metric_path, 'test', test_logger) == expected_config

    with pytest.raises(Exception) as bad_metrics:
        util.load_json_config(dup_metrics_path, 'test', test_logger)
    expected_output = 'The json file has duplicate keys: node_logged_in_users'
    assert str(bad_metrics.value) == expected_output


def test_detect_duplicate_json_keys():
    expected_result = {
        'key0': 'val0',
        'key1': 'val1'
    }
    assert util._detect_duplicate_json_keys(
        [('key0', 'val0'), ('key1', 'val1')]
    ) == expected_result

    with pytest.raises(ValueError) as duplicate_json_keys:
        util._detect_duplicate_json_keys([('duplicate_key', 'val0'), ('duplicate_key', 'val1')])
    expected_output = 'The json file has duplicate keys: duplicate_key'
    assert str(duplicate_json_keys.value) == expected_output
