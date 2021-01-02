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
    pipx_exit_code,
    captured_outerr,
    caplog,
    package_name,
    test_error_fh,
    using_clear_path,
    deps=False,
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

    pipx_problem = not (install_success and not caplog_problem and app_success)
    pip_error = (
        pipx_exit_code != 0
    ) and f"Error installing {package_name}" in captured_outerr.err

    return pipx_problem, pip_error


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
    pipx_exit_code = run_pipx_cli(
        ["install", package_spec, "--verbose"] + (["--include-deps"] if deps else [])
    )
    elapsed_time = time.time() - start_time
    captured = capsys.readouterr()

    pipx_problem, pip_error = verify_post_install(
        pipx_exit_code,
        captured,
        caplog,
        package_name,
        test_error_fh,
        using_clear_path=using_clear_path,
        deps=deps,
    )

    if error_path is not None and (pipx_problem or pip_error):
        print_error_report(
            error_path,
            captured,
            test_error_fh,
            package_spec,
            "clear PATH" if using_clear_path else "sys PATH",
        )

    return pipx_problem, pip_error, elapsed_time


def key_pass_fail(test_dict, test_key):
    if test_dict.get(test_key, None) is not None:
        return "PASS" if test_dict[test_key] else "FAIL"
    else:
        return ""


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

    (pipx_problem, pip_error, elapsed_time_clear) = install_and_verify(
        capsys,
        caplog,
        monkeypatch,
        None,
        using_clear_path=True,
        package_spec=package_spec,
        package_name=package_name,
        deps=deps,
    )

    install_data[package_spec]["clear_elapsed_time"] = elapsed_time_clear
    install_data[package_spec]["clear_pip_pass"] = not pip_error
    install_data[package_spec]["clear_pipx_pass"] = not pipx_problem
    clear_path_ok = not (pipx_problem or pip_error)

    if not install_data[package_spec]["clear_pip_pass"]:
        # if we fail to install due to pip install error, try again with
        #   full system path
        (pipx_problem, pip_error, elapsed_time_sys) = install_and_verify(
            capsys,
            caplog,
            monkeypatch,
            module_globals["error_path"],
            using_clear_path=False,
            package_spec=package_spec,
            package_name=package_name,
            deps=deps,
        )
        install_data[package_spec]["sys_elapsed_time"] = elapsed_time_sys
        install_data[package_spec]["sys_pip_pass"] = not pip_error
        install_data[package_spec]["sys_pipx_pass"] = not pipx_problem
        sys_path_ok = not (pipx_problem or pip_error)
    else:
        sys_path_ok = False

    overall_pass = clear_path_ok or sys_path_ok

    with module_globals["report_path"].open("a") as report_fh:
        clear_pip_pf = key_pass_fail(install_data[package_spec], "clear_pip_pass")
        clear_pipx_pf = key_pass_fail(install_data[package_spec], "clear_pipx_pass")
        clear_install_time = (
            f"{install_data[package_spec]['clear_elapsed_time']:>3.0f}s"
        )

        sys_pip_pf = key_pass_fail(install_data[package_spec], "sys_pip_pass")
        sys_pipx_pf = key_pass_fail(install_data[package_spec], "sys_pipx_pass")
        if install_data[package_spec].get("sys_elapsed_time", None) is not None:
            sys_install_time = (
                f"{install_data[package_spec]['sys_elapsed_time']:>3.0f}s"
            )
        else:
            sys_install_time = ""

        overall_pf = "PASS" if overall_pass else "FAIL"

        print(
            f"{package_spec:24}{overall_pf:12}"
            f"{clear_pip_pf:8}{clear_pipx_pf:8}{clear_install_time:8}"
            f"{sys_pip_pf:8}{sys_pipx_pf:8}{sys_install_time:8}",
            file=report_fh,
            flush=True,
        )

    if pip_error:
        # Use xfail to specify error that is from a pip installation problem
        pytest.xfail("pip installation error")

    return overall_pass


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
        print("=" * 79, file=report_fh)
        print(f"{sys.platform:16}{py_version_str:16}{dt_string}", file=report_fh)
        print("", file=report_fh)
        print(
            f"{'package_spec':24}{'overall':12}{'cleared PATH':24}{'system PATH':24}",
            file=report_fh,
        )
        print(
            f"{'':24}{'':12}{'pip':8}{'pipx':8}{'time':8}{'pip':8}{'pipx':8}{'time':8}",
            file=report_fh,
        )
        print("-" * 79, file=report_fh)

    yield

    with module_globals["report_path"].open("a") as report_fh:
        print("\nSummary", file=report_fh)
        print("-" * 79, file=report_fh)
        for package_spec in install_data:
            clear_pip_pass = install_data[package_spec]["clear_pip_pass"]
            clear_pipx_pass = install_data[package_spec]["clear_pipx_pass"]
            sys_pip_pass = install_data[package_spec].get("sys_pip_pass", False)
            sys_pipx_pass = install_data[package_spec].get("sys_pipx_pass", False)

            if clear_pip_pass and clear_pipx_pass:
                continue
            elif not clear_pip_pass and sys_pip_pass and sys_pipx_pass:
                print(f"{package_spec} needs prebuilt wheel", file=report_fh)
            else:
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
