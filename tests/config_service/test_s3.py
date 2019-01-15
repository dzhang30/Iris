import logging
import os
import shutil
from collections import namedtuple
from unittest.mock import patch

import pytest

from iris.config_service.aws.s3 import S3

logger = logging.getLogger('iris.test')


@patch('iris.config_service.aws.s3.boto3')
def test_s3_download_bucket(mock_boto3):
    MockBucketObject = namedtuple('MockBucketObject', 'key')

    mock_boto3.Session.return_value.resource.return_value.Bucket.return_value.objects.all.return_value = [
        MockBucketObject('test_path/key1'), MockBucketObject('test_path/key2')]

    test_s3 = S3(bucket_name='test bucket', aws_profile_name='test profile', logger=logger)
    downloaded_files = test_s3.download_bucket('tests/config_service/test_download_directory')
    assert downloaded_files == ['test_path/key1', 'test_path/key2']

    # test download_bucket() is correctly creating directories (os.makedirs) to download s3 objects to
    assert os.path.isdir('tests/config_service/test_download_directory/test_path')

    shutil.rmtree('tests/config_service/test_download_directory')


@patch('iris.config_service.aws.s3.boto3')
def test_s3_upload_object(mock_boto3):
    mock_boto3.Session.return_value.resource.return_value.Bucket.return_value.upload_file.return_value = None

    test_s3 = S3(bucket_name='test bucket', aws_profile_name='test profile', logger=logger)
    object_key = test_s3.upload_object('tests/config_service/test_configs/correct_configs/poc_metrics.json')
    assert object_key == 'poc_metrics.json'

    invalid_path = 'tests/config_service/test_configs/invalid.py'
    with pytest.raises(ValueError) as file_doesnt_exist:
        test_s3.upload_object(invalid_path)
    assert 'Could not upload the file {}. Check if the path is correct'.format(invalid_path) == str(
        file_doesnt_exist.value)


@patch('iris.config_service.aws.s3.boto3')
def test_s3_upload_directory(mock_boto3):
    mock_boto3.Session.return_value.resource.return_value.Bucket.return_value.upload_file.return_value = None

    test_s3 = S3(bucket_name='test bucket', aws_profile_name='test profile', logger=logger)
    object_keys = test_s3.upload_directory('tests/config_service/test_configs/correct_configs/')
    assert set(object_keys) == {'poc_global_config.json', 'poc_metrics.json', 'profiles/poc_profile_0.json',
                                'profiles/poc_profile_1.json'}

    invalid_path = 'tests/config_service/test_configs/invalid/'
    with pytest.raises(ValueError) as directory_doesnt_exist:
        test_s3.upload_directory(invalid_path)
    assert 'Could not upload the directory {}. Check if the path is correct'.format(invalid_path) == str(
        directory_doesnt_exist.value)


def test_s3_create_object_key():
    object_key = S3._create_object_key('test/config_service/test_configs', 'test/config_service/', 'poc_metrics.json')
    assert 'test_configs/poc_metrics.json' == object_key
