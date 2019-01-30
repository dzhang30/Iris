#!/usr/bin/env bash
# This file is used to clean up any directories created by running Pyinstaller and the binary program it produces
rm -rf dist
rm -rf build
rm -rf logs
rm -rf prom_files
rm -rf local_config.json
rm -rf downloads
rm -rf main.spec