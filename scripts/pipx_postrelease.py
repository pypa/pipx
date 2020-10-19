import py_compile
import re
import subprocess
import sys
from pathlib import Path
from typing import List


def python_mypy_ok(filepath: Path) -> bool:
    mypy_proc = subprocess.run(["mypy", filepath])
    return True if mypy_proc.returncode == 0 else False


def python_syntax_ok(filepath: Path) -> bool:
    compiled_file = filepath.with_suffix(".pyc")
    if py_compile.compile(str(filepath), cfile=str(compiled_file)) is None:
        return False
    else:
        compiled_file.unlink()
        return True


def copy_file_replace_line(
    orig_file: Path, new_file: Path, line_re: str, new_line: str
) -> None:
    old_version_fh = orig_file.open("r")
    new_version_fh = new_file.open("w")
    for line in old_version_fh:
        if re.search(line_re, line):
            new_version_fh.write(new_line + "\n")
        else:
            new_version_fh.write(line)
    old_version_fh.close()
    new_version_fh.close()


def fix_version_py(current_version_list: List[str]) -> bool:
    version_code_file = Path("src/pipx/version.py")
    new_version_code_file = Path("src/pipx/version.py.new")
    new_version_list = current_version_list + ['"dev0"']

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


def main(argv) -> int:
    return post_release()


if __name__ == "__main__":
    try:
        status = main(sys.argv)
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        status = 130

    sys.exit(status)
