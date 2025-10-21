# tox-gh-actions <!-- omit in toc -->

[![PyPI version](https://badge.fury.io/py/tox-gh-actions.svg)](https://badge.fury.io/py/tox-gh-actions)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/tox-gh-actions.svg)](https://pypi.python.org/pypi/tox-gh-actions/)
[![GitHub Actions (Tests)](https://github.com/ymyzk/tox-gh-actions/actions/workflows/tests.yml/badge.svg)](https://github.com/ymyzk/tox-gh-actions/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/ymyzk/tox-gh-actions/branch/master/graph/badge.svg?token=7RWjRk2LkX)](https://codecov.io/gh/ymyzk/tox-gh-actions)

**tox-gh-actions** is a tox plugin which helps running tox on GitHub Actions
with multiple different Python versions on multiple workers in parallel.
This project is inspired by [tox-travis](https://github.com/tox-dev/tox-travis).

- [Features](#features)
- [Usage](#usage)
- [Examples](#examples)
  - [Basic Example](#basic-example)
    - [tox-gh-actions Configuration](#tox-gh-actions-configuration)
    - [Workflow Configuration](#workflow-configuration)
  - [Advanced Examples](#advanced-examples)
    - [Factor-Conditional Settings: Python Version](#factor-conditional-settings-python-version)
    - [Factor-Conditional Settings: Environment Variable](#factor-conditional-settings-environment-variable)
    - [tox requires](#tox-requires)
  - [Overriding Environments to Run](#overriding-environments-to-run)
- [Versioning](#versioning)
- [Versions and Compatibility](#versions-and-compatibility)
- [Understanding Behavior of tox-gh-actions](#understanding-behavior-of-tox-gh-actions)
  - [How tox-gh-actions Works](#how-tox-gh-actions-works)
  - [Logging](#logging)

## Features
When running tox on GitHub Actions, tox-gh-actions
* detects which environment to run based on configurations and
* provides utilities such as [grouping log lines](https://github.com/actions/toolkit/blob/main/docs/commands.md#group-and-ungroup-log-lines).

## Usage
1. Add configurations under `[gh-actions]` section along with tox's configuration.
   - It will be `pyproject.toml`, `tox.ini`, or `setup.cfg`. See [tox's documentation](https://tox.wiki/en/latest/config.html) for more details.

2. Install `tox-gh-actions` package in the GitHub Actions workflow before running `tox` command.

## Examples
### Basic Example
The following configuration will create 3 jobs when running the workflow on GitHub Actions.
- On Python 3.10 job, tox runs `py310` environment
- On Python 3.12 job, tox runs `py312` environment
- On Python 3.14 job, tox runs `py314` and `mypy` environments

#### tox-gh-actions Configuration
Add `[gh-actions]` section to the same file as tox's configuration.

If you're using `tox.ini`:
```ini
[tox]
envlist = py310, py312, py314, mypy

[gh-actions]
python =
    3.10: py310
    3.12: py312
    3.14: py314, mypy

[testenv]
...
```

If you're using `setup.cfg`:
```ini
[tox:tox]
envlist = py310, py312, py314, mypy

[gh-actions]
python =
    3.10: py310
    3.12: py312
    3.14: py314, mypy

[testenv]
...
```

If you're using `pyproject.toml`:
```toml
[tool.tox]
legacy_tox_ini = """
[tox]
envlist = py310, py312, py314, mypy

[gh-actions]
python =
    3.10: py310
    3.12: py312
    3.14: py314, mypy

[testenv]
"""
```

#### Workflow Configuration
`.github/workflows/<workflow>.yml`:
```yaml
name: Python package

on:
  - push
  - pull_request

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.12', '3.14']

    steps:
    - uses: actions/checkout@v5
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v6
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        python -m pip install tox tox-gh-actions
    - name: Test with tox
      run: tox
```

### Advanced Examples
#### Factor-Conditional Settings: Python Version
The following configuration will create 2 jobs when running the workflow on GitHub Actions.
- On Python 3.12 job, tox runs `py12-django42` environment
- On Python 3.13 job, tox runs `py313-django42`  and `py313-django52` environments

`tox.ini`:
```ini
[tox]
envlist = py312-django42, py313-django{42,52}

[gh-actions]
python =
    3.12: py312
    3.13: py313

[testenv]
...
```

When using pre-release versions of Python, please do not specify `-beta` or `-dev` in `tox.ini`.

`.github/workflows/<workflow>.yml`:
```yaml
...
jobs:
  build:
    strategy:
      matrix:
        python-version: [3.14, 3.15.0-beta.3]
...
```

`tox.ini`:
```ini
[tox]
envlist = py39, py310

[gh-actions]
python =
    3.14: py314
    3.15: py315
    # The following won't work
    # 3.15-beta.3: py315
    # 3.15-dev: py315

[testenv]
...
```

_Added in 3.5.0_: To use a free-threaded Python build, add the `t` suffix.

 `tox.ini`:
```ini
[tox]
envlist = py314, py314t

[gh-actions]
python =
    3.14: py314
    3.14t: py314t

[testenv]
...
```

PyPy is also supported in the `python` configuration key.
Support of Pyston is experimental and not tested by our CI.

 `tox.ini`:
```ini
[tox]
envlist = py313, py314, pypy3, pyston38

[gh-actions]
python =
    3.13: py313
    3.14: py314, mypy
    pypy-3.11: pypy3
    pyston-3.8: pyston38

[testenv]
...

[testenv:pyston38]
basepython = pyston38
```

You can also specify without minor versions in the `python` configuration key.

`tox.ini`:
```ini
[tox]
envlist = py3, pypy3

[gh-actions]
python =
    3: py3, mypy
    pypy-3: pypy3

[testenv]
...
```

If there are multiple matching Python versions in the configuration, only the most precise one is used.
For example, if you are running CPython 3.14 and `gh-actions.python` has both `3` and `3.14`,
tox-gh-actions gets factors only from the key `3.14`.

_Changed in 3.0_: `pypy3` is not supported in the configuration anymore. Please use `pypy-3` instead.

#### Factor-Conditional Settings: Environment Variable
You can also use environment variable to decide which environment to run.
The following is an example to install different dependency based on platform.
It will create 9 jobs when running the workflow on GitHub Actions.
- On Python 3.10/ubuntu-latest job, tox runs `py310-linux` environment
- On Python 3.12/ubuntu-latest job, tox runs `py312-linux` environment
- and so on.

`.github/workflows/<workflow>.yml`:
```yaml
name: Python package

on:
  - push
  - pull_request

jobs:
  build:
    runs-on: ${{ matrix.platform }}
    strategy:
      matrix:
        platform: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.10', '3.12', '3.14']

    steps:
    - uses: actions/checkout@v5
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v6
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        python -m pip install tox tox-gh-actions
    - name: Test with tox
      run: tox
      env:
        PLATFORM: ${{ matrix.platform }}
```

`tox.ini`:
```ini
[tox]
envlist = py{310,312,314}-{linux,macos,windows}

[gh-actions]
python =
    3.10: py310
    3.12: py312
    3.14: py3114

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

_Changed in 3.0_: Environment variables should not use lowercase letters.
Because of the limitation in tox's configuration loading API,
tox-gh-actions always convert keys in `[gh-actions:env]` to uppercase.

#### tox requires
If your project uses [tox's `requires` configuration](https://tox.wiki/en/latest/config.html#conf-requires),
you must add `tox-gh-actions` to the `requires` configuration as well. Otherwise, tox-gh-actions won't be loaded as a tox plugin.

```ini
[tox]
requires =
  tox-conda
  tox-gh-actions
```

### Overriding Environments to Run
_Changed in 2.0_: When a list of environments to run is specified explicitly via `-e` option or `TOXENV` environment variable ([tox's help](https://tox.wiki/en/latest/cli_interface.html#tox-run--e)),
tox-gh-actions respects the given environments and simply runs the given environments without enforcing its configuration.

Before 2.0, tox-gh-actions was always enforcing its configuration even when a list of environments is given explicitly.

## Versioning
This project follows [PEP 440](https://www.python.org/dev/peps/pep-0440/) and uses a format of major.minor.patch (X.Y.Z).
The major version (X) will be incremented when we make backward incompatible changes to a public API.
The public API of this project is the configuration of tox-gh-actions.
The major version can be also incremented when we require a new version of tox.

This project tries not to introduce backward incompatibles changes as much as possible so that users don't need to
update their project's configuration too frequently.

tox-gh-actions 3.x may drop support of unsupported Python 3.y versions in the future without bumping its major version.

## Versions and Compatibility
We recommend to use the latest version of tox 4.x and tox-gh-actions 3.x.
To use tox-gh-actions with tox 3.x, please install tox-gh-actions 2.x.
The following table shows compatibility between tox and tox-gh-actions.

| tox | tox-gh-actions | Supported by tox-gh-actions  | Branch                                                    |
|-----|----------------|------------------------------|-----------------------------------------------------------|
| 4.x | 3.x            | Yes (stable)                 | [master](https://github.com/ymyzk/tox-gh-actions)         |
| 3.x | 2.x            | Only security fixes (stable) | [tox3](https://github.com/ymyzk/tox-gh-actions/tree/tox3) |

## Understanding Behavior of tox-gh-actions
### How tox-gh-actions Works
See [ARCHITECTURE.md](./ARCHITECTURE.md) for more details.

### Logging
tox-gh-actions writes log messages using the standard `logging` module.
This is handy for understanding behavior of tox-gh-actions and for debugging tox-gh-actions.
To see the log messages, please run `tox -vv`.
