"""
This module uses the pytest infrastructure to produce reports on a large list
of packages.  It verifies installation with and without an intact system PATH.
It also generates report summaries and error reports files.

Test pytest outcomes:
    PASS - if no pip errors, and no pipx issues, and package apps verified
            all installed correctly
    XFAIL - if there is a pip error, i.e. an installation problem out of pipx's
            control
    FAIL - if there is no pip error, but there is a problem due to pipx,
            including a pipx error or warning, incorrect list of
            installed apps, etc.
"""

import io
import os
import re
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

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
    "zest-releaser",
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
        self.package_name: str = ""
        self.package_spec: str = ""
        self.clear_elapsed_time: Optional[float] = None
        self.clear_pip_pass: Optional[bool] = None
        self.clear_pipx_pass: Optional[bool] = None
        self.sys_elapsed_time: Optional[float] = None
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

    def _get_pass_fail_str(self, test_attr: str) -> str:
        if getattr(self, test_attr) is not None:
            return "PASS" if getattr(self, test_attr) else "FAIL"
        else:
            return ""


class ModuleGlobalsData:
    def __init__(self):
        self.errors_path = Path(".")
        self.install_data: List[PackageData] = []
        self.py_version_display = "Python {0.major}.{0.minor}.{0.micro}".format(sys.version_info)
        self.py_version_short = "{0.major}.{0.minor}".format(sys.version_info)
        self.report_path = Path(".")
        self.sys_platform = sys.platform
        self.test_class = ""
        self.test_start = datetime.now()
        self.test_end = datetime.now()  # default, must be set later

    def reset(self, test_class: str = "") -> None:
        self.errors_path = Path(".")
        self.install_data = []
        self.report_path = Path(".")
        self.test_class = test_class
        self.test_start = datetime.now()


@pytest.fixture(scope="module")
def module_globals() -> ModuleGlobalsData:
    return ModuleGlobalsData()


def pip_cache_purge() -> None:
    subprocess.run([sys.executable, "-m", "pip", "cache", "purge"], check=True)


def write_report_legend(report_legend_path: Path) -> None:
    with report_legend_path.open("w", encoding="utf-8") as report_legend_fh:
        print(
            textwrap.dedent(
                """
                LEGEND
                ===========
                cleared_PATH = PATH used for pipx tests with only pipx bin dir and nothing else
                sys_PATH = Normal system PATH with all default directories included

                overall = PASS or FAIL for complete end-to-end pipx install, PASS if no errors
                        or warnings and all the proper apps were installed and linked
                pip = PASS or FAIL sub-category based only if pip inside of pipx installs
                        package with/without error
                pipx = PASS or FAIL sub-category based on the non-pip parts of pipx, including
                        whether any errors or warnings are present, and if all the proper apps
                        were installed and linked
                """
            ).strip(),
            file=report_legend_fh,
        )


def format_report_table_header(module_globals: ModuleGlobalsData) -> str:
    header_string = "\n\n"
    header_string += "=" * 79 + "\n"

    header_string += f"{module_globals.sys_platform:16}"
    header_string += f"{module_globals.py_version_display:16}"
    header_string += f"{module_globals.test_start.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    header_string += f"{'package_spec':24}{'overall':12}{'cleared_PATH':24}"
    header_string += f"{'system_PATH':24}\n"

    header_string += f"{'':24}{'':12}{'pip':8}{'pipx':8}{'time':8}"
    header_string += f"{'pip':8}{'pipx':8}{'time':8}\n"

    header_string += "-" * 79

    return header_string


def format_report_table_row(package_data: PackageData) -> str:
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


def format_report_table_footer(module_globals: ModuleGlobalsData) -> str:
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

    dt_string = module_globals.test_end.strftime("%Y-%m-%d %H:%M:%S")
    el_datetime = module_globals.test_end - module_globals.test_start
    el_datetime = el_datetime - timedelta(microseconds=el_datetime.microseconds)
    footer_string += f"\nFinished {dt_string}\n"
    footer_string += f"Elapsed: {el_datetime}"

    return footer_string


