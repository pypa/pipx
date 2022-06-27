#!/usr/bin/env python3

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from time import sleep
from typing import List, Sequence, Union

logger = logging.getLogger(__name__)
if sys.version_info.major != 3 or sys.version_info.minor < 7:
    exit("Error: python3.7+ is required")


def bold(s: str) -> str:
    return f"\033[1m{s}\033[0m"


class PipxInstallationError(RuntimeError):
    pass


WINDOWS = os.name == "nt"

DEFAULT_PIPX_HOME = Path.home() / ".local/pipx/venvs"
DEFAULT_PIPX_BIN_DIR = Path.home() / ".local/bin"


def run(cmd: Sequence[Union[str, Path]], check=True) -> int:
    cmd_str = " ".join(str(c) for c in cmd)
    logger.debug(f"running {cmd_str}")

    # windows cannot take Path objects, only strings
    cmd_str_list = [str(c) for c in cmd]
    returncode = subprocess.run(
        cmd_str_list, env={**os.environ, "USE_EMOJI": "0"}
    ).returncode
    if check and returncode:
        raise RuntimeError(f"{cmd_str!r} failed")
    return returncode


class Venv:
    def __init__(self, path: Path, *, verbose=False, python=sys.executable):
        self.root = path
        self._python = python
        self.bin_path = path / "bin" if not WINDOWS else path / "Scripts"
        self.python_path = self.bin_path / ("python" if not WINDOWS else "python.exe")
        self.verbose = verbose

    def create_venv(self):
        run([self._python, "-m", "venv", self.root])
        self.upgrade_package("pip")

    def install_package(self, application):
        self.run_pip(["install", application])

    def upgrade_package(self, package):
        self.run_pip(["install", "--upgrade", package])

    def run_pip(self, cmd: List[str]):
        cmd = [str(self.python_path), "-m", "pip"] + cmd
        if not self.verbose:
            cmd.append("-q")
        run(cmd)

    def run_python(self, cmd: List[str]):
        cmd = [str(self.python_path)] + cmd
        run(cmd)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Installer script to install pipx. After installing, pipx will be available for use. "
        + "pipx will be by itself, so you can run `pipx upgrade pipx` or `pipx uninstall pipx`. "
        + "Environment variables PIPX_BIN_DIR and PIPX_HOME can be used."
    )
    parser.add_argument(
        "--spec",
        default="pipx",
        help=(
            "The package specification of pipx to install. This value is passed "
            'to "pip install <value>". For example, to install from the github repository '
            "use `git+https://github.com/pypa/pipx.git`. "
            "Default: %(default)s"
        ),
    )
    parser.add_argument(
        "--no-modify-path",
        action="store_true",
        help="Don't configure the PATH environment variable",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=("reinstall pipx even if existing installation was found"),
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help=("The Python binary to associate pipx with. Must be v3.7+."),
    )
    parser.add_argument(
        "--verbose", action="store_true", help=("Display more detailed output")
    )
    parser.add_argument(
        "--nowait",
        action="store_true",
        help=("Proceed with installation without waiting"),
    )
    return parser.parse_args()


def install_pipx(
    pipx_spec: str, python_bin: str, verbose: bool, no_modify_path: bool
) -> None:
    with tempfile.TemporaryDirectory() as venv_dir:
        venv = Venv(Path(venv_dir), python=python_bin, verbose=verbose)
        venv.create_venv()

        install_pipx_cmd = ["-m", "pip", "install", pipx_spec]
        if not verbose:
            install_pipx_cmd.append("--quiet")
        logger.debug("Installing pipx in temp venv")
        venv.run_python(install_pipx_cmd)
        # now run it to install itself
        logger.debug("Installing pipx to system")
        venv.run_python(
            ["-m", "pipx", "install", pipx_spec, "--force", "--python", python_bin]
        )
        if no_modify_path:
            logger.debug("Not modifing user's path")
        else:
            logger.debug("Ensuring pipx is on user's path")
            venv.run_python(["-m", "pipx", "ensurepath", "--force"])


def main():
    args = parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    pipx_local_venvs = Path(os.environ.get("PIPX_HOME", DEFAULT_PIPX_HOME)).resolve()
    local_bin_dir = Path(os.environ.get("PIPX_BIN_DIR", DEFAULT_PIPX_BIN_DIR)).resolve()

    pipx_local_venvs.mkdir(parents=True, exist_ok=True)
    local_bin_dir.mkdir(parents=True, exist_ok=True)

    pipx_venv = pipx_local_venvs / "pipx"
    logger.info(bold("Welcome to the pipx installer!"))
    logger.info("")

    remove_existing_venv = False
    if (pipx_venv).exists():
        if args.force:
            remove_existing_venv = True
        else:
            logger.error(
                "pipx is already installed. To reinstall, pass the `--force` flag."
            )
            logger.error("")
            logger.error(
                "If you don't want to reinstall, go ahead and use pipx by typing `pipx`."
            )
            logger.error("")
            logger.error(f"If you want to uninstall, run {bold('pipx uninstall pipx')}")
            return

    logger.info("This will download and globally install pipx for you.")
    logger.info(
        "It does this by installing pipx to a temporary location, then uses the"
    )
    logger.info("temporarily-installed pipx to install pipx system-wide.")
    logger.info("")
    logger.info("pipx will be installed to:")
    logger.info("")
    logger.info(f"  {local_bin_dir}")
    logger.info("")
    logger.info("This can be modified with the PIPX_BIN_DIR environment variable.")
    logger.info("")
    logger.info("Virtual environments for installed packages will be created at:")
    logger.info("")
    logger.info(f"  {pipx_local_venvs}")
    logger.info("")
    logger.info("This can be modified with the PIPX_HOME environment variable.")
    logger.info("")
    logger.info(f"You can uninstall anytime with {bold('pipx uninstall pipx')}")
    logger.info("")
    logger.info("The following options have been specified:")
    logger.info("")
    logger.info(
        f"  modify PATH variable in shell: {bold('no')if args.no_modify_path else bold('yes')}"
    )
    logger.info(f"  python: {bold(args.python)}")
    logger.info(f"  pipx package specification: {bold(args.spec)}")
    if remove_existing_venv:
        logger.info(f"  will overwrite existing installation at {bold(pipx_venv)}")
    logger.info("")

    if not args.nowait:
        sleep_time = 10
        logger.info(
            f"Waiting {sleep_time} seconds before continuing (pass --nowait to run immediately)..."
        )
        sleep(sleep_time)

    logger.info("")

    if remove_existing_venv:
        logger.warning(
            f"Removing existing pipx installation at {str(pipx_venv)!r} since --force was passed"
        )
        shutil.rmtree(pipx_venv)

    install_pipx(args.spec, args.python, args.verbose, args.no_modify_path)
    logger.info("")
    logger.info("Try running 'pipx list' or 'pipx install'")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("")
        logger.info("")
        logger.info("Exiting pipx installation")
        exit(1)
    except PipxInstallationError as e:
        logger.error("An error was encountered:")
        exit(e)
