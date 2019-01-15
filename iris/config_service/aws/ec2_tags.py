import os
from configparser import ConfigParser
from dataclasses import dataclass
from logging import Logger
from typing import List, Dict

import boto3
import requests
from botocore.exceptions import ClientError


@dataclass
class EC2Tags:
    logger: Logger
    region_name: str = 'us-east-1'
    instance_id: str = 'i-379f14b7'  # hardcoding stg-tvclient101's instance_id until we figure out how to provision

    ec2_metadata_url = 'http://169.254.169.254/latest/meta-data/'

    def get_iris_tags(self) -> Dict[str, str]:
        instance_tags: List = []
        ec2_error = ClientError({}, '')

        profiles = self._get_aws_profiles()
        for profile in profiles:  # we must loop through each profile as a host won't know what profile it's in
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
            new_err_msg = '{0}. Could not find the instance in any defined aws profiles {1}'.format(err_msg, profiles)
            self.logger.error(ec2_error)
            raise ClientError({'Error': {'Code': err_code, 'Message': new_err_msg}}, ec2_error.operation_name)

        iris_tags = self._extract_iris_tags(instance_tags)

        self.logger.info('Retrieved iris_tags: {}'.format(iris_tags))

        return iris_tags

    def _get_aws_profiles(self) -> List[str]:
        aws_credentials_path = os.getenv('AWS_SHARED_CREDENTIALS_FILE')

        config = ConfigParser()
        file_read = config.read(aws_credentials_path)  # type: ignore
        if not file_read:
            err_msg = 'Could not open/read the aws credentials file: {0}'.format(aws_credentials_path)
            self.logger.error(err_msg)
            raise OSError(err_msg)

        return config.sections()

    def _extract_iris_tags(self, instance_tags: List) -> Dict[str, str]:
        iris_tags = {}
        for tag in instance_tags:
            if tag['Key'] == 'ihr:iris:profile':
                iris_tags['ihr:iris:profile'] = tag['Value']
            if tag['Key'] == 'ihr:iris:enabled':
                iris_tags['ihr:iris:enabled'] = tag['Value']

        if 'ihr:iris:profile' not in iris_tags or 'ihr:iris:enabled' not in iris_tags:
            err_msg = 'Instance {} does not have both iris tags ihr:iris:profile & ihr:iris:enabled. It only has {}'. \
                format(self.instance_id, iris_tags)
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
