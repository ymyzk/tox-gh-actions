from collections import defaultdict
import os
import shutil
import subprocess
import sys

import pytest


INT_TEST_DIR = os.path.join(os.path.dirname(__file__), "integration")


@pytest.fixture(autouse=True)
def precondition():
    # Clean up files from previous integration tests
    shutil.rmtree(os.path.join(INT_TEST_DIR, ".tox"), ignore_errors=True)
    shutil.rmtree(os.path.join(INT_TEST_DIR, "out"), ignore_errors=True)

    # Make sure tox and tox-gh-actions are installed
    stdout = run_tox(["--version"])
    assert "tox-gh-actions" in stdout.decode("utf-8")


@pytest.mark.integration
def test_integration():
    expected_envs_map = defaultdict(
        list,
        [
            ((2, 7), ["py27"]),
            ((3, 9), ["py39"]),
        ],
    )
    python_version = sys.version_info[:2]
    # TODO Support non CPython implementation
    if "PyPy" not in sys.version:
        expected_envs = expected_envs_map[python_version]
    else:
        expected_envs = []

    stdout = run_tox()

    assert_envs_executed(INT_TEST_DIR, expected_envs)

    # Make sure to support both POSIX and Windows
    stdout_lines = stdout.decode("utf-8").splitlines()
    # TODO Assert ordering
    for expected_env in expected_envs:
        assert "::group::tox: " + expected_env in stdout_lines
    if len(expected_envs) > 0:
        assert "::endgroup::" in stdout_lines


def assert_envs_executed(root_dir, envs):
    out_dir = os.path.join(root_dir, "out")
    if os.path.isdir(out_dir):
        out_envs = set(os.listdir(out_dir))
    else:
        out_envs = set()
    expected_envs = set(envs)
    assert out_envs == expected_envs


def run_tox(args=None):
    if args is None:
        args = []
    env = os.environ.copy()
    env["GITHUB_ACTIONS"] = "true"
    return subprocess.check_output(
        [sys.executable, "-m", "tox"] + args,
        cwd=INT_TEST_DIR,
        env=env,
    )
