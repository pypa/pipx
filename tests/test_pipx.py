#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import tempfile
import unittest
from shutil import which
from pathlib import Path

from pipx.main import split_run_argv
from pipx.util import WINDOWS


PIPX_PATH = CURDIR = Path(__file__).parent.parent


class PipxStaticTests(unittest.TestCase):
    def run_cmd(self, cmd):
        print(f"Running {' '.join(cmd)!r}")
        rc = subprocess.run(cmd).returncode
        if rc:
            print(f"test failed; exiting with code {rc}")
            exit(rc)

    def test_static(self):
        files = ["pipx", "tests"]
        self.run_cmd(["black", "--check"] + files)
        self.run_cmd(["flake8"] + files)
        self.run_cmd(["mypy"] + files)


class TestPipxArgParsing(unittest.TestCase):
    def test_split_run_argv(self):
        args_to_parse, binary_args = split_run_argv(["pipx"])
        self.assertEqual(args_to_parse, [])
        self.assertEqual(binary_args, [])

        args_to_parse, binary_args = split_run_argv(["pipx", "list"])
        self.assertEqual(args_to_parse, ["list"])
        self.assertEqual(binary_args, [])

        args_to_parse, binary_args = split_run_argv(["pipx", "list", "--help"])
        self.assertEqual(args_to_parse, ["list", "--help"])
        self.assertEqual(binary_args, [])

        args_to_parse, binary_args = split_run_argv(
            ["pipx", "run", "pycowsay", "moo", "--help"]
        )
        self.assertEqual(args_to_parse, ["run", "pycowsay"])
        self.assertEqual(binary_args, ["moo", "--help"])

        args_to_parse, binary_args = split_run_argv(
            ["pipx", "upgrade", "pycowsay", "moo", "--help"]
        )
        self.assertEqual(args_to_parse, ["upgrade", "pycowsay", "moo", "--help"])
        self.assertEqual(binary_args, [])

        args_to_parse, binary_args = split_run_argv(
            ["pipx", "runpip", "pycowsay", "--version"]
        )
        self.assertEqual(args_to_parse, ["runpip", "pycowsay"])
        self.assertEqual(binary_args, ["--version"])


