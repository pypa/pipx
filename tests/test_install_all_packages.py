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
from typing import List, Optional

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


class PackageData:
    def __init__(self):
        self.package_name: Optional[str] = None
        self.package_spec: Optional[str] = None
        self.clear_elapsed_time: Optional[timedelta] = None
        self.clear_pip_pass: Optional[bool] = None
        self.clear_pipx_pass: Optional[bool] = None
        self.sys_elapsed_time: Optional[timedelta] = None
        self.sys_pip_pass: Optional[bool] = None
        self.sys_pipx_pass: Optional[bool] = None
        self.overall_pass: Optional[bool] = None

    @property
    def clear_pip_pf_str(self) -> str:
        return self._get_pass_fail_str("clear_pip_pass")

    @property
    def clear_pipx_pf_str(self) -> str:
        return self._get_pass_fail_str("clear_pipx_pass")

    @property
    def sys_pip_pf_str(self) -> str:
        return self._get_pass_fail_str("sys_pip_pass")

    @property
    def sys_pipx_pf_str(self) -> str:
        return self._get_pass_fail_str("sys_pipx_pass")

    @property
    def overall_pf_str(self) -> str:
        return self._get_pass_fail_str("overall_pass")

    def _get_pass_fail_str(self, test_attr) -> str:
        if getattr(self, test_attr) is not None:
            return "PASS" if getattr(self, test_attr) else "FAIL"
        else:
            return ""


class ModuleGlobalsData:
    def __init__(self):
        self.errors_path = Path(".")
        self.install_data: List[PackageData] = []
        self.py_version_display = "Python {0.major}.{0.minor}.{0.micro}".format(
            sys.version_info
        )
        self.py_version_short = "{0.major}.{0.minor}".format(sys.version_info)
        self.report_path = Path(".")
        self.sys_platform = sys.platform
        self.test_class = ""
        self.test_start = datetime.now()

    def reset(self, test_class: str = ""):
        self.errors_path = Path(".")
        self.install_data = []
        self.report_path = Path(".")
        self.test_class = test_class
        self.test_start = datetime.now()


@pytest.fixture(scope="module")
def module_globals():
    return ModuleGlobalsData()


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

    pip_pass = not (
        (pipx_exit_code != 0)
        and f"Error installing {package_name}" in captured_outerr.err
    )
    if pip_pass:
        pipx_pass = install_success and not caplog_problem and app_success
    else:
        pipx_pass = None

    return pip_pass, pipx_pass


def print_error_report(
    module_globals, command_captured, test_error_fh, package_spec, test_type
):
    py_version_str = module_globals.py_version_display
    sys_platform = module_globals.sys_platform

    with module_globals.errors_path.open("a") as errors_fh:
        print("\n\n", file=errors_fh)
        print("=" * 79, file=errors_fh)
        print(
            f"{package_spec:24}{test_type:16}{sys_platform:16}{py_version_str}",
            file=errors_fh,
        )
        print("\nSTDOUT:", file=errors_fh)
        print("-" * 76, file=errors_fh)
        print(command_captured.out, end="", file=errors_fh)
        print("\nSTDERR:", file=errors_fh)
        print("-" * 76, file=errors_fh)
        print(command_captured.err, end="", file=errors_fh)
        print("\n\nTEST WARNINGS / ERRORS:", file=errors_fh)
        print("-" * 76, file=errors_fh)
        print(test_error_fh.getvalue(), end="", file=errors_fh)


