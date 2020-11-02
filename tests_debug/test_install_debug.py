import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest  # type: ignore

from helpers import PKGSPEC, run_pipx_cli

REPORT_PATH = Path("./test_install_debug_report.txt")
INSTALL_DATA = {}

# def install_package(capsys, pipx_temp_env, caplog, package, package_name=""):
#     if not package_name:
#         package_name = package
#
#     run_pipx_cli(["install", package, "--verbose"])
#     captured = capsys.readouterr()
#     assert f"installed package {package_name}" in captured.out
#     if not sys.platform.startswith("win"):
#         # TODO assert on windows too
#         # https://github.com/pipxproject/pipx/issues/217
#         assert "symlink missing or pointing to unexpected location" not in captured.out
#     assert "not modifying" not in captured.out
#     assert "is not on your PATH environment variable" not in captured.out
#     for record in caplog.records:
#         assert "⚠️" not in record.message
#         assert "WARNING" not in record.message


def pip_cache_purge():
    return subprocess.run([sys.executable, "-m", "pip", "cache", "purge"])


def install_package_debug(
    monkeypatch, capsys, pipx_temp_env, caplog, package, package_name=""
):
    orig_path = os.getenv("PATH_OLD")

    INSTALL_DATA[package] = {}
    if not package_name:
        package_name = package

    start_time = time.time()
    run_pipx_cli(["install", package, "--verbose"])
    elapsed_time1 = time.time() - start_time
    elapsed_time2 = 0

    captured_clear_path = capsys.readouterr()
    install_success = f"installed package {package_name}" in captured_clear_path.out
    for record in caplog.records:
        assert "⚠️" not in record.message
        assert "WARNING" not in record.message
    if install_success:
        INSTALL_DATA[package]["clear_path_ok"] = True
    else:
        INSTALL_DATA[package]["clear_path_ok"] = False
        monkeypatch.setenv("PATH", orig_path)

        start_time = time.time()
        run_pipx_cli(["install", package, "--verbose"])
        elapsed_time2 = time.time() - start_time

        captured_sys_path = capsys.readouterr()
        install_success_orig_path = (
            f"installed package {package_name}" in captured_sys_path.out
        )
        if install_success_orig_path:
            INSTALL_DATA[package]["sys_path_ok"] = True
        else:
            INSTALL_DATA[package]["sys_path_ok"] = False
            print(captured_sys_path.out)

    with REPORT_PATH.open("a") as report_fh:
        clear_path = "PASS" if INSTALL_DATA[package]["clear_path_ok"] else "FAIL"
        install_time1 = f"{elapsed_time1:>3.0f}s"
        if INSTALL_DATA[package]["clear_path_ok"]:
            sys_path = ""
            install_time2 = ""
        else:
            sys_path = "PASS" if INSTALL_DATA[package]["sys_path_ok"] else "FAIL"
            install_time2 = f"{elapsed_time2:>3.0f}s"
        print(
            f"{package:24}{clear_path:16}{sys_path:16}"
            f"{install_time1} {install_time2}",
            file=report_fh,
        )

    assert install_success or install_success_orig_path