class TestPipxCommands(unittest.TestCase):
    def setUp(self):
        """install pipx to temporary directory and save pipx binary path"""

        temp_dir = tempfile.TemporaryDirectory(prefix="pipx_tests_")
        env = os.environ
        home_dir = Path(temp_dir.name) / "subdir" / "pipxhome"
        bin_dir = Path(temp_dir.name) / "otherdir" / "pipxbindir"
        env["PIPX_HOME"] = str(home_dir)
        env["PIPX_BIN_DIR"] = str(bin_dir)
        if WINDOWS:
            pipx_bin = "pipx.exe"
        else:
            pipx_bin = "pipx"

        subprocess.run(
            [sys.executable, "-m", "pip", "install", ".", "--quiet", "--upgrade"],
            check=True,
        )
        self.assertTrue(which(pipx_bin))
        self.pipx_bin = pipx_bin
        self.temp_dir = temp_dir
        print()  # blank line to unit tests doesn't get overwritten by pipx output

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_basic_commands(self):
        subprocess.run([self.pipx_bin, "--version"], check=True)
        subprocess.run([self.pipx_bin, "list"], check=True)

    def test_pipx_help_contains_text(self):
        ret = subprocess.run(
            [self.pipx_bin, "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertTrue("pipx" in ret.stdout.decode().lower())

    def test_arg_forwarding(self):
        # passing --help to pycowsay should NOT contain the word pipx
        ret = subprocess.run(
            [self.pipx_bin, "run", "pycowsay", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertTrue("pipx" not in ret.stdout.decode().lower())
        self.assertTrue("pipx" not in ret.stderr.decode().lower())

    def test_pipx_venv_cache(self):
        subprocess.run(
            [self.pipx_bin, "run", "--verbose", "pycowsay", "pycowsay args"], check=True
        )
        ret = subprocess.run(
            [
                self.pipx_bin,
                "run",
                "--verbose",
                "pycowsay",
                "different args should re-use cache",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertTrue("Reusing cached venv" in ret.stderr.decode())
        ret = subprocess.run(
            [
                self.pipx_bin,
                "run",
                "--verbose",
                "--no-cache",
                "pycowsay",
                "no cache should remove cache",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertTrue("Removing cached venv" in ret.stderr.decode())

    def test_install(self):
        easy_packages = ["pycowsay", "black"]
        tricky_packages = ["cloudtoken", "awscli", "ansible", "shell-functools"]
        all_packages = easy_packages + tricky_packages

        for package in all_packages:
            subprocess.run([self.pipx_bin, "install", package], check=True)

        ret = subprocess.run(
            [self.pipx_bin, "list"], check=True, stdout=subprocess.PIPE
        )

        for package in all_packages:
            self.assertTrue(package in ret.stdout.decode())

    def test_editable_install(self):
        subprocess.run(
            [self.pipx_bin, "install", "-e", "pipx", "--spec", PIPX_PATH], check=True
        )

    def test_install_existing_package(self):
        subprocess.run([self.pipx_bin, "install", "pycowsay"], check=True)
        subprocess.run([self.pipx_bin, "install", "pycowsay"], check=True)

    def test_runpip(self):
        subprocess.run([self.pipx_bin, "install", "pycowsay"], check=True)
        subprocess.run([self.pipx_bin, "runpip", "pycowsay", "list"], check=True)

    def test_include_deps_install(self):
        self.assertNotEqual(
            subprocess.run(
                [self.pipx_bin, "install", "jupyter", "--spec", "jupyter==1.0.0"]
            ).returncode,
            0,
        )
        self.assertEqual(
            subprocess.run(
                [
                    self.pipx_bin,
                    "install",
                    "--include-deps",
                    "jupyter",
                    "--spec",
                    "jupyter==1.0.0",
                ]
            ).returncode,
            0,
        )

    def test_inject(self):
        subprocess.run([self.pipx_bin, "install", "pycowsay"], check=True)
        ret = subprocess.run(
            [self.pipx_bin, "inject", "pycowsay", "black"],
            stdout=subprocess.PIPE,
            check=True,
        )
        self.assertTrue("black" not in ret.stdout.decode())
        self.assertNotEqual(
            subprocess.run(
                [self.pipx_bin, "inject", "pycowsay", "black", "--include-deps"]
            ).returncode,
            0,
        )
        ret = subprocess.run(
            [
                self.pipx_bin,
                "inject",
                "pycowsay",
                "black",
                "--include-binaries",
                "--include-deps",
            ],
            stdout=subprocess.PIPE,
        )
        self.assertEqual(ret.returncode, 0)
        self.assertTrue("black" in ret.stdout.decode())

    def test_uninstall(self):
        subprocess.run([self.pipx_bin, "install", "pycowsay"], check=True)
        subprocess.run([self.pipx_bin, "uninstall", "pycowsay"], check=True)
        subprocess.run([self.pipx_bin, "uninstall-all"], check=True)

    def test_upgrade(self):
        self.assertNotEqual(
            subprocess.run([self.pipx_bin, "upgrade", "pycowsay"]).returncode, 0
        )
        subprocess.run([self.pipx_bin, "install", "pycowsay"], check=True)
        subprocess.run([self.pipx_bin, "upgrade", "pycowsay"], check=True)

    def test_run_downloads_from_internet(self):
        subprocess.run(
            [
                self.pipx_bin,
                "run",
                "https://gist.githubusercontent.com/cs01/"
                "fa721a17a326e551ede048c5088f9e0f/raw/"
                "6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py",
            ],
            check=True,
        )


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(
        loader.loadTestsFromTestCase(
            PipxStaticTests, TestPipxArgParsing, TestPipxCommands
        )
    )

    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)

    num_failures = len(result.errors) + len(result.failures)
    return num_failures


if __name__ == "__main__":
    exit(main())
