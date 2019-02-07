import json
import logging
import os
import time

from iris.config_service.aws.ec2_tags import EC2Tags
from iris.config_service.aws.s3 import S3
from iris.config_service.config_lint.linter import Linter

logger = logging.getLogger('iris.config_service')


def run_config_service(aws_creds_path: str, s3_region_name: str, s3_bucket_env: str, s3_bucket_name: str,
                       s3_download_to_path: str, ec2_region_name: str, ec2_dev_instance_id: str, ec2_metadata_url: str,
                       dev_mode: bool, local_config_path: str, run_frequency: float) -> None:
    # Run config service S3 puller to get the config files from iris bucket
    try:
        while True:
            logger.info('Starting Config_Service')

            logger.info('Downloading content from s3 bucket: {} to dir: {}'.format(s3_bucket_name, s3_download_to_path))

            s3 = S3(
                aws_creds_path=aws_creds_path,
                region_name=s3_region_name,
                bucket_environment=s3_bucket_env,
                bucket_name=s3_bucket_name,
                logger=logger
            )

            s3.download_bucket(s3_download_to_path)

            # run linter to transform downloaded s3 configs into Python objects. Also lints the configs for errors
            global_config_path = os.path.join(s3_download_to_path, 'global_config.json')
            metrics_config_path = os.path.join(s3_download_to_path, 'metrics.json')
            profile_configs_path = os.path.join(s3_download_to_path, 'profiles')

            logger.info('Starting linter to transform the downloaded configs into GlobalConfig, Metric, & Profile objs')
            linter = Linter(logger)

            logger.info('Linting Global Config file at {}'.format(global_config_path))
            global_config = linter.lint_global_config(global_config_path)

            logger.info('Linting Metrics Config file at {}'.format(metrics_config_path))
            metrics = linter.lint_metrics_config(global_config, metrics_config_path)

            logger.info('Linting Profile Configs file at {}'.format(profile_configs_path))
            profiles = linter.lint_profile_configs(profile_configs_path)

            # run EC2Tags to retrieve the iris_tags of the host
            logger.info('Retrieving current ec2 host iris_tags')

            ec2 = EC2Tags(
                aws_creds_path=aws_creds_path,
                region_name=ec2_region_name,
                ec2_metadata_url=ec2_metadata_url,
                dev_mode=dev_mode,
                dev_instance_id=ec2_dev_instance_id,
                logger=logger
            )

            ec2_iris_tags = ec2.get_iris_tags()

            # use iris_tags and downloaded s3 configs to generate the local_config object
            logger.info('Matching retrieved iris_tags with the downloaded configs to generate the local_config obj')

            iris_profile = ec2_iris_tags['ihr:iris:profile']
            if iris_profile not in profiles:
                err_msg = 'The ihr:iris:profile tag on {} is not defined in any profile configs'.format(ec2.instance_id)
                logger.error(err_msg)
                raise KeyError(err_msg)

            local_config_metrics = {}
            for prof_metric in profiles[iris_profile].metrics:
                if prof_metric not in metrics:
                    err_msg = 'Metric {} in profile {} not defined in metrics config'.format(prof_metric, iris_profile)
                    logger.error(err_msg)
                    raise KeyError(err_msg)

                local_config_metrics[prof_metric] = metrics[prof_metric].to_json()

            logger.info('Generated the local_config object')

            # write the local_config object to a file for the scheduler to use
            with open(local_config_path, 'w') as outfile:
                json.dump(local_config_metrics, outfile, indent=2)
                logger.info('Finished writing to local_config file at {}'.format(local_config_path))

            logger.info('Finished Config_Service\n')

            time.sleep(run_frequency)

    # will log twice for defined err logs in iris code, but will catch & log other unlogged errs in code (3rd party err)
    except Exception as e:
        logger.error(e)
        raise
