"""Preview a release locally, or dispatch its protected workflow."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final

_ROOT: Final = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bump", choices=("auto", "major", "minor", "patch"), default="auto")
    parser.add_argument("--dispatch", action="store_true", help="start the protected release workflow on GitHub")
    args = parser.parse_args()
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
    if _run("git", "status", "--porcelain", cwd=_ROOT, capture_output=True).stdout:
        msg = "commit or stash changes before previewing a release"
        raise RuntimeError(msg)

    with TemporaryDirectory(prefix="pipx-release-") as temporary_directory:
        source = Path(temporary_directory) / "source"
        _run("git", "clone", "--quiet", "--shared", str(_ROOT), str(source))
        tags = _run("git", "tag", "--list", cwd=source, capture_output=True).stdout
        version = _run(
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
        previous = _run(
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
            "--git",
            "--resolve-authors",
            cwd=source,
        )
        _run("towncrier", "build", "--yes", "--version", version, cwd=source)
        try:
            _run("prek", "run", "docstrfmt", "--files", "docs/changelog.rst", cwd=source)
        except subprocess.CalledProcessError:
            _run("prek", "run", "docstrfmt", "--files", "docs/changelog.rst", cwd=source)
        _run("prek", "run", "--all-files", cwd=source)
        _run("git", "config", "user.name", "pipx release preview", cwd=source)
        _run("git", "config", "user.email", "preview@localhost", cwd=source)
        _run("git", "add", "docs/changelog.rst", "changelog.d", cwd=source)
        _run("git", "commit", "-m", f"Release {version}", cwd=source)
        _run("git", "tag", "-a", version, "-m", f"release {version}", cwd=source)
        note_args = [
            "release-creator",
            "notes",
            "--changelog",
            "docs/changelog.rst",
            "--tag",
            version,
            "--repository",
            "pypa/pipx",
            "--issue-role",
            "issue",
            "--artifact-url",
            f"https://pypi.org/project/pipx/{version}/",
        ]
        if previous:
            note_args.extend(("--previous", previous))
        notes = _run(*note_args, cwd=source, capture_output=True).stdout
        if "### " not in notes:
            msg = f"{version} has no user-facing release notes"
            raise RuntimeError(msg)
        _run(
            "uv",
            "build",
            "--sdist",
            "--wheel",
            "--out-dir",
            "dist",
            cwd=source,
            env=dict(os.environ, UV_EXCLUDE_NEWER="1 week"),
        )
        _run(
            "twine",
            "check",
            *(str(path) for path in sorted((*source.glob("dist/*.whl"), *source.glob("dist/*.tar.gz")))),
            cwd=source,
        )
        _run("check-wheel-contents", "--no-config", "dist", cwd=source)
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
    main()


__all__ = [
    "main",
]
