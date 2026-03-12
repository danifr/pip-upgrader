# pip-upgrader [![CI](https://github.com/simion/pip-upgrader/actions/workflows/ci.yml/badge.svg)](https://github.com/simion/pip-upgrader/actions/workflows/ci.yml)

An interactive pip requirements upgrader. Because upgrading
requirements, package by package, is a pain in the ass. It also updates
the version in your requirements.txt and pyproject.toml files.

## Purpose

This cli tool helps you interactively(or not) upgrade packages from
requirements files or **pyproject.toml**, and also **update the pinned
version in-place**.

If no requirements are given, the command **attempts to detect
requirements file(s) and pyproject.toml** in the current directory.

Quick preview:

![image](https://raw.githubusercontent.com/simion/pip-upgrader/master/demo.gif)

## Installation

    uv tool install pip-upgrader

or with pip:

    pip install pip-upgrader

**Requires Python 3.10+**

To avoid installing all these dependencies in your project, you can
install `pip-upgrader` as a tool (via `uv tool install`) or in your
system Python, rather than your virtualenv.

## Usage

**CD into your project.** Then:

    $ pip-upgrade

This will update the pinned versions in your requirements files. You then install yourself with `uv sync`, `pip install -r requirements.txt`, or whatever you use.

Arguments:

    requirements_file(s)          The requirement FILE, WILDCARD PATH to multiple files, or pyproject.toml. (positional arguments)
    --prerelease                  Include prerelease versions for upgrade, when querying pypi repositories.
    -p <package>                  Pre-choose which packages to upgrade. Skips any prompt.
    --dry-run                     Simulates the upgrade, but does not execute the actual upgrade.
    --skip-greater-equal          Skip packages with >= pins (by default both == and >= are checked).
    --use-default-index           Skip searching for custom index-url in pip configuration file(s).
    --timeout <seconds>           Set a custom timeout for PyPI requests (default: 15 seconds).

Examples:

    pip-upgrade             # auto discovers requirements file(s) and pyproject.toml
    pip-upgrade requirements.txt
    pip-upgrade pyproject.toml
    pip-upgrade requirements/dev.txt requirements/production.txt

    # skip prompt and manually choose some/all packages for upgrade
    pip-upgrade requirements.txt -p django -p celery
    pip-upgrade requirements.txt -p all

    # upgrade dependencies in pyproject.toml
    pip-upgrade pyproject.toml -p all

    # include pre-release versions
    pip-upgrade --prerelease

    # skip packages pinned with >= (only upgrade == pins)
    pip-upgrade --skip-greater-equal

    # set a custom timeout for PyPI requests
    pip-upgrade --timeout 30

## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management:

```sh
uv sync --extra test --extra dev   # install all dependencies
uv run pytest                      # run tests
uv run ruff check .                # lint
uv run ruff format --check .       # check formatting
```

## Releasing

Releases are published to PyPI automatically via GitHub Actions when a version tag is pushed:

```sh
git tag v2.1.0
git push origin v2.1.0
```

This triggers the `publish.yml` workflow which builds and publishes to PyPI using trusted publishers (OIDC).
