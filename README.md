# tox-gh-actions
[![PyPI version](https://badge.fury.io/py/tox-gh-actions.svg)](https://badge.fury.io/py/tox-gh-actions)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/tox-gh-actions.svg)](https://pypi.python.org/pypi/tox-gh-actions/)
[![GitHub license](https://img.shields.io/github/license/ymyzk/tox-gh-actions)](https://github.com/ymyzk/tox-gh-actions/blob/master/LICENSE)
[![GitHub Actions (Tests)](https://github.com/ymyzk/tox-gh-actions/workflows/Tests/badge.svg)](https://github.com/ymyzk/tox-gh-actions)

**tox-gh-actions** is a tox plugin which helps running tox on GitHub Actions
with multiple different Python versions.  This project is inspired by
[tox-travis](https://github.com/tox-dev/tox-travis).

## Usage
1. Add configurations under `[gh-actions]` section along with tox's configuration.
   - It will be `pyproject.toml`, `tox.ini`, or `setup.cfg`. See [tox's documentation](https://tox.readthedocs.io/en/latest/config.html) for more details.

2. Install `tox-gh-actions` package in the GitHub Actions workflow before running `tox` command.

## Examples
### Basic Example
The following configuration will create 4 jobs when running the workflow on GitHub Actions.
- On Python 2.7 job, tox runs `py27` environment
- On Python 3.6 job, tox runs `py36` environment
- On Python 3.7 job, tox runs `py37` environment
- On Python 3.8 job, tox runs `py38` and `mypy` environments

#### tox-gh-actions Configuration
Add `[gh-actions]` section to the same file as tox's cofiguration.

If you're using `tox.ini`:
```ini
[tox]
envlist = py27, py36, py37, py38, mypy

[gh-actions]
python =
    2.7: py27
    3.6: py36
    3.7: py37
    3.8: py38, mypy

[testenv]
...
```

If you're using `setup.cfg`:
```ini
[tox:tox]
envlist = py27, py36, py37, py38, mypy

[gh-actions]
python =
    2.7: py27
    3.6: py36
    3.7: py37
    3.8: py38, mypy

[testenv]
...
```

If you're using `pyproject.toml`:
```toml
[tool.tox]
legacy_tox_ini = """
[tox]
envlist = py27, py36, py37, py38, mypy

[gh-actions]
python =
    2.7: py27
    3.6: py36
    3.7: py37
    3.8: py38, mypy

[testenv]
"""
```

#### Workflow Configuration
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
        python-version: [2.7, 3.6, 3.7, 3.8]

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

### Advanced Example
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

PyPy is also supported in the `python` configuration key.

 `tox.ini`:
```ini
[tox]
envlist = py27, py38, pypy2, pypy3

[gh-actions]
python =
    2.7: py27
    3.8: py38, mypy
    pypy2: pypy2
    pypy3: pypy3

[testenv]
...
```

You can also use environment variable to decide which environment to run.
The following is an example to install different dependency based on platform.
It will create 12 jobs when running the workflow on GitHub Actions.
- On Python 2.7/ubuntu-latest job, tox runs `py27-linux` environment
- On Python 3.5/ubuntu-latest job, tox runs `py35-linux` environment
- and so on.

`.github/workflows/<workflow>.yml`:
```yaml
name: Python package

on: [push]

jobs:
  build:
    runs-on: ${{ matrix.platform }}
    strategy:
      max-parallel: 4
      matrix:
        platform: [ubuntu-latest, macos-latest, windows-latest]
        python-version: [2.7, 3.6, 3.7, 3.8]

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
      env:
        PLATFORM: ${{ matrix.platform }}
```

`tox.ini`:
```ini
[tox]
envlist = py{27,36,37,38}-{linux,macos,windows}

[gh-actions]
python =
    2.7: py27
    3.8: py38, mypy
    pypy2: pypy2
    pypy3: pypy3

[gh-actions:env]
PLATFORM =
    ubuntu-latest: linux
    macos-latest: macos
    windows-latest: windows

[testenv]
deps =
  <common dependency>
  linux: <Linux specific deps>
  macos: <macOS specific deps>
  windows: <Windows specific deps>
...
```

See [tox's documentation about factor-conditional settings](https://tox.readthedocs.io/en/latest/config.html#factors-and-factor-conditional-settings) as well.

