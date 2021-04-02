import pytest
from tox.config import Config

from tox_gh_actions import plugin


@pytest.mark.parametrize(
    "config,expected",
    [
        (
            {
                "gh-actions": {
                    "python": """2.7: py27
3.5: py35
3.6: py36
3.7: py37, flake8"""
                }
            },
            {
                "python": {
                    "2.7": ["py27"],
                    "3.5": ["py35"],
                    "3.6": ["py36"],
                    "3.7": ["py37", "flake8"],
                },
                "envs_are_optional": None,
                "env": {},
            },
        ),
        (
            {
                "gh-actions": {
                    "python": """2.7: py27
3.5: py35
3.6: py36
3.7: py37, flake8""",
                    "envs_are_optional": "true",
                }
            },
            {
                "python": {
                    "2.7": ["py27"],
                    "3.5": ["py35"],
                    "3.6": ["py36"],
                    "3.7": ["py37", "flake8"],
                },
                "envs_are_optional": True,
                "env": {},
            },
        ),
        (
            {
                "gh-actions": {
                    "python": """2.7: py27
3.8: py38"""
                },
                "gh-actions:env": {
                    "PLATFORM": """ubuntu-latest: linux
macos-latest: macos
windows-latest: windows"""
                },
            },
            {
                "python": {
                    "2.7": ["py27"],
                    "3.8": ["py38"],
                },
                "envs_are_optional": None,
                "env": {
                    "PLATFORM": {
                        "ubuntu-latest": ["linux"],
                        "macos-latest": ["macos"],
                        "windows-latest": ["windows"],
                    },
                },
            },
        ),
        (
            {"gh-actions": {}},
            {
                "python": {},
                "envs_are_optional": None,
                "env": {},
            },
        ),
        (
            {
                "gh-actions": {
                    "envs_are_optional": "false",
                }
            },
            {
                "python": {},
                "envs_are_optional": False,
                "env": {},
            },
        ),
        (
            {
                "gh-actions": {
                    "unknown": "unknown",
                }
            },
            {
                "python": {},
                "envs_are_optional": None,
                "env": {},
            },
        ),
        (
            {},
            {
                "python": {},
                "envs_are_optional": None,
                "env": {},
            },
        ),
    ],
)
def test_parse_config(config, expected):
    assert plugin.parse_config(config) == expected


@pytest.mark.parametrize(
    "config,version,environ,expected",
    [
        (
            {
                "python": {
                    "2.7": ["py27", "flake8"],
                    "3.8": ["py38", "flake8"],
                },
                "unknown": {},
            },
            ["2.7", "2"],
            {},
            [["py27", "flake8"]],
        ),
        # Get factors using less precise Python version
        (
            {
                "python": {
                    "2": ["py2", "flake8"],
                    "3": ["py3", "flake8"],
                },
                "unknown": {},
            },
            ["3.8", "3"],
            {},
            [["py3", "flake8"]],
        ),
        # Get factors only from the most precise Python version
        (
            {
                "python": {
                    "2": ["py2", "flake8"],
                    "3": ["py3", "flake8"],
                    "3.9": ["py39"],
                },
                "unknown": {},
            },
            ["3.9", "3"],
            {},
            [["py39"]],
        ),
        (
            {
                "python": {
                    "2.7": ["py27", "flake8"],
                    "3.8": ["py38", "flake8"],
                },
                "env": {
                    "SAMPLE": {
                        "VALUE1": ["fact1", "fact2"],
                        "VALUE2": ["fact3", "fact4"],
                    },
                },
            },
            ["2.7", "2"],
            {
                "SAMPLE": "VALUE1",
                "HOGE": "VALUE3",
            },
            [["py27", "flake8"], ["fact1", "fact2"]],
        ),
        (
            {
                "python": {
                    "2.7": ["py27", "flake8"],
                    "3.8": ["py38", "flake8"],
                },
                "env": {
                    "SAMPLE": {
                        "VALUE1": ["fact1", "fact2"],
                        "VALUE2": ["fact3", "fact4"],
                    },
                    "HOGE": {
                        "VALUE3": ["fact5", "fact6"],
                        "VALUE4": ["fact7", "fact8"],
                    },
                },
            },
            ["2.7", "2"],
            {
                "SAMPLE": "VALUE1",
                "HOGE": "VALUE3",
            },
            [["py27", "flake8"], ["fact1", "fact2"], ["fact5", "fact6"]],
        ),
        (
            {
                "python": {
                    "2.7": ["py27", "flake8"],
                    "3.8": ["py38", "flake8"],
                },
                "env": {
                    "SAMPLE": {
                        "VALUE1": ["django18", "flake8"],
                        "VALUE2": ["django18"],
                    },
                },
            },
            ["2.7", "2"],
            {
                "SAMPLE": "VALUE1",
                "HOGE": "VALUE3",
            },
            [["py27", "flake8"], ["django18", "flake8"]],
        ),
        (
            {
                "python": {
                    "2.7": ["py27", "flake8"],
                    "3.8": ["py38", "flake8"],
                },
                "env": {
                    "SAMPLE": {
                        "VALUE1": ["fact1", "fact2"],
                        "VALUE2": ["fact3", "fact4"],
                    },
                },
                "unknown": {},
            },
            ["2.7", "2"],
            {
                "SAMPLE": "VALUE3",
            },
            [["py27", "flake8"]],
        ),
        (
            {
                "python": {
                    "2.7": ["py27", "flake8"],
                    "3.8": ["py38", "flake8"],
                },
                "env": {
                    "SAMPLE": {
                        "VALUE1": [],
                    },
                },
                "unknown": {},
            },
            ["3.8", "3"],
            {
                "SAMPLE": "VALUE2",
            },
            [["py38", "flake8"]],
        ),
        (
            {
                "python": {
                    "3.8": ["py38", "flake8"],
                },
            },
            ["2.7", "2"],
            {},
            [],
        ),
        (
            {
                "python": {},
            },
            "3.8",
            {},
            [],
        ),
    ],
)
def test_get_factors(mocker, config, version, environ, expected):
    mocker.patch("tox_gh_actions.plugin.os.environ", environ)
    result = normalize_factors_list(plugin.get_factors(config, version))
    expected = normalize_factors_list(expected)
    assert result == expected


