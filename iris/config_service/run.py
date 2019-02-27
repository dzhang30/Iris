import json
import logging
import os
import tempfile
import time

from iris.config_service.aws.ec2_tags import EC2Tags, MissingIrisTagsError
from iris.config_service.aws.s3 import S3
from iris.config_service.config_lint.linter import Linter
from iris.utils.prom_helpers import PromStrBuilder, PromFileWriter

logger = logging.getLogger('iris.config_service')


def run_config_service(aws_creds_path: str, s3_region_name: str, s3_bucket_env: str, s3_bucket_name: str,
                       s3_download_to_path: str, ec2_region_name: str, ec2_dev_instance_id: str, ec2_metadata_url: str,
                       local_config_path: str, prom_dir_path: str, run_frequency: float, dev_mode: bool) -> None:
    general_error_flag = False
    missing_iris_tags_error_flag = False
    while True:
        # Run config service S3 puller to get the config files from iris bucket
        try:
            logger.info('Resuming the Config_Service')

            logger.info('Downloading content from s3 bucket: {} to dir: {}'.format(s3_bucket_name, s3_download_to_path))

            s3 = S3(
                aws_creds_path=aws_creds_path,
                region_name=s3_region_name,
                bucket_environment=s3_bucket_env,
                bucket_name=s3_bucket_name,
                dev_mode=dev_mode,
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
                dev_instance_id=ec2_dev_instance_id,
                dev_mode=dev_mode,
                logger=logger
            )

            ec2_iris_tags = ec2.get_iris_tags()

            # use iris_tags and downloaded s3 configs to generate the local_config object
            logger.info('Matching retrieved iris_tags with the downloaded configs to generate the local_config obj')

            iris_profile = ec2_iris_tags['ihr:iris:profile']
            if iris_profile not in profiles:
                err_msg = 'The ihr:iris:profile tag on {} is not defined in any profile config'.format(ec2.instance_id)
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

            with tempfile.NamedTemporaryFile('w', delete=False) as tmpfile:
                json.dump(local_config_metrics, tmpfile, indent=2)
            os.rename(tmpfile.name, local_config_path)

            logger.info('Finished writing to local_config file at {}'.format(local_config_path))

            general_error_flag = False
            missing_iris_tags_error_flag = False

        except MissingIrisTagsError as e:
            logger.error('Config_Service MissingIrisTagsError: {}'.format(e))
            missing_iris_tags_error_flag = True

        # will log twice for defined err logs in iris, but will catch & log unlogged errs in code (3rd party err)
        except Exception as e:
            logger.error('Config_Service has an err: {}'.format(e))
            general_error_flag = True

        finally:
            general_error_name = 'iris_config_service_error'
            general_error_prom_builder = PromStrBuilder(
                metric_name=general_error_name,
                metric_result=int(general_error_flag),
                help_str='Indicate if a general exception/error has occured in the Scheduler',
                type_str='gauge'
            )
            general_error_prom_string = general_error_prom_builder.create_prom_string()
            general_error_prom_file_path = os.path.join(prom_dir_path, '{}.prom'.format(general_error_name))

            missing_iris_tags_name = 'iris_missing_ec2_tags'
            missing_iris_tags_prom_builder = PromStrBuilder(
                metric_name=missing_iris_tags_name,
                metric_result=int(missing_iris_tags_error_flag),
                help_str='Indicate if the ec2 host is missing the iris tags',
                type_str='gauge'
            )
            missing_iris_tags_prom_string = missing_iris_tags_prom_builder.create_prom_string()
            missing_iris_tags_prom_file_path = os.path.join(prom_dir_path, '{}.prom'.format(missing_iris_tags_name))

            prom_writer = PromFileWriter(logger=logger)
            prom_writer.write_prom_file(general_error_prom_file_path, general_error_prom_string)
            prom_writer.write_prom_file(missing_iris_tags_prom_file_path, missing_iris_tags_prom_string)

            logger.info('Sleeping the Config_Service for {}\n'.format(run_frequency))

            time.sleep(run_frequency)