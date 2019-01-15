import os
from dataclasses import dataclass
from logging import Logger
from shutil import rmtree
from typing import List

import boto3


@dataclass
class S3:
    bucket_name: str
    aws_profile_name: str
    logger: Logger
    region_name: str = 'us-east-1'

    def __post_init__(self) -> None:
        s3 = boto3.Session(profile_name=self.aws_profile_name, region_name=self.region_name).resource('s3')
        self._bucket = s3.Bucket(self.bucket_name)

    def download_bucket(self, download_path: str) -> List[str]:
        if os.path.isdir(download_path):  # clear the old download directory on each run
            rmtree(download_path)

        downloaded_files = []
        for object_ in self._bucket.objects.all():
            downloaded_files.append(object_.key)
            obj_dir_path = '/'.join(object_.key.split('/')[:-1])

            os.makedirs(os.path.join(download_path, obj_dir_path), exist_ok=True)  # won't make dir if it already exists

            self._bucket.download_file(object_.key, os.path.join(download_path, object_.key))

        self.logger.info('Downloaded {} files. Files: {}.'.format(len(downloaded_files), downloaded_files))

        return downloaded_files

    def upload_object(self, object_path: str) -> str:
        if not os.path.isfile(object_path):
            err_msg = 'Could not upload the file {}. Check if the path is correct'.format(object_path)
            self.logger.error('ValueError: {}'.format(err_msg))
            raise ValueError(err_msg)

        object_key = object_path.rsplit('/')[-1]
        self._bucket.upload_file(object_path, object_key)

        self.logger.info('Uploaded file object: {}'.format(object_key))

        return object_key

    def upload_directory(self, object_path: str) -> List[str]:
        if not os.path.isdir(object_path):
            err_msg = 'Could not upload the directory {}. Check if the path is correct'.format(object_path)
            self.logger.error('ValueError: {}'.format(err_msg))
            raise ValueError(err_msg)

        if object_path[-1] != '/':
            object_path += '/'

        result = []
        for dir_path, _, files in os.walk(object_path):
            for file_ in files:
                object_key = self._create_object_key(dir_path, object_path, file_)
                self._bucket.upload_file(os.path.join(dir_path, file_), object_key)

                result.append(object_key)

        self.logger.info('Uploaded directory: {} with content: {}'.format(object_path, result))

        return result

    @staticmethod
    def _create_object_key(dir_path: str, object_path: str, object_file: str) -> str:
        object_dir = dir_path.replace(object_path, '')
        return '{}/{}'.format(object_dir, object_file) if object_dir else object_file
