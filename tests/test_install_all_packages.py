import io
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest  # type: ignore

from helpers import run_pipx_cli
from package_info import PKG

REPORTS_DIR = "./reports"
REPORT_FILENAME_ROOT = "all_packages"
# "package_name, package_spec",
PACKAGE_PARAMETRIZE_LIST = [
    ("ansible", PKG["ansible"]["spec"]),
    ("awscli", PKG["awscli"]["spec"]),
    ("b2", PKG["b2"]["spec"]),
    ("beancount", PKG["beancount"]["spec"]),
    ("beets", PKG["beets"]["spec"]),
    ("black", PKG["black"]["spec"]),
    ("cactus", PKG["cactus"]["spec"]),
    ("chert", PKG["chert"]["spec"]),
    ("cloudtoken", PKG["cloudtoken"]["spec"]),
    ("coala", PKG["coala"]["spec"]),
    ("cookiecutter", PKG["cookiecutter"]["spec"]),
    ("cython", PKG["cython"]["spec"]),
    ("datasette", PKG["datasette"]["spec"]),
    ("diffoscope", PKG["diffoscope"]["spec"]),
    ("doc2dash", PKG["doc2dash"]["spec"]),
    ("doitlive", PKG["doitlive"]["spec"]),
    ("gdbgui", PKG["gdbgui"]["spec"]),
    ("gns3-gui", PKG["gns3-gui"]["spec"]),
    ("grow", PKG["grow"]["spec"]),
    ("guake", PKG["guake"]["spec"]),
    ("gunicorn", PKG["gunicorn"]["spec"]),
    ("howdoi", PKG["howdoi"]["spec"]),
    ("httpie", PKG["httpie"]["spec"]),
    ("hyde", PKG["hyde"]["spec"]),
    ("ipython", PKG["ipython"]["spec"]),
    ("isort", PKG["isort"]["spec"]),
    ("jaraco-financial", PKG["jaraco-financial"]["spec"]),
    ("kaggle", PKG["kaggle"]["spec"]),
    ("kibitzr", PKG["kibitzr"]["spec"]),
    ("klaus", PKG["klaus"]["spec"]),
    ("kolibri", PKG["kolibri"]["spec"]),
    ("lektor", PKG["lektor"]["spec"]),
    ("localstack", PKG["localstack"]["spec"]),
    ("mackup", PKG["mackup"]["spec"]),
    ("magic-wormhole", PKG["magic-wormhole"]["spec"]),
    ("mayan-edms", PKG["mayan-edms"]["spec"]),
    ("mkdocs", PKG["mkdocs"]["spec"]),
    ("mycli", PKG["mycli"]["spec"]),
    ("nikola", PKG["nikola"]["spec"]),
    ("nox", PKG["nox"]["spec"]),
    ("pelican", PKG["pelican"]["spec"]),
    ("platformio", PKG["platformio"]["spec"]),
    ("ppci", PKG["ppci"]["spec"]),
    ("prosopopee", PKG["prosopopee"]["spec"]),
    ("ptpython", PKG["ptpython"]["spec"]),
    ("pycowsay", PKG["pycowsay"]["spec"]),
    ("pylint", PKG["pylint"]["spec"]),
    ("retext", PKG["retext"]["spec"]),
    ("robotframework", PKG["robotframework"]["spec"]),
    ("shell-functools", PKG["shell-functools"]["spec"]),
    ("speedtest-cli", PKG["speedtest-cli"]["spec"]),
    ("sphinx", PKG["sphinx"]["spec"]),
    ("sqlmap", PKG["sqlmap"]["spec"]),
    ("streamlink", PKG["streamlink"]["spec"]),
    ("taguette", PKG["taguette"]["spec"]),
    ("term2048", PKG["term2048"]["spec"]),
    ("tox-ini-fmt", PKG["tox-ini-fmt"]["spec"]),
    ("visidata", PKG["visidata"]["spec"]),
    ("vulture", PKG["vulture"]["spec"]),
    ("weblate", PKG["weblate"]["spec"]),
    ("youtube-dl", PKG["youtube-dl"]["spec"]),
    ("zeo", PKG["zeo"]["spec"]),
]


@pytest.fixture(scope="module")
def module_globals():
    return {
        "test_start": 0,
        "error_path": Path("."),
        "report_path": Path("."),
        "install_data": {},
        "doing_dep_test": False,
    }


def pip_cache_purge():
    return subprocess.run([sys.executable, "-m", "pip", "cache", "purge"])


