import logging
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError
from requests import ConnectionError

from iris.config_service.aws.ec2_tags import EC2Tags

test_logger = logging.getLogger('iris.test')


@patch('iris.config_service.aws.ec2_tags.os')
@patch('iris.config_service.aws.ec2_tags.boto3')
@patch('iris.config_service.aws.ec2_tags.requests')
def test_successful_get_tags(mock_requests, mock_boto3, mock_os):
    mock_requests.get.return_value.text = 'i-test'
    mock_boto3.Session.return_value.resource.return_value.Instance.return_value.tags = [
        {'Key': 'ihr:iris:profile', 'Value': 'test0'}, {'Key': 'ihr:iris:enabled', 'Value': 'true'}]

    mock_os.getenv.return_value = 'tests/config_service/test_configs/test_aws_credentials'

    assert {'ihr:iris:profile': 'test0', 'ihr:iris:enabled': 'true'} == EC2Tags(test_logger).get_iris_tags()


@patch('iris.config_service.aws.ec2_tags.os')
@patch('iris.config_service.aws.ec2_tags.boto3')
@patch('iris.config_service.aws.ec2_tags.requests')
def test_get_tags_failure(mock_requests, mock_boto3, mock_os):
    test_err = ClientError({'Error': {'Code': 000, 'Message': 'test message'}}, 'test get aws instance')

    mock_requests.get.return_value.text = 'i-test'
    mock_boto3.Session.return_value.resource.return_value.Instance.side_effect = test_err
    mock_os.getenv.return_value = 'tests/config_service/test_configs/test_aws_credentials'

    with pytest.raises(ClientError):
        ec2_tags = EC2Tags(test_logger)
        ec2_tags.get_iris_tags()


@patch('iris.config_service.aws.ec2_tags.os')
def test_successful_get_aws_profiles(mock_os):
    mock_os.getenv.return_value = 'tests/config_service/test_configs/test_aws_credentials'
    expected_aws_credentials_sections = ['test0', 'test1']

    ec2_tags = EC2Tags(test_logger)
    result_sections = ec2_tags._get_aws_profiles()

    assert expected_aws_credentials_sections == result_sections


@patch('iris.config_service.aws.ec2_tags.os')
def test_get_aws_profiles_failure(mock_os):
    mock_os.getenv.return_value = 'tests/config_service/test_configs/failure_aws_credentials'

    with pytest.raises(OSError):
        ec2_tags_fail = EC2Tags(test_logger)
        ec2_tags_fail._get_aws_profiles()


@patch('iris.config_service.aws.ec2_tags.requests')
def test_successful_request_instance_id(mock_requests):
    mock_requests.get.return_value.text = 'test successful'
    assert 'test successful' == EC2Tags(test_logger)._request_instance_id()


@patch('iris.config_service.aws.ec2_tags.requests.get')
def test_request_instance_id_failure(mock_requests):
    mock_requests.side_effect = ConnectionError

    with pytest.raises(ConnectionError):
        EC2Tags(test_logger)._request_instance_id()
