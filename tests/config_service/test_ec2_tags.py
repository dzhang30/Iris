import logging
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError
from requests import ConnectionError

from iris.config_service.aws.ec2_tags import EC2Tags

test_aws_creds_path = 'tests/config_service/test_configs/test_aws_credentials'
test_incorrect_path = 'tests/config_service/incorrect_path'

test_logger = logging.getLogger('iris.test')


@patch('iris.config_service.aws.ec2_tags.boto3')
@patch('iris.config_service.aws.ec2_tags.requests')
def test_successful_get_tags(mock_requests, mock_boto3):
    mock_requests.get.return_value.text = 'i-test'
    mock_boto3.Session.return_value.resource.return_value.Instance.return_value.tags = [
        {'Key': 'ihr:iris:profile', 'Value': 'test0'},
        {'Key': 'ihr:iris:enabled', 'Value': 'true'},
        {'Key': 'ihr:application:environment', 'Value': 'test_env'},
        {'Key': 'Name', 'Value': 'test_host'}
    ]

    expected_result = {
        'ihr:iris:profile': 'test0',
        'ihr:iris:enabled': 'true',
        'ihr:application:environment': 'test_env',
        'name': 'test_host'
    }

    assert EC2Tags(test_aws_creds_path, False, test_logger).get_iris_tags() == expected_result


@patch('iris.config_service.aws.ec2_tags.boto3')
@patch('iris.config_service.aws.ec2_tags.requests')
def test_get_tags_failure(mock_requests, mock_boto3):
    test_err = ClientError(
        {
            'Error': {
                'Code': 000,
                'Message': 'test message'
            }
        },
        'test get aws instance'
    )

    mock_requests.get.return_value.text = 'i-test'
    mock_boto3.Session.return_value.resource.return_value.Instance.side_effect = test_err

    with pytest.raises(ClientError):
        EC2Tags(test_aws_creds_path, False, test_logger).get_iris_tags()


@patch('iris.config_service.aws.ec2_tags.requests')
def test_successful_get_aws_profiles(mock_requests):
    mock_requests.get.return_value.text = 'i-test'
    expected_aws_creds_sections = ['test0', 'test1']

    ec2_tags = EC2Tags(test_aws_creds_path, False, test_logger)
    result_sections = ec2_tags._get_aws_profiles()

    assert result_sections == expected_aws_creds_sections


@patch('iris.config_service.aws.ec2_tags.requests')
def test_get_aws_profiles_failure(mock_requests):
    mock_requests.get.return_value.text = 'i-test'

    with pytest.raises(OSError):
        EC2Tags(test_incorrect_path, False, test_logger)._get_aws_profiles()


@patch('iris.config_service.aws.ec2_tags.requests')
def test_successful_request_instance_id(mock_requests):
    mock_requests.get.return_value.text = 'test successful'
    assert EC2Tags(test_aws_creds_path, False, test_logger)._request_instance_id() == 'test successful'


@patch('iris.config_service.aws.ec2_tags.requests.get')
def test_request_instance_id_failure(mock_requests):
    mock_requests.side_effect = ConnectionError

    with pytest.raises(ConnectionError):
        EC2Tags(test_aws_creds_path, False, test_logger)._request_instance_id()
