from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from pipx.commands.run_uv import run_script_via_uv_run, run_via_uv_tool_run
from pipx.util import PipxError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def fake_uv(mocker: MockerFixture) -> Path:
    binary = Path("/opt/uv/bin/uv")
    mocker.patch("pipx.commands.run_uv.resolve_uv_binary", return_value=binary)
    return binary


def test_run_via_uv_tool_run_basic(mocker: MockerFixture, fake_uv: Path) -> None:
    exec_mock = mocker.patch("pipx.commands.run_uv.exec_app")
    mocker.patch("pipx.commands.run_uv.which", return_value=None)
    run_via_uv_tool_run(
        app="black",
        package_or_url="black",
        dependencies=[],
        app_args=["--check"],
        python="python3.12",
        pip_args=[],
        venv_args=[],
        use_cache=True,
        verbose=False,
    )
    # ``mocker.patch`` keeps ``exec_app``'s ``NoReturn`` annotation, so pre-commit
    # mypy flags everything below as unreachable; ``unused-ignore`` covers the
    # local-checker case where the unreachable detection doesn't fire.
    (cmd,), _ = exec_mock.call_args  # type: ignore[unreachable, unused-ignore]
    assert cmd == [str(fake_uv), "tool", "run", "--python", "python3.12", "black", "--check"]


def test_run_via_uv_tool_run_threads_spec_and_with(mocker: MockerFixture, fake_uv: Path) -> None:
    exec_mock = mocker.patch("pipx.commands.run_uv.exec_app")
    mocker.patch("pipx.commands.run_uv.which", return_value=None)
    run_via_uv_tool_run(
        app="rope",
        package_or_url="git+https://example.com/rope.git",
        dependencies=["rich", "click"],
        app_args=["--version"],
        python="python3.12",
        pip_args=["--index-url", "https://example.com/simple", "--pre"],
        venv_args=[],
        use_cache=False,
        verbose=True,
    )
    (cmd,), _ = exec_mock.call_args  # type: ignore[unreachable, unused-ignore]
    assert cmd == [
        str(fake_uv),
        "tool",
        "run",
        "--from",
        "git+https://example.com/rope.git",
        "--python",
        "python3.12",
        "--with",
        "rich",
        "--with",
        "click",
        "--no-cache",
        "--verbose",
        "--index-url",
        "https://example.com/simple",
        "--prerelease=allow",
        "rope",
        "--version",
    ]


def test_run_via_uv_tool_run_omits_from_when_app_matches_spec(mocker: MockerFixture, fake_uv: Path) -> None:
    exec_mock = mocker.patch("pipx.commands.run_uv.exec_app")
    mocker.patch("pipx.commands.run_uv.which", return_value=None)
    run_via_uv_tool_run(
        app="black",
        package_or_url="black",
        dependencies=[],
        app_args=[],
        python="",
        pip_args=[],
        venv_args=[],
        use_cache=True,
        verbose=False,
    )
    (cmd,), _ = exec_mock.call_args  # type: ignore[unreachable, unused-ignore]
    assert "--from" not in cmd


def test_run_script_via_uv_run_uses_uv_run_script(mocker: MockerFixture, fake_uv: Path, tmp_path: Path) -> None:
    exec_mock = mocker.patch("pipx.commands.run_uv.exec_app")
    script = tmp_path / "demo.py"
    script.write_text("print('hi')\n")
    run_script_via_uv_run(
        script_path=script,
        app_args=["--quiet"],
        python="python3.12",
        pip_args=[],
        venv_args=[],
        use_cache=True,
        verbose=False,
    )
    (cmd,), _ = exec_mock.call_args  # type: ignore[unreachable, unused-ignore]
    assert cmd == [str(fake_uv), "run", "--script", "--python", "python3.12", str(script), "--quiet"]


def test_run_via_uv_tool_run_rejects_venv_args(mocker: MockerFixture, fake_uv: Path) -> None:
    mocker.patch("pipx.commands.run_uv.exec_app")
    mocker.patch("pipx.commands.run_uv.which", return_value=None)
    with pytest.raises(PipxError, match=r"--venv-args .* is not supported"):
        run_via_uv_tool_run(
            app="black",
            package_or_url="black",
            dependencies=[],
            app_args=[],
            python="",
            pip_args=[],
            venv_args=["--system-site-packages"],
            use_cache=True,
            verbose=False,
        )
