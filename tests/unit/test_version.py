def test_version():
    pkg = __import__("tox_gh_actions", fromlist=["__version__"])
    assert pkg.__version__
