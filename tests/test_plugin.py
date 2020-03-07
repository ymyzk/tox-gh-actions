import pytest

from tox_gh_actions import plugin


@pytest.mark.parametrize("config,expected", [
    (
        {
            "python": """2.7: py27
3.5: py35
3.6: py36
3.7: py37, flake8"""
        },
        {
            "python": {
                "2.7": ["py27"],
                "3.5": ["py35"],
                "3.6": ["py36"],
                "3.7": ["py37", "flake8"],
            },
        },
    ),
    (
        {},
        {"python": {}},
    ),
])
def test_parse_config(config, expected):
    assert plugin.parse_config(config) == expected


@pytest.mark.parametrize("config,factors,expected", [
    (
        {
            "python": {
                "2.7": ["py27", "flake8"],
                "3.8": ["py38", "flake8"],
            },
            "unknown": {},
        },
        "2.7",
        ["py27", "flake8"],
    ),
    (
        {
            "python": {
                "3.8": ["py38", "flake8"],
            },
        },
        "2.7",
        [],
    ),
    (
        {
            "python": {},
        },
        "3.8",
        [],
    ),
])
def test_get_factors(config, factors, expected):
    assert plugin.get_factors(config, factors) == expected


@pytest.mark.parametrize("envlist,factors,expected", [
    (
        ['py27', 'py37', 'flake8'],
        ['py37', 'flake8'],
        ['py37', 'flake8'],
    ),
    (
        ['py27', 'py37', 'flake8'],
        [],
        [],
    ),
    (
        [],
        ['py37', 'flake8'],
        [],
    ),
    (
        ['py27-dj111', 'py37-dj111', 'py37-dj20', 'flake8'],
        ['py37', 'flake8'],
        ['py37-dj111', 'py37-dj20', 'flake8'],
    ),
])
def test_get_envlist_from_factors(envlist, factors, expected):
    assert plugin.get_envlist_from_factors(envlist, factors) == expected


@pytest.mark.parametrize("version,info,expected", [
    (
        "3.8.1 (default, Jan 22 2020, 06:38:00) \n[GCC 9.2.0]",
        (3, 8, 1, "final", 0),
        "3.8",
    ),
    (
        "3.6.9 (1608da62bfc7, Dec 23 2019, 10:50:04)\n"
        "[PyPy 7.3.0 with GCC 7.3.1 20180303 (Red Hat 7.3.1-5)]",
        (3, 6, 9, "final", 0),
        "pypy3",
    ),
    (
        "2.7.13 (724f1a7d62e8, Dec 23 2019, 15:36:24)\n"
        "[PyPy 7.3.0 with GCC 7.3.1 20180303 (Red Hat 7.3.1-5)]",
        (2, 7, 13, "final", 42),
        "pypy2",
    )
])
def test_get_version(mocker, version, info, expected):
    mocker.patch("tox_gh_actions.plugin.sys.version", version)
    mocker.patch("tox_gh_actions.plugin.sys.version_info", info)
    assert plugin.get_python_version() == expected
