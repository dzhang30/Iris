import json
import os
from logging import Logger
from typing import Dict, List, Set, Tuple, Any


def check_file_exists(file_path: str, file_type: str, logger: Logger) -> bool:
    if not os.path.isfile(file_path):
        err_msg = 'The {} file path {} does not exist or is incorrect. Check the path'.format(file_type, file_path)
        logger.error(err_msg)
        raise OSError(err_msg)

    return True


def check_dir_exists(dir_path: str, dir_type: str, logger: Logger) -> bool:
    if not os.path.isdir(dir_path):
        err_msg = 'The {} directory path {} does not exist or is incorrect. Check the path'.format(dir_type, dir_path)
        logger.error(err_msg)
        raise OSError(err_msg)

    return True


def find_list_duplicate(list_data: List[Any]) -> Any:
    unique_data: Set = set()
    for data in list_data:
        if data in unique_data:
            return data
        unique_data.add(data)

    return None


def load_json_config(config_path: str, config_type: str, logger: Logger) -> Dict[str, Any]:
    check_file_exists(file_path=config_path, file_type=config_type, logger=logger)

    try:
        with open(config_path, 'r') as stream:
            config_json = json.load(stream, object_pairs_hook=_detect_duplicate_json_keys)  # type: ignore
    except Exception as e:
        err_msg = 'Error loading the config file {0}. Err: {1}'.format(config_path, e)
        logger.error(err_msg)
        raise

    return config_json


def _detect_duplicate_json_keys(pairs: List[Tuple]) -> Dict[str, Any]:
    config_json: Dict = {}

    for key, val in pairs:
        if key in config_json:
            raise ValueError('The json file has duplicate keys: {0}'.format(key))
        config_json[key] = val

    return config_json
