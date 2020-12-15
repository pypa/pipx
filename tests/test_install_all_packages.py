"""
This module uses the pytest infrastructure to produce reports on a large list
of packages.  It verifies installation with and without an intact system PATH.

It is not meant to ever fail in the normal pytest sense.  Instead failing
installs will be recorded in the reports
"""
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
PACKAGE_NAME_LIST = [
    "ansible",
    "awscli",
    "b2",
    "beancount",
    "beets",
    "black",
    "cactus",
    "chert",
    "cloudtoken",
    "coala",
    "cookiecutter",
    "cython",
    "datasette",
    "diffoscope",
    "doc2dash",
    "doitlive",
    "gdbgui",
    "gns3-gui",
    "grow",
    "guake",
    "gunicorn",
    "howdoi",
    "httpie",
    "hyde",
    "ipython",
    "isort",
    "jaraco-financial",
    "kaggle",
    "kibitzr",
    "klaus",
    "kolibri",
    "lektor",
    "localstack",
    "mackup",
    "magic-wormhole",
    "mayan-edms",
    "mkdocs",
    "mycli",
    "nikola",
    "nox",
    "pelican",
    "platformio",
    "ppci",
    "prosopopee",
    "ptpython",
    "pycowsay",
    "pylint",
    "retext",
    "robotframework",
    "shell-functools",
    "speedtest-cli",
    "sphinx",
    "sqlmap",
    "streamlink",
    "taguette",
    "term2048",
    "tox-ini-fmt",
    "visidata",
    "vulture",
    "weblate",
    "youtube-dl",
    "zeo",
]


@pytest.fixture(scope="module")
def module_globals():
    return {
        "test_start": 0,
        "error_path": Path("."),
        "report_path": Path("."),
        "install_data": {},
    }


def pip_cache_purge():
    return subprocess.run([sys.executable, "-m", "pip", "cache", "purge"])


def verify_installed_apps(captured_outerr, package_name, test_error_fh, deps=False):
    package_apps = PKG[package_name]["apps"].copy()
    if deps:
        package_apps += PKG[package_name]["apps_of_dependencies"]

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


def verify_post_install(
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


def install_and_verify(
    capsys,
    caplog,
    monkeypatch,
    error_path,
    using_clear_path,
    package_spec,
    package_name,
    deps,
):
    _ = capsys.readouterr()
    caplog.clear()

    test_error_fh = io.StringIO()

    monkeypatch.setenv(
        "PATH", os.getenv("PATH_TEST" if using_clear_path else "PATH_ORIG")
    )

    start_time = time.time()
    run_pipx_cli(
        ["install", package_spec, "--verbose"] + (["--include-deps"] if deps else [])
    )
    elapsed_time = time.time() - start_time
    captured = capsys.readouterr()

    install_success = verify_post_install(
        captured,
        caplog,
        package_name,
        test_error_fh,
        using_clear_path=using_clear_path,
        deps=deps,
    )

    if error_path is not None and not install_success:
        print_error_report(
            error_path,
            captured,
            test_error_fh,
            package_spec,
            "clear PATH" if using_clear_path else "sys PATH",
        )

    return install_success, elapsed_time


def install_package_both_paths(
    module_globals,
    monkeypatch,
    capsys,
    pipx_temp_env,
    caplog,
    package_name="",
    deps=False,
):
    package_spec = PKG[package_name]["spec"]
    install_data = module_globals["install_data"]
    install_data[package_spec] = {}

    (
        install_data[package_spec]["clear_path_ok"],
        elapsed_time_clear,
    ) = install_and_verify(
        capsys,
        caplog,
        monkeypatch,
        None,
        using_clear_path=True,
        package_spec=package_spec,
        package_name=package_name,
        deps=deps,
    )

    if not install_data[package_spec]["clear_path_ok"]:
        # uninstall in case problems found by verify_post_install did not prevent
        #   pipx installation
        run_pipx_cli(["uninstall", package_name])

        (
            install_data[package_spec]["sys_path_ok"],
            elapsed_time_sys,
        ) = install_and_verify(
            capsys,
            caplog,
            monkeypatch,
            module_globals["error_path"],
            using_clear_path=False,
            package_spec=package_spec,
            package_name=package_name,
            deps=deps,
        )

    with module_globals["report_path"].open("a") as report_fh:
        pf_clear = "PASS" if install_data[package_spec]["clear_path_ok"] else "FAIL"
        install_time_clear = f"{elapsed_time_clear:>3.0f}s"
        if install_data[package_spec]["clear_path_ok"]:
            elapsed_time_sys = 0
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
    return (
        install_data[package_spec]["clear_path_ok"]
        or install_data[package_spec]["sys_path_ok"]
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

    @pytest.mark.parametrize("package_name", PACKAGE_NAME_LIST)
    @pytest.mark.all_packages
    def test_all_packages(
        self,
        module_globals,
        start_end_report,
        monkeypatch,
        capsys,
        pipx_temp_env,
        caplog,
        package_name,
    ):
        pip_cache_purge()
        assert install_package_both_paths(
            module_globals,
            monkeypatch,
            capsys,
            pipx_temp_env,
            caplog,
            package_name,
            deps=False,
        )


class TestAllPackagesDeps:
    test_class = "deps"

    @pytest.mark.parametrize("package_name", PACKAGE_NAME_LIST)
    @pytest.mark.all_packages
    def test_deps_all_packages(
        self,
        module_globals,
        start_end_report,
        monkeypatch,
        capsys,
        pipx_temp_env,
        caplog,
        package_name,
    ):
        pip_cache_purge()
        assert install_package_both_paths(
            module_globals,
            monkeypatch,
            capsys,
            pipx_temp_env,
            caplog,
            package_name,
            deps=True,
        )
