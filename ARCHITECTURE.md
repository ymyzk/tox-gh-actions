# Architecture
This document describes the high-level architecture of tox-gh-actions.

## Overview
tox-gh-actions is implemented as [a plugin of tox](https://tox.readthedocs.io/en/latest/plugins.html).
When both tox and tox-gh-actions are installed, hooks defined by tox-gh-actions are automatically triggered by tox.

When tox-gh-actions is executed, it will run the following steps:
1. If tox is not running on GitHub Actions or a list of environments is explicitly given, tox-gh-actions won't do anything special.
2. Get a list of environments from `envlist` in the configuration file.
3. Pick environments to run in the current build based on the configuration in the `[gh-actions]` section.
4. Override `envlist` with the selected environments and tox will run them.

What's important here is that tox-gh-actions picks environments from `envlist` rather than
generating a new list of environments from the `[gh-actions]` configuration.
This design choice enables clear and easy to understand behavior of the plugin for users.

## Deciding Environments to Run
tox-gh-actions decides which environments to run based on Python version and/or environment variables.

### Python Version
Currently, tox-gh-actions assumes that Python version used for running tox is the Python version
users want to use when running tox environments. This should be a reasonable assumption as
users usually install only one Python version on each GitHub Actions job and run multiple jobs
in parallel.

### Using Factors to Decide Environments
tox-gh-actions decides which environments to run using factors. This is an example `tox.ini`:
```ini
[tox]
envlist = py{37,38}-{linux,macos,windows}

[gh-actions]
python =
    3.7: py37
    3.8: py38

[gh-actions:env]
PLATFORM =
    ubuntu-latest: linux
    macos-latest: macos
    windows-latest: windows
```

This `tox.ini` defines 6 environments as a default envlist:
`py38-linux`, `py38-macos`, `py38-windows`, `py38-linux`, `py38-macos`, and `py38-windows`.
tox-gh-actions needs to decide which environments to run from this list.

Consider a case to run tox-gh-actions on a job with Python 3.8 installed and `PLATFORM=ubuntu-latest` is set.
On this job, tox-gh-actions finds factors `py38` and `linux`, then tries to find environments matching
all factors. In this case, it will find `py38-linux` from the envlist and execute it.

This is a bit more complex example:
```ini
[tox]
envlist = py{37,38}-{linux,macos,windows}-django{2,3}

[gh-actions]
python =
    3.7: py37
    3.8: py38

[gh-actions:env]
PLATFORM =
    ubuntu-latest: linux
    macos-latest: macos
    windows-latest: windows
```

Consider a case to run tox-gh-actions on a job with Python 3.8 and `PLATFORM=ubuntu-latest` again.
It will find factors `py38` and `linux` for this job, then it will find `py38-linux-django2` and `py38-linux-django3`
environments from the list and run them. Please remind that tox-gh-actions won't generate new environments.
Thus, it won't run an environment like `py38-linux` which is not defined in the envlist.
