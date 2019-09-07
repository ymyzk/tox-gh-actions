# tox-gh-actions
Seamless integration of tox into GitHub Actions

## Usage
`tox.ini`:
```ini
[tox]
envlist = py27, py35, py36, py37, mypy

[gh-actions]
python =
    2.7: py27
    3.5: py35
    3.6: py36
    3.7: py37, mypy

[testenv]
...
```

`.github/workflows/<workflow>.yml`:
```yaml
name: Python package

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      max-parallel: 4
      matrix:
        python-version: [2.7, 3.5, 3.6, 3.7]

    steps:
    - uses: actions/checkout@v1
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v1
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install tox tox-gh-actions
    - name: Test with tox
      run: tox
```
