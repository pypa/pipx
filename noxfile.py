import shutil
import subprocess
import sys
from pathlib import Path

import nox

PYTHON_ALL_VERSIONS = ["3.12", "3.11", "3.10", "3.9", "3.8"]
PYTHON_DEFAULT_VERSION = "3.12"
DOC_DEPENDENCIES = [
    "jinja2",
    "mkdocs",
    "mkdocs-material",
    "mkdocs-gen-files",
    "mkdocs-macros-plugin",
    "towncrier",
    "markdown-gfm-admonition",
]
MAN_DEPENDENCIES = ["argparse-manpage[setuptools]"]
TEST_DEPENDENCIES = ["pytest", "pypiserver[passlib]", 'setuptools; python_version>="3.12"', "pytest-cov"]
# Packages whose dependencies need an intact system PATH to compile
# pytest setup clears PATH.  So pre-build some wheels to the pip cache.
PREBUILD_PACKAGES = {"all": ["jupyter==1.0.0"], "macos": [], "unix": [], "win": []}
PIPX_TESTS_CACHE_DIR = Path("./.pipx_tests/package_cache")
PIPX_TESTS_PACKAGE_LIST_DIR = Path("testdata/tests_packages")

# Platform logic
PLATFORM = {"darwin": "macos", "win32": "win"}.get(sys.platform, "unix")
nox.options.sessions = ["tests", "lint", "build_docs", "zipapp"]
if PLATFORM != "win":  # build_docs fail on Windows, even if `chcp.com 65001` is used
    nox.options.sessions.append("build_man")
nox.options.reuse_existing_virtualenvs = True


def prebuild_wheels(session: nox.Session, prebuild_dict) -> None:
    prebuild_list = prebuild_dict.get("all", []) + prebuild_dict.get(PLATFORM, [])

    session.install("wheel")
    wheel_dir = Path(session.virtualenv.location) / "prebuild_wheels"
    wheel_dir.mkdir(exist_ok=True)

    for prebuild in prebuild_list:
        session.run("pip", "wheel", f"--wheel-dir={wheel_dir}", prebuild, silent=True)


def on_main_no_changes(session: nox.Session) -> None:
    if len(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()) > 0:  # has changes
        session.error("All changes must be committed or removed before publishing")
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    if branch != "main":
        session.error(f"Must be on 'main' branch. Currently on {branch!r} branch")


def tests_with_options(session: nox.Session, *, net_pypiserver: bool) -> None:
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


def create_upcoming_changelog(session: nox.Session) -> Path:
    draft_changelog_content = session.run("towncrier", "build", "--version", "Upcoming", "--draft", silent=True)
    draft_changelog = Path("docs", "_draft_changelog.md")
    if draft_changelog_content and "No significant changes" not in draft_changelog_content:
        lines_to_keep = draft_changelog_content.split("\n")
        changelog_start = 0
        for i, line in enumerate(lines_to_keep):
            if line.startswith("##"):
                changelog_start = i
                break
        lines_to_keep[changelog_start] = "## Planned for next release"
        clean_changelog_content = "\n".join(lines_to_keep[changelog_start:])
        draft_changelog.write_text(clean_changelog_content)
    return draft_changelog


@nox.session(python=PYTHON_ALL_VERSIONS)
def tests(session: nox.Session) -> None:
    """Tests using local pypiserver only"""
    tests_with_options(session, net_pypiserver=False)


@nox.session
def cover(session: nox.Session) -> None:
    """Coverage analysis"""
    session.install("coverage")
    session.run("coverage", "report", "--show-missing", "--fail-under=70")
    session.run("coverage", "erase")


@nox.session
def zipapp(session: nox.Session) -> None:
    """Build a zipapp with shiv"""
    session.install("shiv")
    session.run("shiv", "-c", "pipx", "-o", "./pipx.pyz", ".")
    session.run("./pipx.pyz", "--version", external=True)


@nox.session(python=PYTHON_DEFAULT_VERSION)
def lint(session):
    session.run("python", "-m", "pip", "install", "pre-commit")
    session.run("pre-commit", "run", "--all-files")


