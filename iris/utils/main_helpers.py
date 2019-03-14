import logging
from configparser import ConfigParser


def check_iris_dev_settings(iris_config: ConfigParser, logger: logging.Logger) -> None:
    try:
        dev_mode = iris_config.getboolean('main_settings', 'dev_mode')
    except ValueError as e:
        valid_boolean_values = ['true', 'false', 'yes', 'no', 'on', 'off', '1', '0', ]

        err_msg_format = '{}. Please set dev_mode in iris.cfg to a valid boolean value: {}'
        err_msg = err_msg_format.format(e, ', '.join(valid_boolean_values))
        logger.error(err_msg)

        raise ValueError(err_msg)

    test_ec2_instance_id = iris_config['config_service_settings']['ec2_dev_instance_id']
    if dev_mode and test_ec2_instance_id == '':
        err_msg = 'Please set the test_ec2_instance_id field in iris.cfg when running in dev mode'
        logger.error(err_msg)
        raise ValueError(err_msg)
