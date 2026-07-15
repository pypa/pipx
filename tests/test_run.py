from __future__ import annotations

import datetime
import importlib
import logging
import os
import shutil
import subprocess
import sys
import textwrap
from typing import TYPE_CHECKING, Final
from unittest import mock

import pytest
from filelock import AcquireReturnProxy, FileLock, Timeout

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

    from pytest_mock import MockerFixture

import pipx.main
from helpers import run_pipx_cli
from package_info import PKG
from pipx import paths, shared_libs
from pipx.pipx_metadata_file import PipxMetadata
from pipx.util import PipxError


@pytest.mark.usefixtures("pipx_temp_env")
def test_help_text(capsys: pytest.CaptureFixture[str]) -> None:
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        run_pipx_cli(["run", "--help"])
    captured = capsys.readouterr()
    assert "Download the latest version of a package" in captured.out


def execvpe_mock(_cmd_path: str, cmd_args: Sequence[str], env: Mapping[str, str]) -> None:
    return_code = subprocess.run(
        [str(x) for x in cmd_args],
        env=env,
        capture_output=False,
        encoding="utf-8",
        text=True,
        check=False,
    ).returncode
    sys.exit(return_code)


def run_pipx_cli_exit(pipx_cmd_list: list[str], assert_exit: int | None = None) -> None:
    with pytest.raises(SystemExit) as sys_exit:
        run_pipx_cli(pipx_cmd_list)
    if assert_exit is not None:
        assert sys_exit.type is SystemExit
        assert sys_exit.value.code == assert_exit


@pytest.mark.parametrize("package_name", ["pycowsay", "pycowsay==0.0.0.2", "pycowsay>=0.0.0.2"])
@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_simple_run(capsys: pytest.CaptureFixture[str], package_name: str) -> None:
    run_pipx_cli_exit(["run", package_name, "--help"])
    captured = capsys.readouterr()
    assert "Download the latest version of a package" not in captured.out


