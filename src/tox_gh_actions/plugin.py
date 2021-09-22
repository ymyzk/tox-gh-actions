from itertools import product
import os
import sys
import threading
from typing import Any, Dict, Iterable, List

import pluggy
from tox.action import Action
from tox.config import Config, TestenvConfig, _split_env as split_env
from tox.reporter import verbosity1, verbosity2, warning
from tox.venv import VirtualEnv


hookimpl = pluggy.HookimplMarker("tox")

# Using thread local for just in case tox uses multiple threads for execution.
# tox seems to be using multiple processes at this point.
thread_locals = threading.local()
thread_locals.is_grouping_started = {}


@hookimpl
def tox_configure(config):
    # type: (Config) -> None
    verbosity1("running tox-gh-actions")
    if not is_running_on_actions():
        verbosity1(
            "tox-gh-actions won't override envlist "
            "because tox is not running in GitHub Actions"
        )
        return
    elif is_env_specified(config):
        verbosity1(
            "tox-gh-actions won't override envlist because "
            "envlist is explicitly given via TOXENV or -e option"
        )
        return

    verbosity2("original envconfigs: {}".format(list(config.envconfigs.keys())))
    verbosity2("original envlist_default: {}".format(config.envlist_default))
    verbosity2("original envlist: {}".format(config.envlist))

    versions = get_python_version_keys()
    verbosity2("Python versions: {}".format(versions))

    gh_actions_config = parse_config(config._cfg.sections)
    verbosity2("tox-gh-actions config: {}".format(gh_actions_config))

    factors = get_factors(gh_actions_config, versions)
    verbosity2("using the following factors to decide envlist: {}".format(factors))

    envlist = get_envlist_from_factors(config.envlist, factors)
    config.envlist_default = config.envlist = envlist
    verbosity1("overriding envlist with: {}".format(envlist))

    if not is_log_grouping_enabled(config):
        verbosity2(
            "disabling log line grouping on GitHub Actions based on the configuration"
        )


@hookimpl
def tox_testenv_create(venv, action):
    # type: (VirtualEnv, Action) -> None
    if is_log_grouping_enabled(venv.envconfig.config):
        start_grouping_if_necessary(venv)


@hookimpl
def tox_testenv_install_deps(venv, action):
    # type: (VirtualEnv, Action) -> None
    if is_log_grouping_enabled(venv.envconfig.config):
        start_grouping_if_necessary(venv)


@hookimpl
def tox_runtest_pre(venv):
    # type: (VirtualEnv) -> None
    if is_log_grouping_enabled(venv.envconfig.config):
        start_grouping_if_necessary(venv)


@hookimpl
def tox_runtest_post(venv):
    # type: (VirtualEnv) -> None
    if is_log_grouping_enabled(venv.envconfig.config):
        print("::endgroup::")


def start_grouping_if_necessary(venv):
    # type: (VirtualEnv) -> None
    """Start log line grouping when necessary.

    This function can be called multiple times when running a test environment
    and it ensures that "::group::" is written only once.

    We shouldn't call this from tox_package and tox_get_python_executable hooks
    because of the timing issue.
    """
    envconfig = venv.envconfig  # type: TestenvConfig
    envname = envconfig.envname

    # Do not enable grouping for an environment used for isolated build
    # because we don't have a hook to write "::endgroup::" for this environment.
    if envname == envconfig.config.isolated_build_env:
        return

    if thread_locals.is_grouping_started.get(envname, False):
        return
    thread_locals.is_grouping_started[envname] = True

    message = envname
    if envconfig.description:
        message += " - " + envconfig.description
    print("::group::tox: " + message)


def parse_config(config):
    # type: (Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, Any]]
    """Parse gh-actions section in tox.ini"""
    config_python = parse_dict(config.get("gh-actions", {}).get("python", ""))
    config_env = {
        name: {k: split_env(v) for k, v in parse_dict(conf).items()}
        for name, conf in config.get("gh-actions:env", {}).items()
    }
    # Example of split_env:
    # "py{27,38}" => ["py27", "py38"]
    return {
        "python": {k: split_env(v) for k, v in config_python.items()},
        "env": config_env,
    }


