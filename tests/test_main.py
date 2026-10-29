from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final, TypedDict, cast

import pytest
from docutils.core import publish_string
from docutils.writers.manpage import Writer

from helpers import current_log_file, run_pipx_cli, skip_if_windows
from package_info import PKG
from pipx import constants, main, paths
from pipx.util import PipxError, redact_url_credentials

if TYPE_CHECKING:
    from collections.abc import Iterator
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

_ROOT: Final = Path(__file__).parents[1]
_MANPAGE_RST: Final = _ROOT / "docs" / "man" / "pipx.1.rst"
_SKIP_WITHOUT_PERMISSIONS: Final[pytest.MarkDecorator] = pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0, reason="needs POSIX permissions that bind the current user"
)


@pytest.fixture
def exit_early(mocker: MockerFixture) -> MagicMock:
    # the real sys.exit would end the test run, so raise instead and let each test catch it
    return mocker.patch.object(sys, "exit", side_effect=ValueError("raised in test to exit early"))


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        pytest.param(["--help"], "usage: pipx", id="help-flag"),
        pytest.param(["help"], "usage: pipx", id="help-command"),
        pytest.param(["help", "install"], "usage: pipx install", id="help-for-subcommand"),
    ],
)
def test_help_text(exit_early: MagicMock, capsys: pytest.CaptureFixture[str], argv: list[str], expected: str) -> None:
    with pytest.raises(ValueError, match="raised in test to exit early"):
        run_pipx_cli(argv)

    exit_early.assert_called_with(0)
    assert expected in capsys.readouterr().out


def test_version(exit_early: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(ValueError, match="raised in test to exit early"):
        run_pipx_cli(["--version"])

    exit_early.assert_called_with(0)
    assert main.__version__ in capsys.readouterr().out.strip()


@pytest.mark.parametrize(
    ("argv", "executable", "expected"),
    [
        pytest.param("/usr/bin/pipx", "", "pipx", id="installed-script"),
        pytest.param("__main__.py", "/usr/bin/python", "/usr/bin/python -m pipx", id="module-invocation"),
    ],
)
def test_prog_name(mocker: MockerFixture, argv: str, executable: str, expected: str) -> None:
    mocker.patch.object(sys, "argv", [argv])
    mocker.patch.object(sys, "executable", executable)
    assert main.prog_name() == expected


@pytest.mark.parametrize(
    ("start", "pipx_copies", "expected"),
    [
        pytest.param(["launcher"], [], (0, ""), id="console-script"),
        pytest.param(["-m", "pipx"], [], (0, ""), id="module"),
        pytest.param(["-m", "pipx"], ["pipx"], (1, "shadowed"), id="module-found-in-working-directory"),
    ],
)
def test_startup_drops_search_path_entry_python_adds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, start: list[str], pipx_copies: list[str], expected: tuple[int, str]
) -> None:
    monkeypatch.delenv("PYTHONSAFEPATH", raising=False)
    (tmp_path / "launcher").write_text("import sys\nfrom pipx.__main__ import cli\nsys.exit(cli())\n")
    (tmp_path / "platformdirs.py").write_text("raise SystemExit('shadowed')\n")
    for copy in pipx_copies:
        shutil.copytree(Path(main.__file__).parent, tmp_path / copy)

    result = subprocess.run(
        [sys.executable, *start, "environment", "--value", "PIPX_BIN_DIR"],
        check=False,
        capture_output=True,
        cwd=tmp_path,
        text=True,
    )

    assert (result.returncode, result.stderr.strip()) == expected


@skip_if_windows
def test_module_starts_in_removed_working_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYTHONSAFEPATH", raising=False)
    start: Final[str] = "os.execv(sys.executable, [sys.executable, '-m', 'pipx', '--version'])"

    result = subprocess.run(
        [sys.executable, "-c", f"import os, sys; os.rmdir(os.getcwd()); {start}"],
        check=False,
        capture_output=True,
        cwd=tmp_path,
        text=True,
    )

    assert (result.returncode, result.stdout.strip()) == (0, main.__version__)


