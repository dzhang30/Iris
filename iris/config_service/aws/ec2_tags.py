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
    """
    The EC2Tags class is responsible for querying the specific Iris tags on the host that's currently running Iris

    :param aws_creds_path: path to the aws_credentials file
    :param region_name: region that the ec2 instance is in
    :param ec2_metadata_url: the metadata url that allows the instance to get info of itself, defined in iris.cfg
    :param dev_mode: set to True when you want to run in dev mode, see readme & iris.cfg
    :param dev_instance_id: the instance id of the host you want to test in dev mode, see readme & iris.cfg. This
    field is not set by default in iris.cfg when running on a host. It must be manually set by the tester
    :param logger: logger for forensics
    """
    aws_creds_path: str
    region_name: str
    ec2_metadata_url: str
    dev_mode: bool
    dev_instance_id: str
    logger: Logger

    def __post_init__(self) -> None:
        """
        Check if the aws_creds_file exists and set the AWS_SHARED_CREDENTIALS_FILE env variable. Retrieve the current
        ec2 host's instance id. If running in dev_mode, then retrieve the ec2 instance id defined in the
        ec2_dev_instance_id field in iris.cfg

        :return: None
        """
        util.check_file_exists(file_path=self.aws_creds_path, file_type='aws_credentials', logger=self.logger)

        os.environ['AWS_SHARED_CREDENTIALS_FILE'] = self.aws_creds_path

        if self.dev_mode:
            self.instance_id = self.dev_instance_id  # local dev mode will use the instance id specified in iris.cfg
        else:
            self.instance_id = self._request_instance_id()

    def get_iris_tags(self) -> Dict[str, str]:
        """
        Retrieve the iris tags on the current host running Iris
        We have defined the iris tags to be:
        ihr:iris:profile
        ihr:iris:enabled

        :return: a dict containing tags for iris to determine which profile config it needs to run (if any)
        """
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
        """
        Helper method to for get_iris_tags to extract the defined iris tags

        :param instance_tags: a list of the tags on the current ec2 host returned by boto3
        :return: a dict containing tags for iris to determine which profile config it needs to run (if any)
        """
        iris_tags = {}
        for tag in instance_tags:
            if tag['Key'] == 'ihr:iris:profile':
                iris_tags['ihr:iris:profile'] = tag['Value']
            if tag['Key'] == 'ihr:iris:enabled':
                iris_tags['ihr:iris:enabled'] = tag['Value']

        if 'ihr:iris:profile' not in iris_tags or 'ihr:iris:enabled' not in iris_tags:
            err_msg_format = 'Instance {} does not have tags ihr:iris:profile & ihr:iris:enabled. It only has {}'
            err_msg = err_msg_format.format(self.instance_id, iris_tags)
            self.logger.error(err_msg)
            raise MissingIrisTagsError(err_msg)

        return iris_tags

    def _request_instance_id(self) -> str:
        """
        Get the instance id of the current ec2 host by utilizing the ec2_metadata_url, the url is defined in iris.cfg

        :return: the instance id of the ec2 host
        """
        instance_id_url = '{0}/instance-id'.format(self.ec2_metadata_url)
        try:
            return requests.get(instance_id_url).text
        except requests.ConnectionError as e:
            err_msg = 'Could not retrieve this host\'s instance id from url: {0}. Error: {1}'.format(instance_id_url, e)
            self.logger.error(err_msg)
            raise requests.ConnectionError(err_msg)


class MissingIrisTagsError(KeyError):
    """
    Specific Exception thrown when ec2 host running Iris doesn't have the necessary tags
    """
    pass


class IrisNotEnabledException(Exception):
    """
    Specific Exception for when the ihr:iris:enabled is set to False
    """
    pass
