import py_compile
import re
import sys
from pathlib import Path


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
    if python_syntax_ok(new_version_code_file):
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


def main(argv) -> int:
    new_version = input("Enter new version: ")
    return pre_release(new_version)


if __name__ == "__main__":
    try:
        status = main(sys.argv)
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        status = 130

    sys.exit(status)
