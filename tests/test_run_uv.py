from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from pipx.commands.run_uv import run_script_via_uv_run, run_via_uv_tool_run
from pipx.util import PipxError

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


@pytest.fixture
def fake_uv(mocker: MockerFixture) -> Path:
    binary: Final[Path] = Path("/opt/uv/bin/uv")
    mocker.patch("pipx.commands.run_uv.resolve_uv_binary", return_value=binary)
    return binary


@pytest.mark.parametrize(
    ("cooldown_days", "cooldown_args"),
    [
        pytest.param(None, [], id="unset"),
        pytest.param(7, ["--exclude-newer", "P7D"], id="seven-days"),
    ],
)
def test_run_via_uv_tool_run_basic(
    exec_mock: MagicMock,
    fake_uv: Path,
    mocker: MockerFixture,
    cooldown_days: int | None,
    cooldown_args: list[str],
) -> None:
    mocker.patch("pipx.commands.run_uv.which", return_value=None)
    with pytest.raises(RuntimeError, match="exec"):
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
            cooldown_days=cooldown_days,
        )
    assert exec_mock.call_args.args[0] == [
        str(fake_uv),
        "tool",
        "run",
        "--python",
        "python3.12",
        *cooldown_args,
        "black",
        "--check",
    ]


def test_run_via_uv_tool_run_threads_spec_and_with(
    exec_mock: MagicMock,
    fake_uv: Path,
    mocker: MockerFixture,
) -> None:
    mocker.patch("pipx.commands.run_uv.which", return_value=None)
    with pytest.raises(RuntimeError, match="exec"):
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
    assert exec_mock.call_args.args[0] == [
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


@pytest.mark.usefixtures("fake_uv")
def test_run_via_uv_tool_run_omits_from_when_app_matches_spec(
    exec_mock: MagicMock,
    mocker: MockerFixture,
) -> None:
    mocker.patch("pipx.commands.run_uv.which", return_value=None)
    with pytest.raises(RuntimeError, match="exec"):
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
    assert "--from" not in exec_mock.call_args.args[0]


@pytest.mark.usefixtures("fake_uv")
def test_run_via_uv_tool_run_refreshes_cache(
    exec_mock: MagicMock,
    mocker: MockerFixture,
) -> None:
    mocker.patch("pipx.commands.run_uv.which", return_value=None)
    with pytest.raises(RuntimeError, match="exec"):
        run_via_uv_tool_run(
            app="black",
            package_or_url="black",
            dependencies=[],
            app_args=[],
            python="",
            pip_args=[],
            venv_args=[],
            use_cache=True,
            refresh=True,
            verbose=False,
        )
    assert "--refresh" in exec_mock.call_args.args[0]


@pytest.mark.parametrize(
    ("cooldown_days", "cooldown_args"),
    [
        pytest.param(None, [], id="unset"),
        pytest.param(7, ["--exclude-newer", "P7D"], id="seven-days"),
    ],
)
def test_run_script_via_uv_run_uses_uv_run_script(
    exec_mock: MagicMock,
    fake_uv: Path,
    tmp_path: Path,
    cooldown_days: int | None,
    cooldown_args: list[str],
) -> None:
    script: Final[Path] = tmp_path / "demo.py"
    script.write_text("print('hi')\n")
    with pytest.raises(RuntimeError, match="exec"):
        run_script_via_uv_run(
            script_path=script,
            app_args=["--quiet"],
            python="python3.12",
            pip_args=[],
            venv_args=[],
            use_cache=True,
            verbose=False,
            cooldown_days=cooldown_days,
        )
    assert exec_mock.call_args.args[0] == [
        str(fake_uv),
        "run",
        "--script",
        "--python",
        "python3.12",
        *cooldown_args,
        str(script),
        "--quiet",
    ]


@pytest.mark.usefixtures("fake_uv")
def test_run_script_via_uv_run_refreshes_cache(
    exec_mock: MagicMock,
    tmp_path: Path,
) -> None:
    script: Final[Path] = tmp_path / "demo.py"
    script.write_text("print('hi')\n")
    with pytest.raises(RuntimeError, match="exec"):
        run_script_via_uv_run(
            script_path=script,
            app_args=[],
            python="",
            pip_args=[],
            venv_args=[],
            use_cache=True,
            verbose=False,
            refresh=True,
        )
    assert "--refresh" in exec_mock.call_args.args[0]


@pytest.mark.usefixtures("fake_uv")
def test_run_via_uv_tool_run_rejects_venv_args(mocker: MockerFixture) -> None:
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


@pytest.fixture
def exec_mock(mocker: MockerFixture) -> MagicMock:
    mocked_exec: Final[MagicMock] = mocker.MagicMock(side_effect=RuntimeError("exec"))
    mocker.patch("pipx.commands.run_uv.exec_app", new=mocked_exec)
    return mocked_exec
