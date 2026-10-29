from __future__ import annotations

from dataclasses import replace
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Final, NoReturn

import pytest

from pipx import paths, subprocess_runner
from pipx.commands.run_uv import run_script_via_uv_run, run_via_uv_tool_run, translate_pip_args_for_uv
from pipx.constants import FetchPythonOptions
from pipx.options import DEFAULT_BACKEND_OPTIONS, CooldownOptions, RunOptions
from pipx.redact import redact_url_credentials
from pipx.util import PipxError

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


@pytest.fixture
def fake_uv(mocker: MockerFixture) -> Path:
    binary: Final[Path] = Path("/opt/uv/bin/uv")
    mocker.patch("pipx.commands.run_uv.resolve_uv_binary", return_value=binary)
    return binary


_RUN_OPTIONS: Final[RunOptions] = RunOptions(
    app_args=[],
    dependencies=[],
    python="",
    pip_args=[],
    venv_args=[],
    is_path=False,
    pypackages=False,
    verbose=False,
    use_cache=True,
    python_args=[],
    refresh=False,
    no_path_check=False,
    backend=DEFAULT_BACKEND_OPTIONS,
    cooldown=CooldownOptions(),
    python_flag_passed=False,
    fetch_python=FetchPythonOptions.NEVER,
)


@pytest.fixture
def tool_run(mocker: MockerFixture) -> partial[NoReturn]:
    mocker.patch("pipx.commands.run_uv.which", autospec=True, return_value=None)
    return partial(run_via_uv_tool_run, "black", "black")


@pytest.fixture
def script_run(tmp_path: Path) -> partial[NoReturn]:
    (script := tmp_path / "demo.py").write_text("print('hi')\n")
    return partial(run_script_via_uv_run, script, tmp_path / "venv")


@pytest.fixture
def exec_mock(mocker: MockerFixture) -> MagicMock:
    mocked_exec: Final[MagicMock] = mocker.create_autospec(subprocess_runner.exec_app, side_effect=RuntimeError("exec"))
    mocker.patch("pipx.commands.run_uv.exec_app", new=mocked_exec)
    return mocked_exec


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
    tool_run: partial[NoReturn],
    cooldown_days: int | None,
    cooldown_args: list[str],
) -> None:
    with pytest.raises(RuntimeError, match="exec"):
        tool_run(
            replace(
                _RUN_OPTIONS,
                app_args=["--check"],
                python="python3.12",
                cooldown=CooldownOptions(cli_days=cooldown_days),
            )
        )

    assert exec_mock.call_args.args[0] == [
        str(fake_uv),
        "tool",
        "run",
        "--python",
        "python3.12",
        *cooldown_args,
        "--",
        "black",
        "--check",
    ]


@pytest.mark.usefixtures("tool_run")
def test_run_via_uv_tool_run_threads_spec_and_with(exec_mock: MagicMock, fake_uv: Path) -> None:
    with pytest.raises(RuntimeError, match="exec"):
        run_via_uv_tool_run(
            "rope",
            "git+https://example.com/rope.git",
            replace(
                _RUN_OPTIONS,
                dependencies=["rich", "click"],
                app_args=["--version"],
                python="python3.12",
                pip_args=["--index-url", "https://example.com/simple", "--pre"],
                use_cache=False,
                verbose=True,
            ),
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
        "--default-index",
        "https://example.com/simple",
        "--prerelease=allow",
        "--",
        "rope",
        "--version",
    ]


@pytest.mark.usefixtures("fake_uv")
def test_run_via_uv_tool_run_omits_from_when_app_matches_spec(
    exec_mock: MagicMock, tool_run: partial[NoReturn]
) -> None:
    with pytest.raises(RuntimeError, match="exec"):
        tool_run(_RUN_OPTIONS)

    assert "--from" not in exec_mock.call_args.args[0]


@pytest.mark.usefixtures("fake_uv")
def test_run_via_uv_tool_run_refreshes_cache(exec_mock: MagicMock, tool_run: partial[NoReturn]) -> None:
    with pytest.raises(RuntimeError, match="exec"):
        tool_run(replace(_RUN_OPTIONS, refresh=True))

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
    script_run: partial[NoReturn],
    cooldown_days: int | None,
    cooldown_args: list[str],
) -> None:
    with pytest.raises(RuntimeError, match="exec"):
        script_run(
            replace(
                _RUN_OPTIONS,
                app_args=["--quiet"],
                python="python3.12",
                cooldown=CooldownOptions(cli_days=cooldown_days),
            )
        )

    assert exec_mock.call_args.args[0] == [
        str(fake_uv),
        "run",
        "--active",
        "--script",
        "--project",
        str(paths.CTX.home),
        "--python",
        "python3.12",
        *cooldown_args,
        str(script_run.args[0]),
        "--quiet",
    ]


