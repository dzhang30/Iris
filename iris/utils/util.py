import json
import os
from configparser import ConfigParser
from logging import Logger
from typing import Dict, List, Set, Tuple, Any


def read_config_file(config_path: str, logger: Logger = None) -> ConfigParser:
    """
    Read the config file (.ini, .cfg, or similar format)

    :param config_path: path to the config file
    :param logger: logger for forensics
    :return: a ConfigParser object that contains the sections of the config file
    """
    config = ConfigParser()
    file_read = config.read(config_path)

    if not file_read:
        err_msg = 'Could not open/read the config file: {0}'.format(config_path)
        if logger:
            logger.error(err_msg)

        raise OSError(err_msg)

    return config


def check_file_exists(file_path: str, file_type: str, logger: Logger) -> bool:
    """
    Check if the file exists. Logs an ERROR if the file_type is aws_credentials, else it will just be a WARNING

    :param file_path: path to the file we want to check
    :param file_type: type of the file (ie aws_credentials, upload_file, etc). Check the usage of this function
    :param logger: logger for forensics
    :return: True if exists, else False
    """
    if not os.path.isfile(file_path):
        err_msg = 'The {} file path {} does not exist or is incorrect. Check the path'.format(file_type, file_path)
        if file_type == 'aws_credentials':
            logger.error(err_msg)
        else:
            logger.warning(err_msg)
        raise OSError(err_msg)

    return True


def check_dir_exists(dir_path: str, dir_type: str, logger: Logger) -> bool:
    """
    Check if the directory exists

    :param dir_path: path to the dir we want to check
    :param dir_type: type of the dir (ie profile_configs, upload, etc). Check the usage of this function
    :param logger: logger for forensics
    :return: True if exists, else False
    """
    if not os.path.isdir(dir_path):
        err_msg = 'The {} directory path {} does not exist or is incorrect. Check the path'.format(dir_type, dir_path)
        logger.error(err_msg)
        raise OSError(err_msg)

    return True


def detect_list_duplicates(items: List[Any], item_description: str, logger: Logger) -> List[Any]:
    """
    Detect if there are duplicates in the list. Used in configs.py and linter.py

    :param items: the list we want to check
    :param item_description: the type of items we are checking (ie config file names, profile names, etc). Check usage
    :param logger: logger for forensics
    :return: an empty list if there are no duplicates. Else logs the duplicates and raises ValueError
    """
    duplicate_items = []
    unique_items: Set = set()

    for item in items:
        if item in unique_items:
            duplicate_items.append(item)
        unique_items.add(item)

    if duplicate_items:
        err_msg = 'There are duplicate {}: {}'.format(item_description, ', '.format(duplicate_items))
        logger.error(err_msg)
        raise ValueError(err_msg)

    return duplicate_items


def load_json_config(config_path: str, config_type: str, logger: Logger) -> Dict[str, Any]:
    """
    Load the specified json config. Used heavily by linter.py

    :param config_path: path to the json file
    :param config_type: type of json file (ie profile, metric, etc)
    :param logger: logger for forensics
    :return: a dict representing the json file
    """
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
    """
    Helper method for load_json_config. This detects if there are duplicate keys in the json file we are trying to load

    :param pairs: a list of tuples (key, val) of the json file
    :return: a dict containing the key, val pair of each json file object. Raises a ValueError if there are duplicate
    keys
    """
    config_json: Dict = {}

    for key, val in pairs:
        if key in config_json:
            raise ValueError('The json file has duplicate keys: {0}'.format(key))
        config_json[key] = val

    return config_json