def test_build_parser_uses_pipx_in_subcommand_help(mocker: MockerFixture, capsys: pytest.CaptureFixture[str]) -> None:
    mocker.patch.object(sys, "argv", ["sphinx-build"])
    parser: Final[argparse.ArgumentParser] = main.build_parser()

    with pytest.raises(SystemExit) as sys_exit:
        parser.parse_args(["run", "--help"])

    assert sys_exit.value.code == 0
    assert capsys.readouterr().out.startswith("usage: pipx run ")


@pytest.mark.usefixtures("exit_early")
def test_run_help_prints_usage_prefix_once_in_color(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("PYTHON_COLORS", raising=False)

    with pytest.raises(ValueError, match="raised in test to exit early"):
        run_pipx_cli(["run", "--help"])

    assert re.sub(r"\x1b\[[0-9;]*m", "", capsys.readouterr().out).count("usage:") == 1


@pytest.mark.parametrize("flag", [pytest.param("-qqq", id="quiet"), pytest.param("-vvvv", id="verbose")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_limit_verbosity(flag: str) -> None:
    assert not run_pipx_cli(["list", flag])


def test_all_subcommands_have_func_registered() -> None:
    parser: Final[argparse.ArgumentParser] = main.get_command_parser()[0]
    subparsers_type: Final[type[argparse.Action]] = argparse._SubParsersAction  # ruff:ignore[private-member-access]  # argparse has no public subparser API
    top_actions = parser._actions  # ruff:ignore[private-member-access]  # argparse has no public subparser API
    subparsers_action = next(a for a in top_actions if isinstance(a, subparsers_type))
    choices: Final[dict[str, argparse.ArgumentParser]] = cast(
        "dict[str, argparse.ArgumentParser]", subparsers_action.choices
    )
    for name, subparser in choices.items():
        assert callable(subparser.get_default("func")), f"{name!r} missing callable func default"
        nested_actions = subparser._actions  # ruff:ignore[private-member-access]  # argparse has no public subparser API
        for nested in (a for a in nested_actions if isinstance(a, subparsers_type)):
            nested_choices = cast("dict[str, argparse.ArgumentParser]", nested.choices)
            for sub_name, sub_parser in nested_choices.items():
                assert callable(sub_parser.get_default("func")), f"{sub_name!r} missing callable func default"


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["install", "pycowsay"], id="install"),
        pytest.param(["inject", "pycowsay", "black"], id="inject"),
        pytest.param(["uninject", "pycowsay", "black"], id="uninject"),
        pytest.param(["expose", "pycowsay"], id="expose"),
        pytest.param(["unexpose", "pycowsay"], id="unexpose"),
        pytest.param(["pin", "pycowsay"], id="pin"),
        pytest.param(["unpin", "pycowsay"], id="unpin"),
        pytest.param(["upgrade", "pycowsay"], id="upgrade"),
        pytest.param(["upgrade-all"], id="upgrade-all"),
        pytest.param(["uninstall", "pycowsay"], id="uninstall"),
        pytest.param(["uninstall-all"], id="uninstall-all"),
        pytest.param(["health"], id="health"),
        pytest.param(["repair"], id="repair"),
        pytest.param(["list"], id="list"),
    ],
)
def test_operation_commands_accept_output_format(argv: list[str]) -> None:
    parser: Final[argparse.ArgumentParser] = main.get_command_parser()[0]

    args: Final[argparse.Namespace] = main.parse_pipx_args(parser, [*argv, "--output", "json"])

    assert args.output == "json"


def test_manpage_matches_parser(tmp_path: Path) -> None:
    generated: Final[Path] = tmp_path / "pipx.1.rst"
    subprocess.run([sys.executable, str(_ROOT / "scripts" / "generate_man.py"), str(generated)], check=True)
    assert _MANPAGE_RST.read_bytes() == generated.read_bytes()


