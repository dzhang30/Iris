import json
import logging
import os
import time

from iris.config_service.config_lint.linter import Linter
from iris.config_service.aws.s3 import S3
from iris.config_service.aws.ec2_tags import EC2Tags

logger = logging.getLogger('iris.config_service')


def run_config_service(aws_profile: str, bucket_name: str, upload_from_path: str, download_to_path: str,
                       local_config_path: str, aws_creds_path: str = None) -> None:
    # Run config service S3 puller to get the config files from iris bucket
    while True:
        logger.info('Starting Config_Service')

        if aws_creds_path:
            os.environ['AWS_SHARED_CREDENTIALS_FILE'] = aws_creds_path

        s3 = S3(bucket_name=bucket_name, aws_profile_name=aws_profile, logger=logger)

        logger.info('Uploading directory: {} to s3: {}'.format(upload_from_path, bucket_name))
        s3.upload_directory(upload_from_path)

        logger.info('Downloading bucket content from s3: {} to directory: {}'.format(bucket_name, download_to_path))
        s3.download_bucket(download_to_path)

        # Run linter to transform downloaded s3 configs into Python objects. Also lints the configs for errors
        logger.info('Starting linter to transform the downloaded configs into GlobalConfig, Metrics, & Profiles objs')
        linter = Linter(logger)
        global_config = linter.lint_global_config('{}/poc_global_config.json'.format(download_to_path))
        metrics = linter.lint_metrics_config(global_config, '{}/poc_metrics.json'.format(download_to_path))
        profiles = linter.lint_profile_configs('{}/profiles'.format(download_to_path))

        # Run EC2Tags to retrieve the iris_tags of the host
        logger.info('Retrieving current ec2 host iris_tags')
        ec2 = EC2Tags(logger=logger)
        ec2_iris_tags = ec2.get_iris_tags()
        iris_profile = ec2_iris_tags['ihr:iris:profile']

        # Use iris_tags and downloaded s3 configs to generate the local_config object
        logger.info('Matching retrieved iris_tags with the downloaded configs to generate the local_config object')
        if iris_profile not in profiles:
            err_msg = 'The ihr:iris:profile tag on {} is not defined in any profile configs'.format(ec2.instance_id)
            logger.error(err_msg)
            raise KeyError(err_msg)

        local_config_metrics = {}
        for profile_metric in profiles[iris_profile].metrics:
            if profile_metric not in metrics:
                err_msg = 'Metric {} in profile {} not defined in metrics config'.format(profile_metric, iris_profile)
                logger.error(err_msg)
                raise KeyError(err_msg)

            local_config_metrics[profile_metric] = metrics[profile_metric].to_json()

        logger.info('Generated the local_config object')

        # Write the local_config object to a file for the scheduler to use
        with open(local_config_path, 'w') as outfile:
            json.dump(local_config_metrics, outfile, indent=2)
            logger.info('Finished writing to local_config file at {}'.format(local_config_path))

        logger.info('Finished Config_Service\n')

        time.sleep(25)
