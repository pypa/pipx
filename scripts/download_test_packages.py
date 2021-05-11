#!/usr/bin/env python3
import re
import subprocess
import sys
from pathlib import Path
from typing import List


def main(argv: List[str]) -> int:
    print(argv)
    if len(argv) < 3:
        print(
            "Please supply filename of test package list as first argument.",
            file=sys.stderr,
        )
        print(
            "Please supply name of the output directory as second argument.",
            file=sys.stderr,
        )
        return 1
    input_file_path = Path(argv[1])
    output_dir_path = Path(argv[2])

    output_dir_path.mkdir(exist_ok=True)

    output_dir_files = list(output_dir_path.iterdir())
    output_dir_hits = []
    with input_file_path.open("r") as input_fh:
        for line in input_fh:
            package_spec = line.strip()
            package_spec_re = re.search(r"^(.+)==(.+)$", package_spec)
            if not package_spec_re:
                print(
                    f"CANNOT PARSE PACKAGE SPEC:\n    {package_spec}", file=sys.stderr
                )
                continue

            package_name = package_spec_re.group(1)
            package_ver = package_spec_re.group(2)
            package_dist_patt = (
                re.escape(package_name)
                + r"-"
                + re.escape(package_ver)
                + r"(.tar.gz|.zip|-)"
            )
            matches = []
            for output_dir_file in output_dir_files:
                if re.search(package_dist_patt, output_dir_file.name):
                    matches.append(output_dir_file)
            if len(matches) == 1:
                output_dir_files.remove(matches[0])
                output_dir_hits.append(matches[0])
                continue
            elif len(matches) > 1:
                print("ERROR: more than one match for {package_spec}.", file=sys.stderr)
                print(f"    {matches}", file=sys.stderr)
                continue

            pip_download_process = subprocess.run(
                [
                    "pip",
                    "download",
                    "--no-deps",
                    package_spec,
                    "-d",
                    str(output_dir_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            if pip_download_process.returncode == 0:
                print(f"Successfully downloaded {package_spec}")
            else:
                print(f"ERRROR downloading {package_spec}", file=sys.stderr)
                print(pip_download_process.stdout, file=sys.stderr)
                print(pip_download_process.stderr, file=sys.stderr)

    print(f"MATCHED (found) FILES: {len(output_dir_hits)}")
    print(f"LEFTOVER (unused) FILES: {len(output_dir_files)}")
    for unused_file in output_dir_files:
        print(f"    Deleting {unused_file}...")
        unused_file.unlink()

    return 0


if __name__ == "__main__":
    try:
        status = main(sys.argv)
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        status = 130

    sys.exit(status)