@pytest.mark.parametrize(
    "package_name, package_spec",
    [
        ("START", "START"),
        ("ansible", PKGSPEC["ansible"]),
        ("awscli", PKGSPEC["awscli"]),
        ("b2", PKGSPEC["b2"]),
        ("beancount", PKGSPEC["beancount"]),  # py3.9 FAIL lxml
        ("beets", PKGSPEC["beets"]),
        ("black", PKGSPEC["black"]),
        ("cactus", PKGSPEC["cactus"]),
        ("chert", PKGSPEC["chert"]),
        ("cloudtoken", PKGSPEC["cloudtoken"]),
        ("coala", PKGSPEC["coala"]),  # problem on win
        ("cookiecutter", PKGSPEC["cookiecutter"]),
        ("cython", PKGSPEC["cython"]),
        ("datasette", PKGSPEC["datasette"]),
        ("diffoscope", PKGSPEC["diffoscope"]),
        ("doc2dash", PKGSPEC["doc2dash"]),
        ("doitlive", PKGSPEC["doitlive"]),
        ("gdbgui", PKGSPEC["gdbgui"]),
        ("gns3-gui", PKGSPEC["gns3-gui"]),
        ("grow", PKGSPEC["grow"]),
        ("guake", PKGSPEC["guake"]),
        ("gunicorn", PKGSPEC["gunicorn"]),
        ("howdoi", PKGSPEC["howdoi"]),  # py3.9 FAIL lxml
        ("httpie", PKGSPEC["httpie"]),
        ("hyde", PKGSPEC["hyde"]),  # py3.9 FAIL pyyaml
        ("ipython", PKGSPEC["ipython"]),
        ("isort", PKGSPEC["isort"]),
        ("jaraco-financial", "jaraco.financial==2.0"),
        ("kaggle", PKGSPEC["kaggle"]),
        ("kibitzr", PKGSPEC["kibitzr"]),  # py3.9 FAIL lxml
        ("klaus", PKGSPEC["klaus"]),  # WIN problem making dep dulwich
        ("kolibri", PKGSPEC["kolibri"]),
        ("lektor", PKGSPEC["lektor"]),
        ("localstack", PKGSPEC["localstack"]),
        ("mackup", PKGSPEC["mackup"]),
        ("magic-wormhole", PKGSPEC["magic-wormhole"]),
        ("mayan-edms", PKGSPEC["mayan-edms"]),  # py3.9 FAIL pillow
        ("mkdocs", PKGSPEC["mkdocs"]),
        ("mycli", PKGSPEC["mycli"]),
        ("nikola", PKGSPEC["nikola"]),  # py3.9 FAIL lxml
        ("nox", PKGSPEC["nox"]),
        ("pelican", PKGSPEC["pelican"]),
        ("platformio", PKGSPEC["platformio"]),
        ("ppci", PKGSPEC["ppci"]),
        ("prosopopee", PKGSPEC["prosopopee"]),
        ("ptpython", PKGSPEC["ptpython"]),
        ("pycowsay", PKGSPEC["pycowsay"]),
        ("pylint", PKGSPEC["pylint"]),
        ("retext", PKGSPEC["retext"]),
        ("robotframework", PKGSPEC["robotframework"]),
        ("shell-functools", PKGSPEC["shell-functools"]),
        ("speedtest-cli", PKGSPEC["speedtest-cli"]),
        ("sphinx", PKGSPEC["sphinx"]),
        ("sqlmap", PKGSPEC["sqlmap"]),
        ("streamlink", PKGSPEC["streamlink"]),
        ("taguette", PKGSPEC["taguette"]),
        ("term2048", PKGSPEC["term2048"]),
        ("tox-ini-fmt", PKGSPEC["tox-ini-fmt"]),
        ("visidata", PKGSPEC["visidata"]),
        ("vulture", PKGSPEC["vulture"]),
        ("weblate", PKGSPEC["weblate"]),  # py3.9 FAIL lxml<4.7.0,>=4.0
        ("youtube-dl", PKGSPEC["youtube-dl"]),
        ("zeo", PKGSPEC["zeo"]),
        ("FINISH", "FINISH"),
    ],
)
@pytest.mark.all_packages
def test_all_packages(
    monkeypatch, capsys, pipx_temp_env, caplog, package_name, package_spec
):
    if package_name == "START" and package_spec == "START":
        dt_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with REPORT_PATH.open("a") as report_fh:
            py_version = f"Python {sys.version_info[0]}.{sys.version_info[1]}"
            print("\n\n", file=report_fh)
            print("=" * 72, file=report_fh)
            print(f"{sys.platform:16}{py_version:16}{dt_string}", file=report_fh)
            print("", file=report_fh)
            print(
                f"{'package_spec':24}{'cleared PATH':16}{'system PATH':16}"
                f"{'install time':16}",
                file=report_fh,
            )
            print("-" * 72, file=report_fh)
    elif package_name == "FINISH" and package_spec == "FINISH":
        with REPORT_PATH.open("a") as report_fh:
            print("\nSummary", file=report_fh)
            print("-" * 72, file=report_fh)
            for package_spec in INSTALL_DATA:
                if INSTALL_DATA[package_spec]["clear_path_ok"]:
                    continue
                elif (
                    not INSTALL_DATA[package_spec]["clear_path_ok"]
                    and INSTALL_DATA[package_spec]["sys_path_ok"]
                ):
                    print(f"{package_spec} needs prebuilt wheel", file=report_fh)
                elif (
                    not INSTALL_DATA[package_spec]["clear_path_ok"]
                    and not INSTALL_DATA[package_spec]["sys_path_ok"]
                ):
                    print(f"{package_spec} FAILS", file=report_fh)
            dt_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\nFinished {dt_string}", file=report_fh)
    else:
        pip_cache_purge()
        install_package_debug(
            monkeypatch, capsys, pipx_temp_env, caplog, package_spec, package_name
        )