def test_manpage_sections(manpage_troff: bytes) -> None:
    assert re.findall(r"^\.SH (.+)$", manpage_troff.decode(), re.MULTILINE) == [
        "Name",
        "SYNOPSIS",
        "DESCRIPTION",
        "COMMANDS",
        "GLOBAL OPTIONS",
        "ENVIRONMENT VARIABLES",
        "SEE ALSO",
        "AUTHORS",
    ]


def test_manpage_header(manpage_troff: bytes) -> None:
    assert re.search(r'^\.TH "pipx" "1" .* "User Commands"$', manpage_troff.decode(), re.MULTILINE)


@pytest.mark.skipif(shutil.which("man") is None, reason="man is not installed")
@pytest.mark.timeout(60)  # man printed nothing for 5 s on a busy Linux CI runner
def test_manpage_renders(manpage_troff: bytes, tmp_path: Path) -> None:
    manpage: Final[Path] = tmp_path / "pipx.1"
    manpage.write_bytes(manpage_troff)
    result = subprocess.run(
        ["man", str(manpage)],  # ruff:ignore[start-process-with-partial-path]  # man resolves via PATH by design in this render smoke test
        capture_output=True,
        text=True,
        env=os.environ | {"COLUMNS": "200", "MANPAGER": "cat", "PAGER": "cat"},
        stdin=subprocess.DEVNULL,
        check=False,
        timeout=30,
    )
    rendered: Final[str] = re.sub(r".\x08", "", result.stdout)
    assert (result.returncode, "pipx" in rendered.lower(), "SYNOPSIS" in rendered) == (0, True, True)


@pytest.fixture
def manpage_troff() -> bytes:
    source: Final[str] = "\n".join(
        line for line in _MANPAGE_RST.read_text(encoding="utf-8").splitlines() if line.strip() != ":orphan:"
    )
    return publish_string(source, writer=Writer(), settings_overrides={"report_level": 5})


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["inject", "ansible-core", "--force", "ansible"], id="flag-before-dependency"),
        pytest.param(["inject", "ansible-core", "ansible", "--force"], id="flag-after-dependency"),
    ],
)
def test_inject_accepts_force_before_or_after_dependency(argv: list[str]) -> None:
    args: Final[argparse.Namespace] = main.parse_pipx_args(main.get_command_parser()[0], argv)

    assert args.package == "ansible-core"
    assert args.dependencies == ["ansible"]
    assert args.force is True


def test_package_is_path_ignores_existing_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "commit-check").mkdir()

    # regression for #1778: a directory sharing the package name is not a path spec, so this must not raise
    main.package_is_path("commit-check")


@pytest.mark.usefixtures("pipx_temp_env")
def test_package_is_path_rejects_forward_slash(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["uninstall", "namespace/package"])
    assert "'namespace/package' looks like a path" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("missing_raw", "python_raw", "expected_option", "expected_invalid"),
    [
        pytest.param(None, None, constants.FetchPythonOptions.NEVER, False, id="unset"),
        pytest.param("1", None, constants.FetchPythonOptions.MISSING, False, id="legacy-truthy"),
        pytest.param("0", None, constants.FetchPythonOptions.NEVER, False, id="legacy-falsy"),
        pytest.param(" False ", None, constants.FetchPythonOptions.NEVER, False, id="legacy-whitespace-falsy"),
        pytest.param("n", None, constants.FetchPythonOptions.NEVER, False, id="legacy-falsy-n"),
        pytest.param(None, "always", constants.FetchPythonOptions.ALWAYS, False, id="explicit-always"),
        pytest.param(None, "garbage", constants.FetchPythonOptions.NEVER, True, id="invalid-value"),
    ],
)
def test_compute_fetch_python(
    missing_raw: str | None,
    python_raw: str | None,
    expected_option: constants.FetchPythonOptions,
    expected_invalid: bool,
) -> None:
    option, invalid = constants._compute_fetch_python(missing_raw, python_raw)  # ruff:ignore[private-member-access]  # no public API
    assert option is expected_option
    assert invalid is expected_invalid