@nox.session(python=PYTHON_ALL_VERSIONS)
def develop(session: nox.Session) -> None:
    """Create a develop environment."""
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    session.install(*DOC_DEPENDENCIES, *TEST_DEPENDENCIES, *MAN_DEPENDENCIES, "-e", ".", "nox")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def build(session: nox.Session) -> None:
    """Build the wheel and source distribution for the project."""
    session.install("build")
    session.run("rm", "-rf", "dist", "build", external=True)
    session.run("python", "-m", "build")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def publish(session: nox.Session) -> None:
    """Publish the package to PyPI."""
    on_main_no_changes(session)
    session.install("twine")
    build(session)
    session.run("python", "-m", "twine", "upload", "dist/*")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def build_docs(session: nox.Session) -> None:
    site_dir = session.posargs or ["site/"]
    session.install(*DOC_DEPENDENCIES, ".")
    session.env["PIPX__DOC_DEFAULT_PYTHON"] = "typically the python used to execute pipx"
    upcoming_changelog = create_upcoming_changelog(session)
    session.run("mkdocs", "build", "--strict", "--site-dir", *site_dir)
    upcoming_changelog.unlink(missing_ok=True)
    for site in site_dir:
        draft_changelog_dir = Path(site, "_draft_changelog")
        if draft_changelog_dir.exists():
            shutil.rmtree(draft_changelog_dir)


@nox.session(python=PYTHON_DEFAULT_VERSION)
def watch_docs(session: nox.Session) -> None:
    session.install(*DOC_DEPENDENCIES, ".")
    upcoming_changelog = create_upcoming_changelog(session)
    session.run("mkdocs", "serve", "--strict")
    upcoming_changelog.unlink(missing_ok=True)


@nox.session(python=PYTHON_DEFAULT_VERSION)
def build_changelog(session: nox.Session) -> None:
    session.install(*DOC_DEPENDENCIES, ".")
    session.run("towncrier", "build", "--version", session.posargs[0], "--yes")


@nox.session(python=PYTHON_DEFAULT_VERSION)
def build_man(session: nox.Session) -> None:
    session.install(*MAN_DEPENDENCIES, ".")
    session.env["PIPX__DOC_DEFAULT_PYTHON"] = "typically the python used to execute pipx"
    session.run("python", "scripts/generate_man.py")


@nox.session(python=PYTHON_ALL_VERSIONS)
def refresh_packages_cache(session: nox.Session) -> None:
    """Populate .pipx_tests/package_cache"""
    print("Updating local tests package spec file cache...")
    PIPX_TESTS_CACHE_DIR.mkdir(exist_ok=True, parents=True)
    script = "scripts/update_package_cache.py"
    session.run("python", script, str(PIPX_TESTS_PACKAGE_LIST_DIR), str(PIPX_TESTS_CACHE_DIR))


@nox.session(python=PYTHON_ALL_VERSIONS)
def create_test_package_list(session: nox.Session) -> None:
    """Update the list of packages needed for running the test suite."""
    session.run("python", "-m", "pip", "install", "--upgrade", "pip")
    output_dir = session.posargs[0] if session.posargs else str(PIPX_TESTS_PACKAGE_LIST_DIR)
    primary = str(PIPX_TESTS_PACKAGE_LIST_DIR / "primary_packages.txt")
    session.run("python", "scripts/list_test_packages.py", primary, output_dir)


@nox.session(python=PYTHON_ALL_VERSIONS)
def tests_internet(session: nox.Session) -> None:
    """Tests using internet pypi only"""
    tests_with_options(session, net_pypiserver=True)


@nox.session(python=PYTHON_ALL_VERSIONS)
def test_all_packages(session: nox.Session) -> None:
    """A more in depth but slower test suite."""
    session.install("-e", ".", *TEST_DEPENDENCIES)
    test_dir = session.posargs or ["tests"]
    session.run("pytest", "-v", "--tb=no", "--show-capture=no", "--net-pypiserver", "--all-packages", *test_dir)