def install_and_verify(
    capsys,
    caplog,
    monkeypatch,
    module_globals,
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

    pip_pass, pipx_pass = verify_post_install(
        pipx_exit_code,
        captured,
        caplog,
        package_name,
        test_error_fh,
        using_clear_path=using_clear_path,
        deps=deps,
    )

    if not pip_pass or not pipx_pass:
        print_error_report(
            module_globals,
            captured,
            test_error_fh,
            package_spec,
            "clear PATH" if using_clear_path else "sys PATH",
        )

    return pip_pass, pipx_pass, elapsed_time


def format_report_table_header(module_globals):
    py_version_str = module_globals.py_version_display
    sys_platform = module_globals.sys_platform
    dt_string = module_globals.test_start.strftime("%Y-%m-%d %H:%M:%S")

    header_string = "\n\n"
    header_string += "=" * 79 + "\n"
    header_string += f"{sys_platform:16}{py_version_str:16}{dt_string}\n\n"
    header_string += (
        f"{'package_spec':24}{'overall':12}{'cleared_PATH':24}{'system_PATH':24}\n"
    )
    header_string += (
        f"{'':24}{'':12}{'pip':8}{'pipx':8}{'time':8}{'pip':8}{'pipx':8}{'time':8}\n"
    )
    header_string += "-" * 79

    return header_string


def format_report_table_row(package_data):
    clear_install_time = f"{package_data.clear_elapsed_time:>3.0f}s"
    if package_data.sys_elapsed_time is not None:
        sys_install_time = f"{package_data.sys_elapsed_time:>3.0f}s"
    else:
        sys_install_time = ""

    row_string = (
        f"{package_data.package_spec:24}{package_data.overall_pf_str:12}"
        f"{package_data.clear_pip_pf_str:8}{package_data.clear_pipx_pf_str:8}"
        f"{clear_install_time:8}"
        f"{package_data.sys_pip_pf_str:8}{package_data.sys_pipx_pf_str:8}"
        f"{sys_install_time:8}"
    )

    return row_string


def format_report_table_footer(module_globals):
    fail_list = []
    prebuild_list = []

    footer_string = "\nSummary\n"
    footer_string += "-" * 79 + "\n"
    for package_data in module_globals.install_data:
        clear_pip_pass = package_data.clear_pip_pass
        clear_pipx_pass = package_data.clear_pipx_pass
        sys_pip_pass = package_data.sys_pip_pass
        sys_pipx_pass = package_data.sys_pipx_pass

        if clear_pip_pass and clear_pipx_pass:
            continue
        elif not clear_pip_pass and sys_pip_pass and sys_pipx_pass:
            prebuild_list.append(package_data.package_spec)
        else:
            fail_list.append(package_data.package_spec)
    if fail_list:
        footer_string += "FAILS:\n"
        for failed_package_spec in sorted(fail_list, key=str.lower):
            footer_string += f"    {failed_package_spec}\n"
    if prebuild_list:
        footer_string += "Needs prebuilt wheel:\n"
        for prebuild_package_spec in sorted(prebuild_list, key=str.lower):
            footer_string += f"    {prebuild_package_spec}\n"

    test_end = datetime.now()
    dt_string = test_end.strftime("%Y-%m-%d %H:%M:%S")
    el_datetime = test_end - module_globals.test_start
    el_datetime = el_datetime - timedelta(microseconds=el_datetime.microseconds)
    footer_string += f"\nFinished {dt_string}\n"
    footer_string += f"Elapsed: {el_datetime}"

    return footer_string


def install_package_both_paths(
    module_globals,
    monkeypatch,
    capsys,
    pipx_temp_env,
    caplog,
    package_name,
    deps=False,
):
    package_data = PackageData()
    module_globals.install_data.append(package_data)
    package_data.package_name = package_name
    package_data.package_spec = PKG[package_name]["spec"]

    (
        package_data.clear_pip_pass,
        package_data.clear_pipx_pass,
        package_data.clear_elapsed_time,
    ) = install_and_verify(
        capsys,
        caplog,
        monkeypatch,
        module_globals,
        using_clear_path=True,
        package_spec=package_data.package_spec,
        package_name=package_data.package_name,
        deps=deps,
    )
    if not package_data.clear_pip_pass:
        # if we fail to install due to pip install error, try again with
        #   full system path
        (
            package_data.sys_pip_pass,
            package_data.sys_pipx_pass,
            package_data.sys_elapsed_time,
        ) = install_and_verify(
            capsys,
            caplog,
            monkeypatch,
            module_globals,
            using_clear_path=False,
            package_spec=package_data.package_spec,
            package_name=package_data.package_name,
            deps=deps,
        )

    package_data.overall_pass = bool(
        (package_data.clear_pip_pass and package_data.clear_pipx_pass)
        or (package_data.sys_pip_pass and package_data.sys_pipx_pass)
    )

    with module_globals.report_path.open("a") as report_fh:
        print(format_report_table_row(package_data), file=report_fh, flush=True)

    if not package_data.clear_pip_pass and not package_data.sys_pip_pass:
        # Use xfail to specify error that is from a pip installation problem
        pytest.xfail("pip installation error")

    return package_data.overall_pass


# use class scope to start and finish at end of all parametrized tests
@pytest.fixture(scope="class")
def start_end_report(module_globals, request):
    reports_path = Path(REPORTS_DIR)
    reports_path.mkdir(exist_ok=True, parents=True)

    module_globals.reset()
    module_globals.test_class = getattr(request.cls, "test_class", "unknown")
    report_filename = (
        f"{REPORT_FILENAME_ROOT}_"
        f"{module_globals.test_class}_"
        f"report_"
        f"{module_globals.sys_platform}_"
        f"{module_globals.py_version_short}_"
        f"{module_globals.test_start.strftime('%Y%m%d')}.txt"
    )
    errors_filename = (
        f"{REPORT_FILENAME_ROOT}_"
        f"{module_globals.test_class}_"
        f"errors_"
        f"{module_globals.sys_platform}_"
        f"{module_globals.py_version_short}_"
        f"{module_globals.test_start.strftime('%Y%m%d')}.txt"
    )
    module_globals.report_path = reports_path / report_filename
    module_globals.errors_path = reports_path / errors_filename

    with module_globals.report_path.open("a") as report_fh:
        print(format_report_table_header(module_globals), file=report_fh)

    yield

    with module_globals.report_path.open("a") as report_fh:
        print(format_report_table_footer(module_globals), file=report_fh)


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
