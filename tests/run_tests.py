from distutils.spawn import find_executable
import os
from pathlib import Path
import unittest
import subprocess
import sys
import tempfile
from pipx.main import split_run_argv
from pipx.util import WINDOWS


class TestPipx(unittest.TestCase):
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
            ["pipx", "run", "cowsay", "moo", "--help"]
        )
        self.assertEqual(args_to_parse, ["run", "cowsay"])
        self.assertEqual(binary_args, ["moo", "--help"])

        args_to_parse, binary_args = split_run_argv(
            ["pipx", "upgrade", "cowsay", "moo", "--help"]
        )
        self.assertEqual(args_to_parse, ["upgrade", "cowsay", "moo", "--help"])
        self.assertEqual(binary_args, [])

    def test_pipx(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.environ
            home_dir = Path(d) / "subdir" / "pipxhome"
            bin_dir = Path(d) / "otherdir" / "pipxbindir"
            if WINDOWS:
                pipx_bin = "pipx.exe"
            else:
                pipx_bin = "pipx"

            env["PIPX_HOME"] = str(home_dir)
            env["PIPX_BIN_DIR"] = str(bin_dir)

            subprocess.run(
                [sys.executable, "-m", "pip", "install", ".", "--verbose", "--upgrade"],
                env=env,
                check=True,
            )

            self.assertTrue(find_executable(pipx_bin))

            subprocess.run([pipx_bin, "--version"], check=True)
            subprocess.run([pipx_bin, "list"], check=True)

            # pipx help should contain the word pipx
            ret = subprocess.run(
                [pipx_bin, "--help"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            self.assertTrue("pipx" in ret.stdout.decode().lower())

            # passing --help to cowsay should NOT contain the word pipx
            ret = subprocess.run(
                [pipx_bin, "run", "cowsay", "--help"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertTrue("pipx" not in ret.stdout.decode().lower())
            self.assertTrue("pipx" not in ret.stderr.decode().lower())

            subprocess.run(
                [pipx_bin, "run", "--verbose", "cowsay", "cowsay args"], check=True
            )
            ret = subprocess.run(
                [
                    pipx_bin,
                    "run",
                    "--verbose",
                    "cowsay",
                    "different args should re-use cache",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            self.assertTrue("Reusing cached venv" in ret.stderr.decode())
            ret = subprocess.run(
                [
                    pipx_bin,
                    "run",
                    "--verbose",
                    "--no-cache",
                    "cowsay",
                    "no cache should remove cache",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            self.assertTrue("Removing cached venv" in ret.stderr.decode())
            subprocess.run([pipx_bin, "install", "cowsay"], check=True)
            subprocess.run([pipx_bin, "install", "black"], check=True)
            subprocess.run([pipx_bin, "inject", "black", "aiohttp"], check=True)
            subprocess.run(
                [pipx_bin, "inject", "black", "aiohttp", "pygdbmi"], check=True
            )
            subprocess.run([pipx_bin, "install", "ansible"], check=True)
            subprocess.run([pipx_bin, "install", "shell-functools"], check=True)
            subprocess.run([pipx_bin, "list"], check=True)
            subprocess.run([pipx_bin, "upgrade", "cowsay"], check=True)
            subprocess.run([pipx_bin, "uninstall", "cowsay"], check=True)
            subprocess.run(
                [
                    pipx_bin,
                    "run",
                    "https://gist.githubusercontent.com/cs01/"
                    "fa721a17a326e551ede048c5088f9e0f/raw/"
                    "6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py",
                ],
                check=True,
            )
            self.assertNotEqual(
                subprocess.run([pipx_bin, "upgrade", "cowsay"]).returncode, 0
            )
            subprocess.run([pipx_bin, "uninstall-all"], check=True)
            self.assertTrue(find_executable(pipx_bin))


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestPipx))

    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)

    num_failures = len(result.errors) + len(result.failures)
    return num_failures


if __name__ == "__main__":
    exit(main())
