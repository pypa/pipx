import sys
from pathlib import Path
from typing import List

from pipx_release import copy_file_replace_line, python_mypy_ok


def fix_version_py(new_version: str) -> bool:
    version_code_file = Path("src/pipx/version.py")
    new_version_code_file = Path("src/pipx/version.py.new")
    new_version_list = new_version.split(".")

    copy_file_replace_line(
        version_code_file,
        new_version_code_file,
        line_re=r"^\s*__version_info__\s*=",
        new_line=f'__version_info__ = ({", ".join(new_version_list)})',
    )
    if python_mypy_ok(new_version_code_file):
        new_version_code_file.rename(version_code_file)
        return True
    else:
        print(f"Aborting: syntax error in {new_version_code_file}")
        return False


def fix_changelog(new_version: str) -> bool:
    changelog_file = Path("docs/changelog.md")
    new_changelog_file = Path("docs/changelog.new")

    copy_file_replace_line(
        changelog_file, new_changelog_file, line_re=r"^\s*dev\s*$", new_line=new_version
    )
    new_changelog_file.rename(changelog_file)

    return True


def pre_release(new_version: str) -> int:
    if fix_version_py(new_version) and fix_changelog(new_version):
        return 0
    else:
        return 1


def main(argv: List[str]) -> int:
    if len(argv) > 1:
        new_version = argv[1]
    else:
        new_version = input("Enter new version: ")
    return pre_release(new_version)


if __name__ == "__main__":
    try:
        status = main(sys.argv)
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        status = 130

    sys.exit(status)