def verify_installed_apps(captured_outerr, package_name, test_error_fh, deps=False):
    if deps:
        package_apps = (
            PKG[package_name]["apps"] + PKG[package_name]["apps_of_dependencies"]
        )
    else:
        package_apps = PKG[package_name]["apps"]

    reported_apps_re = re.search(
        r"These apps are now globally available(.+)", captured_outerr.out, re.DOTALL
    )
    if reported_apps_re:
        reported_apps = [
            x.strip()[2:] for x in reported_apps_re.group(1).strip().split("\n")
        ]
        if set(reported_apps) != set(package_apps):
            app_success = False
            print(
                "verify_install: REPORTED APPS DO NOT MATCH PACKAGE", file=test_error_fh
            )
            print(f"pipx reported apps: {reported_apps}", file=test_error_fh)
            print(f" true package apps: {package_apps}", file=test_error_fh)
        else:
            app_success = True
    else:
        app_success = False
        print("verify_install: APPS TESTING ERROR", file=test_error_fh)

    return app_success


def verify_install(
    captured_outerr, caplog, package_name, test_error_fh, using_clear_path, deps=False
):
    caplog_problem = False
    install_success = f"installed package {package_name}" in captured_outerr.out
    for record in caplog.records:
        if "⚠️" in record.message or "WARNING" in record.message:
            if using_clear_path or "was already on your PATH" not in record.message:
                caplog_problem = True
            print("verify_install: WARNING IN CAPLOG:", file=test_error_fh)
            print(record.message, file=test_error_fh)
    if install_success and PKG[package_name].get("apps", None) is not None:
        app_success = verify_installed_apps(
            captured_outerr, package_name, test_error_fh, deps=deps
        )
    else:
        app_success = True

    return install_success and not caplog_problem and app_success


def print_error_report(
    error_path, command_captured, test_error_fh, package_spec, header
):
    py_version_str = f"Python {sys.version_info[0]}.{sys.version_info[1]}"
    with error_path.open("a") as error_fh:
        print("\n\n", file=error_fh)
        print("=" * 76, file=error_fh)
        print(
            f"{package_spec:24}{header:16}{sys.platform:16}{py_version_str:}",
            file=error_fh,
        )
        print("\nSTDOUT:", file=error_fh)
        print("-" * 76, file=error_fh)
        print(command_captured.out, end="", file=error_fh)
        print("\nSTDERR:", file=error_fh)
        print("-" * 76, file=error_fh)
        print(command_captured.err, end="", file=error_fh)
        print("\n\nTEST WARNINGS / ERRORS:", file=error_fh)
        print("-" * 76, file=error_fh)
        print(test_error_fh.getvalue(), end="", file=error_fh)


def install_package(
    module_globals,
    monkeypatch,
    capfd,
    pipx_temp_env,
    caplog,
    package_spec,
    package_name="",
    deps=False,
):
    sys_path = os.getenv("PATH_ORIG")
    clear_path = os.getenv("PATH_TEST")

    test_error_fh = io.StringIO()
    install_data = module_globals["install_data"]
    install_data[package_spec] = {}
    if not package_name:
        package_name = package_spec

    monkeypatch.setenv("PATH", clear_path)
    start_time = time.time()
    run_pipx_cli(
        ["install", package_spec, "--verbose"] + (["--include-deps"] if deps else [])
    )
    elapsed_time_clear = time.time() - start_time
    elapsed_time_sys = 0

    captured_clear_path = capfd.readouterr()
    install_success = verify_install(
        captured_clear_path,
        caplog,
        package_name,
        test_error_fh,
        using_clear_path=True,
        deps=deps,
    )

    if install_success:
        install_data[package_spec]["clear_path_ok"] = True
    else:
        install_data[package_spec]["clear_path_ok"] = False

        # uninstall in case problems found by verify_install did not prevent
        #   pipx installation
        run_pipx_cli(["uninstall", package_name])
        _ = capfd.readouterr()

        monkeypatch.setenv("PATH", sys_path)

        start_time = time.time()
        run_pipx_cli(
            ["install", package_spec, "--verbose"]
            + (["--include-deps"] if deps else [])
        )
        elapsed_time_sys = time.time() - start_time
        captured_sys_path = capfd.readouterr()

        install_success_orig_path = verify_install(
            captured_sys_path,
            caplog,
            package_name,
            test_error_fh,
            using_clear_path=False,
            deps=deps,
        )

        if install_success_orig_path:
            install_data[package_spec]["sys_path_ok"] = True
        else:
            install_data[package_spec]["sys_path_ok"] = False
            print_error_report(
                module_globals["error_path"],
                captured_sys_path,
                test_error_fh,
                package_spec,
                "sys PATH",
            )

    with module_globals["report_path"].open("a") as report_fh:
        pf_clear = "PASS" if install_data[package_spec]["clear_path_ok"] else "FAIL"
        install_time_clear = f"{elapsed_time_clear:>3.0f}s"
        if install_data[package_spec]["clear_path_ok"]:
            pf_sys = ""
            install_time_sys = ""
        else:
            pf_sys = "PASS" if install_data[package_spec]["sys_path_ok"] else "FAIL"
            install_time_sys = f"{elapsed_time_sys:>3.0f}s"
        print(
            f"{package_spec:24}{pf_clear:16}{pf_sys:16}"
            f"{install_time_clear} {install_time_sys}",
            file=report_fh,
            flush=True,
        )


