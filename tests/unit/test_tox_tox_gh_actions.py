def test_flag_help(cmd):
    result = cmd("--help")
    result.assert_success(is_run_test_env=False)
    assert "--magic" in result.out
