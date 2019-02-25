import inspect
import os
import sys

# set python project  paths to import iris module
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
project_root_dir = os.path.dirname(current_dir)
sys.path.insert(0, project_root_dir)

from iris.config_service.config_lint.linter import Linter  # noqa: E402
from scripts.util import get_script_logger  # noqa: E402
from iris.utils import util  # noqa: I201
from iris.utils import main_helpers  # noqa: E402
from iris.scheduler.scheduler import Scheduler  # noqa: E402

logger = get_script_logger('execute_metrics_script')

if __name__ == '__main__':
    try:
        logger.info('Running execute_metrics script for local development')

        script_settings = util.read_config_file(os.path.join(project_root_dir, 'iris.cfg'), logger)
        main_helpers.check_iris_test_settings(script_settings, logger)

        iris_root_path = script_settings['main_settings']['iris_root_path']
        local_config_path = os.path.join(iris_root_path, 'local_config.json')
        global_config_path = os.path.join(os.path.join(iris_root_path, 'downloads'), 'global_config.json')
        prom_dir_path = os.path.join(iris_root_path, 'prom_files')

        logger.info('Starting linter to transform the config files pulled down from S3 into python objects')

        linter = Linter(logger)

        global_config_obj = linter.lint_global_config(global_config_path)
        local_config_obj = linter.lint_metrics_config(global_config_obj, local_config_path)
        metrics_list = list(local_config_obj.values())

        logger.info('Executing metrics: {}'.format([metric.name for metric in metrics_list]))

        scheduler = Scheduler(metrics_list, prom_dir_path, logger=logger)
        scheduler.run()

    except KeyError:
        pass

    finally:
        logger.info('Finished running execute_metrics script')
