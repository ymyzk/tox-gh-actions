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
    python = section.get('python', {})
    verbosity0("python: {}".format(python))


@hookimpl
def tox_runtest_post(venv):
    verbosity0("cinderella is {}".format(venv.envconfig.cinderella))
