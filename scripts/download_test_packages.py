#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import List

from list_test_packages import create_test_packages_list
from test_packages_support import get_platform_list_path


def process_command_line(argv):
    """Process command line invocation arguments and switches.

    Args:
        argv: list of arguments, or `None` from ``sys.argv[1:]``.

    Returns:
        argparse.Namespace: named attributes of arguments and switches
    """
    # script_name = argv[0]
    argv = argv[1:]

    # initialize the parser object:
    parser = argparse.ArgumentParser(
        description="Check and update as needed the pipx tests package cache "
        "for use with the pipx tests local pypiserver."
    )

    # specifying nargs= puts outputs of parser in list (even if nargs=1)

    # required arguments
    parser.add_argument(
        "package_list_dir",
        help="Directory where platform- and python-specific package lists are found for pipx tests.",
    )
    parser.add_argument(
        "output_dir", help="Directory to store the packages distribution files."
    )

    # switches/options:
    # parser.add_argument(
    #    '-s', '--max_size', action='store',
    #    help='String specifying maximum size of images.  ' \
    #            'Larger images will be resized. (e.g. "1024x768")')
    # parser.add_argument(
    #     "-v",
    #     "--verbose",
    #     action="store_true",
    #     help="Maximum verbosity, especially for pip operations.",
    # )

    args = parser.parse_args(argv)

    return args


def update_test_packages_cache(
    package_list_dir_path: Path, output_dir_path: Path
) -> int:
    exit_code = 0

    platform_package_list_path = get_platform_list_path(package_list_dir_path)
    output_dir_path.mkdir(exist_ok=True)

    output_dir_files = list(output_dir_path.iterdir())
    output_dir_hits = []

    if not platform_package_list_path.exists():
        print(
            f"WARNING.  File {str(platform_package_list_path)}\n"
            "    does not exist.  Creating now...",
            file=sys.stderr,
        )
        create_list_returncode = create_test_packages_list(
            package_list_dir_path,
            package_list_dir_path / "tests_primary_packages.txt",
            verbose=False,
        )
        if create_list_returncode == 0:
            print(
                f"File {str(platform_package_list_path)}\n"
                "    successfully created.  Please check this file in to the"
                "    repository for future use.",
                file=sys.stderr,
            )
        else:
            print(
                f"ERROR.  Unable to create {str(platform_package_list_path)}\n"
                "    Cannot continue.\n",
                file=sys.stderr,
            )
            return 1

    try:
        platform_package_list_fh = platform_package_list_path.open("r")
    except IOError:
        print(
            f"ERROR.  File {str(platform_package_list_path)}\n"
            "    is not readable.  Cannot continue.\n",
            file=sys.stderr,
        )
        return 1
    else:
        platform_package_list_fh.close()

    print(
        f"Using {str(platform_package_list_path)}\n    to specify needed package files."
    )
    print(f"Ensuring {str(output_dir_path)}\n    contains necessary package files...")

    with platform_package_list_path.open("r") as platform_package_list_fh:
        for line in platform_package_list_fh:
            package_spec = line.strip()
            package_spec_re = re.search(r"^(.+)==(.+)$", package_spec)
            if not package_spec_re:
                print(f"ERROR: CANNOT PARSE {package_spec}", file=sys.stderr)
                exit_code = 1
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
                exit_code = 1
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
                print(f"ERROR downloading {package_spec}", file=sys.stderr)
                print(pip_download_process.stdout, file=sys.stderr)
                print(pip_download_process.stderr, file=sys.stderr)
                exit_code = 1

    print(f"EXISTING (found) FILES: {len(output_dir_hits)}")
    print(f"LEFTOVER (unused) FILES: {len(output_dir_files)}")
    for unused_file in output_dir_files:
        print(f"    Deleting {unused_file}...")
        unused_file.unlink()

    return exit_code


def main(argv: List[str]) -> int:
    args = process_command_line(argv)
    return update_test_packages_cache(
        Path(args.package_list_dir), Path(args.output_dir)
    )


if __name__ == "__main__":
    try:
        status = main(sys.argv)
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        status = 130

    sys.exit(status)