def verify_installed_resources(
    resource_type: str,
    captured_outerr,
    package_name: str,
    test_error_fh: io.StringIO,
    deps: bool = False,
) -> bool:
    resource_name = {"app": "apps", "man": "man_pages"}[resource_type]
    resource_name_long = {"app": "apps", "man": "manual pages"}[resource_type]
    package_resources = PKG[package_name][resource_name].copy()
    if deps:
        package_resources += PKG[package_name]["%s_of_dependencies" % resource_name]
    if len(package_resources) == 0:
        return True

    reported_resources_re = re.search(
        r"These " + resource_name_long + r" are now globally available\n((?:    - [^\n]+\n)*)",
        captured_outerr.out,
        re.DOTALL,
    )
    if reported_resources_re:
        reported_resources = [x.strip()[2:] for x in reported_resources_re.group(1).strip().split("\n")]
        if set(reported_resources) != set(package_resources):
            resource_success = False
            print("verify_install: REPORTED APPS DO NOT MATCH PACKAGE", file=test_error_fh)
            print(
                f"pipx reported %s: {reported_resources}" % resource_name,
                file=test_error_fh,
            )
            print(
                f" true package %s: {package_resources}" % resource_name,
                file=test_error_fh,
            )
        else:
            resource_success = True
    else:
        resource_success = False
        print("verify_install: APPS TESTING ERROR", file=test_error_fh)

    return resource_success


def verify_post_install(
    pipx_exit_code: int,
    captured_outerr,
    caplog,
    package_name: str,
    test_error_fh: io.StringIO,
    using_clear_path: bool,
    deps: bool = False,
) -> Tuple[bool, Optional[bool], Optional[Path]]:
    pip_error_file = None
    caplog_problem = False
    install_success = f"installed package {package_name}" in captured_outerr.out
    for record in caplog.records:
        if "⚠️" in record.message or "WARNING" in record.message:
            if using_clear_path or "was already on your PATH" not in record.message:
                caplog_problem = True
            print("verify_install: WARNING IN CAPLOG:", file=test_error_fh)
            print(record.message, file=test_error_fh)
        if "Fatal error from pip prevented installation" in record.message:
            pip_error_file_re = re.search(r"pip output in file:\s+(\S.+)$", record.message)
            if pip_error_file_re:
                pip_error_file = Path(pip_error_file_re.group(1))

    if install_success and PKG[package_name].get("apps", None) is not None:
        app_success = verify_installed_resources("app", captured_outerr, package_name, test_error_fh, deps=deps)
    else:
        app_success = True
    if install_success and (
        PKG[package_name].get("man_pages", None) is not None
        or PKG[package_name].get("man_pages_of_dependencies", None) is not None
    ):
        man_success = verify_installed_resources("man", captured_outerr, package_name, test_error_fh, deps=deps)
    else:
        man_success = True

    pip_pass = not ((pipx_exit_code != 0) and f"Error installing {package_name}" in captured_outerr.err)
    pipx_pass: Optional[bool]
    if pip_pass:
        pipx_pass = install_success and not caplog_problem and app_success and man_success
    else:
        pipx_pass = None

    return pip_pass, pipx_pass, pip_error_file


def print_error_report(
    module_globals: ModuleGlobalsData,
    command_captured,
    test_error_fh: io.StringIO,
    package_spec: str,
    test_type: str,
    pip_error_file: Optional[Path],
) -> None:
    with module_globals.errors_path.open("a", encoding="utf-8") as errors_fh:
        print("\n\n", file=errors_fh)
        print("=" * 79, file=errors_fh)
        print(
            f"{package_spec:24}{test_type:16}{module_globals.sys_platform:16}" f"{module_globals.py_version_display}",
            file=errors_fh,
        )
        print("\nSTDOUT:", file=errors_fh)
        print("-" * 76, file=errors_fh)
        print(command_captured.out, end="", file=errors_fh)
        print("\nSTDERR:", file=errors_fh)
        print("-" * 76, file=errors_fh)
        print(command_captured.err, end="", file=errors_fh)
        if pip_error_file is not None:
            print("\nPIP ERROR LOG FILE:", file=errors_fh)
            print("-" * 76, file=errors_fh)
            with pip_error_file.open("r") as pip_error_fh:
                print(pip_error_fh.read(), end="", file=errors_fh)
        print("\n\nTEST WARNINGS / ERRORS:", file=errors_fh)
        print("-" * 76, file=errors_fh)
        print(test_error_fh.getvalue(), end="", file=errors_fh)


