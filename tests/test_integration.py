import sys

import pytest
from pytest import MonkeyPatch
from tox.pytest import ToxProjectCreator, init_fixture  # noqa: F401


requires_cpython = pytest.mark.skipif(
    sys.implementation.name != "cpython", reason="Requires CPython to run this test"
)


@pytest.mark.integration
@requires_cpython
def test_sunny_day_with_legacy_command(
    monkeypatch: MonkeyPatch, tox_project: ToxProjectCreator
) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("TOXENV", raising=False)
    env = f"py{sys.version_info[0]}{sys.version_info[1]}"
    version = f"{sys.version_info[0]}.{sys.version_info[1]}"
    tox_ini = f"""
[tox]
envlist = dummy, {env}

[testenv]
package = skip

[gh-actions]
python =
    2.6: dummy
    {version}: {env}
"""
    project = tox_project({"tox.ini": tox_ini})

    result = project.run()

    result.assert_success()
    assert f"py{sys.version_info[0]}{sys.version_info[1]}: OK" in result.out
    assert "dummy" not in result.out


@pytest.mark.integration
@requires_cpython
def test_sunny_day_with_run_command(
    monkeypatch: MonkeyPatch, tox_project: ToxProjectCreator
) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("TOXENV", raising=False)
    env = f"py{sys.version_info[0]}{sys.version_info[1]}"
    version = f"{sys.version_info[0]}.{sys.version_info[1]}"
    tox_ini = f"""
[tox]
envlist = dummy, {env}

[testenv]
package = skip

[gh-actions]
python =
    2.6: dummy
    {version}: {env}
"""
    project = tox_project({"tox.ini": tox_ini})

    result = project.run("run")

    result.assert_success()
    assert f"py{sys.version_info[0]}{sys.version_info[1]}: OK" in result.out
    assert "dummy" not in result.out


@pytest.mark.integration
@requires_cpython
def test_sunny_day_with_list_command(
    monkeypatch: MonkeyPatch, tox_project: ToxProjectCreator
) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("TOXENV", raising=False)
    env = f"py{sys.version_info[0]}{sys.version_info[1]}"
    version = f"{sys.version_info[0]}.{sys.version_info[1]}"
    tox_ini = f"""
[tox]
envlist = dummy, {env}

[testenv]
package = skip

[gh-actions]
python =
    2.6: dummy
    {version}: {env}
"""
    project = tox_project({"tox.ini": tox_ini})

    result = project.run("list")

    result.assert_success()
    assert [
        "default environments:",
        f"py{sys.version_info[0]}{sys.version_info[1]} -> [no description]",
        "",
    ] == result.out.splitlines()[:3]
