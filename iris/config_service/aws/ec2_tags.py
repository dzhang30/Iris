import os
from dataclasses import dataclass
from logging import Logger
from typing import List, Dict

import boto3
import requests
from botocore.exceptions import ClientError

from iris.utils import util


@dataclass
class EC2Tags:
    aws_creds_path: str
    region_name: str
    ec2_metadata_url: str
    dev_instance_id: str
    dev_mode: bool
    logger: Logger

    def __post_init__(self) -> None:
        util.check_file_exists(file_path=self.aws_creds_path, file_type='aws_credentials', logger=self.logger)

        os.environ['AWS_SHARED_CREDENTIALS_FILE'] = self.aws_creds_path

        if self.dev_mode:
            self.instance_id = self.dev_instance_id  # local dev mode will use the instance id specified in iris.cfg
        else:
            self.instance_id = self._request_instance_id()

    def get_iris_tags(self) -> Dict[str, str]:
        instance_tags: List = []
        ec2_error = ClientError({}, '')

        aws_creds_config = util.read_config_file(self.aws_creds_path, self.logger)
        profiles = aws_creds_config.sections()

        # try each profile name in the aws_credentials file as the host won't know it's own aws profile
        for profile in profiles:
            ec2 = boto3.Session(profile_name=profile, region_name=self.region_name).resource('ec2')
            try:
                instance_tags = ec2.Instance(self.instance_id).tags
                break
            except ClientError as ce:
                ec2_error = ce
                continue

        if not instance_tags:
            err_code = ec2_error.response['Error']['Code']
            err_msg = ec2_error.response['Error']['Message']
            new_err_msg = '{}. Can not find the instance in these aws profiles {}'.format(err_msg, ', '.join(profiles))
            self.logger.error(new_err_msg)
            raise ClientError({'Error': {'Code': err_code, 'Message': new_err_msg}}, ec2_error.operation_name)

        iris_tags = self._extract_iris_tags(instance_tags)

        self.logger.info('Retrieved iris_tags: {}'.format(iris_tags))

        return iris_tags

    def _extract_iris_tags(self, instance_tags: List) -> Dict[str, str]:
        iris_tags = {}
        for tag in instance_tags:
            if tag['Key'] == 'ihr:iris:profile':
                iris_tags['ihr:iris:profile'] = tag['Value']
            if tag['Key'] == 'ihr:iris:enabled':
                iris_tags['ihr:iris:enabled'] = tag['Value']
            if tag['Key'] == 'ihr:application:environment':
                iris_tags['ihr:application:environment'] = tag['Value']
            if tag['Key'] == 'Name':
                iris_tags['name'] = tag['Value']

        if 'ihr:iris:profile' not in iris_tags or 'ihr:iris:enabled' not in iris_tags:
            err_msg_format = 'Instance {} does not have tags ihr:iris:profile & ihr:iris:enabled. It only has {}'
            err_msg = err_msg_format.format(self.instance_id, iris_tags)
            self.logger.error(err_msg)
            raise MissingIrisTagsError(err_msg)

        return iris_tags

    def _request_instance_id(self) -> str:
        instance_id_url = '{0}/instance-id'.format(self.ec2_metadata_url)
        try:
            return requests.get(instance_id_url).text
        except requests.ConnectionError as e:
            err_msg = 'Could not retrieve this host\'s instance id from url: {0}. Error: {1}'.format(instance_id_url, e)
            self.logger.error(err_msg)
            raise requests.ConnectionError(err_msg)


class MissingIrisTagsError(KeyError):
    pass
