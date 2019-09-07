import sys

import pluggy
from tox.reporter import verbosity0

hookimpl = pluggy.HookimplMarker("tox")


@hookimpl
def tox_addoption(parser):
    """Add a command line option for later use"""
    parser.add_argument("--magic", action="store", help="this is a magical option")
    parser.add_testenv_attribute(
        name="cinderella",
        type="string",
        default="not here",
        help="an argument pulled from the tox.ini",
    )


@hookimpl
def tox_configure(config):
    """Access your option during configuration"""
    verbosity0("Python version is: {}".format(sys.version_info))
    verbosity0("flag magic is: {}".format(config.option.magic))
    ini = config._cfg
    section = ini.sections.get('gh-actions', {})
    verbosity0("section: {}".format(section))
    python = parse_dict(section.get('python', ''))
    verbosity0("python: {}".format(python))
    verbosity0("envlist: {}".format(config.envlist))
    verbosity0("envlist_default: {}".format(config.envlist_default))


@hookimpl
def tox_runtest_post(venv):
    verbosity0("cinderella is {}".format(venv.envconfig.cinderella))


# From https://github.com/tox-dev/tox-travis/blob/master/src/tox_travis/utils.py
# https://github.com/tox-dev/tox-travis/blob/master/LICENSE

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
