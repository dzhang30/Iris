import inspect
import os
import sys

# set python project  paths to import iris module
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
project_root_dir = os.path.dirname(current_dir)
sys.path.insert(0, project_root_dir)

from scripts.util import get_script_logger  # noqa: E402
from iris.utils import util  # noqa: I201
from iris.utils import main_helpers  # noqa: E402
from iris.config_service.aws.s3 import S3  # noqa: E402

logger = get_script_logger('download_configs_script')

if __name__ == '__main__':
    try:
        logger.info('Running download_configs script for local development')

        script_settings = util.read_config_file(os.path.join(project_root_dir, 'iris.cfg'), logger)
        main_helpers.check_iris_test_settings(script_settings, logger)

        iris_root_path = script_settings['main_settings']['iris_root_path']
        aws_creds_path = os.path.join(iris_root_path, 'aws_credentials')
        s3_download_path = os.path.join(iris_root_path, 'downloads')

        # S3 settings:
        region_name = script_settings['config_service_settings']['s3_region_name']
        bucket_env = script_settings['config_service_settings']['s3_bucket_env']
        bucket_name = script_settings['config_service_settings']['s3_bucket_name']

        logger.info('Downloading content from s3 bucket: {} to dir: {}'.format(bucket_name, s3_download_path))

        s3 = S3(
            aws_creds_path=aws_creds_path,
            region_name=region_name,
            bucket_environment=bucket_env,
            bucket_name=bucket_name,
            dev_mode=True,
            logger=logger
        )
        s3.download_bucket(s3_download_path)

        logger.info('You can now edit the metrics.json & profiles/*.json in {}. Check README'.format(s3_download_path))

    except KeyError as e:
        err_msg = 'Make sure the proper fields are set in iris.cfg. Err: {}'.format(e)
        logger.error('KeyError: {}'.format(err_msg))

    finally:
        logger.info('Finished running downloads_configs script')
