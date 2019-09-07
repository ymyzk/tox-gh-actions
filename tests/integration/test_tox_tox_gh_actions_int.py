def test_run(initproj, cmd):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
                [tox]
                envlist = py, b
                skipsdist = True
                [testenv]
                commands=python -c "print('perform')"
                [testenv:b]
                cinderella = True
            """
        },
    )
    result = cmd("--magic", "yes")
    result.assert_success(is_run_test_env=False)
