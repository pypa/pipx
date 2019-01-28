#!/usr/bin/env python3
import sys
assert sys.version_info >= (3, 6, 0), "Python 3.6+ is required"

import argparse
from pathlib import Path
from shutil import copy, which
import os
import textwrap
from typing import Sequence, Union
import subprocess
import logging


try:
    WindowsError
except NameError:
    WINDOWS = False
else:
    WINDOWS = True


DEFAULT_PIPX_HOME = Path.home() / ".local/pipx/venvs"
DEFAULT_PIPX_BIN_DIR = Path.home() / ".local/bin"


class PipxError(Exception):
    pass


def echo(msg=""):
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()
    sys.exit(1)


def succeed(msg=""):
    if msg:
        echo(msg)
    sys.exit(0)


def _run(cmd: Sequence[Union[str, Path]], check=True) -> int:
    cmd_str = " ".join(str(c) for c in cmd)
    logging.info(f"running {cmd_str}")
    # windows cannot take Path objects, only strings
    cmd_str_list = [str(c) for c in cmd]
    returncode = subprocess.run(cmd_str_list).returncode
    if check and returncode:
        raise PipxError(f"{cmd_str!r} failed")
    return returncode


class Venv:
    def __init__(self, path, *, verbose=False, python=sys.executable):
        self.root = path
        self._python = python
        self.bin_path = path / "bin" if not WINDOWS else path / "Scripts"
        self.python_path = self.bin_path / ("python" if not WINDOWS else "python.exe")
        self.verbose = verbose

    def create_venv(self):
        _run([self._python, "-m", "venv", self.root])
        self.upgrade_package("pip")

    def install_package(self, application):
        before = {child for child in self.bin_path.iterdir()}
        self._run_pip(["install", application])
        after = {child for child in self.bin_path.iterdir()}
        new_binaries = after - before
        new_binaries_str = ", ".join(str(s) for s in new_binaries)
        logging.info(f"downloaded new binaries: {new_binaries_str}")
        return new_binaries

    def upgrade_package(self, package):
        self._run_pip(["install", "--upgrade", package])

    def _run_pip(self, cmd):
        cmd = [str(self.python_path), "-m", "pip"] + cmd
        if not self.verbose:
            cmd.append("-q")
        _run(cmd)


def ensure_pipx_on_path(bin_dir, modify_path):
    if which("pipx"):
        echo("pipx is installed")
        return
    shell = os.environ.get("SHELL", "")
    if "bash" in shell:
        config_file = "~/.bashrc"
    elif "zsh" in shell:
        config_file = "~/.zshrc"
    elif "fish" in shell:
        config_file = "~/.config/fish/config.fish"
    else:
        config_file = None

    if config_file:
        config_file = os.path.expanduser(config_file)

    if modify_path and config_file and os.path.exists(config_file):
        with open(config_file, "a") as f:
            f.write("\n# added by pipx (https://github.com/cs01/pipx)\n")
            if "fish" in shell:
                f.write("set -x PATH %s $PATH\n\n" % bin_dir)
            else:
                f.write('export PATH="%s:$PATH"\n' % bin_dir)
        echo("Added %s to the PATH environment variable in %s" % (bin_dir, config_file))
        echo("")
        echo("Open a new terminal to use pipx")
    else:
        if WINDOWS:
            textwrap.dedent(
                f"""
                Note:
                To finish installation, {str(bin_dir)!r} must be added to your PATH
                environment variable.

                To do this, go to settings and type "Environment Variables".
                In the Environment Variables window edit the PATH variable
                by adding the following to the end of the value, then open a new
                terminal.

                    ;{str(bin_dir)}
            """
            )

        else:
            echo(
                textwrap.dedent(
                    f"""
                    Note:
                    To finish installation, {str(bin_dir)!r} must be added to your PATH
                    environemnt variable.

                    To do this, add the following line to your shell
                    config file (such as ~/.bashrc if using bash):

                        export PATH={str(bin_dir)}:$PATH
                """
                )
            )


