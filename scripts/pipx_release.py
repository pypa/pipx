import re
import subprocess
from pathlib import Path


def python_mypy_ok(filepath: Path) -> bool:
    mypy_proc = subprocess.run(["mypy", filepath])
    return True if mypy_proc.returncode == 0 else False


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
