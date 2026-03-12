# pip-upgrader [![CI](https://github.com/simion/pip-upgrader/actions/workflows/ci.yml/badge.svg)](https://github.com/simion/pip-upgrader/actions/workflows/ci.yml)

An interactive pip requirements upgrader. Because upgrading
requirements, package by package, is a pain in the ass. It also updates
the version in your requirements.txt file.

## Purpose

This cli tools helps you interactively(or not) upgrade packages from
requirements file, and also **update the pinned version from
requirements file(s)**.

If no requirements are given, the command **attempts to detect the
requirements file(s)** in the current directory.

Quick preview:

![image](https://raw.githubusercontent.com/simion/pip-upgrader/master/demo.gif)

## Installation

    pip install pip-upgrader

**Note:** this packages installs the following requirements: `'docopt-ng',
'packaging', 'requests', 'terminaltables', 'colorclass'`

To avoid installing all these dependencies in your project, you can
install `pip-upgrader` in your system, rather than your virtualenv. If
you install it in your system, and need to upgrade it, run `pip install
-U pip-upgrader`

## Usage

**Activate your virtualenv** (important, because it will also install
the new versions of upgraded packages in current virtualenv)

**CD into your project.** Then: :

    $ pip-upgrade

Arguments: :

    requirements_file(s)          The requirement FILE, or WILDCARD PATH to multiple files. (positional arguments)
    --prerelease                  Include prerelease versions for upgrade, when querying pypi repositories.
    -p <package>                  Pre-choose which packages tp upgrade. Skips any prompt.
    --dry-run                     Simulates the upgrade, but does not execute the actual upgrade.
    --check-greater-equal         Also checks packages with minimum version pinned (package>=version).
    --skip-package-installation   Only upgrade the version in requirements files, don't install the new package.
    --skip-virtualenv-check       Disable virtualenv check. Allows installing the new packages outside the virtualenv.
    --use-default-index           Skip searching for custom index-url in pip configuration file(s).
    --timeout <seconds>           Set a custom timeout for PyPI requests (default: 15 seconds).

Examples:

    pip-upgrade             # auto discovers requirements file. Prompts for selecting upgrades
    pip-upgrade requirements.txt
    pip-upgrade requirements/dev.txt requirements/production.txt

    # skip prompt and manually choose some/all packages for upgrade
    pip-upgrade requirements.txt -p django -p celery
    pip-upgrade requirements.txt -p all

    # include pre-release versions
    pip-upgrade --prerelease

    # also check packages pinned with >= instead of ==
    pip-upgrade --check-greater-equal

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
git tag v1.10.0
git push origin v1.10.0
```

This triggers the `publish.yml` workflow which builds and publishes to PyPI using trusted publishers (OIDC).