@pytest.mark.parametrize("backend", ["pip", "uv"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_run_normalizes_inferred_package_name(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    backend: str,
) -> None:
    mocker.patch("os.execvpe", new=execvpe_mock)
    monkeypatch.setenv("PATH", f"{os.environ['PATH']}{os.pathsep}{os.defpath}")

    run_pipx_cli_exit(["run", "--backend", backend, "bLaCk", "--version"], assert_exit=0)


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_preserves_explicit_app_name(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["run", "--spec", "black", "bLaCk.app"]) == 1
    assert "'bLaCk.app' executable script not found in package 'black'." in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_cache(caplog: pytest.LogCaptureFixture) -> None:
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    caplog.set_level(logging.DEBUG)
    run_pipx_cli_exit(["run", "--verbose", "pycowsay", "cowsay", "args"], assert_exit=0)
    assert "Reusing cached venv" in caplog.text

    run_pipx_cli_exit(["run", "--no-cache", "pycowsay", "cowsay", "args"])
    assert "Removing cached venv" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_refresh_rebuilds_cached_environment() -> None:
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    venv_dir: Final[Path] = next(path for path in paths.ctx.venv_cache.iterdir() if path.is_dir())
    marker: Final[Path] = venv_dir / "marker"
    marker.touch()

    run_pipx_cli_exit(["run", "--refresh", "pycowsay", "cowsay", "args"])

    assert not marker.exists()


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_refresh_retains_replacement() -> None:
    run_pipx_cli_exit(["run", "--refresh", "pycowsay", "cowsay", "args"])
    venv_dir: Final[Path] = next(path for path in paths.ctx.venv_cache.iterdir() if path.is_dir())
    marker: Final[Path] = venv_dir / "marker"
    marker.touch()

    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])

    assert marker.exists()


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_skips_a_cache_entry_held_by_another_run(mocker: MockerFixture) -> None:
    paths.ctx.venv_cache.mkdir(parents=True, exist_ok=True)
    held: Final[Path] = paths.ctx.venv_cache / "held-by-another-run"
    held.mkdir()
    (held / "pipx_expired_venv").touch()

    real_acquire: Final = FileLock.acquire

    def acquire(
        self: FileLock,
        timeout: float | None = None,
        poll_interval: float | None = None,
        *,
        poll_intervall: float | None = None,
        blocking: bool | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> AcquireReturnProxy:
        if timeout == 0:
            raise Timeout(str(self.lock_file))
        return real_acquire(
            self,
            timeout,
            poll_interval,
            poll_intervall=poll_intervall,
            blocking=blocking,
            cancel_check=cancel_check,
        )

    mocker.patch.object(FileLock, "acquire", acquire)

    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "hi"])

    assert held.is_dir()


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_with_isolates_cache_by_dependency(mocker: MockerFixture) -> None:
    inject: Final = mocker.patch.object(importlib.import_module("pipx.commands.run"), "inject_dep")

    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "hi"])
    plain_dirs: Final[set[Path]] = {path for path in paths.ctx.venv_cache.iterdir() if path.is_dir()}

    run_pipx_cli_exit(["run", "--with", "packaging", "pycowsay", "cowsay", "hi"])
    with_dirs: Final[set[Path]] = {path for path in paths.ctx.venv_cache.iterdir() if path.is_dir()} - plain_dirs

    assert (len(with_dirs), inject.call_count, inject.call_args.kwargs["package_spec"]) == (1, 1, "packaging")


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_resolves_interpreter_for_requires_python(tmp_path: Path, mocker: MockerFixture) -> None:
    resolve: Final = mocker.patch.object(
        importlib.import_module("pipx.commands.run"), "interpreter_for", return_value=sys.executable
    )
    script: Final[Path] = tmp_path / "script.py"
    script.write_text('# /// script\n# requires-python = ">=3.11"\n# ///\nprint("hi")\n', encoding="utf-8")

    run_pipx_cli_exit(["run", "--backend", "pip", str(script)], assert_exit=0)

    assert str(resolve.call_args.args[0]) == ">=3.11"


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_rejects_python_failing_requires_python(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    script: Final[Path] = tmp_path / "script.py"
    script.write_text('# /// script\n# requires-python = ">=3.99"\n# ///\nprint("hi")\n', encoding="utf-8")

    assert run_pipx_cli(["run", "--backend", "pip", "--python", sys.executable, str(script)]) == 1
    assert ">=3.99" in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_reports_invalid_inline_metadata(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    script: Final[Path] = tmp_path / "script.py"
    script.write_text("# /// script\n# dependencies = [\n# ///\nprint('hi')\n", encoding="utf-8")

    assert run_pipx_cli(["run", "--backend", "pip", str(script)]) == 1
    assert "Invalid inline script metadata" in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_cache_options_are_mutually_exclusive(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit, match="2"):
        run_pipx_cli(["run", "--no-cache", "--refresh", "pycowsay"])
    assert "not allowed with argument" in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_does_not_mark_cache_as_installation(mocker: MockerFixture) -> None:
    mocker.patch("os.execvpe", new=execvpe_mock)

    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])

    venv_dir = next(path for path in paths.ctx.venv_cache.iterdir() if path.is_dir())
    assert PipxMetadata(venv_dir).environment is None


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_cooldown_separates_cache(
    root: Path,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mocker.patch("os.execvpe", autospec=True, side_effect=execvpe_mock)
    find_links: Final[Path] = (
        root / ".pipx_tests" / "package_cache" / f"{sys.version_info.major}.{sys.version_info.minor}"
    )
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={find_links}"

    run_pipx_cli_exit(
        ["run", "--backend", "pip", "--cooldown", "7", pip_args, PKG["pycowsay"]["spec"], "hello"],
        assert_exit=0,
    )
    cached_venvs: Final[set[Path]] = {path for path in paths.ctx.venv_cache.iterdir() if path.is_dir()}
    caplog.clear()

    run_pipx_cli_exit(
        ["run", "--backend", "pip", "--cooldown", "0", pip_args, PKG["pycowsay"]["spec"], "hello"],
        assert_exit=0,
    )

    assert (
        len({path for path in paths.ctx.venv_cache.iterdir() if path.is_dir()}),
        "--uploaded-prior-to" in caplog.text,
    ) == (len(cached_venvs) + 1, False)


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_no_path_check(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    which = mock.Mock(return_value="/fake/bin/pycowsay")
    for module_name in ("pipx.commands.run", "pipx.commands.run_uv"):
        monkeypatch.setattr(importlib.import_module(module_name), "which", which)

    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    which.assert_called_once_with("pycowsay")
    assert "is already on your PATH" in caplog.text

    caplog.clear()
    run_pipx_cli_exit(["run", "--no-path-check", "pycowsay", "cowsay", "args"])
    which.assert_called_once_with("pycowsay")
    assert "is already on your PATH" not in caplog.text


@pytest.mark.usefixtures("pipx_ultra_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_cachedir_tag(caplog: pytest.LogCaptureFixture) -> None:
    tag_path = paths.ctx.venv_cache / "CACHEDIR.TAG"
    assert not tag_path.exists()

    # Run pipx to create tag
    caplog.set_level(logging.DEBUG)
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    assert "Adding CACHEDIR.TAG to cache directory" in caplog.text
    assert tag_path.exists()
    caplog.clear()

    # Run pipx again to verify the tag file is not recreated
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    assert "Adding CACHEDIR.TAG to cache directory" not in caplog.text
    assert tag_path.exists()

    # Verify the tag file starts with the required signature.
    with tag_path.open("r") as tag_file:
        assert tag_file.read().startswith("Signature: 8a477f597d28d172789f06886806bc55")


@pytest.mark.usefixtures("pipx_ultra_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_cache_sweep_ignores_tag(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    tag_path = paths.ctx.venv_cache / "CACHEDIR.TAG"
    expired_venv = paths.ctx.venv_cache / "expired"
    expired_venv.mkdir()

    class FutureDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz: datetime.tzinfo | None = None) -> FutureDateTime:
            return cls.fromtimestamp((super().now(tz) + datetime.timedelta(days=15)).timestamp(), tz)

    monkeypatch.setattr(datetime, "datetime", FutureDateTime)
    caplog.set_level(logging.INFO)
    caplog.clear()

    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])

    assert not expired_venv.exists()
    assert tag_path.exists()
    assert f"Removing expired venv {tag_path}" not in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_script_from_internet() -> None:
    run_pipx_cli_exit(
        [
            "run",
            (
                "https://gist.githubusercontent.com/cs01/"
                "fa721a17a326e551ede048c5088f9e0f/raw/"
                "6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py"
            ),
        ],
        assert_exit=0,
    )


@pytest.mark.parametrize(
    ("input_run_args", "expected_app_with_args"),
    [
        (["--", "pycowsay", "--", "hello"], ["pycowsay", "--", "hello"]),
        (["--", "pycowsay", "--", "--", "hello"], ["pycowsay", "--", "--", "hello"]),
        (["--", "pycowsay", "hello", "--"], ["pycowsay", "hello", "--"]),
        (["--", "pycowsay", "hello", "--", "--"], ["pycowsay", "hello", "--", "--"]),
        (["--", "pycowsay", "--"], ["pycowsay", "--"]),
        (["--", "pycowsay", "--", "--"], ["pycowsay", "--", "--"]),
        (["pycowsay", "--", "hello"], ["pycowsay", "--", "hello"]),
        (["pycowsay", "--", "--", "hello"], ["pycowsay", "--", "--", "hello"]),
        (["pycowsay", "hello", "--"], ["pycowsay", "hello", "--"]),
        (["pycowsay", "hello", "--", "--"], ["pycowsay", "hello", "--", "--"]),
        (["pycowsay", "--"], ["pycowsay", "--"]),
        (["pycowsay", "--", "--"], ["pycowsay", "--", "--"]),
        (["--", "--", "pycowsay", "--"], ["--", "pycowsay", "--"]),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_appargs_doubledash(
    monkeypatch: pytest.MonkeyPatch, input_run_args: list[str], expected_app_with_args: list[str]
) -> None:
    parser, _ = pipx.main.get_command_parser()
    monkeypatch.setattr(sys, "argv", ["pipx", "run", *input_run_args])
    parsed_pipx_args = parser.parse_args()
    pipx.main.check_args(parsed_pipx_args)
    assert parsed_pipx_args.app_with_args == expected_app_with_args


def test_run_ensure_null_pythonpath() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = "test"
    assert (
        "None"
        in subprocess.run(
            [
                sys.executable,
                "-m",
                "pipx",
                "run",
                "ipython",
                "-c",
                "import os; print(os.environ.get('PYTHONPATH'))",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )


# packages listed roughly in order of increasing test duration
@pytest.mark.parametrize(
    ("package", "package_or_url", "app_appargs", "skip_win"),
    [
        ("pycowsay", "pycowsay", ["pycowsay", "hello"], False),
        ("shell-functools", PKG["shell-functools"]["spec"], ["filter", "--help"], True),
        ("black", PKG["black"]["spec"], ["black", "--help"], False),
        ("pylint", PKG["pylint"]["spec"], ["pylint", "--help"], False),
        ("kaggle", PKG["kaggle"]["spec"], ["kaggle", "--help"], False),
        ("ipython", PKG["ipython"]["spec"], ["ipython", "--version"], False),
        ("awscli", PKG["awscli"]["spec"], ["aws", "--help"], True),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_package_determination(
    caplog: pytest.LogCaptureFixture,
    package: str,
    package_or_url: str,
    app_appargs: list[str],
    skip_win: bool,
) -> None:
    if sys.platform.startswith("win") and skip_win:
        # Skip packages with 'scripts' in setup.py that don't work on Windows
        pytest.skip()

    caplog.set_level(logging.INFO)

    run_pipx_cli_exit(["run", "--verbose", "--spec", package_or_url, "--", *app_appargs])

    assert "Cannot determine package name" not in caplog.text
    assert f"Determined package name: {package}" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_without_requirements(tmp_path: Path) -> None:
    script = tmp_path / "test.py"
    out = tmp_path / "output.txt"
    test_str = "Hello, world!"
    script.write_text(
        textwrap.dedent(
            f"""
                from pathlib import Path
                Path({str(out)!r}).write_text({test_str!r})
            """
        ).strip()
    )
    run_pipx_cli_exit(["run", script.as_uri()])
    assert out.read_text() == test_str


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_passes_python_args_to_script(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    mocker.patch("os.execvpe", new=execvpe_mock)
    output: Final[Path] = tmp_path / "flags.txt"
    script: Final[Path] = tmp_path / "flags.py"
    script.write_text(
        f"import sys\nfrom pathlib import Path\nPath({str(output)!r}).write_text(str(sys.flags.bytes_warning))",
        encoding="utf-8",
    )

    run_pipx_cli_exit(["run", "--python-args=-bb", str(script)], assert_exit=0)

    assert output.read_text(encoding="utf-8") == "2"


def test_run_rejects_invalid_python_args(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit, match="2"):
        run_pipx_cli(["run", '--python-args="', "demo"])

    assert "invalid Python arguments: No closing quotation" in capsys.readouterr().err


@pytest.mark.parametrize("backend", ["pip", "uv"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_run_passes_python_args_to_app(
    mocker: MockerFixture,
    tmp_path: Path,
    backend: str,
) -> None:
    mocker.patch("os.execvpe", new=execvpe_mock)
    project: Final[Path] = tmp_path / "flags-app"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        """\
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "flags-app"
version = "1"

[project.scripts]
flags-app = "flags_app:main"

[tool.setuptools]
py-modules = ["flags_app"]
""",
        encoding="utf-8",
    )
    output: Final[Path] = tmp_path / "flags.txt"
    (project / "flags_app.py").write_text(
        (
            "import sys\nfrom pathlib import Path\n\n"
            "def main() -> None:\n    Path(sys.argv[1]).write_text(str(sys.flags.bytes_warning))"
        ),
        encoding="utf-8",
    )

    run_pipx_cli_exit(
        [
            "run",
            "--backend",
            backend,
            "--python-args=-X dev -bb",
            "--spec",
            str(project),
            "flags-app",
            str(output),
        ],
        assert_exit=0,
    )

    assert output.read_text(encoding="utf-8") == "2"


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_rejects_python_args_for_pypackages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app: Final[Path] = (
        tmp_path / "__pypackages__" / f"{sys.version_info.major}.{sys.version_info.minor}" / "lib" / "bin" / "demo"
    )
    app.parent.mkdir(parents=True)
    app.touch()
    monkeypatch.chdir(tmp_path)

    assert run_pipx_cli(["run", "--python-args=-b", "demo"]) == 1

    assert capsys.readouterr().err == "--python-args cannot run applications from __pypackages__.\n"


@pytest.mark.parametrize(
    ("encoding", "script_text"),
    [
        pytest.param("cp850", 'print("äöü")', id="cp850-text"),
        pytest.param(
            "cp437",
            'import sys; print("┏━┓" if sys.stdout.encoding == "utf-8" else "+-+")',
            id="cp437-terminal-fallback",
        ),
    ],
)
def test_run_preserves_console_encoding(tmp_path: Path, encoding: str, script_text: str) -> None:
    script = tmp_path / "console_output.py"
    script.write_text(script_text, encoding="utf-8")
    env = os.environ | {
        "PIPX_DEFAULT_BACKEND": "pip",
        "PIPX_HOME": str(tmp_path / "pipx"),
        "PYTHONIOENCODING": encoding,
    }

    direct_output = subprocess.run(
        [sys.executable, script],
        env=env,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout
    pipx_output = subprocess.run(
        [sys.executable, "-m", "pipx", "run", script],
        env=env,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout

    assert pipx_output == direct_output


@pytest.mark.parametrize(
    ("script_text", "expected_output"),
    [
        pytest.param(
            """
            # /// script
            # dependencies = []
            # ///
            from pathlib import Path
            Path({out!r}).write_text("explicit-empty")
            """,
            "explicit-empty",
            id="explicit-empty-dependencies",
        ),
        pytest.param(
            """
            # /// script
            # ///
            from pathlib import Path
            Path({out!r}).write_text("implicit-empty")
            """,
            "implicit-empty",
            id="implicit-empty-dependencies",
        ),
        pytest.param(
            """
            # /// script
            # dependencies = ["requests==2.31.0"]
            # ///

            # Check requests can be imported
            import requests
            # Check dependencies of requests can be imported
            import certifi
            # Check the installed version
            from pathlib import Path
            Path({out!r}).write_text(requests.__version__)
            """,
            "2.31.0",
            id="non-empty-dependencies",
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_with_requirements(script_text: str, expected_output: str, tmp_path: Path) -> None:
    script = tmp_path / "test.py"
    out = tmp_path / "output.txt"
    script.write_text(
        textwrap.dedent(script_text.format(out=str(out))).strip(),
        encoding="utf-8",
    )
    run_pipx_cli_exit(["run", script.as_uri()])
    assert out.read_text() == expected_output


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_with_requirements_and_cli_with_pip_backend(tmp_path: Path) -> None:
    script = tmp_path / "test.py"
    out = tmp_path / "output.txt"
    script.write_text(
        textwrap.dedent(
            f"""
            # /// script
            # dependencies = ["requests==2.31.0"]
            # ///

            import black
            import requests
            from pathlib import Path

            Path({str(out)!r}).write_text(f"requests={{requests.__version__}}, package={{black.__name__}}")
            """
        ).strip(),
        encoding="utf-8",
    )

    run_pipx_cli_exit(
        ["run", "--backend", "pip", "--with", PKG["black"]["spec"], script.as_uri()],
        assert_exit=0,
    )
    assert out.read_text() == "requests=2.31.0, package=black"

    out.unlink()
    run_pipx_cli_exit(["run", "--backend", "pip", script.as_uri()], assert_exit=1)
    assert not out.exists()


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_script_cooldown(
    root: Path,
    tmp_path: Path,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mocker.patch("os.execvpe", autospec=True, side_effect=execvpe_mock)
    output: Final[Path] = tmp_path / "output.txt"
    script: Final[Path] = tmp_path / "test.py"
    script.write_text(
        textwrap.dedent(
            f"""
            # /// script
            # dependencies = ["pycowsay==0.0.0.2"]
            # ///

            from pathlib import Path
            Path({str(output)!r}).write_text("done")
            """
        ).strip(),
        encoding="utf-8",
    )
    find_links: Final[Path] = (
        root / ".pipx_tests" / "package_cache" / f"{sys.version_info.major}.{sys.version_info.minor}"
    )

    run_pipx_cli_exit(
        [
            "run",
            "--backend",
            "pip",
            "--cooldown",
            "7",
            f"--pip-args=--no-index --find-links={find_links}",
            script.as_uri(),
        ],
        assert_exit=0,
    )

    assert (output.read_text(encoding="utf-8"), "--uploaded-prior-to P7D" in caplog.text) == ("done", True)


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_with_requirements_old(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    script = tmp_path / "test.py"
    script.write_text(
        textwrap.dedent(
            """
                # /// pyproject
                # run.requirements = ["requests==2.31.0"]
                # ///
                import requests
            """
        ).strip(),
        encoding="utf-8",
    )
    assert run_pipx_cli(["run", script.as_uri()]) == 1
    assert "Use `# /// script`" in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_correct_traceback(capfd: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    script = tmp_path / "test.py"
    script.write_text(
        textwrap.dedent(
            """
                raise RuntimeError("Should fail")
            """
        ).strip()
    )

    with pytest.raises(SystemExit):
        run_pipx_cli(["run", str(script)])

    captured = capfd.readouterr()
    assert "test.py" in captured.err


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_with_args(tmp_path: Path) -> None:
    script = tmp_path / "test.py"
    out = tmp_path / "output.txt"
    script.write_text(
        textwrap.dedent(
            f"""
                import sys
                from pathlib import Path
                Path({str(out)!r}).write_text(str(int(sys.argv[1]) + 1))
            """
        ).strip()
    )
    run_pipx_cli_exit(["run", script.as_uri(), "1"])
    assert out.read_text() == "2"


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_with_requirements_and_args(tmp_path: Path) -> None:
    script = tmp_path / "test.py"
    out = tmp_path / "output.txt"
    script.write_text(
        textwrap.dedent(
            f"""
                # /// script
                # dependencies = ["packaging"]
                # ///
                import packaging
                import sys
                from pathlib import Path
                Path({str(out)!r}).write_text(str(int(sys.argv[1]) + 1))
            """
        ).strip()
    )
    run_pipx_cli_exit(["run", script.as_uri(), "1"])
    assert out.read_text() == "2"


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_with_failing_requirements(capfd: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    script = tmp_path / "test.py"
    script.write_text(
        textwrap.dedent(
            """
                # /// script
                # dependencies = ["will_fail @ git+https://0.0.0.0/will_fail.git"]
                # ///
                import will_fail
            """
        ).strip()
    )

    # Attempt first invocation of `pipx run`.
    # This should fail as the `will_fail` package will not be able to be installed.
    return_code = run_pipx_cli(["run", str(script)])
    captured = capfd.readouterr()

    assert return_code != 0
    assert "Error installing will_fail @ git+https://0.0.0.0/will_fail.git." in captured.err

    # Attempt second invocation of `pipx run`.
    # If above failure was detected and the temporary venv marked for deletion,
    # then this should fail in the same manner.
    # If the above failure was not detected, then a ModuleNotFoundError will be raised.
    return_code = run_pipx_cli(["run", str(script)])
    captured = capfd.readouterr()

    assert return_code != 0
    assert "ModuleNotFoundError: No module named 'will_fail'" not in captured.err
    assert "Error installing will_fail @ git+https://0.0.0.0/will_fail.git." in captured.err


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_pip_args_forwarded_to_shared_libs(
    capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    # strategy:
    # 1. start from an empty env to ensure the next command would trigger a shared lib update
    assert shared_libs.shared_libs.needs_upgrade
    # 2. install any package with --no-index
    # and check that the shared library update phase fails
    return_code = run_pipx_cli(["run", "--verbose", "--pip-args=--no-index", "pycowsay", "hello"])
    assert "Upgrading shared libraries in" in caplog.text

    captured = capsys.readouterr()
    assert return_code != 0
    assert "ERROR: Could not find a version that satisfies the requirement pip" in captured.err
    assert "Failed to upgrade shared libraries" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_with_invalid_requirement(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    script = tmp_path / "test.py"
    script.write_text(
        textwrap.dedent(
            """
                # /// script
                # dependencies = ["this is an invalid requirement"]
                # ///
                print()
            """
        ).strip()
    )
    ret = run_pipx_cli(["run", script.as_uri()])
    assert ret == 1

    captured = capsys.readouterr()
    assert "Invalid requirement this is an invalid requirement" in captured.err


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_script_by_absolute_name(tmp_path: Path) -> None:
    script = tmp_path / "test.py"
    out = tmp_path / "output.txt"
    test_str = "Hello, world!"
    script.write_text(
        textwrap.dedent(
            f"""
                from pathlib import Path
                Path({str(out)!r}).write_text({test_str!r})
            """
        ).strip()
    )
    run_pipx_cli_exit(["run", "--path", str(script)])
    assert out.read_text() == test_str


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_script_by_relative_name(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = tmp_path / "test.py"
    out = tmp_path / "output.txt"
    test_str = "Hello, world!"
    script.write_text(
        textwrap.dedent(
            f"""
                from pathlib import Path
                Path({str(out)!r}).write_text({test_str!r})
            """
        ).strip()
    )
    with monkeypatch.context() as m:
        m.chdir(tmp_path)
        run_pipx_cli_exit(["run", "test.py"])
    assert out.read_text() == test_str


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
@pytest.mark.skipif(sys.platform.startswith("win"), reason="uses file descriptor")
def test_run_script_by_file_descriptor(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    read_fd, write_fd = os.pipe()
    out = tmp_path / "output.txt"
    test_str = "Hello, world!"

    os.write(
        write_fd,
        textwrap
        .dedent(
            f"""
                from pathlib import Path
                Path({str(out)!r}).write_text({test_str!r})
            """
        )
        .strip()
        .encode("utf-8"),
    )
    os.close(write_fd)

    with monkeypatch.context() as m:
        m.chdir(tmp_path)
        try:
            run_pipx_cli_exit(["run", f"/dev/fd/{read_fd}"])
        finally:
            os.close(read_fd)
    assert out.read_text() == test_str


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="uses windows version format")
@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_with_windows_python_version(tmp_path: Path) -> None:
    script = tmp_path / "test.py"
    out = tmp_path / "output.txt"
    script.write_text(
        textwrap.dedent(
            f"""
                import sys
                from pathlib import Path
                Path({str(out)!r}).write_text(sys.version)
            """
        ).strip()
    )
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    run_pipx_cli_exit(["run", script.as_uri(), "--python", version])
    assert version in out.read_text()


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_verify_script_name_provided(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    (tmp_path / "black").mkdir()
    run_pipx_cli_exit(["run", "black"])
    captured = capsys.readouterr()
    assert "black" in captured.err


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_shared_lib_as_app(capfd: pytest.CaptureFixture[str]) -> None:
    run_pipx_cli_exit(["run", "pip", "--help"])
    captured = capfd.readouterr()
    assert "pip <command> [options]" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_local_path_entry_point(
    caplog: pytest.LogCaptureFixture,
    empty_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(empty_project.parent)
    caplog.set_level(logging.INFO)

    run_pipx_cli_exit(["run", f".{os.sep}{empty_project.name}"])

    assert "Using discovered entry point for 'pipx run'" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_vcs_url_infers_app_name(root: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    project = tmp_path / "empty-project-vcs"
    shutil.copytree(root / "testdata" / "empty_project", project)
    pyproject = project / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace("empty_project.main:cli", "empty_project.main:main"))
    subprocess.run(["git", "init", "--quiet"], cwd=project, check=True)  # noqa: S607  # git resolved from PATH in tests
    subprocess.run(["git", "add", "."], cwd=project, check=True)  # noqa: S607  # git resolved from PATH in tests
    subprocess.run(
        [  # noqa: S607  # git resolved from PATH in tests
            "git",
            "-c",
            "user.name=pipx tests",
            "-c",
            "user.email=pipx@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--quiet",
            "-m",
            "test fixture",
        ],
        cwd=project,
        check=True,
    )

    command = ["run", "--backend", "pip", f"git+{project.as_uri()}"]
    run_pipx_cli_exit(command, assert_exit=0)
    run_pipx_cli_exit(command, assert_exit=0)

    assert caplog.text.count("Determined package name: empty-project") == 1
    assert "Reusing cached venv" in caplog.text


@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_with(capsys: pytest.CaptureFixture[str]) -> None:
    run_pipx_cli_exit(["run", "--refresh", "--with", "black", "pycowsay", "--help"])
    captured = capsys.readouterr()
    assert "injected package black into venv pycowsay" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_with_cooldown(
    root: Path,
    empty_project: Path,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    mocker.patch("os.execvpe", autospec=True, side_effect=execvpe_mock)
    find_links: Final[Path] = (
        root / ".pipx_tests" / "package_cache" / f"{sys.version_info.major}.{sys.version_info.minor}"
    )

    run_pipx_cli_exit(
        [
            "run",
            "--backend",
            "pip",
            "--cooldown",
            "7",
            "--with",
            str(empty_project),
            f"--pip-args=--no-index --find-links={find_links}",
            PKG["pycowsay"]["spec"],
            "hello",
        ],
        assert_exit=0,
    )

    assert (
        "injected package empty-project into venv" in capsys.readouterr().out,
        "--uploaded-prior-to P7D" in caplog.text,
    ) == (True, True)


@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_with_cache(caplog: pytest.LogCaptureFixture) -> None:
    run_pipx_cli_exit(["run", "--refresh", "--with", "black", "pycowsay", "args"], assert_exit=0)

    caplog.set_level(logging.DEBUG)
    caplog.clear()
    run_pipx_cli_exit(["run", "--verbose", "--with", "black", "pycowsay", "args"], assert_exit=0)
    assert "Reusing cached venv" in caplog.text


def test_maybe_script_content_accepts_url_query_string(mocker: MockerFixture) -> None:
    run_module = importlib.import_module("pipx.commands.run")
    mocker.patch.object(run_module, "_http_get_request", return_value="print('hi')")

    assert run_module.maybe_script_content("https://example.invalid/tool.py?raw=1", is_path=False) == "print('hi')"


def test_http_get_request_rejects_oversized_script(mocker: MockerFixture) -> None:
    run_module = importlib.import_module("pipx.commands.run")

    response = mocker.MagicMock()
    response.read.return_value = b"x" * (run_module._MAX_SCRIPT_BYTES + 1)  # noqa: SLF001  # private helper under test, no public API
    response.headers.get_content_charset.return_value = "utf-8"
    response.__enter__.return_value = response
    mocker.patch.object(run_module.urllib.request, "urlopen", return_value=response)

    with pytest.raises(PipxError, match="larger than"):
        run_module._http_get_request("https://example.invalid/big.py")  # noqa: SLF001  # private helper under test, no public API