@pytest.mark.parametrize(
    ("invalid", "fetch_python_raw", "missing_raw", "expected"),
    [
        pytest.param(True, "garbage", None, "PIPX_FETCH_PYTHON must be unset", id="invalid-value"),
        pytest.param(False, "missing", "1", "Setting both", id="both-env-vars"),
    ],
)
def test_validate_fetch_python_raises(
    monkeypatch: pytest.MonkeyPatch,
    invalid: bool,
    fetch_python_raw: str | None,
    missing_raw: str | None,
    expected: str,
) -> None:
    monkeypatch.setattr(main, "_FETCH_PYTHON_INVALID", invalid)
    monkeypatch.setattr(main, "_FETCH_PYTHON_RAW", fetch_python_raw)
    monkeypatch.setattr(main, "_FETCH_MISSING_PYTHON_RAW", missing_raw)
    with pytest.raises(main.PipxError, match=expected):
        main._validate_fetch_python()  # ruff:ignore[private-member-access]  # no public API


def test_validate_fetch_python_deprecated_env_warning(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(main, "_FETCH_PYTHON_INVALID", False)
    monkeypatch.setattr(main, "_FETCH_PYTHON_RAW", None)
    monkeypatch.setattr(main, "_FETCH_MISSING_PYTHON_RAW", "1")
    main._validate_fetch_python()  # ruff:ignore[private-member-access]  # no public API
    assert "PIPX_FETCH_MISSING_PYTHON is deprecated" in capsys.readouterr().err


def test_validate_fetch_python_passes_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "_FETCH_PYTHON_INVALID", False)
    monkeypatch.setattr(main, "_FETCH_PYTHON_RAW", None)
    monkeypatch.setattr(main, "_FETCH_MISSING_PYTHON_RAW", None)
    main._validate_fetch_python()  # ruff:ignore[private-member-access]  # no public API


@pytest.mark.parametrize(
    ("raw", "expected_days", "expected_invalid"),
    [
        pytest.param(None, None, False, id="unset"),
        pytest.param("  ", None, False, id="blank"),
        pytest.param("7", 7, False, id="days"),
        pytest.param(" 7 ", 7, False, id="whitespace-padded"),
        pytest.param("0", 0, False, id="zero"),
        pytest.param("-1", None, True, id="negative"),
        pytest.param("garbage", None, True, id="not-an-integer"),
    ],
)
def test_compute_cooldown(raw: str | None, expected_days: int | None, expected_invalid: bool) -> None:
    assert constants._compute_cooldown(raw) == (expected_days, expected_invalid)  # ruff:ignore[private-member-access]  # no public API


