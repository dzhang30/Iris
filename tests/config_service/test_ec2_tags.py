import logging
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError
from requests import ConnectionError

from iris.config_service.aws.ec2_tags import EC2Tags

test_aws_creds_path = 'tests/config_service/test_configs/test_aws_credentials'

test_logger = logging.getLogger('iris.test')


@patch('iris.config_service.aws.ec2_tags.boto3')
@patch('iris.config_service.aws.ec2_tags.requests')
def test_successful_get_tags(mock_requests, mock_boto3):
    mock_requests.get.return_value.text = 'i-test'
    mock_boto3.Session.return_value.resource.return_value.Instance.return_value.tags = [
        {'Key': 'ihr:iris:profile', 'Value': 'test0'},
        {'Key': 'ihr:iris:enabled', 'Value': 'true'},
    ]

    expected_result = {
        'ihr:iris:profile': 'test0',
        'ihr:iris:enabled': 'true',
    }

    ec2_tags = get_test_ec2_tags_instance()
    assert ec2_tags.get_iris_tags() == expected_result


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

    ec2_tags = get_test_ec2_tags_instance()
    with pytest.raises(ClientError):
        ec2_tags.get_iris_tags()


@patch('iris.config_service.aws.ec2_tags.requests')
def test_successful_request_instance_id(mock_requests):
    mock_requests.get.return_value.text = 'test successful'
    ec2_tags = get_test_ec2_tags_instance()
    assert ec2_tags._request_instance_id() == 'test successful'


@patch('iris.config_service.aws.ec2_tags.requests.get')
def test_request_instance_id_failure(mock_requests):
    mock_requests.side_effect = ConnectionError

    ec2_tags = get_test_ec2_tags_instance()
    with pytest.raises(ConnectionError):
        ec2_tags._request_instance_id()


@patch('iris.config_service.aws.ec2_tags.requests')
def get_test_ec2_tags_instance(mock_requests):
    mock_requests.get.return_value.text = 'test successful'

    return EC2Tags(
        aws_creds_path=test_aws_creds_path,
        region_name='test region',
        ec2_metadata_url='test url',
        dev_instance_id='i-000',
        dev_mode=False,
        logger=test_logger
    )
