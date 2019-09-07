import os
import sys

import pluggy
from tox.config import _split_env as split_env
from tox.reporter import verbosity0, verbosity2


hookimpl = pluggy.HookimplMarker("tox")


@hookimpl
def tox_configure(config):
    version = '.'.join([str(i) for i in sys.version_info[:2]])
    verbosity2("Python version: {}".format(version))

    ini = config._cfg
    section = ini.sections.get("gh-actions", {})
    python_envlist = parse_dict(section.get("python", ""))
    verbosity2("original envlist: {}".format(config.envlist))
    verbosity2("original envlist_default: {}".format(config.envlist_default))
    envlist = split_env(python_envlist.get(version, ""))
    envlist = list(set(envlist) & set(config.envlist))
    verbosity2("new envlist: {}".format(envlist))

    if "GITHUB_ACTION" not in os.environ:
        verbosity0("tox is not running in GitHub Actions")
        verbosity0("tox-gh-actions won't override envlist")
        return
    config.envlist_default = config.envlist = envlist


# The following function was copied from
# https://github.com/tox-dev/tox-travis/blob/0.12/src/tox_travis/utils.py#L11-L32
# which is licensed under MIT LICENSE
# https://github.com/tox-dev/tox-travis/blob/0.12/LICENSE

def parse_dict(value):
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
    pairs = [line.split(':', 1) for line in lines if line]
    return dict((k.strip(), v.strip()) for k, v in pairs)