def get_factors(gh_actions_config, versions):
    # type: (Dict[str, Dict[str, Any]], Iterable[str]) -> List[str]
    """Get a list of factors"""
    factors = []  # type: List[List[str]]
    for version in versions:
        if version in gh_actions_config["python"]:
            show_deprecation_warning_for_old_style_pypy_config(version)
            verbosity2("got factors for Python version: {}".format(version))
            factors.append(gh_actions_config["python"][version])
            break  # Shouldn't check remaining versions
    for env, env_config in gh_actions_config.get("env", {}).items():
        if env in os.environ:
            env_value = os.environ[env]
            if env_value in env_config:
                factors.append(env_config[env_value])
    return [x for x in map(lambda f: "-".join(f), product(*factors)) if x]


def show_deprecation_warning_for_old_style_pypy_config(version):
    # type: (str) -> None
    if version not in {"pypy2", "pypy3"}:
        return
    warning(
        """PendingDeprecationWarning
Support of old-style PyPy config keys will be removed in tox-gh-actions v3.
Please use "pypy-2" and "pypy-3" instead of "pypy2" and "pypy3".

Example of tox.ini:
[gh-actions]
python =
    pypy-2: pypy2
    pypy-3: pypy3
    # The followings won't work with tox-gh-actions v3
    # pypy2: pypy2
    # pypy3: pypy3
    """
    )


def get_envlist_from_factors(envlist, factors):
    # type: (Iterable[str], Iterable[str]) -> List[str]
    """Filter envlist using factors"""
    result = []
    for env in envlist:
        for factor in factors:
            env_facts = env.split("-")
            if all(f in env_facts for f in factor.split("-")):
                result.append(env)
                break
    return result


def get_python_version_keys():
    # type: () -> List[str]
    """Get Python version in string for getting factors from gh-action's config

    Examples:
    - CPython 2.7.z => [2.7, 2]
    - CPython 3.8.z => [3.8, 3]
    - PyPy 2.7 (v7.3.z) => [pypy-2.7, pypy-2, pypy2]
    - PyPy 3.6 (v7.3.z) => [pypy-3.6, pypy-3, pypy3]
    - Pyston based on Python CPython 3.8.8 (v2.2) => [pyston-3.8, pyston-3]

    Support of "pypy2" and "pypy3" is for backward compatibility with
    tox-gh-actions v2.2.0 and before.
    """
    major_version = str(sys.version_info[0])
    major_minor_version = ".".join([str(i) for i in sys.version_info[:2]])
    if "PyPy" in sys.version:
        return [
            "pypy-" + major_minor_version,
            "pypy-" + major_version,
            "pypy" + major_version,
        ]
    elif hasattr(sys, "pyston_version_info"):  # Pyston
        return [
            "pyston-" + major_minor_version,
            "pyston-" + major_version,
        ]
    else:
        # Assume this is running on CPython
        return [major_minor_version, major_version]


def is_running_on_actions():
    # type: () -> bool
    """Returns True when running on GitHub Actions"""
    # See the following document on which environ to use for this purpose.
    # https://docs.github.com/en/free-pro-team@latest/actions/reference/environment-variables#default-environment-variables
    return os.environ.get("GITHUB_ACTIONS") == "true"


def is_log_grouping_enabled(config):
    # type: (Config) -> bool
    """Returns True when the plugin should enable log line grouping

    This plugin won't enable grouping when both --parallel and --parallel-live are
    enabled because log lines from different environments will be mixed.
    """
    if not is_running_on_actions():
        return False
    if config.option.parallel > 1 and config.option.parallel_live:
        return False
    return True


def is_env_specified(config):
    # type: (Config) -> bool
    """Returns True when environments are explicitly given"""
    if os.environ.get("TOXENV"):
        # When TOXENV is a non-empty string
        return True
    elif config.option.env is not None:
        # When command line argument (-e) is given
        return True
    return False


# The following function was copied from
# https://github.com/tox-dev/tox-travis/blob/0.12/src/tox_travis/utils.py#L11-L32
# which is licensed under MIT LICENSE
# https://github.com/tox-dev/tox-travis/blob/0.12/LICENSE


def parse_dict(value):
    # type: (str) -> Dict[str, str]
    """Parse a dict value from the tox config.
    .. code-block: ini
        [travis]
        python =
            2.7: py27, docs
            3.5: py{35,36}
    With this config, the value of ``python`` would be parsed
    by this function, and would return::
        {
            '2.7': 'py27, docs',
            '3.5': 'py{35,36}',
        }
    """
    lines = [line.strip() for line in value.strip().splitlines()]
    pairs = [line.split(":", 1) for line in lines if line]
    return dict((k.strip(), v.strip()) for k, v in pairs)
