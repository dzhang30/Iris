import logging
import os
import shutil
from collections import namedtuple
from unittest.mock import patch

import pytest

from iris.config_service.aws.s3 import S3

test_aws_creds_path = 'tests/config_service/test_configs/test_aws_credentials'

test_logger = logging.getLogger('iris.test')


@patch('iris.config_service.aws.s3.boto3')
def test_s3_download_bucket(mock_boto3):
    MockBucketObject = namedtuple('MockBucketObject', 'key')

    mock_boto3.Session.return_value.resource.return_value.Bucket.return_value.objects.all.return_value = [
        MockBucketObject('test_path/key1'),
        MockBucketObject('test_path/key2')
    ]

    test_s3 = S3(
        aws_creds_path=test_aws_creds_path,
        bucket_name='test bucket',
        aws_profile_name='test profile',
        logger=test_logger
    )
    expected_files = ['test_path/key1', 'test_path/key2']
    test_download_dir_path = 'tests/config_service/test_download_directory'
    assert test_s3.download_bucket(test_download_dir_path) == expected_files

    # test download_bucket() is correctly creating directories (os.makedirs) to download s3 objects to
    assert os.path.isdir(os.path.join(test_download_dir_path, 'test_path'))
    shutil.rmtree(test_download_dir_path)


@patch('iris.config_service.aws.s3.boto3')
def test_s3_upload_object(mock_boto3):
    mock_boto3.Session.return_value.resource.return_value.Bucket.return_value.upload_file.return_value = None

    test_s3 = S3(
        aws_creds_path=test_aws_creds_path,
        bucket_name='test bucket',
        aws_profile_name='test profile',
        logger=test_logger
    )
    test_metrics_path = 'tests/config_service/test_configs/correct_configs/metrics.json'
    assert test_s3.upload_object(test_metrics_path) == 'metrics.json'

    invalid_path = 'tests/config_service/test_configs/invalid.py'
    with pytest.raises(OSError):
        test_s3.upload_object(invalid_path)


@patch('iris.config_service.aws.s3.boto3')
def test_s3_upload_directory(mock_boto3):
    mock_boto3.Session.return_value.resource.return_value.Bucket.return_value.upload_file.return_value = None

    test_s3 = S3(
        aws_creds_path=test_aws_creds_path,
        bucket_name='test bucket',
        aws_profile_name='test profile',
        logger=test_logger
    )
    expected_keys = {
        'global_config.json',
        'metrics.json',
        'profiles/profile_0.json',
        'profiles/profile_1.json'
    }
    test_upload_path = 'tests/config_service/test_configs/correct_configs/'
    assert set(test_s3.upload_directory(test_upload_path)) == expected_keys

    invalid_path = 'tests/config_service/test_configs/invalid/'
    with pytest.raises(OSError):
        test_s3.upload_directory(invalid_path)


def test_s3_create_object_key():
    object_key = S3._create_object_key(
        'test/config_service/test_configs',
        'test/config_service/',
        'metrics.json'
    )
    assert object_key == 'test_configs/metrics.json'
