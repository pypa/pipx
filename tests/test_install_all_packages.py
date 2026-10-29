from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from all_packages import PACKAGE_NAMES, Report, install_package_both_paths, open_report, pip_cache_purge

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.mark.parametrize("package_name", PACKAGE_NAMES)
@pytest.mark.all_packages
@pytest.mark.usefixtures("pipx_temp_env")
def test_all_packages(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    report: Report,
    package_name: str,
) -> None:
    pip_cache_purge()
    assert install_package_both_paths(monkeypatch, capsys, caplog, report, package_name, deps=False)


@pytest.fixture(scope="module")
def report() -> Iterator[Report]:
    with open_report("nodeps") as nodeps_report:
        yield nodeps_report
