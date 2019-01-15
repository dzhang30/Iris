import logging

import pytest

from iris.config_service.utils import util

test_logger = logging.getLogger('iris.test')


def test_find_list_duplicate():
    duplicate_list = ['test0', 'test1', 'test1']
    assert 'test1' == util.find_list_duplicate(duplicate_list)

    non_duplicate_list = ['test0', 'test1', 'test2']
    assert util.find_list_duplicate(non_duplicate_list) is None


def test_load_json_config():
    expected_config = {"node_logged_in_users": {"help": "The number of users currently logged into the node",
                                                "metric_type": "gauge",
                                                "execution_frequency": 30, "execution_timeout": 30,
                                                "bash_command": "who | wc -l",
                                                "export_method": "textfile"}}

    assert util.load_json_config(
        'tests/config_service/test_configs/correct_configs/poc_metrics.json', test_logger) == expected_config

    dup_metrics_file = 'tests/config_service/test_configs/incorrect_configs/metrics.json'
    with pytest.raises(Exception) as bad_metrics:
        util.load_json_config(dup_metrics_file, test_logger)
    assert 'Error loading the config file {0}. Err: The json file has duplicate keys: node_logged_in_users'.format(
        dup_metrics_file) == str(bad_metrics.value)

    with pytest.raises(OSError) as file_doesnt_exist:
        util.load_json_config('tests/config_service/test_configs/invalid.json', test_logger)
    assert 'tests/config_service/test_configs/invalid.json is not a file. Check if the path is correct' == str(
        file_doesnt_exist.value)


def test_detect_duplicate_json_keys():
    assert util._detect_duplicate_json_keys([('key0', 'val0'), ('key1', 'val1')]) == {'key0': 'val0', 'key1': 'val1'}

    with pytest.raises(ValueError) as duplicate_json_keys:
        util._detect_duplicate_json_keys([('duplicate_key', 'val0'), ('duplicate_key', 'val1')])
    assert 'The json file has duplicate keys: duplicate_key' == str(duplicate_json_keys.value)
