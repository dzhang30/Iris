# Design Doc                     
https://docs.google.com/document/d/1xIBwOCU0p7NjxlX5_Y98w9nitYV5z7rnCT491lMl-QE/edit?usp=sharing

# Iris
There is a need to capture metrics beyond the basics of what are provided by the Prometheus Node Exporter installed on all hosts. Additional metrics may be related to the application running on a specific host or hosts, specialized system checks beyond the scope of the node exporter, or other metrics that will replace Nagios or CheckMK.

## One-Time Setup 
Install `brew` and `python 3.7` (based on your setup, you might have to specify python version in the command line)

These steps will install the pre-requisites for running iris on your local machine.

```bash
# Install Homebrew
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

# Make sure python3 (3.7) is installed
brew install python3

python3 --version

which python3.7

```

## Installing Iris

* Checkout iris repo from github
* Install iris into your virtual environment

```bash
git clone git@github.com:XXX/iris.git
cd iris

# Create a venv directory to hold our virtual environment. Point it to python3.7
virtualenv venv --python=python3.7

# Activate the virtual environment so we can download the dependencies into it
source venv/bin/activate 

# Make sure a new version of pip is installed
pip install --upgrade pip setuptools

# Download the dependencies
python setup.py install

```

## Local Development and Testing

By default, Iris will download and create all dependent files to the `/opt/iris` directory specified by the `iris_root_path` field in `iris.cfg` 

To run and test the Iris code locally:
* open `iris.cfg` 
    * set `dev_mode = true`
    * set `ec2_dev_instance_id` field to the instance id of the ec2 host you want to test on 
        * this will direct boto3 EC2 API calls to point at the specified host
* run the `scripts/download_configs.py` file to pull down the current configs for iris. They will be located in `/opt/iris/downloads`
    ```
    sudo python scripts/download_configs.py
    ```
* create new test metrics or edit existing ones in  `/opt/iris/downloads/metrics.json`
    * add your test metric to `metrics.json` in the following format
    ```
    # metrics.json
    {
      "node_logged_in_users": {
        "help": "The number of users currently logged into the node",
        "metric_type": "gauge",
        "execution_frequency": 30,
        "bash_command": "who | wc -l",
        "export_method": "textfile"
      },
      "node_running_processes": {
        "help": "The number of running processes on the node",
        "metric_type": "gauge",
        "execution_frequency": 20,
        "bash_command": "ps ax | wc -l",
        "export_method": "textfile"
      },
      ...
      ...
      "test_metric_1" : {
        "help": "test metric 1",
        "metric_type": "gauge",
        "execution_frequency": 27,
        "bash_command": "test command 1",
        "export_method": "textfile"
      },
      "test_metric_2" : {
        "help": "test metric 2",
        "metric_type": "gauge",
        "execution_frequency": 25,
        "bash_command": "test command 2",
        "export_method": "textfile"
      }
    }
    ```
* create a new profile config or edit an existing one in `/opt/iris/downloads/profiles/` for the test instance specified by the `ec2_dev_instance_id` field in `iris.cfg`
    * name the file after the host name (if `host_name = testclient101.net`, then name the file `testclient101.json`).
    * profile config file format:
    ```
    # test_instance_name.json
    {
        "profile_name": "test_instance_name",
        "metrics": [
            "node_logged_in_users",
            "node_running_processes",
            "test_metric_1",
            "test_metric_2",
        ]
    }
    ```
* create the iris tags for the ec2 instance you are testing on
    * add `xxx:iris:profile` tag and set it to the profile config name without the `.json` suffix
        * e.g. `xxx:iris:enabled = tvclient` for the `testclient101.net` host
    * add `xxx:iris:enabled = True`
  

Make sure that these requirements are fulfilled to complete testing:
* `tox` runs successfully (unit testing, linting, type checking, coverage)
* `pyinstaller` binary builds and runs successfully (check pyinstaller section)
* go back in `iris.cfg` and set `iris_mode = prod` and `iris_root_path = /opt/iris` before committing and deploying

## Unit Testing, Linting, Type Checking and Coverage
We use `Tox` to automate and run our testing environment. This includes running `coverage`, `pytest` via setup.py test, `mypy` for type checking, and `flake8` for linting  

```bash               
tox
```


## Creating Iris executable via Pyinstaller
We use `Pyinstaller` to transform Iris into an executable file that will run Iris as a daemon.
Use this as the final step to local testing by making sure the binary builds and runs correctly.

If you did not change the `iris_root_path = /opt/iris` in `iris.cfg`, then you will need to run the below commands with `sudo`. 


```bash
# Run Pyinstaller and set the path argument to include the virtual environment directory that holds all of Iris' dependencies
sudo pyinstaller --paths=venv/lib/python3.7/site-packages/ --add-data=iris.cfg:. --clean main.py

# Run Iris executable
sudo ./dist/main/main

# To rebuild the Iris executable, we first remove the directories it produced and then run the commands
sudo ./clean.sh
sudo pyinstaller --paths=venv/lib/python3.7/site-packages/ --add-data=iris.cfg:. --clean main.py
sudo ./dist/main/main
```

## Coding Standards
Code in the project should follow PEP8 standards, with the exception that lines can be up to 120 characters. The linter
will check this for you.

Please also add type hints/annotations to the code that you write (follows PEP 484 & PEP 526 standards, mypy will ensure this).

Guidelines:
1. All code that should be tested, is tested. Tests should be included in the same PR as your change. All tests should be written using pytest.
2. All code should be type hinted/annotated and checked with mypy
3. All methods should be documented. It should be clear the parameters expected, and what results a consumer might get.
4. All methods should return values. Avoid manipulation of parameters without explicitly returning the value.
5. Metric naming conventions: https://prometheus.io/docs/practices/naming/