@pytest.mark.usefixtures("fake_uv")
def test_run_script_via_uv_run_refreshes_cache(exec_mock: MagicMock, script_run: partial[NoReturn]) -> None:
    with pytest.raises(RuntimeError, match="exec"):
        script_run(replace(_RUN_OPTIONS, refresh=True))

    assert "--refresh" in exec_mock.call_args.args[0]


@pytest.mark.parametrize(
    ("venv_arg", "expected"),
    [
        pytest.param(
            "--system-site-packages",
            "--system-site-packages is not supported by `pipx run` under the uv backend.\n",
            id="plain",
        ),
        pytest.param(
            "--prompt=http://u:s3cr3ttok@host/",
            f"{redact_url_credentials('--prompt=http://u:s3cr3ttok@host/')} is not supported",
            id="credentials-masked",
        ),
    ],
)
@pytest.mark.usefixtures("fake_uv", "exec_mock")
def test_run_via_uv_tool_run_rejects_venv_args(tool_run: partial[NoReturn], venv_arg: str, expected: str) -> None:
    with pytest.raises(PipxError) as error:
        tool_run(replace(_RUN_OPTIONS, venv_args=[venv_arg]))

    assert str(error.value).startswith(expected)


@pytest.mark.parametrize(
    ("pip_args", "expected"),
    [
        pytest.param([], [], id="empty"),
        pytest.param(["-q"], [], id="strip-quiet-short"),
        pytest.param(["--quiet"], [], id="strip-quiet-long"),
        pytest.param(
            ["--index-url", "https://example.com/simple"],
            ["--default-index", "https://example.com/simple"],
            id="index-url",
        ),
        pytest.param(
            ["-i", "https://example.com/simple"],
            ["--default-index", "https://example.com/simple"],
            id="index-url-short",
        ),
        pytest.param(
            ["--extra-index-url", "https://other.example/simple"],
            ["--extra-index-url", "https://other.example/simple"],
            id="extra-index",
        ),
        pytest.param(["--pre"], ["--prerelease=allow"], id="pre-to-prerelease"),
        pytest.param(["--index-url=https://example.com"], ["--default-index=https://example.com"], id="equals-form"),
        pytest.param(["--no-binary", ":all:"], ["--no-binary"], id="no-binary-all"),
        pytest.param(
            ["--no-binary", "one,two"],
            ["--no-binary-package", "one", "--no-binary-package", "two"],
            id="no-binary-packages",
        ),
        pytest.param(["--no-binary=:none:"], [], id="no-binary-none"),
        pytest.param(["--only-binary", ":all:"], ["--no-build"], id="only-binary-all"),
        pytest.param(
            ["--only-binary=one,two"],
            ["--no-build-package", "one", "--no-build-package", "two"],
            id="only-binary-packages",
        ),
        pytest.param(
            ["--trusted-host", "packages.example"],
            ["--allow-insecure-host", "packages.example"],
            id="trusted-host",
        ),
        pytest.param(
            ["--trusted-host=packages.example"],
            ["--allow-insecure-host=packages.example"],
            id="trusted-host-equals",
        ),
    ],
)
def test_translate_pip_args_for_uv(pip_args: list[str], expected: list[str]) -> None:
    assert translate_pip_args_for_uv(pip_args) == expected


@pytest.mark.parametrize(
    ("pip_args", "match"),
    [
        pytest.param(["--editable"], "is not supported", id="editable"),
        pytest.param(["-e"], "is not supported", id="editable-short"),
        pytest.param(
            ["--no-build-isolation"],
            "contains '--no-build-isolation', which has no",
            id="unknown-flag",
        ),
        pytest.param(["--no-deps"], "contains '--no-deps', which has no", id="no-deps"),
        pytest.param(["--no-binary="], "Invalid value", id="empty-no-binary"),
        pytest.param(["--index-url"], "Missing value", id="missing-value"),
    ],
)
def test_translate_pip_args_for_uv_errors(pip_args: list[str], match: str) -> None:
    with pytest.raises(PipxError, match=match):
        translate_pip_args_for_uv(pip_args)


def test_translate_pip_args_for_uv_rejection_hides_url_credentials() -> None:
    proxy: Final[str] = "--proxy=http://u:s3cr3ttok@proxy:3128"

    with pytest.raises(PipxError) as error:
        translate_pip_args_for_uv([proxy])

    assert str(error.value).startswith(f"--pip-args contains {redact_url_credentials(proxy)!r}, which has no")
