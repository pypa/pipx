from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import textwrap
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from helpers import run_pipx_cli
from package_info import PKG

if TYPE_CHECKING:
    from collections.abc import Generator

    from _pytest.capture import CaptureResult

PACKAGE_NAMES: Final[list[str]] = [
    "ansible",
    "awscli",
    "b2",
    "beancount",
    "beets",
    "black",
    "cactus",
    "chert",
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


@contextmanager
def open_report(variant: str) -> Generator[Report]:
    # one report spans every package a test module installs
    reports_path: Final[Path] = Path("./reports")
    reports_path.mkdir(exist_ok=True, parents=True)
    test_start: Final[datetime] = datetime.now(tz=UTC)
    report_suffix: Final[str] = (
        f"{sys.platform}_{sys.version_info.major}.{sys.version_info.minor}_{test_start.strftime('%Y%m%d')}.txt"
    )
    report: Final[Report] = Report(
        report_path=reports_path / f"all_packages_{variant}_report_{report_suffix}",
        errors_path=reports_path / f"all_packages_{variant}_errors_{report_suffix}",
        test_start=test_start,
    )

    _write_report_legend(reports_path / "all_packages_report_legend.txt")

    with report.report_path.open("a", encoding="utf-8") as report_fh:
        print(_format_report_table_header(report), file=report_fh)

    try:
        yield report
    finally:
        test_end: Final[datetime] = datetime.now(tz=UTC)
        with report.report_path.open("a", encoding="utf-8") as report_fh:
            print(_format_report_table_footer(report, test_end), file=report_fh)


@dataclass(slots=True, kw_only=True)
class Report:
    report_path: Path
    errors_path: Path
    test_start: datetime
    install_data: list[PackageData] = field(default_factory=list)


def _write_report_legend(report_legend_path: Path) -> None:
    legend: Final[str] = textwrap.dedent(
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
    ).strip()
    report_legend_path.write_text(f"{legend}\n", encoding="utf-8")


def _format_report_table_header(report: Report) -> str:
    return (
        f"\n\n{'=' * 79}\n"
        f"{sys.platform:16}{_py_version_display():16}"
        f"{report.test_start.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"{'package_spec':24}{'overall':12}{'cleared_PATH':24}{'system_PATH':24}\n"
        f"{'':24}{'':12}{'pip':8}{'pipx':8}{'time':8}{'pip':8}{'pipx':8}{'time':8}\n"
        f"{'-' * 79}"
    )


def _py_version_display() -> str:
    return f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _format_report_table_footer(report: Report, test_end: datetime) -> str:
    fail_list: Final[list[str]] = []
    prebuild_list: Final[list[str]] = []
    for package_data in report.install_data:
        if package_data.clear_pip_pass and package_data.clear_pipx_pass:
            continue
        if not package_data.clear_pip_pass and package_data.sys_pip_pass and package_data.sys_pipx_pass:
            prebuild_list.append(package_data.package_spec)
        else:
            fail_list.append(package_data.package_spec)

    summary: Final[list[str]] = ["", "Summary", "-" * 79]
    for title, package_specs in (("FAILS:", fail_list), ("Needs prebuilt wheel:", prebuild_list)):
        summary.extend(
            [title, *(f"    {package_spec}" for package_spec in sorted(package_specs, key=str.lower))]
            if package_specs
            else []
        )
    elapsed: Final[timedelta] = test_end - report.test_start
    summary.extend([
        "",
        f"Finished {test_end.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Elapsed: {elapsed - timedelta(microseconds=elapsed.microseconds)}",
    ])
    return "\n".join(summary)


def pip_cache_purge() -> None:
    subprocess.run([sys.executable, "-m", "pip", "cache", "purge"], check=True)


def install_package_both_paths(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    report: Report,
    package_name: str,
    *,
    deps: bool,
) -> bool:
    package_data: Final[PackageData] = PackageData(package_name=package_name, package_spec=PKG[package_name]["spec"])
    report.install_data.append(package_data)

    (
        package_data.clear_pip_pass,
        package_data.clear_pipx_pass,
        package_data.clear_elapsed_time,
    ) = _install_and_verify(
        capsys,
        caplog,
        monkeypatch,
        report,
        using_clear_path=True,
        package_data=package_data,
        deps=deps,
    )
    if not package_data.clear_pip_pass:
        # a package that fails to build with the cleared PATH may install with the system one; the report lists it
        # as needing a prebuilt wheel
        (
            package_data.sys_pip_pass,
            package_data.sys_pipx_pass,
            package_data.sys_elapsed_time,
        ) = _install_and_verify(
            capsys,
            caplog,
            monkeypatch,
            report,
            using_clear_path=False,
            package_data=package_data,
            deps=deps,
        )

    package_data.overall_pass = bool(
        (package_data.clear_pip_pass and package_data.clear_pipx_pass)
        or (package_data.sys_pip_pass and package_data.sys_pipx_pass)
    )

    with report.report_path.open("a", encoding="utf-8") as report_fh:
        print(_format_report_table_row(package_data), file=report_fh, flush=True)

    # a test passes when pip and pipx both succeed and xfails on a pip error, which is outside pipx's control; a pipx
    # error or warning, or a wrong list of installed apps, fails it
    if not package_data.clear_pip_pass and not package_data.sys_pip_pass:
        pytest.xfail("pip installation error")

    return package_data.overall_pass


@dataclass(slots=True, kw_only=True)
class PackageData:
    package_name: str
    package_spec: str
    clear_elapsed_time: float | None = None
    clear_pip_pass: bool | None = None
    clear_pipx_pass: bool | None = None
    sys_elapsed_time: float | None = None
    sys_pip_pass: bool | None = None
    sys_pipx_pass: bool | None = None
    overall_pass: bool | None = None


def _install_and_verify(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    report: Report,
    *,
    using_clear_path: bool,
    package_data: PackageData,
    deps: bool,
) -> tuple[bool, bool | None, float]:
    capsys.readouterr()
    caplog.clear()
    test_error_fh: Final[io.StringIO] = io.StringIO()
    monkeypatch.setenv("PATH", os.environ["PATH_TEST" if using_clear_path else "PATH_ORIG"])

    start_time: Final[float] = time.time()
    pipx_exit_code: Final[int] = run_pipx_cli([
        "install",
        package_data.package_spec,
        "--verbose",
        *(["--include-deps"] if deps else []),
    ])
    elapsed_time: Final[float] = time.time() - start_time
    captured: Final[CaptureResult[str]] = capsys.readouterr()

    pip_pass, pipx_pass, pip_error_file = _verify_post_install(
        pipx_exit_code,
        captured,
        caplog,
        package_data.package_name,
        test_error_fh,
        using_clear_path=using_clear_path,
        deps=deps,
    )

    if not pip_pass or not pipx_pass:
        _print_error_report(
            report,
            captured,
            test_error_fh,
            package_data.package_spec,
            "clear PATH" if using_clear_path else "sys PATH",
            pip_error_file=pip_error_file,
        )

    return pip_pass, pipx_pass, elapsed_time


def _verify_post_install(
    pipx_exit_code: int,
    captured_outerr: CaptureResult[str],
    caplog: pytest.LogCaptureFixture,
    package_name: str,
    test_error_fh: io.StringIO,
    *,
    using_clear_path: bool,
    deps: bool,
) -> tuple[bool, bool | None, Path | None]:
    pip_error_file: Path | None = None
    caplog_problem = False
    for record in caplog.records:
        if "⚠️" in record.message or "WARNING" in record.message:
            if using_clear_path or "was already on your PATH" not in record.message:
                caplog_problem = True
            print("verify_install: WARNING IN CAPLOG:", file=test_error_fh)
            print(record.message, file=test_error_fh)
        if "Fatal error from pip prevented installation" in record.message and (
            pip_error_file_re := re.search(r"pip output in file:\s+(\S.+)$", record.message)
        ):
            pip_error_file = Path(pip_error_file_re.group(1))

    install_success: Final[bool] = f"installed package {package_name}" in captured_outerr.out
    app_success: Final[bool] = (
        _verify_installed_resources("app", captured_outerr, package_name, test_error_fh, deps=deps)
        if install_success and PKG[package_name].get("apps") is not None
        else True
    )
    man_success: Final[bool] = (
        _verify_installed_resources("man", captured_outerr, package_name, test_error_fh, deps=deps)
        if install_success
        and (
            PKG[package_name].get("man_pages") is not None
            or PKG[package_name].get("man_pages_of_dependencies") is not None
        )
        else True
    )
    pip_pass: Final[bool] = not (pipx_exit_code != 0 and f"Error installing {package_name}" in captured_outerr.err)
    return (
        pip_pass,
        install_success and not caplog_problem and app_success and man_success if pip_pass else None,
        pip_error_file,
    )


def _verify_installed_resources(
    resource_type: str,
    captured_outerr: CaptureResult[str],
    package_name: str,
    test_error_fh: io.StringIO,
    *,
    deps: bool,
) -> bool:
    resource_name: Final[str] = {"app": "apps", "man": "man_pages"}[resource_type]
    package_resources: Final[list[str]] = [
        *PKG[package_name][resource_name],
        *(PKG[package_name][f"{resource_name}_of_dependencies"] if deps else []),
    ]
    if not package_resources:
        return True

    resource_name_long: Final[str] = {"app": "apps", "man": "manual pages"}[resource_type]
    if not (
        reported_resources_re := re.search(
            rf"These {resource_name_long} are now available\n((?:    - [^\n]+\n)*)", captured_outerr.out, re.DOTALL
        )
    ):
        print("verify_install: APPS TESTING ERROR", file=test_error_fh)
        return False
    reported_resources: Final[list[str]] = [
        line.strip()[2:] for line in reported_resources_re.group(1).strip().split("\n")
    ]
    if set(reported_resources) == set(package_resources):
        return True
    print("verify_install: REPORTED APPS DO NOT MATCH PACKAGE", file=test_error_fh)
    print(f"pipx reported {resource_name}: {reported_resources}", file=test_error_fh)
    print(f" true package {resource_name}: {package_resources}", file=test_error_fh)
    return False


def _print_error_report(
    report: Report,
    command_captured: CaptureResult[str],
    test_error_fh: io.StringIO,
    package_spec: str,
    test_type: str,
    *,
    pip_error_file: Path | None,
) -> None:
    with report.errors_path.open("a", encoding="utf-8") as errors_fh:
        print("\n\n", file=errors_fh)
        print("=" * 79, file=errors_fh)
        print(f"{package_spec:24}{test_type:16}{sys.platform:16}{_py_version_display()}", file=errors_fh)
        print("\nSTDOUT:", file=errors_fh)
        print("-" * 76, file=errors_fh)
        print(command_captured.out, end="", file=errors_fh)
        print("\nSTDERR:", file=errors_fh)
        print("-" * 76, file=errors_fh)
        print(command_captured.err, end="", file=errors_fh)
        if pip_error_file is not None:
            print("\nPIP ERROR LOG FILE:", file=errors_fh)
            print("-" * 76, file=errors_fh)
            print(pip_error_file.read_text(encoding="utf-8"), end="", file=errors_fh)
        print("\n\nTEST WARNINGS / ERRORS:", file=errors_fh)
        print("-" * 76, file=errors_fh)
        print(test_error_fh.getvalue(), end="", file=errors_fh)


def _format_report_table_row(package_data: PackageData) -> str:
    sys_install_time: Final[str] = (
        f"{package_data.sys_elapsed_time:>3.0f}s" if package_data.sys_elapsed_time is not None else ""
    )
    return (
        f"{package_data.package_spec:24}{_pass_fail(package_data.overall_pass):12}"
        f"{_pass_fail(package_data.clear_pip_pass):8}{_pass_fail(package_data.clear_pipx_pass):8}"
        f"{f'{package_data.clear_elapsed_time:>3.0f}s':8}"
        f"{_pass_fail(package_data.sys_pip_pass):8}{_pass_fail(package_data.sys_pipx_pass):8}"
        f"{sys_install_time:8}"
    )


def _pass_fail(outcome: bool | None) -> str:
    if outcome is None:
        return ""
    return "PASS" if outcome else "FAIL"


__all__ = [
    "PACKAGE_NAMES",
    "Report",
    "install_package_both_paths",
    "open_report",
    "pip_cache_purge",
]