def normalize_factors_list(factors):
    """Utility to make it compare equality of a list of factors"""
    return [factors[:1], {frozenset(f) for f in factors[1:]}]


@pytest.mark.parametrize(
    "envlist,factors,lax,expected",
    [
        (
            ["py27", "py37", "flake8"],
            [["py37", "flake8"]],
            [True, False],
            ["py37", "flake8"],
        ),
        (
            ["py27", "py37", "flake8"],
            [],
            [True, False],
            [],
        ),
        (
            [],
            [["py37", "flake8"]],
            [True, False],
            [],
        ),
        (
            ["py27-dj111", "py37-dj111", "py37-dj20", "flake8"],
            [["py37", "flake8"]],
            [True, False],
            ["py37-dj111", "py37-dj20", "flake8"],
        ),
        (
            ["py27-django18", "py37-django18", "flake8"],
            [["py27", "flake8"], ["django18", "flake8"]],
            [True, False],
            ["py27-django18", "flake8"],
        ),
        # The following two show the difference between lax and non lax selection:
        (
            ["py27-dj111", "py37-dj111", "py37-dj20", "flake8"],
            [["py37", "flake8"], ["dj111"]],
            [True],
            ["py37-dj111", "flake8"],
        ),
        (
            ["py27-dj111", "py37-dj111", "py37-dj20", "flake8"],
            [["py37", "flake8"], ["dj111"]],
            [False],
            ["py37-dj111"],
        ),
        # When lax selection is enabled the most specific match is used rather than
        # selecting any match:
        (
            ["py27-dj111", "py37-dj111", "py37-dj20", "flake8", "flake8-dj111"],
            [["py37", "flake8"], ["dj111"]],
            [True],
            ["py37-dj111", "flake8-dj111"],
        ),
        (
            ["py27-dj111", "py37-dj111", "py37-dj20", "flake8", "flake8-dj111"],
            [["py37", "flake8"], ["dj111"]],
            [False],
            ["py37-dj111", "flake8-dj111"],
        ),
    ],
)
def test_get_envlist_from_factors(envlist, factors, lax, expected):
    for _lax in lax:
        assert plugin.get_envlist_from_factors(envlist, factors, _lax) == expected


@pytest.mark.parametrize(
    "version,info,expected",
    [
        (
            "3.8.1 (default, Jan 22 2020, 06:38:00) \n[GCC 9.2.0]",
            (3, 8, 1, "final", 0),
            ["3.8", "3"],
        ),
        (
            "3.6.9 (1608da62bfc7, Dec 23 2019, 10:50:04)\n"
            "[PyPy 7.3.0 with GCC 7.3.1 20180303 (Red Hat 7.3.1-5)]",
            (3, 6, 9, "final", 0),
            ["pypy-3.6", "pypy-3", "pypy3"],
        ),
        (
            "2.7.13 (724f1a7d62e8, Dec 23 2019, 15:36:24)\n"
            "[PyPy 7.3.0 with GCC 7.3.1 20180303 (Red Hat 7.3.1-5)]",
            (2, 7, 13, "final", 42),
            ["pypy-2.7", "pypy-2", "pypy2"],
        ),
    ],
)
def test_get_version_keys(mocker, version, info, expected):
    mocker.patch("tox_gh_actions.plugin.sys.version", version)
    mocker.patch("tox_gh_actions.plugin.sys.version_info", info)
    assert plugin.get_python_version_keys() == expected


@pytest.mark.parametrize(
    "environ,expected",
    [
        ({"GITHUB_ACTIONS": "true"}, True),
        ({"GITHUB_ACTIONS": "false"}, False),
        ({}, False),
    ],
)
def test_is_running_on_actions(mocker, environ, expected):
    mocker.patch("tox_gh_actions.plugin.os.environ", environ)
    assert plugin.is_running_on_actions() == expected


@pytest.mark.parametrize(
    "option_env,environ,expected",
    [
        (None, {"TOXENV": "flake8"}, True),
        (["py27,py38"], {}, True),
        (["py27", "py38"], {}, True),
        (["py27"], {"TOXENV": "flake8"}, True),
        (None, {}, False),
    ],
)
def test_is_env_specified(mocker, option_env, environ, expected):
    mocker.patch("tox_gh_actions.plugin.os.environ", environ)
    option = mocker.MagicMock()
    option.env = option_env
    config = Config(None, option, None, mocker.MagicMock(), [])
    assert plugin.is_env_specified(config) == expected
