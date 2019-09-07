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
    verbosity0("flag magic is: {}".format(config.option.magic))


@hookimpl
def tox_runtest_post(venv):
    verbosity0("cinderella is {}".format(venv.envconfig.cinderella))
