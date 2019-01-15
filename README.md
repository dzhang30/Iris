# Iris
There is a need to capture metrics beyond the basics of what are provided by the Prometheus Node Exporter installed on all hosts. Additional metrics may be related to the application running on a specific host or hosts, specialized system checks beyond the scope of the node exporter, or other metrics that will replace Nagios or CheckMK.

## One-Time Setup
These steps will install the pre-requisites for running iris on your local machine. 

* Install `brew` and `python 3.7`
* Setup your virtualenv using `direnv`

```bash
# Install Homebrew
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

# Make sure both direnv and python3 are installed
brew install direnv python3

# Run this to enable, add to .profile or .zshrc to make permanent
eval "$(direnv hook $SHELL)"  
```

## Installing Custom Metrics

* Checkout iris repo from github
* Install iris into your virtual environment

```bash
git clone git@github.com:iheartradio/iris.git
cd iris

# Enable direnv in this project folder
direnv allow

# Make sure a new version of pip is installed
pip install --upgrade pip setuptools

# Install project dependencies
python setup.py install

```

## Testing, Linting, Type Checking and Coverage
We use `Tox` to automate and run our testing environment. This includes running `coverage`, `pytest` via setup.py test, `mypy` for type checking, and `flake8` for linting  

```bash
tox
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
