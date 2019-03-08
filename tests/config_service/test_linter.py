import logging
import os

import pytest

from iris.config_service.configs import GlobalConfig, Metric, Profile
from iris.config_service.config_lint.linter import Linter

test_global_config_path = 'tests/config_service/test_configs/correct_configs/global_config.json'
test_metric_config_path = 'tests/config_service/test_configs/correct_configs/metrics.json'
test_profile_configs_path = 'tests/config_service/test_configs/correct_configs/profiles'

test_incorrect_profiles_path = 'tests/config_service/test_configs/incorrect_configs/profiles'
test_invalid_path = 'tests/config_service/test_configs/invalid/'

test_logger = logging.getLogger('iris.test')


def test_lint_global_config():
    expected_global_config = GlobalConfig(exec_timeout=30,
                                          max_exec_freq=86400,
                                          min_exec_freq=10,
                                          logger=test_logger)
    linter = Linter(test_logger)
    assert linter.lint_global_config(test_global_config_path) == expected_global_config


def test_lint_metrics_config():
    linter = Linter(test_logger)
    test_global_config = linter.lint_global_config(test_global_config_path)

    expected_metric = Metric(gc=test_global_config,
                             name='node_logged_in_users',
                             metric_type='gauge',
                             help="The number of users currently logged into the node",
                             execution_frequency=30, export_method='textfile',
                             bash_command="who | wc -l",
                             logger=test_logger)

    metrics = linter.lint_metrics_config(global_config=test_global_config, metrics_config_path=test_metric_config_path)
    assert metrics['node_logged_in_users'] == expected_metric


def test_lint_profile_configs():
    expected_profile_0 = Profile(name='profile_0',
                                 metrics=['node_logged_in_users', 'node_open_file_descriptors'],
                                 logger=test_logger)
    expected_profile_1 = Profile(name='profile_1',
                                 metrics=['node_logged_in_users'],
                                 logger=test_logger)

    linter = Linter(test_logger)
    profiles = linter.lint_profile_configs(test_profile_configs_path)
    assert profiles['profile_0'] == expected_profile_0
    assert profiles['profile_1'] == expected_profile_1

    with pytest.raises(ValueError):
        linter.lint_profile_configs(test_incorrect_profiles_path)

    with pytest.raises(OSError):
        linter.lint_profile_configs(test_invalid_path)


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

    expected_metric = Metric(
        gc=test_global_config,
        name='test',
        metric_type='gauge',
        help="help test",
        execution_frequency=30,
        export_method='textfile',
        bash_command="lsof",
        logger=test_logger
    )

    assert linter._json_to_metric(global_config=test_global_config,
                                  metric_name='test',
                                  metric_body=test_metric_body) == expected_metric


def test_json_to_profile():
    test_profile_path = os.path.join(test_profile_configs_path, 'profile_0.json')
    expected_profile = Profile(name='profile_0',
                               metrics=["node_logged_in_users", "node_open_file_descriptors"],
                               logger=test_logger)

    linter = Linter(test_logger)
    assert linter._json_to_profile(test_profile_path) == expected_profile


def test_detect_mismatch_profilename_filename():
    valid_profiles = {
        'valid_test0': Profile(name='valid_test0', metrics=['test_metric0'], logger=test_logger),
        'valid_test1': Profile(name='valid_test1', metrics=['test_metric1'], logger=test_logger)
    }

    linter = Linter(test_logger)
    assert linter._detect_mismatch_profilename_filename(valid_profiles) == []

    invalid_profiles = {'invalid_test0': Profile(name='valid_test0', metrics=['test_metric0'], logger=test_logger)}
    with pytest.raises(ValueError):
        linter._detect_mismatch_profilename_filename(invalid_profiles)
