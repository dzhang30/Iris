from setuptools import setup

requires = [
    'aiofiles==0.4.0',
    'atomicwrites==1.2.1',
    'attrs==18.2.0',
    'boto3==1.9.66',
    'botocore==1.12.66',
    'certifi==2022.12.7',
    'chardet==3.0.4',
    'coverage==4.5.2',
    'docutils==0.14',
    'filelock==3.0.10',
    'flake8==3.6.0',
    'flake8-import-order==0.18',
    'idna==2.7',
    'jmespath==0.9.3',
    'lockfile==0.12.2',
    'mccabe==0.6.1',
    'more-itertools==4.3.0',
    'mypy==0.641',
    'mypy-extensions==0.4.1',
    'pluggy==0.8.0',
    'py==1.7.0',
    'pycodestyle==2.4.0',
    'pyflakes==2.0.0',
    'pyinstaller==3.4',
    'pytest==3.10.0',
    'pytest-asyncio==0.9.0',
    'pytest-mock==1.10.1',
    'python-daemon==2.2.0',
    'python-dateutil==2.7.5',
    'requests==2.21.0',
    's3transfer==0.1.13',
    'six==1.11.0',
    'toml==0.10.0',
    'tox==3.6.0',
    'typed-ast==1.1.0',
    'urllib3==1.23',
]

setup(
    package_dir={'': 'iris'},
    install_requires=requires,
    zip_safe=False,
    setup_requires=['pytest-runner'],
)
