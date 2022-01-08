from typing import Any, Dict, Iterable, List, Tuple

import pytest
from pytest_mock import MockerFixture

from tox_gh_actions import plugin


@pytest.mark.parametrize(
    "config,version,environ,expected",
    [
        (
            {
                "python": {
                    "3.7": ["py37", "flake8"],
                    "3.8": ["py38", "flake8"],
                },
                "unknown": {},
            },
            ["3.7", "3"],
            {},
            ["py37", "flake8"],
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
            ["py3", "flake8"],
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
            ["py39"],
        ),
        (
            {
                "python": {
                    "3.7": ["py37", "flake8"],
                    "3.8": ["py38", "flake8"],
                },
                "env": {
                    "SAMPLE": {
                        "VALUE1": ["fact1", "fact2"],
                        "VALUE2": ["fact3", "fact4"],
                    },
                },
            },
            ["3.7", "3"],
            {
                "SAMPLE": "VALUE1",
                "HOGE": "VALUE3",
            },
            ["py37-fact1", "py37-fact2", "flake8-fact1", "flake8-fact2"],
        ),
        (
            {
                "python": {
                    "3.7": ["py37", "flake8"],
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
            ["3.7", "3"],
            {
                "SAMPLE": "VALUE1",
                "HOGE": "VALUE3",
            },
            [
                "py37-fact1-fact5",
                "py37-fact1-fact6",
                "py37-fact2-fact5",
                "py37-fact2-fact6",
                "flake8-fact1-fact5",
                "flake8-fact1-fact6",
                "flake8-fact2-fact5",
                "flake8-fact2-fact6",
            ],
        ),
        (
            {
                "python": {
                    "3.7": ["py37", "flake8"],
                    "3.8": ["py38", "flake8"],
                },
                "env": {
                    "SAMPLE": {
                        "VALUE1": ["django18", "flake8"],
                        "VALUE2": ["django18"],
                    },
                },
            },
            ["3.7", "3"],
            {
                "SAMPLE": "VALUE1",
                "HOGE": "VALUE3",
            },
            [
                "py37-django18",
                "py37-flake8",
                "flake8-django18",
                "flake8-flake8",
            ],
        ),
        (
            {
                "python": {
                    "3.7": ["py37", "flake8"],
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
            ["3.7", "3"],
            {
                "SAMPLE": "VALUE3",
            },
            ["py37", "flake8"],
        ),
        (
            {
                "python": {
                    "3.7": ["py37", "flake8"],
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
            ["py38", "flake8"],
        ),
        (
            {
                "python": {
                    "3.8": ["py38", "flake8"],
                },
            },
            ["3.7", "3"],
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
# TODO Improve type hints for config
def test_get_factors(
    mocker: MockerFixture,
    config: Dict[str, Any],
    version: List[str],
    environ: Dict[str, str],
    expected: List[str],
) -> None:
    mocker.patch("tox_gh_actions.plugin.os.environ", environ)
    result = normalize_factors_list(plugin.get_factors(config, version))
    assert result == normalize_factors_list(expected)


def normalize_factors_list(factors: Iterable[str]) -> List[Tuple[str, ...]]:
    """Utility to make it compare equality of a list of factors"""
    result = [tuple(sorted(f.split("-"))) for f in factors]
    result.sort()
    return result


@pytest.mark.parametrize(
    "envlist,factors,expected",
    [
        (
            ["py37", "py38", "flake8"],
            ["py38", "flake8"],
            ["py38", "flake8"],
        ),
        (
            ["py37", "py38", "flake8"],
            [],
            [],
        ),
        (
            [],
            ["py37", "flake8"],
            [],
        ),
        (
            ["py37-dj111", "py38-dj111", "py38-dj20", "flake8"],
            ["py38", "flake8"],
            ["py38-dj111", "py38-dj20", "flake8"],
        ),
        (
            ["py37-django18", "py38-django18", "flake8"],
            [
                "py37-django18",
                "py37-flake8",
                "flake8-django18",
                "flake8-flake8",
            ],
            ["py37-django18", "flake8"],
        ),
    ],
)
def test_get_envlist_from_factors(
    envlist: List[str], factors: List[str], expected: List[str]
) -> None:
    assert plugin.get_envlist_from_factors(envlist, factors) == expected


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
            ["pypy-3.6", "pypy-3"],
        ),
    ],
)
def test_get_version_keys(
    mocker: MockerFixture,
    version: str,
    info: Tuple[int, int, int, str, int],
    expected: List[str],
) -> None:
    mocker.patch("tox_gh_actions.plugin.sys.version", version)
    mocker.patch("tox_gh_actions.plugin.sys.version_info", info)
    assert plugin.get_python_version_keys() == expected


def test_get_version_keys_on_pyston(mocker: MockerFixture) -> None:
    mocker.patch(
        "tox_gh_actions.plugin.sys.pyston_version_info",
        (2, 2, 0, "final", 0),
        create=True,  # For non-Pyston implementation
    )
    mocker.patch(
        "tox_gh_actions.plugin.sys.version",
        "3.8.8 (heads/rel2.2:6287d61, Apr 29 2021, 15:46:12)\n"
        "[Pyston 2.2.0, GCC 9.3.0]",
    )
    mocker.patch(
        "tox_gh_actions.plugin.sys.version_info",
        (3, 8, 8, "final", 0),
    )
    assert plugin.get_python_version_keys() == ["pyston-3.8", "pyston-3"]


@pytest.mark.parametrize(
    "environ,expected",
    [
        ({"GITHUB_ACTIONS": "true"}, True),
        ({"GITHUB_ACTIONS": "false"}, False),
        ({}, False),
    ],
)
def test_is_running_on_actions(
    mocker: MockerFixture, environ: Dict[str, str], expected: bool
) -> None:
    mocker.patch("tox_gh_actions.plugin.os.environ", environ)
    assert plugin.is_running_on_actions() == expected
