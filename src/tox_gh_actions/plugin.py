from itertools import permutations, product

from logging import getLogger
import os
import sys
import sysconfig
from typing import Any, Dict, Iterable, Iterator, List, Tuple

from tox.config.cli.parser import Parsed
from tox.config.loader.memory import MemoryLoader
from tox.config.loader.section import Section
from tox.config.loader.str_convert import StrConvert
from tox.config.main import Config
from tox.config.of_type import _PLACE_HOLDER
from tox.config.sets import ConfigSet, CoreConfigSet
from tox.config.types import EnvList
from tox.execute.api import Outcome
from tox.plugin import impl
from tox.session.state import State
from tox.tox_env.api import ToxEnv

logger = getLogger(__name__)


@impl
def tox_add_core_config(core_conf: ConfigSet, state: State) -> None:
    config = state.conf

    logger.info("running tox-gh-actions")
    if not is_running_on_actions():
        logger.warning(
            "tox-gh-actions won't override envlist because tox is not running "
            "in GitHub Actions"
        )
        return
    elif is_env_specified(config):
        logger.warning(
            "tox-gh-actions won't override envlist because "
            "envlist is explicitly given via TOXENV or -e option"
        )

    original_envlist: EnvList = config.core["envlist"]
    logger.debug("original envlist: %s", original_envlist.envs)

    versions = get_python_version_keys()
    logger.debug("Python versions: {}".format(versions))

    gh_actions_config = load_config(config)
    logger.debug("tox-gh-actions config: %s", gh_actions_config)

    factors = get_factors(gh_actions_config, versions)
    logger.debug("using the following factors to decide envlist: %s", factors)

    envlist = get_envlist_from_factors(original_envlist.envs, factors)
    override_envlist(config.core, EnvList(envlist))

    if not is_log_grouping_enabled(config.options):
        logger.debug(
            "disabling log line grouping on GitHub Actions based on the configuration"
        )


@impl
def tox_before_run_commands(tox_env: ToxEnv) -> None:
    if is_log_grouping_enabled(tox_env.options):
        message = tox_env.name
        description = tox_env.conf["description"]  # type: str
        if description:
            message += " - " + description
        print("::group::tox: " + message)


@impl
def tox_after_run_commands(
    tox_env: ToxEnv, exit_code: int, outcomes: List[Outcome]
) -> None:
    if is_log_grouping_enabled(tox_env.options):
        print("::endgroup::")


class EmptyConfigSet(ConfigSet):
    def register_config(self) -> None:
        pass


def load_config(config: Config) -> Dict[str, Dict[str, Any]]:
    # It's better to utilize ConfigSet to parse gh-actions configuration but
    # we use our custom configuration parser at this point for compatibility with
    # the existing config files and limitations in ConfigSet API.
    python_config = {}
    for loader in load_config_section(config, "gh-actions").loaders:
        if "python" not in loader.found_keys():
            continue
        python_config = parse_factors_dict(loader.load_raw("python", None, None))

    env = {}
    for loader in load_config_section(config, "gh-actions:env").loaders:
        for env_variable in loader.found_keys():
            if env_variable.upper() in env:
                continue
            env[env_variable.upper()] = parse_factors_dict(
                loader.load_raw(env_variable, None, None)
            )

    # TODO Use more precise type
    return {
        "python": python_config,
        "env": env,
    }


def load_config_section(config: Config, section_name: str) -> ConfigSet:
    return config.get_section_config(
        Section(None, section_name), base=[], of_type=EmptyConfigSet, for_env=None
    )


def override_envlist(core: CoreConfigSet, env_list: EnvList) -> None:
    core.loaders.insert(0, MemoryLoader(env_list=env_list))
    if env_list == core["envlist"]:  # Config was not cached
        return
    logger.debug("expiring envlist cache to override")
    # We need to expire cache explicitly otherwise the overridden envlist won't be
    # read at all
    core._defined["envlist"]._cache = _PLACE_HOLDER  # type: ignore
    if env_list == core["envlist"]:  # Cleared the cache successfully
        return
    logger.error("failed to override envlist (tox's API might be changed?)")


def get_factors(
    gh_actions_config: Dict[str, Dict[str, Any]], versions: Iterable[str]
) -> List[str]:
    """Get a list of factors"""
    factors: List[List[str]] = []
    for version in versions:
        if version in gh_actions_config["python"]:
            logger.debug("got factors for Python version: %s", version)
            factors.append(gh_actions_config["python"][version])
            break  # Shouldn't check remaining versions
    for env, env_config in gh_actions_config.get("env", {}).items():
        if env in os.environ:
            env_value = os.environ[env]
            if env_value in env_config:
                factors.append(env_config[env_value])
    return [x for x in map(lambda f: "-".join(f), product(*factors)) if x]


