import re
import sys
from pathlib import Path
from typing import List

from pipx_release import copy_file_replace_line, python_mypy_ok


def fix_version_py(current_version_list: List[str]) -> bool:
    version_code_file = Path("src/pipx/version.py")
    new_version_code_file = Path("src/pipx/version.py.new")
    # Version with "dev0" suffix precedes version without "dev0" suffix,
    #   so to follow previous version we must add to version number before
    #   appending "dev0".
    new_version_list = current_version_list + ["1", '"dev0"']

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


def fix_changelog() -> bool:
    changelog_file = Path("docs/changelog.md")
    new_changelog_file = Path("docs/changelog.new")

    old_version_fh = changelog_file.open("r")
    new_version_fh = new_changelog_file.open("w")
    new_version_fh.write("dev\n\n\n")
    for line in old_version_fh:
        new_version_fh.write(line)
    old_version_fh.close()
    new_version_fh.close()

    new_changelog_file.rename(changelog_file)

    return True


def get_current_version() -> List[str]:
    version_code_file = Path("src/pipx/version.py")
    version_fh = version_code_file.open("r")

    version = None
    for line in version_fh:
        version_re = re.search(r"^\s*__version_info__\s*=\s*\(([^)]+)\)", line)
        if version_re:
            version = version_re.group(1)

    if version is not None:
        return version.split(", ")
    else:
        return []


def post_release() -> int:
    current_version_list = get_current_version()
    if not current_version_list:
        return 1

    if fix_version_py(current_version_list) and fix_changelog():
        return 0
    else:
        return 1


def main(argv: List[str]) -> int:
    return post_release()


if __name__ == "__main__":
    try:
        status = main(sys.argv)
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        status = 130

    sys.exit(status)
