import logging

import pytest

from iris.config_service.configs import GlobalConfig, Metric, Profile
from iris.config_service.config_lint.linter import Linter

test_global_config_path = 'tests/config_service/test_configs/correct_configs/poc_global_config.json'
test_metric_config_path = 'tests/config_service/test_configs/correct_configs/poc_metrics.json'
test_profile_configs_path = 'tests/config_service/test_configs/correct_configs/profiles'

test_logger = logging.getLogger('iris.test')


def test_lint_global_config():
    linter = Linter(test_logger)
    test_global_config = linter.lint_global_config(test_global_config_path)

    assert test_global_config == GlobalConfig(config_service_pull_freq=300,
                                              garbage_collector_run_freq=60,
                                              exec_timeout=30,
                                              max_exec_freq=86400,
                                              min_exec_freq=10,
                                              logger=test_logger)


def test_lint_metrics_config():
    linter = Linter(test_logger)
    test_global_config = linter.lint_global_config(test_global_config_path)
    metrics = linter.lint_metrics_config(global_config=test_global_config, metrics_config_path=test_metric_config_path)

    assert metrics['node_logged_in_users'] == Metric(gc=test_global_config,
                                                     name='node_logged_in_users',
                                                     metric_type='gauge',
                                                     help="The number of users currently logged into the node",
                                                     execution_frequency=30, export_method='textfile',
                                                     bash_command="who | wc -l",
                                                     logger=test_logger)


def test_lint_profile_configs():
    linter = Linter(test_logger)
    profiles = linter.lint_profile_configs(test_profile_configs_path)

    assert profiles['poc_profile_1'] == Profile(name='poc_profile_1', metrics=['node_logged_in_users'],
                                                logger=test_logger)
    assert profiles['poc_profile_0'] == Profile(name='poc_profile_0',
                                                metrics=['node_logged_in_users', 'node_open_file_descriptors'],
                                                logger=test_logger)

    with pytest.raises(ValueError) as bad_names:
        linter.lint_profile_configs('tests/config_service/test_configs/incorrect_configs/profiles')
    assert 'Profile name incorrect_name must match containing filename poc_profile_0.json' == str(
        bad_names.value)

    with pytest.raises(OSError) as directory_doesnt_exist:
        linter.lint_profile_configs('tests/config_service/test_configs/invalid/')
    assert 'tests/config_service/test_configs/invalid/ is not a directory' == str(directory_doesnt_exist.value)


def test_json_to_metric():
    test_metric_body = {
        'help': 'help test',
        'metric_type': 'gauge',
        'execution_frequency': 30,
        'execution_timeout': 30,
        'bash_command': 'lsof',
        'export_method': 'textfile'
    }

    linter = Linter(test_logger)
    test_global_config = linter.lint_global_config(test_global_config_path)

    expected_metric = Metric(gc=test_global_config, name='test', metric_type='gauge', help="help test",
                             execution_frequency=30, export_method='textfile', bash_command="lsof", logger=test_logger)

    assert linter._json_to_metric(global_config=test_global_config, metric_name='test',
                                  metric_body=test_metric_body) == expected_metric


def test_json_to_profile():
    test_profile_path = 'tests/config_service/test_configs/correct_configs/profiles/poc_profile_0.json'
    expected_profile = Profile(name='poc_profile_0', metrics=["node_logged_in_users", "node_open_file_descriptors"],
                               logger=test_logger)

    linter = Linter(test_logger)

    assert linter._json_to_profile(test_profile_path) == expected_profile


def test_diff_profile_name_filename():
    valid_profiles = {
        'valid_test0': Profile(name='valid_test0', metrics=['test_metric0'], logger=test_logger),
        'valid_test1': Profile(name='valid_test1', metrics=['test_metric1'], logger=test_logger)
    }

    linter = Linter(test_logger)
    assert not linter._diff_profile_name_filename(valid_profiles)

    invalid_profiles = {'invalid_test0': Profile(name='valid_test0', metrics=['test_metric0'], logger=test_logger)}
    assert linter._diff_profile_name_filename(invalid_profiles) == ('valid_test0', 'invalid_test0')
