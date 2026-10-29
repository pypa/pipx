"""Preview a release locally, or dispatch its protected workflow."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final

_ROOT: Final[Path] = Path(__file__).resolve().parent.parent


class _Options(argparse.Namespace):
    bump: str
    dispatch: bool


def main() -> None:
    parser: Final = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bump", choices=("auto", "major", "minor", "patch"), default="auto")
    parser.add_argument("--dispatch", action="store_true", help="start the protected release workflow on GitHub")
    args: Final = parser.parse_args(namespace=_Options())
    if args.dispatch:
        _run(
            "gh",
            "workflow",
            "run",
            "pre-release.yml",
            "--repo",
            "pypa/pipx",
            "--ref",
            "main",
            "-f",
            f"bump={args.bump}",
        )
        return
    with TemporaryDirectory(prefix="pipx-release-") as temporary_directory:
        source: Final[Path] = Path(temporary_directory) / "source"
        _run("git", "clone", "--quiet", "--shared", str(_ROOT), str(source))
        tags: Final[str] = _run("git", "tag", "--list", cwd=source, capture_output=True).stdout
        version: Final[str] = _run(
            "release-creator",
            "tags",
            "--next",
            args.bump,
            "--directory",
            "changelog.d",
            cwd=source,
            stdin_text=tags,
            capture_output=True,
        ).stdout.strip()
        previous: Final[str] = _run(
            "release-creator",
            "tags",
            version,
            "--previous",
            cwd=source,
            stdin_text=tags,
            capture_output=True,
        ).stdout.strip()
        _run(
            "release-creator",
            "fragments",
            "--directory",
            "changelog.d",
            "--repository",
            "pypa/pipx",
            cwd=source,
        )
        _run("towncrier", "build", "--yes", "--version", version, cwd=source)
        _run(
            "release-creator",
            "contributors",
            "--changelog",
            "docs/changelog.rst",
            "--version",
            version,
            "--repository",
            "pypa/pipx",
            cwd=source,
        )
        try:
            _run("prek", "run", "docstrfmt", "--files", "docs/changelog.rst", cwd=source)
        except subprocess.CalledProcessError:  # the hook fails when it rewrites the file, so a rerun checks the result
            _run("prek", "run", "docstrfmt", "--files", "docs/changelog.rst", cwd=source)
        _run("prek", "run", "--all-files", cwd=source)
        _run("git", "config", "user.name", "pipx release preview", cwd=source)
        _run("git", "config", "user.email", "preview@localhost", cwd=source)
        _run("git", "add", "docs/changelog.rst", "changelog.d", cwd=source)
        _run("git", "commit", "-m", f"Release {version}", cwd=source)
        _run("git", "tag", "-a", version, "-m", f"release {version}", cwd=source)
        notes: Final[str] = _run(
            "release-creator",
            "notes",
            "--changelog",
            "docs/changelog.rst",
            "--tag",
            version,
            "--repository",
            "pypa/pipx",
            "--artifact-url",
            f"https://pypi.org/project/pipx/{version}/",
            *(("--previous", previous) if previous else ()),
            cwd=source,
            capture_output=True,
        ).stdout
        build_environment: Final[Path] = Path(temporary_directory) / "build"
        _run("uv", "venv", "--python", "3.15", str(build_environment), cwd=source)
        _run(
            "uv",
            "pip",
            "sync",
            "--preview-features",
            "pylock",
            "--python",
            str(build_environment),
            "--group",
            "build",
            "--require-hashes",
            "pylock.toml",
            cwd=source,
        )
        epoch: Final[str] = _run("git", "log", "-1", "--format=%ct", cwd=source, capture_output=True).stdout.strip()
        _run(
            "uv",
            "build",
            "--python",
            str(build_environment),
            "--sdist",
            "--wheel",
            "--no-build-isolation",
            "--out-dir",
            "dist",
            cwd=source,
            env=dict(os.environ, SOURCE_DATE_EPOCH=epoch),
        )
        sys.stdout.write(notes)


def _run(
    *command: str,
    cwd: Path = _ROOT,
    stdin_text: str | None = None,
    capture_output: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        input=stdin_text,
        capture_output=capture_output,
        stdout=None if capture_output else sys.stderr,
        text=True,
        check=True,
        shell=False,
        env=env,
    )


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        if error.stderr:
            sys.stderr.write(error.stderr)
        raise SystemExit(error.returncode) from None
