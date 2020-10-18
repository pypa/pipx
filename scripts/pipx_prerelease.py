import py_compile
import sys
from pathlib import Path


def python_syntax_ok(filepath: Path) -> bool:
    compiled_file = filepath.with_suffix(".pyc")
    if py_compile.compile(str(filepath), cfile=str(compiled_file)) is None:
        return False
    else:
        compiled_file.unlink()
        return True


def pre_release(new_version: str) -> int:
    version_code_file = Path("src/pipx/version.py")
    new_version_code_file = Path("src/pipx/version.py.new")
    new_version_list = new_version.split(".")
    new_version_line = f'__version_info__ = ({", ".join(new_version_list)})\n'

    old_version_fh = version_code_file.open("r")
    new_version_fh = new_version_code_file.open("w")
    for line in old_version_fh:
        if line.lstrip().startswith("__version_info__"):
            new_version_fh.write(new_version_line)
        else:
            new_version_fh.write(line)
    old_version_fh.close()
    new_version_fh.close()

    if python_syntax_ok(new_version_code_file):
        new_version_code_file.rename(version_code_file)
        return 0
    else:
        print(f"Aborting: syntax error in {new_version_code_file}")
        return 1


def main(argv) -> int:
    new_version = input("Enter new version: ")
    return pre_release(new_version)


if __name__ == "__main__":
    try:
        status = main(sys.argv)
    except KeyboardInterrupt:
        # Make a very clean exit (no debug info) if user breaks with Ctrl-C
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        # exit error code for Ctrl-C
        status = 130

    sys.exit(status)
