import json
import re

from tox_gh_actions.plugin import get_problem_matcher_file_path


def match_problem(log):
    """Simulate GitHub Actions' problem matcher for ease of testing

    This is not the same as the actual implementation by GitHub Actions.
    https://github.com/actions/toolkit/blob/main/docs/problem-matchers.md
    """
    with open(get_problem_matcher_file_path()) as f:
        matchers = json.load(f)
    results = []
    for line in log.split("\n"):
        for matcher in matchers["problemMatcher"]:
            # TODO Add multi-lines matcher support if necessary
            pattern = matcher["pattern"][0]
            match = re.search(pattern["regexp"], line)
            if not match:
                continue
            groups = match.groups()
            result = {}
            for key, value in pattern.items():
                if key == "regexp":
                    continue
                result[key] = groups[value - 1]
            results.append(result)
    return results


def test_could_not_install_deps_error():
    log = (
        "ERROR: could not install deps [flake7]; "
        "v = InvocationError('/tmp/.tox/py310/bin/python -m pip install flake7', 1)"
    )
    assert match_problem(log) == [
        {
            "message": (
                "could not install deps [flake7]; v = "
                "InvocationError('/tmp/.tox/py310/bin/python -m pip install flake7', 1)"
            ),
            "severity": "ERROR",
        }
    ]


def test_invocation_error_not_found():
    log = "ERROR: InvocationError for command could not find executable flake9"
    assert match_problem(log) == [
        {
            "message": "InvocationError for command could not find executable flake9",
            "severity": "ERROR",
        }
    ]


def test_invocation_error_non_zero_exit_code():
    log = "ERROR: InvocationError for command /usr/bin/false (exited with code 1)"
    assert match_problem(log) == [
        {
            "message": (
                "InvocationError for command /usr/bin/false " "(exited with code 1)"
            ),
            "severity": "ERROR",
        }
    ]


def test_warnings_on_allowlist_externals():
    log = """WARNING: test command found but not installed in testenv
  cmd: /bin/echo
  env: /tmp/.tox/py310
Maybe you forgot to specify a dependency?
See also the allowlist_externals envconfig setting.

DEPRECATION WARNING: this will be an error in tox 4 and above!
"""
    assert match_problem(log) == [
        {
            "message": "test command found but not installed in testenv",
            "severity": "WARNING",
        },
        {
            "message": "DEPRECATION WARNING: this will be an error in tox 4 and above!",
            "severity": "WARNING",
        },
    ]
