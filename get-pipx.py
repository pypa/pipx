#!/usr/bin/env python3

import argparse
from pathlib import Path
from shutil import which
import sys
import os
import textwrap
import subprocess
import logging

DEFAULT_PIPX_HOME = Path.home() / ".local/pipx/venvs"
DEFAULT_PIPX_BIN_DIR = Path.home() / ".local/bin"


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


def _run(cmd, check=True):
    cmd_str = " ".join(str(c) for c in cmd)
    logging.info(f"running {cmd_str}")
    returncode = subprocess.run(cmd).returncode
    if check and returncode:
        fail(f"{cmd_str!r} failed")


class Venv:
    def __init__(self, path, *, verbose=False, python="python3"):
        self.root = path
        self._python = python
        self.bin_path = path / "bin"
        self.pip_path = self.bin_path / "pip"
        self.python_path = self.bin_path / "python"
        self.verbose = verbose

    def create_venv(self):
        _run([self._python, "-m", "venv", self.root])
        self.upgrade_package("pip")

    def install_package(self, application):
        before = set(child for child in self.bin_path.iterdir())
        self._run_pip(["install", application])
        after = set(child for child in self.bin_path.iterdir())
        new_binaries = after - before
        new_binaries_str = ", ".join(str(s) for s in new_binaries)
        logging.info(f"downloaded new binaries: {new_binaries_str}")
        return new_binaries

    def upgrade_package(self, package):
        self._run_pip(["install", "--upgrade", package])

    def _run_pip(self, cmd):
        cmd = [self.pip_path] + cmd
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
        echo("Open a new terminal to use pipx")
    else:
        echo(
            textwrap.dedent(
                """
            %(sep)s

            Note:
              To finish installation, %(bin_dir)s must be added to your PATH.
              This can be done by adding the following line to your shell
              config file:

              export PATH=%(bin_dir)s:$PATH

            %(sep)s
            """
                % dict(sep="=" * 60, bin_dir=bin_dir)
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


def install(pipx_local_venvs, package, local_bin_dir, pipx_symlink, python, verbose):
    venv_dir = pipx_local_venvs / "pipx"
    venv_dir.mkdir(parents=True, exist_ok=True)
    pipx_symlink.parent.mkdir(parents=True, exist_ok=True)
    logging.info(f"virtualenv location is {venv_dir}")
    venv = Venv(venv_dir, python=python, verbose=verbose)
    venv.create_venv()
    venv.install_package(package)
    binary = venv.bin_path / "pipx"
    if not binary.is_file():
        fail(f"Expected to find {str(binary)}")
    if pipx_symlink.is_file():
        if pipx_symlink.resolve().samefile(binary):
            echo(f"re-using existing symlink at {str(pipx_symlink)}")
        else:
            pipx_symlink.unlink()
    else:
        pipx_symlink.symlink_to(binary)


def parse_options(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--src",
        default="git+https://github.com/cs01/pipx.git",
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

    pipx_symlink = local_bin_dir / "pipx"

    if which("pipx"):
        if args.overwrite:
            echo("reinstalling pipx")
        else:
            succeed("You already have pipx installed. Type `pipx` to run.")
    elif pipx_symlink.is_symlink() and pipx_symlink.resolve().is_file():
        echo("pipx is already installed but not on your PATH")
        ensure_pipx_on_path(local_bin_dir, not args.no_modify_path)
        succeed()

    echo("Installing pipx")
    install(
        pipx_local_venvs,
        args.src,
        local_bin_dir,
        pipx_symlink,
        args.python,
        args.verbose,
    )
    ensure_pipx_on_path(local_bin_dir, not args.no_modify_path)
    print()
    print("Now that pipx is installed, we suggest you run one of these commands.")
    print()
    print("  pipx BINARY [BINARY ARGS ...] #  i.e. pipx cowsay moo")
    print()
    print("  pipx install PACKAGE  # i.e. pipx install cowsay")
    print()
    print("  pipx --help  # to see options")
    print()
    print("Questions or comments? See https://github.com/cs01/pipx")
    print("Enjoy! ✨ 🌟 ✨")

if __name__ == "__main__":
    main()
