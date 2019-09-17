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
