from itertools import combinations, product
import os
import sys
from typing import Any, Dict, Iterable, List

import pluggy
from tox.config import Config, TestenvConfig, _split_env as split_env
from tox.reporter import verbosity1, verbosity2, warning
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

    if gh_actions_config["envs_are_optional"] is None:
        warning(
            "Config 'gh-actions.envs_are_optional' will become the default in a "
            "future release. Set explicitly to 'true' or 'false' to disable this "
            "warning."
        )

    factors = get_factors(gh_actions_config, versions)
    verbosity2("using the following factors to decide envlist: {}".format(factors))

    envlist = get_envlist_from_factors(
        config.envlist,
        factors,
        envs_are_optional=gh_actions_config["envs_are_optional"],
    )
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


def parse_env_config(value):
    # type: (str) -> Dict[str, Dict[str, List[str]]]
    return {k: split_env(v) for k, v in parse_dict(value).items()}


def parse_config(config):
    # type: (Dict[str, Dict[str, str]]) -> Dict[str, Any]
    """Parse gh-actions section in tox.ini"""
    action_config = config.get("gh-actions", {})
    envs_are_optional = action_config.get("envs_are_optional")
    # Example of split_env:
    # "py{27,38}" => ["py27", "py38"]
    return {
        "python": parse_env_config(action_config.get("python", "")),
        "envs_are_optional": (
            None if envs_are_optional is None else envs_are_optional.lower() == "true"
        ),
        "env": {
            name: parse_env_config(conf)
            for name, conf in config.get("gh-actions:env", {}).items()
        },
    }


def get_factors(gh_actions_config, versions):
    # type: (Dict[str, Any], Iterable[str]) -> List[List[str]]
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
    return factors


def get_envlist_from_factors(envlist, grouped_factors, envs_are_optional=False):
    # type: (Iterable[str], Iterable[List[List[str]]], bool) -> List[str]
    """Filter envlist using factors"""
    if not grouped_factors:
        return []

    result = set()
    all_env_factors = [(set(e.split("-")), e) for e in envlist]

    if not envs_are_optional:
        for env_factors, env in all_env_factors:
            for factors in product(*grouped_factors):
                if env_factors.issuperset(factors):
                    result.add(env)
    else:
        # The first factors come from the python config and are required
        for required_factor in grouped_factors[0]:
            env_factors = [(f, e) for f, e in all_env_factors if required_factor in f]

            # The remaining factors come from the env and will be tried exactly at
            # first, and then will be tried again after a single factor is removed
            # until there is only 1 factor left. All matches after removing N factors
            # are added to the result set.
            matches = set()
            for optional_factors in product(*grouped_factors[1:]):
                for count in range(len(optional_factors), 0, -1):
                    for factors in combinations(optional_factors, count):
                        factors = set(factors)
                        matches.update(e for f, e in env_factors if f >= factors)

                    if matches:
                        result |= matches
                        break

            # if none of the optional factors matched add all required matches
            if not matches:
                result.update(e for f, e in env_factors)

    return [i for i in envlist if i in result]


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
