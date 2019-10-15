#!/usr/bin/env python3

import os
import subprocess
import sys
import tempfile
import unittest
from shutil import which
from pathlib import Path

from pipx.util import WINDOWS


PIPX_PATH = CURDIR = Path(__file__).parent.parent

assert not hasattr(sys, "real_prefix"), "Tests cannot run under virtualenv"
assert getattr(sys, "base_prefix", sys.prefix) != sys.prefix, "Tests require venv"


class TestPipxCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._shared_dir = tempfile.TemporaryDirectory(prefix="pipx_shared_dir_")

    @classmethod
    def tearDownClass(cls):
        cls._shared_dir.cleanup()

    def setUp(self):
        """install pipx to temporary directory and save pipx binary path"""

        temp_dir = tempfile.TemporaryDirectory(prefix="pipx_tests_")
        home_dir = Path(temp_dir.name) / "subdir" / "pipxhome"
        bin_dir = Path(temp_dir.name) / "otherdir" / "pipxbindir"

        Path(temp_dir.name).mkdir(exist_ok=True)
        env = os.environ
        env["PIPX_SHARED_LIBS"] = str(self._shared_dir.name)
        env["PIPX_HOME"] = str(home_dir)
        env["PIPX_BIN_DIR"] = str(bin_dir)

        if WINDOWS:
            pipx_bin = "pipx.exe"
        else:
            pipx_bin = "pipx"

        self.assertTrue(which(pipx_bin))
        self.pipx_bin = pipx_bin
        self.temp_dir = temp_dir
        self.bin_dir = bin_dir
        print()  # blank line to unit tests doesn't get overwritten by pipx output

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_basic_commands(self):
        subprocess.run([self.pipx_bin, "--version"], check=True)
        subprocess.run([self.pipx_bin, "list"], check=True)
        subprocess.run([self.pipx_bin, "completions"], check=True)

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
        stdout = ret.stdout.decode().lower()
        stderr = ret.stderr.decode().lower()
        print(stdout)
        print(stderr)
        self.assertTrue("pipx" not in stdout)
        self.assertTrue("pipx" not in stderr)

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
        if WINDOWS:
            all_packages = easy_packages
        else:
            all_packages = easy_packages + tricky_packages

        for package in all_packages:
            subprocess.run([self.pipx_bin, "install", package], check=True)

        ret = subprocess.run(
            [self.pipx_bin, "list"], check=True, stdout=subprocess.PIPE
        )

        for package in all_packages:
            self.assertTrue(package in ret.stdout.decode())

    def test_force_install(self):
        subprocess.run(
            [self.pipx_bin, "install", "cowsay"], check=True, stdout=subprocess.PIPE
        )

        subprocess.run(
            [self.pipx_bin, "install", "cowsay", "--force"],
            check=True,
            stdout=subprocess.PIPE,
        )

    def test_shared_libs_automatically_recreated(self):
        self._shared_dir.cleanup()
        subprocess.run([self.pipx_bin, "install", "pycowsay"], check=True)

    def test_install_no_packages_found(self):
        ret = subprocess.run(
            [self.pipx_bin, "install", "--include-deps", "pygdbmi"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertTrue("No apps associated with package" in ret.stderr.decode())

    # TODO determine why this is failing in CI
    # def test_editable_install(self):
    #     subprocess.run(
    #         [self.pipx_bin, "install", "-e", "pipx", "--spec", PIPX_PATH], check=True
    #     )

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
        self.assertTrue("black" in ret.stdout.decode())
        self.assertTrue("apps" not in ret.stdout.decode())
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
                "--include-apps",
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

    def test_upgrade_all(self):
        self.assertNotEqual(
            subprocess.run([self.pipx_bin, "upgrade", "pycowsay"]).returncode, 0
        )
        subprocess.run([self.pipx_bin, "install", "pycowsay"], check=True)
        subprocess.run([self.pipx_bin, "upgrade-all"], check=True)

    def test_reinstall_all(self):
        self.assertNotEqual(
            subprocess.run([self.pipx_bin, "upgrade", "pycowsay"]).returncode, 0
        )
        subprocess.run([self.pipx_bin, "install", "pycowsay"], check=True)
        if WINDOWS:
            py = sys.executable
        else:
            py = "python3"
        subprocess.run([self.pipx_bin, "reinstall-all", py], check=True)

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

    @unittest.skipIf(sys.platform == "win32", reason="fails on Windows")
    def test_existing_symlink_points_to_existing_wrong_location_warning(self):
        self.bin_dir.mkdir(exist_ok=True, parents=True)
        (self.bin_dir / "pycowsay").symlink_to(os.devnull)

        env = os.environ.copy()
        env["PATH"] = f"{str(self.bin_dir)}:{env.get('PATH')}"
        ret = subprocess.run(
            [self.pipx_bin, "install", "pycowsay"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        stdout = ret.stdout.decode()
        stderr = ret.stderr.decode()
        self.assertTrue("File exists at" in stderr)
        self.assertTrue("symlink missing or pointing to unexpected location" in stdout)
        # bin dir was on path, so the warning should NOT appear (even though the symlink
        # pointed to the wrong location)
        self.assertTrue("is not on your PATH environment variable" not in stderr)

    def test_existing_symlink_points_to_nothing(self):
        self.bin_dir.mkdir(exist_ok=True, parents=True)
        (self.bin_dir / "pycowsay").symlink_to("/asdf/jkl")

        env = os.environ.copy()
        env["PATH"] = f"{str(self.bin_dir)}:{env.get('PATH')}"
        ret = subprocess.run(
            [self.pipx_bin, "install", "pycowsay"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=True,
        )
        stdout = ret.stdout.decode()
        self.assertTrue("These apps are now globally available" in stdout)
        self.assertTrue(
            "symlink missing or pointing to unexpected location" not in stdout
        )

    def test_path_warning(self):
        # warning should appear since temp directory is not on PATH
        self.assertTrue(
            "is not on your PATH environment variable."
            in subprocess.run(
                [self.pipx_bin, "install", "pycowsay"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stderr.decode()
        )

        env = os.environ.copy()
        # add bin dir to path, warning should NOT appear now
        env["PATH"] = f"{str(self.bin_dir)}:{env.get('PATH')}"
        self.assertTrue(
            "is not on your PATH environment variable."
            not in subprocess.run(
                [self.pipx_bin, "install", "pycowsay"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            ).stderr.decode()
        )


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestPipxCommands))

    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)

    num_failures = len(result.errors) + len(result.failures)
    return num_failures


if __name__ == "__main__":
    exit(main())