def get_envlist_from_factors(
    envlist: Iterable[str], factors: Iterable[str]
) -> List[str]:
    """Filter envlist using factors"""
    result = []
    for env in envlist:
        for factor in factors:
            env_facts = env.split("-")
            if all(f in env_facts for f in factor.split("-")):
                result.append(env)
                break
    return result


def get_abiflags() -> str:
    """Return ABI flags as a string of character codes.

    POSIX builds provide sys.abiflags. This function constructs
    an equivalent character code sequence for Windows by
    parsing the EXT_SUFFIX configuration variable.
    """
    try:
        return sys.abiflags
    except AttributeError:  # Windows
        ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
        if not ext_suffix:
            return ""

        # Looks like [_d].cp314[t]-win_amd64.pyd
        prefix, cp3, suffix = ext_suffix.partition(".cp3")
        if not cp3:  # Before Python 3.10, hard-coded as ".pyd"
            return ""

        abiflags = ""
        if prefix == "_d":
            abiflags += "d"

        if suffix.split("-", 1)[0].endswith("t"):
            abiflags += "t"

        return abiflags


def permuted_combinations(seq: str) -> Iterator[Tuple[str, ...]]:
    """Generate all combinations of any length and ordering.

    >>> list(permuted_combinations("t"))
    [(), ('t',)]
    >>> list(permuted_combinations("td"))
    [(), ('t',), ('d',), ('t', 'd'), ('d', 't')]
    """
    for n in range(len(seq) + 1):
        yield from permutations(seq, n)


def get_python_version_keys() -> List[str]:
    """Get Python version in string for getting factors from gh-action's config

    Examples:
    - CPython 3.8.z => [3.8, 3]
    - PyPy 3.6 (v7.3.z) => [pypy-3.6, pypy-3]
    - Pyston based on Python CPython 3.8.8 (v2.2) => [pyston-3.8, pyston-3]
    - CPython 3.13.z (free-threading build) => [3.13t, 3.13, 3]
    """
    major, minor = sys.version_info[:2]
    if "PyPy" in sys.version:
        return [
            f"pypy-{major}.{minor}",
            f"pypy-{major}",
        ]
    elif hasattr(sys, "pyston_version_info"):  # Pyston
        return [
            f"pyston-{major}.{minor}",
            f"pyston-{major}",
        ]
    else:
        # Assume this is running on CPython
        ret = [f"{major}"]
        ret.extend(
            f"{major}.{minor}{''.join(flags)}"
            for flags in permuted_combinations(get_abiflags())
        )
        return sorted(ret, reverse=True)


def is_running_on_actions() -> bool:
    """Returns True when running on GitHub Actions"""
    # See the following document on which environ to use for this purpose.
    # https://docs.github.com/en/free-pro-team@latest/actions/reference/environment-variables#default-environment-variables
    return os.environ.get("GITHUB_ACTIONS") == "true"


def is_log_grouping_enabled(options: Parsed) -> bool:
    """Returns True when the plugin should enable log line grouping

    This plugin won't enable grouping when --parallel is enabled
    because log lines from different environments will be mixed.
    """
    if not is_running_on_actions():
        return False

    # The parallel option is not always defined (e.g., `tox run`) so we should check
    # its existence first.
    # As --parallel-live option doesn't seem to be working correctly,
    # this condition is more conservative compared to the plugin for tox 3.
    if hasattr(options, "parallel"):
        if options.parallel is None:
            # Case for `tox -p`
            return False
        elif isinstance(options.parallel, int) and options.parallel > 0:
            # Case for `tox p` or `tox -p <num>`
            return False
        elif isinstance(options.parallel, int) and options.parallel == 0:
            # Case for `tox` or `tox -p 0`
            # tox will disable the parallel execution
            return True
        logger.warning(
            "tox-gh-actions couldn't understand the parallel option. "
            "ignoring the given option: %s",
            options.parallel,
        )

    return True


def is_env_specified(config: Config) -> bool:
    """Returns True when environments are explicitly given"""
    if hasattr(config.options, "env") and not config.options.env.is_default_list:
        # is_default_list becomes False when TOXENV is a non-empty string
        # and when command line argument (-e) is given.
        return True
    return False


def parse_factors_dict(value: str) -> Dict[str, List[str]]:
    """Parse a dict value from key to factors.

    For example, this function converts an input
        3.8: py38, docs
        3.9: py39-django{2,3}
    to a dict
    {
        "3.8": ["py38", "docs"],
        "3.9": ["py39-django2", "py39-django3"],
    }
    """
    return {k: StrConvert.to_env_list(v).envs for k, v in parse_dict(value).items()}


# The following function was copied from
# https://github.com/tox-dev/tox-travis/blob/0.12/src/tox_travis/utils.py#L11-L32
# which is licensed under MIT LICENSE
# https://github.com/tox-dev/tox-travis/blob/0.12/LICENSE


def parse_dict(value: str) -> Dict[str, str]:
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
