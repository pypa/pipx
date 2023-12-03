import subprocess
import sys
from pathlib import Path

import nox  # type: ignore

PYTHON_ALL_VERSIONS = ["3.12", "3.11", "3.10", "3.9", "3.8"]
PYTHON_DEFAULT_VERSION = "3.12"
DOC_DEPENDENCIES = ["jinja2", "mkdocs", "mkdocs-material", "mkdocs-gen-files"]
MAN_DEPENDENCIES = ["argparse-manpage[setuptools]"]
TEST_DEPENDENCIES = ["pytest", "pypiserver[passlib]", 'setuptools; python_version>="3.12"', "pytest-cov"]
# Packages whose dependencies need an intact system PATH to compile
# pytest setup clears PATH.  So pre-build some wheels to the pip cache.
PREBUILD_PACKAGES = {"all": ["jupyter==1.0.0"], "macos": [], "unix": [], "win": []}
PIPX_TESTS_CACHE_DIR = Path("./.pipx_tests/package_cache")
PIPX_TESTS_PACKAGE_LIST_DIR = Path("testdata/tests_packages")

# Platform logic
if sys.platform == "darwin":
    PLATFORM = "macos"
elif sys.platform == "win32":
    PLATFORM = "win"
else:
    PLATFORM = "unix"

# Set nox options
if PLATFORM == "win":
    # build_docs fail on Windows, even if `chcp.com 65001` is used
    nox.options.sessions = ["tests", "lint", "build_man"]
else:
    nox.options.sessions = ["tests", "lint", "build_docs", "build_man"]
nox.options.reuse_existing_virtualenvs = True


def prebuild_wheels(session, prebuild_dict):
    prebuild_list = prebuild_dict.get("all", []) + prebuild_dict.get(PLATFORM, [])

    session.install("wheel")
    wheel_dir = Path(session.virtualenv.location) / "prebuild_wheels"
    wheel_dir.mkdir(exist_ok=True)

    for prebuild in prebuild_list:
        session.run("pip", "wheel", f"--wheel-dir={wheel_dir}", prebuild, silent=True)


def has_changes():
    cmd = "git status --porcelain"
    status = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE).stdout.decode().strip()
    return len(status) > 0


def get_branch():
    cmd = "git rev-parse --abbrev-ref HEAD"
    return subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE).stdout.decode().strip()


def on_main_no_changes(session):
    if has_changes():
        session.error("All changes must be committed or removed before publishing")
    branch = get_branch()
    if branch != "main":
        session.error(f"Must be on 'main' branch. Currently on {branch!r} branch")


@nox.session(python=PYTHON_ALL_VERSIONS)
def refresh_packages_cache(session):
    """Populate .pipx_tests/package_cache"""
    print("Updating local tests package spec file cache...")
    PIPX_TESTS_CACHE_DIR.mkdir(exist_ok=True, parents=True)
    session.run(
        "python",
        "scripts/update_package_cache.py",
        str(PIPX_TESTS_PACKAGE_LIST_DIR),
        str(PIPX_TESTS_CACHE_DIR),
    )


def tests_with_options(session, net_pypiserver):
    prebuild_wheels(session, PREBUILD_PACKAGES)
    session.install("-e", ".", *TEST_DEPENDENCIES)
    test_dir = session.posargs or ["tests"]

    if net_pypiserver:
        pypiserver_option = ["--net-pypiserver"]
    else:
        refresh_packages_cache(session)
        pypiserver_option = []

    session.run("pytest", *pypiserver_option, "--cov=pipx", "--cov-report=", *test_dir)
    session.notify("cover")


@nox.session(python=PYTHON_ALL_VERSIONS)
def tests_internet(session):
    """Tests using internet pypi only"""
    tests_with_options(session, net_pypiserver=True)


@nox.session(python=PYTHON_ALL_VERSIONS)
def tests(session):
    """Tests using local pypiserver only"""
    tests_with_options(session, net_pypiserver=False)


@nox.session(python=PYTHON_ALL_VERSIONS)
def test_all_packages(session):
    session.install("-e", ".", *TEST_DEPENDENCIES)
    test_dir = session.posargs or ["tests"]
    session.run("pytest", "-v", "--tb=no", "--show-capture=no", "--net-pypiserver", "--all-packages", *test_dir)


@nox.session
def cover(session):
    """Coverage analysis"""
    session.install("coverage")
    session.run("coverage", "report", "--show-missing", "--fail-under=70")
    session.run("coverage", "erase")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def lint(session):
    session.run("python", "-m", "pip", "install", "pre-commit")
    session.run("pre-commit", "run", "--all-files")


@nox.session(python=PYTHON_ALL_VERSIONS)
def develop(session):
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    session.install(*DOC_DEPENDENCIES, *TEST_DEPENDENCIES, *MAN_DEPENDENCIES, "-e", ".")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def build(session):
    session.install("build")
    session.run("rm", "-rf", "dist", "build", external=True)
    session.run("python", "-m", "build")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def publish(session):
    on_main_no_changes(session)
    session.install("twine")
    build(session)
    print("REMINDER: Has the changelog been updated?")
    session.run("python", "-m", "twine", "upload", "dist/*")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def build_docs(session):
    site_dir = session.posargs or ["site/"]
    session.install(*DOC_DEPENDENCIES, ".")
    session.env["PIPX__DOC_DEFAULT_PYTHON"] = "typically the python used to execute pipx"
    session.run("mkdocs", "build", "--strict", "--site-dir", *site_dir)


@nox.session(python=PYTHON_DEFAULT_VERSION)
def watch_docs(session):
    session.install(*DOC_DEPENDENCIES, ".")
    session.run("mkdocs", "serve", "--strict")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def build_man(session):
    session.install(*MAN_DEPENDENCIES)
    session.env["PIPX__DOC_DEFAULT_PYTHON"] = "typically the python used to execute pipx"
    session.run("python", "scripts/generate_man.py")


@nox.session(python=PYTHON_ALL_VERSIONS)
def create_test_package_list(session):
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    output_dir = session.posargs[0] if session.posargs else str(PIPX_TESTS_PACKAGE_LIST_DIR)
    primary = str(PIPX_TESTS_PACKAGE_LIST_DIR / "primary_packages.txt")
    session.run("python", "scripts/list_test_packages.py", primary, output_dir)
