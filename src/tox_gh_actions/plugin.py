from itertools import product
import os
import sys
from typing import Any, Dict, Iterable, List

import pluggy
from tox.config import Config, TestenvConfig, _split_env as split_env
from tox.reporter import verbosity1, verbosity2
from tox.venv import VirtualEnv


hookimpl = pluggy.HookimplMarker("tox")


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


@hookimpl
def tox_runtest_pre(venv):
    # type: (VirtualEnv) -> None
    if is_running_on_actions():
        envconfig = venv.envconfig  # type: TestenvConfig
        message = envconfig.envname
        if envconfig.description:
            message += " - " + envconfig.description
        print("::group::tox: " + message)


@hookimpl
def tox_runtest_post(venv):
    # type: (VirtualEnv) -> None
    if is_running_on_actions():
        print("::endgroup::")


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
            verbosity2("got factors for Python version: {}".format(version))
            factors.append(gh_actions_config["python"][version])
            break  # Shouldn't check remaining versions
    for env, env_config in gh_actions_config.get("env", {}).items():
        if env in os.environ:
            env_value = os.environ[env]
            if env_value in env_config:
                factors.append(env_config[env_value])
    return [x for x in map(lambda f: "-".join(f), product(*factors)) if x]


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


def is_env_specified(config):
    # type: (Config) -> None
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
