"""Handles creating a release."""

from __future__ import annotations

from pathlib import Path
from subprocess import call, check_call

from git import Commit, Remote, Repo, TagReference  # type: ignore[import-not-found]
from packaging.version import Version

ROOT_DIR = Path(__file__).resolve().parents[1]
CHANGELOG_DIR = ROOT_DIR / "changelog.d"


def main(version_str: str, *, push: bool) -> None:
    repo = Repo(str(ROOT_DIR))
    if repo.is_dirty():
        msg = "Current repository is dirty. Please commit any changes and try again."
        raise RuntimeError(msg)
    remote = get_remote(repo)
    remote.fetch()
    version = resolve_version(version_str, repo)
    print(f"Releasing {version}")
    release_commit = release_changelog(repo, version)
    tag = tag_release_commit(release_commit, repo, version)
    if push:
        print("Pushing release commit")
        repo.git.push(remote.name, "HEAD:main")
        print("Pushing release tag")
        repo.git.push(remote.name, tag)
    print("All done! ✨ 🍰 ✨")


def resolve_version(version_str: str, repo: Repo) -> Version:
    if version_str not in {"auto", "major", "minor", "patch"}:
        return Version(version_str)
    latest_tag = repo.git.describe("--tags", "--abbrev=0")
    parts = [int(x) for x in latest_tag.split(".")]
    if version_str == "major":
        parts = [parts[0] + 1, 0, 0]
    elif version_str == "minor":
        parts = [parts[0], parts[1] + 1, 0]
    elif version_str == "patch":
        parts[2] += 1
    elif any(CHANGELOG_DIR.glob("*.feature.md")) or any(CHANGELOG_DIR.glob("*.removal.md")):
        parts = [parts[0], parts[1] + 1, 0]
    else:
        parts[2] += 1
    return Version(".".join(str(p) for p in parts))


def get_remote(repo: Repo) -> Remote:
    upstream_remote = "pypa/pipx"
    urls = set()
    for remote in repo.remotes:
        for url in remote.urls:
            if url.rstrip(".git").endswith(upstream_remote):
                return remote
            urls.add(url)
    msg = f"Could not find {upstream_remote} remote, has {urls}"
    raise RuntimeError(msg)


def release_changelog(repo: Repo, version: Version) -> Commit:
    print("Generating release commit")
    check_call(["towncrier", "build", "--yes", "--version", version.public], cwd=str(ROOT_DIR))
    call(["pre-commit", "run", "--all-files"], cwd=str(ROOT_DIR))
    repo.git.add(".")
    check_call(["pre-commit", "run", "--all-files"], cwd=str(ROOT_DIR))
    return repo.index.commit(f"Release {version}")


def tag_release_commit(release_commit: Commit, repo: Repo, version: Version) -> TagReference:
    print("Tagging release commit")
    existing_tags = [x.name for x in repo.tags]
    if str(version) in existing_tags:
        print(f"Deleting existing tag {version}")
        repo.delete_tag(str(version))
    print(f"Creating tag {version}")
    return repo.create_tag(str(version), ref=release_commit, force=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="release")
    parser.add_argument("--version", default="auto")
    parser.add_argument("--no-push", action="store_true")
    options = parser.parse_args()
    main(options.version, push=not options.no_push)