def test_cli_rejects_invalid_env_cooldown(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(main, "_COOLDOWN_INVALID", True)
    monkeypatch.setattr(main, "_COOLDOWN_RAW", "garbage")

    assert run_pipx_cli(["list"])

    assert "PIPX_COOLDOWN must be unset or a non-negative integer, got 'garbage'." in capsys.readouterr().err


@pytest.mark.usefixtures("exit_early")
def test_deprecated_fetch_missing_python_silent_under_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(ValueError, match="raised in test to exit early"):
        run_pipx_cli(["install", "--fetch-missing-python", "--help"])

    assert "--fetch-missing-python is deprecated" not in capsys.readouterr().err


@pytest.mark.parametrize("windows", [pytest.param(True, id="windows"), pytest.param(False, id="posix")])
@pytest.mark.parametrize(
    ("pip_args", "expected"),
    [
        pytest.param("--no-deps", ["--no-deps"], id="bare"),
        pytest.param("'--no-deps --pre'", ["--no-deps", "--pre"], id="wrapped-value"),
        pytest.param("--find-links '/opt/foo bar'", ["--find-links", "/opt/foo bar"], id="quoted-path"),
        pytest.param('--find-links "/opt/foo bar"', ["--find-links", "/opt/foo bar"], id="double-quoted-path"),
        pytest.param(
            "'--find-links=/opt/foo bar' '--constraint=/opt/c d.txt'",
            ["--find-links=/opt/foo bar", "--constraint=/opt/c d.txt"],
            id="two-quoted-arguments",
        ),
    ],
)
def test_get_pip_args_quoting(mocker: MockerFixture, windows: bool, pip_args: str, expected: list[str]) -> None:
    mocker.patch.object(main, "WINDOWS", windows)

    assert main.get_pip_args({"pip_args": pip_args}) == expected


def test_get_pip_args_keeps_windows_path_separator(mocker: MockerFixture) -> None:
    mocker.patch.object(main, "WINDOWS", True)

    assert main.get_pip_args({"pip_args": r"'--no-index --find-links=D:\TEST\DIR'"}) == [
        "--no-index",
        r"--find-links=D:\TEST\DIR",
    ]


def test_get_pip_args_honours_posix_escape(mocker: MockerFixture) -> None:
    mocker.patch.object(main, "WINDOWS", False)

    assert main.get_pip_args({"pip_args": "--find-links /opt/foo\\ bar"}) == ["--find-links", "/opt/foo bar"]


def test_get_pip_args_rejects_unclosed_quote() -> None:
    with pytest.raises(PipxError, match="invalid pip arguments: No closing quotation"):
        main.get_pip_args({"pip_args": "--find-links '/opt/foo bar"})


def test_get_pip_args_forwards_index_url() -> None:
    assert main.get_pip_args({"index_url": "https://example.com/simple"}) == [
        "--index-url",
        "https://example.com/simple",
    ]


@pytest.mark.parametrize("index_url", [pytest.param("", id="empty"), pytest.param("  ", id="whitespace")])
def test_get_pip_args_rejects_empty_index_url(index_url: str) -> None:
    with pytest.raises(PipxError, match="--index-url is empty"):
        main.get_pip_args({"index_url": index_url})


@pytest.mark.parametrize(
    ("pip_args", "option"),
    [
        pytest.param("--index-url=", "--index-url", id="index-url-attached"),
        pytest.param("--index-url ''", "--index-url", id="index-url-separate"),
        pytest.param("-i=", "-i", id="short-attached"),
        pytest.param("-i '  '", "-i", id="short-whitespace"),
        pytest.param("--default-index=", "--default-index", id="default-index"),
        pytest.param("--index=", "--index", id="index"),
        pytest.param("--pre --extra-index-url=", "--extra-index-url", id="extra-index-url"),
    ],
)
def test_get_pip_args_rejects_empty_index_in_pip_args(pip_args: str, option: str) -> None:
    with pytest.raises(PipxError, match=f"^{option} is empty"):
        main.get_pip_args({"pip_args": pip_args})


@pytest.mark.parametrize(
    "pip_args",
    [
        pytest.param("--index-url", id="missing-value"),
        pytest.param("-ihttps://example.com/simple", id="short-joined"),
        pytest.param("--index-url https://example.com/simple", id="separate"),
    ],
)
def test_get_pip_args_keeps_non_empty_index_in_pip_args(pip_args: str) -> None:
    assert main.get_pip_args({"pip_args": pip_args}) == pip_args.split()


_LOCAL: Final = pytest.param("OVERRIDE_PIPX_HOME", [], id="local")
_GLOBAL: Final = pytest.param("OVERRIDE_PIPX_GLOBAL_HOME", ["--global"], id="global")


@_SKIP_WITHOUT_PERMISSIONS
@pytest.mark.parametrize("command", [pytest.param("environment", id="environment"), pytest.param("list", id="list")])
@pytest.mark.parametrize(("locked_home", "flags"), [_LOCAL, _GLOBAL], indirect=["locked_home"])
def test_read_only_command_runs_without_writable_home(locked_home: Path, flags: list[str], command: str) -> None:
    del locked_home
    assert run_pipx_cli([command, *flags]) == 0


@_SKIP_WITHOUT_PERMISSIONS
@pytest.mark.parametrize(
    ("locked_home", "flags", "fix"),
    [
        pytest.param(
            *_LOCAL.values, "point PIPX_HOME, PIPX_BIN_DIR and PIPX_MAN_DIR at writable directories", id="local"
        ),
        pytest.param(
            *_GLOBAL.values,
            "run pipx with sudo, or point PIPX_GLOBAL_HOME, PIPX_GLOBAL_BIN_DIR and PIPX_GLOBAL_MAN_DIR at writable"
            " directories",
            id="global",
        ),
    ],
    indirect=["locked_home"],
)
def test_unwritable_home_reports_error(
    locked_home: Path, capsys: pytest.CaptureFixture[str], flags: list[str], fix: str
) -> None:
    exit_code = run_pipx_cli(["install", *flags, "pycowsay"])
    assert (exit_code, capsys.readouterr().err) == (1, f"Cannot create {locked_home}: permission denied; {fix}.\n")


@pytest.fixture
def locked_home(
    request: pytest.FixtureRequest,
    pipx_temp_env: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
) -> Iterator[Path]:
    del pipx_temp_env
    # the log file falls back to the user log directory, keep it inside the test
    mocker.patch("platformdirs.user_log_path", autospec=True, return_value=tmp_path / "logs")
    (locked := tmp_path / "locked").mkdir(mode=0o500)
    monkeypatch.setattr(paths, request.param, home := locked / "pipx")
    paths.ctx.make_local()
    yield home
    locked.chmod(0o700)


@pytest.fixture
def json_install_verbose(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # requested for its isolated pipx home
    capsys: pytest.CaptureFixture[str],
) -> pytest.CaptureFixture[str]:
    assert not run_pipx_cli(["install", "--output", "json", "--verbose", PKG["pycowsay"]["spec"]])
    return capsys


def test_json_output_keeps_streamed_progress_off_stdout(
    json_install_verbose: pytest.CaptureFixture[str],
) -> None:
    assert json.loads(json_install_verbose.readouterr().out)["status"] == "success"


def test_json_output_streams_progress_to_stderr(json_install_verbose: pytest.CaptureFixture[str]) -> None:
    assert "Collecting pycowsay" in json_install_verbose.readouterr().err


class _Envelope(TypedDict):
    command: list[str]
    status: str
    exit_code: int
    errors: list[dict[str, str | None]]


def _envelope_failure(stdout: str) -> tuple[list[str], str, int, list[str | None]]:
    document: Final[_Envelope] = json.loads(stdout)
    return (
        document["command"],
        document["status"],
        document["exit_code"],
        [error["code"] for error in document["errors"]],
    )


@pytest.mark.parametrize(
    "patches",
    [
        pytest.param({"_COOLDOWN_INVALID": True, "_COOLDOWN_RAW": "abc"}, id="cooldown"),
        pytest.param({"_MAX_LOGS_INVALID": True, "_MAX_LOGS_RAW": "x"}, id="max-logs"),
        pytest.param({"_FETCH_PYTHON_INVALID": True}, id="fetch-python"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_json_output_reports_invalid_environment_variable_in_envelope(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    patches: dict[str, bool | str],
) -> None:
    for name, value in patches.items():
        monkeypatch.setattr(main, name, value)

    assert run_pipx_cli(["cache", "dir", "--output", "json"]) == 1

    assert _envelope_failure(capsys.readouterr().out) == (["cache", "dir"], "error", 1, ["pipx_error"])


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["install", "--python", "/nonexistent/python3", "pycowsay"], id="unresolvable-python"),
        pytest.param(["uninstall", "some/path"], id="package-path"),
        pytest.param(["uninstall", "https://example.com/pycowsay"], id="package-url"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_json_output_reports_rejected_arguments_in_envelope(
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
) -> None:
    assert run_pipx_cli([*argv, "--output", "json"]) == 1

    assert _envelope_failure(capsys.readouterr().out) == ([argv[0]], "error", 1, ["pipx_error"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_json_output_reports_missing_uv_in_envelope(capsys: pytest.CaptureFixture[str], mocker: MockerFixture) -> None:
    mocker.patch("pipx.backends.find_uv_binary", return_value=(None, "missing"))
    mocker.patch("pipx.backends.uv.find_uv_binary", return_value=(None, "missing"))

    assert run_pipx_cli(["install", "--backend", "uv", "--output", "json", "pycowsay"]) == 1

    assert _envelope_failure(capsys.readouterr().out) == (["install"], "error", 1, ["pipx_error"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_cli_skips_uv_detection_without_backend_choice(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    monkeypatch.delenv("PIPX_DEFAULT_BACKEND")
    find_uv_binary: Final[MagicMock] = mocker.patch(
        "pipx.backends.find_uv_binary", autospec=True, return_value=(Path("/usr/local/bin/uv"), "path")
    )

    assert not run_pipx_cli(["list"])

    find_uv_binary.assert_not_called()


@pytest.mark.usefixtures("pipx_temp_env")
def test_cli_without_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli([]) == 1

    assert capsys.readouterr().out.startswith("usage: pipx")


@pytest.mark.usefixtures("pipx_temp_env")
def test_package_is_path_hides_url_credentials(capsys: pytest.CaptureFixture[str]) -> None:
    spec: Final[str] = "tool @ https://u:s3cr3ttok@host/tool.whl"

    assert run_pipx_cli(["upgrade", spec])

    assert f"'{redact_url_credentials(spec)}' looks like a path" in " ".join(capsys.readouterr().err.split())


@pytest.mark.usefixtures("pipx_temp_env")
def test_log_masks_command_line_password_with_space() -> None:
    run_pipx_cli(["upgrade", "--index-url", "https://alice:correct horse@host/simple", "nosuchpackage"])

    log: Final[str] = current_log_file().read_text(encoding="utf-8")
    assert "upgrade --index-url https://****:****@host/simple nosuchpackage" in log


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env", "permissive_umask")
def test_log_dir_is_created_owner_only() -> None:
    assert not run_pipx_cli(["list"])

    assert stat.S_IMODE(paths.ctx.logs.stat().st_mode) == 0o700


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env", "permissive_umask")
def test_log_dir_left_world_readable_is_tightened() -> None:
    paths.ctx.logs.mkdir(mode=0o755, parents=True)

    assert not run_pipx_cli(["list"])

    assert stat.S_IMODE(paths.ctx.logs.stat().st_mode) == 0o700


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env", "permissive_umask")
def test_log_file_is_owner_only() -> None:
    assert not run_pipx_cli(["list"])

    assert stat.S_IMODE(current_log_file().stat().st_mode) == 0o600


@pytest.mark.usefixtures("pipx_temp_env")
def test_log_dir_that_cannot_change_mode_still_logs(mocker: MockerFixture) -> None:
    mocker.patch.object(Path, "chmod", autospec=True, side_effect=PermissionError)

    assert not run_pipx_cli(["list"])

    assert current_log_file().parent == paths.ctx.logs


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["install", "--preinstall=-rrequirements.txt", "pycowsay"], id="install-preinstall"),
        pytest.param(["run", "--with=--find-links=elsewhere", "script.py"], id="run-with"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_option_shaped_package_is_refused(capsys: pytest.CaptureFixture[str], argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        run_pipx_cli(argv)

    assert "is an installer option, not a package; pass it with --pip-args" in capsys.readouterr().err
