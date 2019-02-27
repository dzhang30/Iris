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
        util.check_file_exists(file_path=self.aws_creds_path, file_type='aws_credentials', logger=self.logger)

        os.environ['AWS_SHARED_CREDENTIALS_FILE'] = self.aws_creds_path

        s3 = boto3.Session(profile_name=self.bucket_environment, region_name=self.region_name).resource('s3')
        self._bucket = s3.Bucket(self.bucket_name)

    def download_bucket(self, download_path: str) -> List[str]:
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
        util.check_file_exists(file_path=upload_file_path, file_type='upload_file', logger=self.logger)

        object_key = upload_file_path.rsplit('/')[-1]
        self._bucket.upload_file(upload_file_path, object_key)

        self.logger.info('Uploaded file object: {}'.format(object_key))

        return object_key

    def upload_directory(self, upload_dir_path: str) -> List[str]:
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
        object_dir = dir_path.replace(upload_dir_path, '')
        return os.path.join(object_dir, object_file) if object_dir else object_file
