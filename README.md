# tox-gh-actions
[![PyPI version](https://badge.fury.io/py/tox-gh-actions.svg)](https://badge.fury.io/py/tox-gh-actions)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/tox-gh-actions.svg)](https://pypi.python.org/pypi/tox-gh-actions/)
[![GitHub license](https://img.shields.io/github/license/ymyzk/tox-gh-actions)](https://github.com/ymyzk/tox-gh-actions/blob/master/LICENSE)
[![GitHub Actions (Tests)](https://github.com/ymyzk/tox-gh-actions/workflows/Tests/badge.svg)](https://github.com/ymyzk/tox-gh-actions)

**tox-gh-actions** is a tox plugin which helps running tox on GitHub Actions
with multiple different Python versions.  This project is inspired by
[tox-travis](https://github.com/tox-dev/tox-travis).

## Usage
The following configuration will create 4 jobs when running the workflow on GitHub Actions.
- On Python 2.7 job, tox runs `py27` environment
- On Python 3.5 job, tox runs `py35` environment
- On Python 3.6 job, tox runs `py36` environment
- On Python 3.7 job, tox runs `py37` and `mypy` environments

`tox.ini`:
```ini
[tox]
envlist = py27, py35, py36, py37, mypy

[gh-actions]
python =
    2.7: py27
    3.5: py35
    3.6: py36
    3.7: py37, mypy

[testenv]
...
```

`.github/workflows/<workflow>.yml`:
```yaml
name: Python package

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      max-parallel: 4
      matrix:
        python-version: [2.7, 3.5, 3.6, 3.7]

    steps:
    - uses: actions/checkout@v1
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v1
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install tox tox-gh-actions
    - name: Test with tox
      run: tox
```

## Advanced Usage
The following configuration will create 2 jobs when running the workflow on GitHub Actions.
- On Python 2.7 job, tox runs `py27-django111` environment
- On Python 3.7 job, tox runs `py37-django111` and `py37-django20` environments

`tox.ini`:
```ini
[tox]
envlist = py27-django{111}, py37-django{111,20}

[gh-actions]
python =
    2.7: py27
    3.7: py37

[testenv]
...
```
