from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Final, cast
from unittest import mock

import pytest
from docutils.core import publish_string

from helpers import run_pipx_cli
from pipx import constants, main

_ROOT: Final = Path(__file__).parents[1]
_MANPAGE_RST: Final = _ROOT / "docs" / "man" / "pipx.1.rst"


def test_help_text(capsys: pytest.CaptureFixture[str]) -> None:
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        assert not run_pipx_cli(["--help"])
    captured = capsys.readouterr()
    assert "usage: pipx" in captured.out


def test_help_command_text(capsys: pytest.CaptureFixture[str]) -> None:
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        assert not run_pipx_cli(["help"])
    captured = capsys.readouterr()
    mock_exit.assert_called_with(0)
    assert "usage: pipx" in captured.out


def test_help_command_for_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        assert not run_pipx_cli(["help", "install"])
    captured = capsys.readouterr()
    mock_exit.assert_called_with(0)
    assert "usage: pipx install" in captured.out


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        assert not run_pipx_cli(["--version"])
    captured = capsys.readouterr()
    mock_exit.assert_called_with(0)
    assert main.__version__ in captured.out.strip()


@pytest.mark.parametrize(
    ("argv", "executable", "expected"),
    [
        ("/usr/bin/pipx", "", "pipx"),
        ("__main__.py", "/usr/bin/python", "/usr/bin/python -m pipx"),
    ],
)
def test_prog_name(monkeypatch: pytest.MonkeyPatch, argv: str, executable: str, expected: str) -> None:
    monkeypatch.setattr("pipx.main.sys.argv", [argv])
    monkeypatch.setattr("pipx.main.sys.executable", executable)
    assert main.prog_name() == expected


def test_limit_verbosity() -> None:
    assert not run_pipx_cli(["list", "-qqq"])
    assert not run_pipx_cli(["list", "-vvvv"])


def test_all_subcommands_have_func_registered() -> None:
    parser, _ = main.get_command_parser()
    subparsers_type = argparse._SubParsersAction  # ruff:ignore[private-member-access]  # argparse has no public subparser API
    top_actions = parser._actions  # ruff:ignore[private-member-access]  # argparse has no public subparser API
    subparsers_action = next(a for a in top_actions if isinstance(a, subparsers_type))
    choices = cast("dict[str, argparse.ArgumentParser]", subparsers_action.choices)
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
    generated = tmp_path / "pipx.1.rst"
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
def test_manpage_renders(manpage_troff: bytes, tmp_path: Path) -> None:
    manpage = tmp_path / "pipx.1"
    manpage.write_bytes(manpage_troff)
    result = subprocess.run(
        ["man", str(manpage)],  # ruff:ignore[start-process-with-partial-path]  # man resolves via PATH by design in this render smoke test
        capture_output=True,
        text=True,
        env=os.environ | {"COLUMNS": "200", "MANPAGER": "cat", "PAGER": "cat"},
        check=False,
        timeout=5,
    )
    rendered = re.sub(r".\x08", "", result.stdout)
    assert (result.returncode, "pipx" in rendered.lower(), "SYNOPSIS" in rendered) == (0, True, True)


@pytest.fixture
def manpage_troff() -> bytes:
    source = "\n".join(
        line for line in _MANPAGE_RST.read_text(encoding="utf-8").splitlines() if line.strip() != ":orphan:"
    )
    return publish_string(source, writer="manpage", settings_overrides={"report_level": 5})


@pytest.mark.parametrize(
    "argv",
    [
        ["inject", "ansible-core", "--force", "ansible"],
        ["inject", "ansible-core", "ansible", "--force"],
    ],
)
def test_inject_accepts_force_before_or_after_dependency(argv: list[str]) -> None:
    parser, _ = main.get_command_parser()

    args = main.parse_pipx_args(parser, argv)

    assert args.package == "ansible-core"
    assert args.dependencies == ["ansible"]
    assert args.force is True


def test_package_is_path_ignores_existing_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression for #1778: a directory in CWD with the same name as a
    # package should not be treated as a path.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "commit-check").mkdir()
    # Should not raise even though a directory of that name exists in CWD.
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


def test_deprecated_fetch_missing_python_silent_under_help(capsys: pytest.CaptureFixture[str]) -> None:
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        run_pipx_cli(["install", "--fetch-missing-python", "--help"])
    assert "--fetch-missing-python is deprecated" not in capsys.readouterr().err
