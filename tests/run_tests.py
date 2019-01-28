import os
from pathlib import Path
import unittest
import subprocess
import sys
import tempfile


try:
    WindowsError
except NameError:
    IS_WIN = False
else:
    IS_WIN = True


class TestPipx(unittest.TestCase):
    def test_pipx(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.environ
            home_dir = Path(d) / "subdir" / "pipxhome"
            bin_dir = Path(d) / "otherdir" / "pipxbindir"
            if IS_WIN:
                pipx_bin = bin_dir / "pipx.exe"
            else:
                pipx_bin = bin_dir / "pipx"

            env["PIPX_HOME"] = str(home_dir)
            env["PIPX_BIN_DIR"] = str(bin_dir)

            subprocess.run(
                [
                    sys.executable,
                    "get-pipx.py",
                    "--src",
                    ".",
                    "--overwrite",
                    "--no-modify-path",
                    "--verbose",
                ],
                env=env,
                check=True,
            )

            subprocess.run([pipx_bin, "--help"], check=True)
            subprocess.run([pipx_bin, "list"], check=True)
            self.assertNotEqual(
                subprocess.run([pipx_bin, "cowsay", "pipx test is passing"]).returncode,
                0,
            )
            subprocess.run(
                [pipx_bin, "run", "cowsay", "pipx test is passing"], check=True
            )
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
            self.assertFalse(pipx_bin.is_file())


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
