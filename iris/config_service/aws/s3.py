import os
from dataclasses import dataclass
from logging import Logger
from shutil import rmtree
from typing import List

import boto3

from iris.utils import util


@dataclass
class S3:
    aws_creds_path: str
    region_name: str
    bucket_environment: str
    bucket_name: str
    dev_mode: bool
    logger: Logger

    def __post_init__(self) -> None:
        """
        The S3 class pulls all of the necessary config files that Iris needs to run from the specified bucket

        :param aws_creds_path: path to the aws_credentials file
        :param region_name: region that the S3 bucket is in
        :param bucket_environment: the bucket_environment/aws_profile_name, is the env the bucket is in ie prod/nonprod
        :param bucket_name: the name of the bucket
        :param dev_mode: set to True when you want to run in dev mode, see readme & iris.cfg
        :param logger: logger for forensics
        :return:
        """
        util.check_file_exists(file_path=self.aws_creds_path, file_type='aws_credentials', logger=self.logger)

        os.environ['AWS_SHARED_CREDENTIALS_FILE'] = self.aws_creds_path

        s3 = boto3.Session(profile_name=self.bucket_environment, region_name=self.region_name).resource('s3')
        self._bucket = s3.Bucket(self.bucket_name)

    def download_bucket(self, download_path: str) -> List[str]:
        """
        Download the contents of the s3 bucket do download_path

        :param download_path: the path to download the bucket content/configs
        :return: a list containing the paths to each downloaded file
        """
        if os.path.isdir(download_path):
            if not self.dev_mode:  # clear the previous download directory on each prod run
                self.logger.info('Cleared the previous content in the downloads dir before pulling down new data')
                rmtree(download_path)
            else:  # do not clear the downloads directory in dev mode so you can run new test metrics and profiles
                msg = 'Dev_Mode run: not clearing the downloads dir {} so you can locally test new metrics/profiles'
                self.logger.info(msg.format(download_path))

        downloaded_files = []
        for object_ in self._bucket.objects.all():
            downloaded_files.append(object_.key)
            obj_dir_path = '/'.join(object_.key.split('/')[:-1])

            # make directories contained in s3 bucket. Won't make dirs if they already exists
            os.makedirs(os.path.join(download_path, obj_dir_path), exist_ok=True)

            self._bucket.download_file(object_.key, os.path.join(download_path, object_.key))

        self.logger.info('Downloaded {} files. Files: {}.'.format(len(downloaded_files), ', '.join(downloaded_files)))

        return downloaded_files

    def upload_object(self, upload_file_path: str) -> str:
        """
        Upload the file/object from upload_file_path to the S3 bucket (initialized when S3 class is created)

        :param upload_file_path: the path to the local file/object you want to upload
        :return: the S3 key name of the file/object that you want to upload
        """
        util.check_file_exists(file_path=upload_file_path, file_type='upload_file', logger=self.logger)

        object_key = upload_file_path.rsplit('/')[-1]
        self._bucket.upload_file(upload_file_path, object_key)

        self.logger.info('Uploaded file object: {}'.format(object_key))

        return object_key

    def upload_directory(self, upload_dir_path: str) -> List[str]:
        """
        Upload the directory from upload_dir_path to the S3 bucket

        :param upload_dir_path: the path to the local directory you want to upload
        :return: a list containing the S3 key names of the directory content that you want to upload
        """
        util.check_dir_exists(dir_path=upload_dir_path, dir_type='upload', logger=self.logger)

        if upload_dir_path[-1] != '/':
            upload_dir_path += '/'

        result = []
        for dir_path, _, files in os.walk(upload_dir_path):
            for file_ in files:
                object_key = self._create_object_key(dir_path, upload_dir_path, file_)
                self._bucket.upload_file(os.path.join(dir_path, file_), object_key)

                result.append(object_key)

        self.logger.info('Uploaded directory: {} with content: {}'.format(upload_dir_path, result))

        return result

    @staticmethod
    def _create_object_key(dir_path: str, upload_dir_path: str, object_file: str) -> str:
        """
        Helper method for upload_directory to create the S3 object key name of the file/object that you want to upload

        :param dir_path: the path to a child directory of the main directory that you want to upload
        :param object_file: the file name within the child directory
        :param upload_dir_path: the path to the main/parent directory that you want to upload
        :return: the S3 key name of the file/object that you want to upload
        """
        object_dir = dir_path.replace(upload_dir_path, '')
        return os.path.join(object_dir, object_file) if object_dir else object_file