def get_fs_package_name(package):
    illegal = ["+", "#", "/", ":"]
    ret = ""
    for x in package:
        if x in illegal:
            ret += "_"
        else:
            ret += x
    return ret


def install(
    pipx_local_venvs,
    pipx_venv,
    package,
    local_bin_dir,
    pipx_exposed_binary,
    python,
    verbose,
):
    pipx_venv.mkdir(parents=True, exist_ok=True)
    pipx_exposed_binary.parent.mkdir(parents=True, exist_ok=True)
    logging.info(f"virtualenv location is {pipx_venv}")
    venv = Venv(pipx_venv, python=python, verbose=verbose)
    venv.create_venv()
    venv.install_package(package)
    binary = venv.bin_path / "pipx" if not WINDOWS else venv.bin_path / "pipx.exe"
    if not binary.is_file():
        fail(f"Expected to find {str(binary)}")

    if WINDOWS:
        # windows creates multiple files that need to be co-located to work,
        # such as pipx.exe and pipx-script.py
        # for name in os.listdir(venv + '/Scripts'):
        for path in venv.bin_path.iterdir():
            if "pipx" in path.name.lower():
                copy(str(path), str(local_bin_dir))

    else:
        if pipx_exposed_binary.is_file():
            if pipx_exposed_binary.resolve().samefile(binary):
                return
            else:
                pipx_exposed_binary.unlink()
        pipx_exposed_binary.symlink_to(binary)


def parse_options(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--src",
        default="pipx-app",
        help=(
            "The specific version of pipx to install. This value is passed "
            'to "pip install <value>". For example, to install from master '
            "use `git+https://github.com/cs01/pipx.git`. "
            "Default: %(default)s"
        ),
    )
    parser.add_argument(
        "--no-modify-path",
        action="store_true",
        help="Don't configure the PATH environment variable",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=("reinstall pipx even if existing installation was found"),
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help=("The Python binary to associate pipx with. Must be v3.6+."),
    )
    parser.add_argument(
        "--verbose", action="store_true", help=("Display more detailed output")
    )
    return parser.parse_args(argv)


def main(argv=sys.argv[1:]):
    args = parse_options(argv)
    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(message)s")

    pipx_local_venvs = Path(os.environ.get("PIPX_HOME", DEFAULT_PIPX_HOME)).resolve()
    local_bin_dir = Path(os.environ.get("PIPX_BIN_DIR", DEFAULT_PIPX_BIN_DIR)).resolve()

    pipx_local_venvs.mkdir(parents=True, exist_ok=True)
    local_bin_dir.mkdir(parents=True, exist_ok=True)

    pipx_exposed_binary = local_bin_dir / ("pipx" if not WINDOWS else "pipx.exe")

    pipx_venv = pipx_local_venvs / "pipx-app"
    if (pipx_venv).exists():
        if args.overwrite:
            echo(f"Overwriting existing pipx installation at {str(pipx_venv)!r}")
        else:
            succeed(
                "You already have pipx installed. Pass the `--overwrite` flag to reinstall. "
                "Type `pipx` to run."
            )
    elif pipx_exposed_binary.is_symlink() and pipx_exposed_binary.resolve().is_file():
        echo("pipx is already installed but not on your PATH")
        ensure_pipx_on_path(local_bin_dir, not args.no_modify_path)
        succeed()

    echo("Installing pipx")
    install(
        pipx_local_venvs,
        pipx_venv,
        args.src,
        local_bin_dir,
        pipx_exposed_binary,
        args.python,
        args.verbose,
    )
    ensure_pipx_on_path(local_bin_dir, not args.no_modify_path)
    print()
    print("Now that pipx is installed you can run these commands.")
    print()
    print("  pipx list")
    print()
    print("  pipx BINARY [BINARY ARGS ...] #  i.e. pipx cowsay moo")
    print()
    print("  pipx install PACKAGE  # i.e. pipx install cowsay")
    print()
    print("  pipx --help")
    print()
    print("Questions or comments? See https://github.com/cs01/pipx")
    print()
    print(f"Enjoy! {'✨ 🌟 ✨' if not WINDOWS else ''}")


if __name__ == "__main__":
    main()
