from setuptools import setup

requires = [
    'aiofiles==0.4.0',
    'boto3==1.9.66',
    'coverage==4.5.2',
    'flake8==3.6.0',
    'flake8-import-order==0.18',
    'mypy==0.641',
    'pytest==3.10.0',
    'pytest-asyncio==0.9.0',
    'requests==2.20.1',
]

test_requirements = [
    'mock',
    'pytest'
]

setup(
    package_dir={'': 'iris'},
    install_requires=requires,
    zip_safe=False,
    tests_require=test_requirements,
    setup_requires=['pytest-runner'],
)