# use class scope to start and finish at end of all parametrized tests
@pytest.fixture(scope="class")
def start_end_report(module_globals, request):
    module_globals["test_start"] = datetime.now()
    dt_string = module_globals["test_start"].strftime("%Y-%m-%d %H:%M:%S")
    date_string = module_globals["test_start"].strftime("%Y%m%d")
    py_version = f"{sys.version_info[0]}.{sys.version_info[1]}"
    py_version_str = f"Python {py_version}"

    reports_path = Path(REPORTS_DIR)
    reports_path.mkdir(exist_ok=True, parents=True)

    test_class = getattr(request.cls, "test_class", "unknown")

    module_globals["report_path"] = (
        reports_path
        / f"./{REPORT_FILENAME_ROOT}_{test_class}_report_{sys.platform}_{py_version}_{date_string}.txt"
    )
    module_globals["error_path"] = (
        reports_path
        / f"./{REPORT_FILENAME_ROOT}_{test_class}_errors_{sys.platform}_{py_version}_{date_string}.txt"
    )

    # Reset global data
    module_globals["install_data"] = {}
    install_data = module_globals["install_data"]

    with module_globals["report_path"].open("a") as report_fh:
        print("\n\n", file=report_fh)
        print("=" * 72, file=report_fh)
        print(f"{sys.platform:16}{py_version_str:16}{dt_string}", file=report_fh)
        print("", file=report_fh)
        print(
            f"{'package_spec':24}{'cleared PATH':16}{'system PATH':16}"
            f"{'install time':16}",
            file=report_fh,
        )
        print("-" * 72, file=report_fh)

    yield

    with module_globals["report_path"].open("a") as report_fh:
        print("\nSummary", file=report_fh)
        print("-" * 72, file=report_fh)
        for package_spec in install_data:
            if install_data[package_spec].get("clear_path_ok", False):
                continue
            elif not install_data[package_spec].get(
                "clear_path_ok", False
            ) and install_data[package_spec].get("sys_path_ok", False):
                print(f"{package_spec} needs prebuilt wheel", file=report_fh)
            elif not install_data[package_spec].get(
                "clear_path_ok", False
            ) and not install_data[package_spec].get("sys_path_ok", False):
                print(f"{package_spec} FAILS", file=report_fh)
        test_end = datetime.now()
        dt_string = test_end.strftime("%Y-%m-%d %H:%M:%S")
        el_datetime = test_end - module_globals["test_start"]
        el_datetime = el_datetime - timedelta(microseconds=el_datetime.microseconds)
        print(f"\nFinished {dt_string}", file=report_fh)
        print(f"Elapsed: {el_datetime}", file=report_fh)


class TestAllPackagesNoDeps:
    test_class = "nodeps"

    @pytest.mark.parametrize("package_name, package_spec", PACKAGE_PARAMETRIZE_LIST)
    @pytest.mark.all_packages
    def test_all_packages(
        self,
        module_globals,
        start_end_report,
        monkeypatch,
        capfd,
        pipx_temp_env,
        caplog,
        package_name,
        package_spec,
    ):
        pip_cache_purge()
        install_package(
            module_globals,
            monkeypatch,
            capfd,
            pipx_temp_env,
            caplog,
            package_spec,
            package_name,
            deps=False,
        )


class TestAllPackagesDeps:
    test_class = "deps"

    @pytest.mark.parametrize("package_name, package_spec", PACKAGE_PARAMETRIZE_LIST)
    @pytest.mark.all_packages
    def test_deps_all_packages(
        self,
        module_globals,
        start_end_report,
        monkeypatch,
        capfd,
        pipx_temp_env,
        caplog,
        package_name,
        package_spec,
    ):
        pip_cache_purge()
        install_package(
            module_globals,
            monkeypatch,
            capfd,
            pipx_temp_env,
            caplog,
            package_spec,
            package_name,
            deps=True,
        )


class TestAllPackagesUninstall:
    test_class = "uninstall"

    @pytest.mark.parametrize("package_name, package_spec", PACKAGE_PARAMETRIZE_LIST)
    @pytest.mark.all_packages
    def test_uninstall_all_packages(
        self,
        module_globals,
        start_end_report,
        monkeypatch,
        capfd,
        pipx_temp_env,
        caplog,
        package_name,
        package_spec,
    ):
        # use system path for everything to ensure most install
        monkeypatch.setenv("PATH", os.getenv("PATH_ORIG"))
        run_pipx_cli(["install", package_spec, "--verbose"])
        run_pipx_cli(["uninstall", package_name])
        run_pipx_cli(["install", package_spec, "--verbose", "--include-deps"])
        run_pipx_cli(["uninstall", package_name])