def install_and_verify(
    capsys: pytest.CaptureFixture,
    caplog,
    monkeypatch,
    module_globals: ModuleGlobalsData,
    using_clear_path: bool,
    package_data: PackageData,
    deps: bool,
) -> Tuple[bool, Optional[bool], float]:
    _ = capsys.readouterr()
    caplog.clear()

    test_error_fh = io.StringIO()

    monkeypatch.setenv("PATH", os.getenv("PATH_TEST" if using_clear_path else "PATH_ORIG"))

    start_time = time.time()
    pipx_exit_code = run_pipx_cli(
        ["install", package_data.package_spec, "--verbose"] + (["--include-deps"] if deps else [])
    )
    elapsed_time = time.time() - start_time
    captured = capsys.readouterr()

    pip_pass, pipx_pass, pip_error_file = verify_post_install(
        pipx_exit_code,
        captured,
        caplog,
        package_data.package_name,
        test_error_fh,
        using_clear_path=using_clear_path,
        deps=deps,
    )

    if not pip_pass or not pipx_pass:
        print_error_report(
            module_globals,
            captured,
            test_error_fh,
            package_data.package_spec,
            "clear PATH" if using_clear_path else "sys PATH",
            pip_error_file,
        )

    return pip_pass, pipx_pass, elapsed_time


def install_package_both_paths(
    monkeypatch,
    capsys: pytest.CaptureFixture,
    caplog,
    module_globals: ModuleGlobalsData,
    pipx_temp_env,
    package_name: str,
    deps: bool = False,
) -> bool:
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
        package_data=package_data,
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
            package_data=package_data,
            deps=deps,
        )

    package_data.overall_pass = bool(
        (package_data.clear_pip_pass and package_data.clear_pipx_pass)
        or (package_data.sys_pip_pass and package_data.sys_pipx_pass)
    )

    with module_globals.report_path.open("a", encoding="utf-8") as report_fh:
        print(format_report_table_row(package_data), file=report_fh, flush=True)

    if not package_data.clear_pip_pass and not package_data.sys_pip_pass:
        # Use xfail to specify error that is from a pip installation problem
        pytest.xfail("pip installation error")

    return package_data.overall_pass


# use class scope to start and finish at end of all parametrized tests
@pytest.fixture(scope="class")
def start_end_test_class(module_globals: ModuleGlobalsData, request):
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

    write_report_legend(reports_path / f"{REPORT_FILENAME_ROOT}_report_legend.txt")

    with module_globals.report_path.open("a", encoding="utf-8") as report_fh:
        print(format_report_table_header(module_globals), file=report_fh)

    yield

    module_globals.test_end = datetime.now()
    with module_globals.report_path.open("a", encoding="utf-8") as report_fh:
        print(format_report_table_footer(module_globals), file=report_fh)


class TestAllPackagesNoDeps:
    test_class = "nodeps"

    @pytest.mark.parametrize("package_name", PACKAGE_NAME_LIST)
    @pytest.mark.all_packages
    def test_all_packages(
        self,
        monkeypatch,
        capsys: pytest.CaptureFixture,
        caplog,
        module_globals: ModuleGlobalsData,
        start_end_test_class,
        pipx_temp_env,
        package_name: str,
    ):
        pip_cache_purge()
        assert install_package_both_paths(
            monkeypatch,
            capsys,
            caplog,
            module_globals,
            pipx_temp_env,
            package_name,
            deps=False,
        )


class TestAllPackagesDeps:
    test_class = "deps"

    @pytest.mark.parametrize("package_name", PACKAGE_NAME_LIST)
    @pytest.mark.all_packages
    def test_deps_all_packages(
        self,
        monkeypatch,
        capsys: pytest.CaptureFixture,
        caplog,
        module_globals: ModuleGlobalsData,
        start_end_test_class,
        pipx_temp_env,
        package_name: str,
    ):
        pip_cache_purge()
        assert install_package_both_paths(
            monkeypatch,
            capsys,
            caplog,
            module_globals,
            pipx_temp_env,
            package_name,
            deps=True,
        )
