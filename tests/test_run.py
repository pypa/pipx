from __future__ import annotations

import datetime as dt
import logging
import os
import shutil
import subprocess
import sys
import textwrap
import zipfile
from contextlib import contextmanager
from functools import partial
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingTCPServer
from threading import Thread
from typing import TYPE_CHECKING, Final, NoReturn

import pytest
from filelock import AcquireReturnProxy, FileLock, Timeout
from flit_core.wheel import make_wheel_in

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterator, Mapping, Sequence
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

import pipx.main
from helpers import PACKAGE_CACHE_DIR_NAME, WIN, pipx_subprocess_env, run_pipx_cli, write_wheel
from package_info import PKG
from pipx import paths, shared_libs, util
from pipx.commands.run import maybe_script_content, run_package
from pipx.pipx_metadata_file import PipxMetadata
from pipx.venv import VenvContainer


@pytest.mark.usefixtures("pipx_temp_env")
def test_help_text(capsys: pytest.CaptureFixture[str], mocker: MockerFixture) -> None:
    mocker.patch.object(sys, "exit", autospec=True, side_effect=ValueError("raised in test to exit early"))

    with pytest.raises(ValueError, match="raised in test to exit early"):
        run_pipx_cli(["run", "--help"])

    assert "Download the latest version of a package" in capsys.readouterr().out


def execvpe_via_subprocess(_cmd_path: str, cmd_args: Sequence[str], env: Mapping[str, str]) -> None:
    sys.exit(
        subprocess.run(
            [str(arg) for arg in cmd_args],
            env=env,
            capture_output=False,
            encoding="utf-8",
            text=True,
            check=False,
        ).returncode
    )


@pytest.fixture
def exec_via_subprocess(mocker: MockerFixture) -> None:
    mocker.patch("os.execvpe", autospec=True, side_effect=execvpe_via_subprocess)


def run_pipx_cli_exit(pipx_cmd_list: list[str], assert_exit: int | None = None) -> None:
    with pytest.raises(SystemExit) as sys_exit:
        run_pipx_cli(pipx_cmd_list)
    if assert_exit is not None:
        assert sys_exit.value.code == assert_exit


@pytest.mark.parametrize(
    "package_name",
    [
        pytest.param("pycowsay", id="name"),
        pytest.param("pycowsay==0.0.0.2", id="pinned"),
        pytest.param("pycowsay>=0.0.0.2", id="lower-bound"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_simple_run(capsys: pytest.CaptureFixture[str], package_name: str) -> None:
    run_pipx_cli_exit(["run", package_name, "--help"])

    assert "Download the latest version of a package" not in capsys.readouterr().out


@pytest.mark.parametrize("backend", [pytest.param("pip", id="pip"), pytest.param("uv", id="uv")])
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_normalizes_inferred_package_name(monkeypatch: pytest.MonkeyPatch, backend: str) -> None:
    monkeypatch.setenv("PATH", f"{os.environ['PATH']}{os.pathsep}{os.defpath}")

    run_pipx_cli_exit(["run", "--backend", backend, "bLaCk", "--version"], assert_exit=0)


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_normalized_name_skips_uv_tool_run(caplog: pytest.LogCaptureFixture) -> None:
    # `uv tool run PyCowSay` would look for a `PyCowSay` script; only the venv path knows what the package installed
    run_pipx_cli_exit(["run", "--backend", "uv", "PyCowSay", "cowsay", "hi"], assert_exit=0)

    assert f"exec_app: {paths.CTX.venv_cache}" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_uv_index_url_beats_uv_default_index(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, pipx_local_pypiserver: str
) -> None:
    monkeypatch.setenv("UV_DEFAULT_INDEX", tmp_path.as_uri())
    # uv's app launcher calls realpath and dirname, which the sandboxed PATH drops
    monkeypatch.setenv("PATH", f"{os.environ['PATH']}{os.pathsep}{os.defpath}")

    run_pipx_cli_exit(["run", "--backend", "uv", "--index-url", pipx_local_pypiserver, "pycowsay", "hi"], assert_exit=0)


@pytest.mark.parametrize(
    "spec_args",
    [
        pytest.param([], id="package-name"),
        pytest.param(["--spec", "pycowsay"], id="explicit-spec"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_run_matching_name_uses_uv_tool_run(mocker: MockerFixture, spec_args: list[str]) -> None:
    # patch the handover rather than os.execvpe, which exec_app calls on POSIX only
    exec_app: Final = mocker.patch("pipx.commands.run_uv.exec_app", autospec=True, side_effect=SystemExit(0))

    run_pipx_cli_exit(["run", "--backend", "uv", *spec_args, "pycowsay", "cowsay", "hi"], assert_exit=0)

    exec_app.assert_called_once()
    assert exec_app.call_args.args[0][1:3] == ["tool", "run"]


@pytest.mark.parametrize(
    "spec_template",
    [
        pytest.param("{path}", id="local-path"),
        pytest.param("empty-project @ {uri}", id="direct-reference"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_spec_honors_dotted_pipx_run_entry_point(
    empty_project: Path,
    caplog: pytest.LogCaptureFixture,
    spec_template: str,
) -> None:
    pyproject: Final[Path] = empty_project / "pyproject.toml"
    pyproject.write_text(
        pyproject
        .read_text(encoding="utf-8")
        .replace('scripts.empty-project = "empty_project.main:cli"', "")
        .replace(
            'entry-points."pipx.run".empty-project = "empty_project.main:cli"',
            'entry-points."pipx.run"."empty.project" = "empty_project.main:main"',
        ),
        encoding="utf-8",
    )
    caplog.set_level(logging.INFO)

    run_pipx_cli_exit(
        [
            "run",
            "--backend",
            "uv",
            "--spec",
            spec_template.format(path=empty_project, uri=empty_project.as_uri()),
            "empty.project",
        ],
        assert_exit=0,
    )

    assert "Using discovered entry point for 'pipx run'" in caplog.text
    assert f"exec_app: {paths.CTX.venv_cache}" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_preserves_explicit_app_name(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["run", "--spec", "black", "bLaCk.app"]) == 1
    assert "'bLaCk.app' executable script not found in package 'black'." in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_cache_reuses_venv(caplog: pytest.LogCaptureFixture) -> None:
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    caplog.set_level(logging.DEBUG)

    run_pipx_cli_exit(["run", "--verbose", "pycowsay", "cowsay", "args"], assert_exit=0)

    assert "Reusing cached venv" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_no_cache_removes_cached_venv(caplog: pytest.LogCaptureFixture) -> None:
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    caplog.set_level(logging.DEBUG)

    run_pipx_cli_exit(["run", "--no-cache", "pycowsay", "cowsay", "args"])

    assert "Removing cached venv" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_refresh_rebuilds_cached_environment() -> None:
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    venv_dir: Final[Path] = next(path for path in paths.CTX.venv_cache.iterdir() if path.is_dir())
    marker: Final[Path] = venv_dir / "marker"
    marker.touch()

    run_pipx_cli_exit(["run", "--refresh", "pycowsay", "cowsay", "args"])

    assert not marker.exists()


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_refresh_retains_replacement() -> None:
    run_pipx_cli_exit(["run", "--refresh", "pycowsay", "cowsay", "args"])
    venv_dir: Final[Path] = next(path for path in paths.CTX.venv_cache.iterdir() if path.is_dir())
    marker: Final[Path] = venv_dir / "marker"
    marker.touch()

    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])

    assert marker.exists()


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_skips_a_cache_entry_held_by_another_run(mocker: MockerFixture) -> None:
    paths.CTX.venv_cache.mkdir(parents=True, exist_ok=True)
    held: Final[Path] = paths.CTX.venv_cache / "held-by-another-run"
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


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_with_isolates_cache_by_dependency() -> None:
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "hi"])
    plain_dirs: Final[set[Path]] = {path for path in paths.CTX.venv_cache.iterdir() if path.is_dir()}

    run_pipx_cli_exit(["run", "--with", "six", "pycowsay", "cowsay", "hi"])
    with_dirs: Final[set[Path]] = {path for path in paths.CTX.venv_cache.iterdir() if path.is_dir()} - plain_dirs

    assert [bool(list(path.rglob("six-*.dist-info"))) for path in (*plain_dirs, *with_dirs)] == [False, True]


@pytest.fixture
def script_interpreters(mocker: MockerFixture) -> None:
    # each searched minor 3.X resolves to /py/3.X, and the default Python reports 3.14.0
    mocker.patch(
        "pipx.requires_python.find_python_interpreter", autospec=True, side_effect=lambda minor, _: f"/py/{minor}"
    )
    mocker.patch(
        "pipx.requires_python.run_subprocess",
        autospec=True,
        side_effect=lambda cmd, **_: subprocess.CompletedProcess(
            cmd, 0, stdout=f"{cmd[0].removeprefix('/py/')}.0" if cmd[0].startswith("/py/") else "3.14.0"
        ),
    )


@pytest.mark.parametrize("backend", [pytest.param("pip", id="pip"), pytest.param("uv", id="uv")])
@pytest.mark.parametrize(
    ("requires_python", "searched"),
    [
        pytest.param(">=3.10", set(), id="default-satisfies"),
        pytest.param("<3.13", {"/py/3.12"}, id="default-fails"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env", "script_interpreters")
def test_run_script_searches_python_only_when_default_fails_requires_python(
    tmp_path: Path, mocker: MockerFixture, backend: str, requires_python: str, searched: set[str]
) -> None:
    exec_mock: Final = mocker.create_autospec(util.exec_app, side_effect=SystemExit(0))
    mocker.patch("pipx.commands.run.exec_app", new=exec_mock)
    mocker.patch("pipx.commands.run_uv.exec_app", new=exec_mock)
    script: Final[Path] = tmp_path / "script.py"
    script.write_text(
        f'# /// script\n# requires-python = "{requires_python}"\n# dependencies = []\n# ///\n', encoding="utf-8"
    )

    run_pipx_cli_exit(["run", "--backend", backend, str(script)], assert_exit=0)

    assert {Path(arg) for arg in exec_mock.call_args.args[0]} & {Path("/py/3.12"), Path("/py/3.15")} == {
        Path(path) for path in searched
    }


@pytest.mark.parametrize("backend", [pytest.param("pip", id="pip"), pytest.param("uv", id="uv")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_run_rejects_python_failing_requires_python(
    tmp_path: Path, mocker: MockerFixture, capsys: pytest.CaptureFixture[str], backend: str
) -> None:
    mocker.patch("pipx.commands.run_uv.exec_app", autospec=True, side_effect=SystemExit(0))
    script: Final[Path] = tmp_path / "script.py"
    script.write_text('# /// script\n# requires-python = ">=3.99"\n# ///\nprint("hi")\n', encoding="utf-8")

    assert run_pipx_cli(["run", "--backend", backend, "--python", sys.executable, str(script)]) == 1
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


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_does_not_mark_cache_as_installation() -> None:
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])

    assert PipxMetadata(next(path for path in paths.CTX.venv_cache.iterdir() if path.is_dir())).environment is None


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_cooldown_separates_cache(package_cache_dir: Path, caplog: pytest.LogCaptureFixture) -> None:
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={package_cache_dir}"

    run_pipx_cli_exit(
        ["run", "--backend", "pip", "--cooldown", "7", pip_args, PKG["pycowsay"]["spec"], "hello"],
        assert_exit=0,
    )
    cached_venvs: Final[set[Path]] = {path for path in paths.CTX.venv_cache.iterdir() if path.is_dir()}
    caplog.clear()

    run_pipx_cli_exit(
        ["run", "--backend", "pip", "--cooldown", "0", pip_args, PKG["pycowsay"]["spec"], "hello"],
        assert_exit=0,
    )

    assert (
        len({path for path in paths.CTX.venv_cache.iterdir() if path.is_dir()}),
        "--uploaded-prior-to" in caplog.text,
    ) == (len(cached_venvs) + 1, False)


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_no_path_check(mocker: MockerFixture, caplog: pytest.LogCaptureFixture) -> None:
    which: Final[MagicMock] = mocker.create_autospec(shutil.which, return_value="/fake/bin/pycowsay")
    mocker.patch("pipx.commands.run.which", new=which)
    mocker.patch("pipx.commands.run_uv.which", new=which)

    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    which.assert_called_once_with("pycowsay")
    assert "is already on your PATH" in caplog.text

    caplog.clear()
    run_pipx_cli_exit(["run", "--no-path-check", "pycowsay", "cowsay", "args"])
    which.assert_called_once_with("pycowsay")
    assert "is already on your PATH" not in caplog.text


@pytest.mark.usefixtures("pipx_ultra_temp_env", "exec_via_subprocess")
def test_cachedir_tag_created_with_signature(caplog: pytest.LogCaptureFixture) -> None:
    tag_path: Final[Path] = paths.CTX.venv_cache / "CACHEDIR.TAG"
    assert not tag_path.exists()
    caplog.set_level(logging.DEBUG)

    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])

    assert (
        "Adding CACHEDIR.TAG to cache directory" in caplog.text,
        tag_path.read_text().startswith("Signature: 8a477f597d28d172789f06886806bc55"),
    ) == (True, True)


@pytest.mark.usefixtures("pipx_ultra_temp_env", "exec_via_subprocess")
def test_cachedir_tag_not_recreated(caplog: pytest.LogCaptureFixture) -> None:
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    caplog.set_level(logging.DEBUG)
    caplog.clear()

    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])

    assert (
        "Adding CACHEDIR.TAG to cache directory" in caplog.text,
        (paths.CTX.venv_cache / "CACHEDIR.TAG").exists(),
    ) == (False, True)


@pytest.mark.usefixtures("pipx_ultra_temp_env", "exec_via_subprocess")
def test_cache_sweep_ignores_tag(mocker: MockerFixture, caplog: pytest.LogCaptureFixture) -> None:
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    tag_path: Final[Path] = paths.CTX.venv_cache / "CACHEDIR.TAG"
    expired_venv: Final[Path] = paths.CTX.venv_cache / "expired"
    expired_venv.mkdir()
    mocker.patch(
        "pipx.commands.run.dt",
        UTC=dt.UTC,
        **{"datetime.now.return_value": dt.datetime.now(dt.UTC) + dt.timedelta(days=15)},
    )
    caplog.set_level(logging.INFO)
    caplog.clear()

    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])

    assert not expired_venv.exists()
    assert tag_path.exists()
    assert f"Removing expired venv {tag_path}" not in caplog.text


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_script_from_url(served_script: str) -> None:
    run_pipx_cli_exit(["run", served_script], assert_exit=0)


@pytest.mark.usefixtures("pipx_temp_env", "planted_json_cwd", "exec_via_subprocess")
def test_run_script_from_url_ignores_working_directory_modules(
    served_script: str, tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "imports-json.py").write_text("import json\n\nprint(json.dumps('ok'))\n", encoding="utf-8")

    run_pipx_cli_exit(["run", served_script.replace("pipx-demo.py", "imports-json.py")], assert_exit=0)

    assert capfd.readouterr().out.splitlines() == ['"ok"']


@pytest.mark.usefixtures("pipx_temp_env", "planted_json_cwd", "exec_via_subprocess")
def test_run_entry_point_ignores_working_directory_modules(
    empty_project: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    (empty_project / "empty_project" / "main.py").write_text(
        "import json\n\n\ndef cli() -> None:\n    print(json.dumps('ok'))\n", encoding="utf-8"
    )

    run_pipx_cli_exit(["run", "--spec", str(empty_project), "empty-project"], assert_exit=0)

    assert capfd.readouterr().out.splitlines() == ['"ok"']


@pytest.fixture
def planted_json_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (cwd := tmp_path / "cwd").mkdir()
    (cwd / "json.py").write_text("raise SystemExit('imported json.py from the working directory')\n", encoding="utf-8")
    monkeypatch.chdir(cwd)


@pytest.fixture
def served_script(tmp_path: Path) -> Iterator[str]:
    # loopback rather than a third-party gist: that host rate-limited the CI runners, and its leaked socket surfaced as
    # an unraisable ResourceWarning in whichever test the GC interrupted
    (tmp_path / "pipx-demo.py").write_text("print('pipx works!')\n", encoding="utf-8")
    with _serving(partial(SimpleHTTPRequestHandler, directory=str(tmp_path))) as port:
        yield f"http://127.0.0.1:{port}/pipx-demo.py"


@contextmanager
def _serving(handler: type[BaseHTTPRequestHandler] | partial[SimpleHTTPRequestHandler]) -> Generator[int, None, None]:
    # not http.server.HTTPServer: its bind resolves the host name, which stalls for 30 s on macOS CI runners
    server: Final[ThreadingTCPServer] = ThreadingTCPServer(("127.0.0.1", 0), handler)
    thread: Final[Thread] = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize(
    ("input_run_args", "expected_app_with_args"),
    [
        pytest.param(["--", "pycowsay", "--", "hello"], ["pycowsay", "--", "hello"], id="sep-app-sep-arg"),
        pytest.param(
            ["--", "pycowsay", "--", "--", "hello"], ["pycowsay", "--", "--", "hello"], id="sep-app-sep-sep-arg"
        ),
        pytest.param(["--", "pycowsay", "hello", "--"], ["pycowsay", "hello", "--"], id="sep-app-arg-sep"),
        pytest.param(
            ["--", "pycowsay", "hello", "--", "--"], ["pycowsay", "hello", "--", "--"], id="sep-app-arg-sep-sep"
        ),
        pytest.param(["--", "pycowsay", "--"], ["pycowsay", "--"], id="sep-app-sep"),
        pytest.param(["--", "pycowsay", "--", "--"], ["pycowsay", "--", "--"], id="sep-app-sep-sep"),
        pytest.param(["pycowsay", "--", "hello"], ["pycowsay", "--", "hello"], id="app-sep-arg"),
        pytest.param(["pycowsay", "--", "--", "hello"], ["pycowsay", "--", "--", "hello"], id="app-sep-sep-arg"),
        pytest.param(["pycowsay", "hello", "--"], ["pycowsay", "hello", "--"], id="app-arg-sep"),
        pytest.param(["pycowsay", "hello", "--", "--"], ["pycowsay", "hello", "--", "--"], id="app-arg-sep-sep"),
        pytest.param(["pycowsay", "--"], ["pycowsay", "--"], id="app-sep"),
        pytest.param(["pycowsay", "--", "--"], ["pycowsay", "--", "--"], id="app-sep-sep"),
        pytest.param(["--", "--", "pycowsay", "--"], ["--", "pycowsay", "--"], id="sep-sep-app-sep"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_appargs_doubledash(
    monkeypatch: pytest.MonkeyPatch, input_run_args: list[str], expected_app_with_args: list[str]
) -> None:
    parser = pipx.main.get_command_parser()
    monkeypatch.setattr(sys, "argv", ["pipx", "run", *input_run_args])
    parsed_pipx_args: Final = parser.parse_args()
    pipx.main.check_args(parsed_pipx_args)
    assert parsed_pipx_args.app_with_args == expected_app_with_args


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_ensure_null_pythonpath(make_wheel: Callable[[dict[str, str]], Path]) -> None:
    wheel: Final[Path] = make_wheel({
        "foo_bar_x.py": "import os\ndef main() -> None:\n    print(os.environ.get('PYTHONPATH'))\n",
        "foo_bar_x-1.dist-info/METADATA": "Metadata-Version: 2.1\nName: foo-bar-x\nVersion: 1\n",
        "foo_bar_x-1.dist-info/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        "foo_bar_x-1.dist-info/entry_points.txt": "[console_scripts]\nfoo-bar-x = foo_bar_x:main\n",
        "foo_bar_x-1.dist-info/RECORD": "",
    })
    assert (
        subprocess.run(
            [sys.executable, "-m", "pipx", "run", "--spec", str(wheel), "foo-bar-x"],
            env=pipx_subprocess_env() | {"PYTHONPATH": "test"},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        == "None\n"
    )


# packages listed roughly in order of increasing test duration
@pytest.mark.parametrize(
    ("package", "package_or_url", "app_appargs"),
    [
        pytest.param("pycowsay", "pycowsay", ["pycowsay", "hello"], id="pycowsay"),
        pytest.param(
            "shell-functools",
            PKG["shell-functools"]["spec"],
            ["filter", "--help"],
            id="shell-functools",
            marks=pytest.mark.skipif(sys.platform.startswith("win"), reason="setup.py scripts do not run on Windows"),
        ),
        pytest.param("black", PKG["black"]["spec"], ["black", "--help"], id="black"),
        pytest.param("kaggle", PKG["kaggle"]["spec"], ["kaggle", "--help"], id="kaggle"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_package_determination(
    caplog: pytest.LogCaptureFixture, package: str, package_or_url: str, app_appargs: list[str]
) -> None:
    caplog.set_level(logging.INFO)

    run_pipx_cli_exit(["run", "--verbose", "--spec", package_or_url, "--", *app_appargs])

    assert "Cannot determine package name" not in caplog.text
    assert f"Determined package name: {package}" in caplog.text


@pytest.mark.parametrize(
    "run_args",
    [
        pytest.param(["{uri}"], id="file-uri"),
        pytest.param(["--path", "{path}"], id="absolute-name"),
        pytest.param(["test.py"], id="relative-name"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_without_requirements(
    hello_script: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, run_args: list[str]
) -> None:
    script, out = hello_script
    monkeypatch.chdir(script.parent)

    run_pipx_cli_exit(["run", *(arg.format(uri=script.as_uri(), path=script) for arg in run_args)])

    assert out.read_text() == "Hello, world!"


@pytest.fixture
def hello_script(tmp_path: Path) -> tuple[Path, Path]:
    out: Final[Path] = tmp_path / "output.txt"
    (script := tmp_path / "test.py").write_text(
        f"from pathlib import Path\nPath({str(out)!r}).write_text('Hello, world!')"
    )
    return script, out


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_passes_python_args_to_script(tmp_path: Path) -> None:
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


@pytest.mark.parametrize("backend", [pytest.param("pip", id="pip"), pytest.param("uv", id="uv")])
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_passes_python_args_to_app(tmp_path: Path, backend: str) -> None:
    project: Final[Path] = tmp_path / "flags-app"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        """\
[build-system]
requires = ["flit-core"]
build-backend = "flit_core.buildapi"

[project]
name = "flags-app"
version = "1"
description = "Record the interpreter flags."

[project.scripts]
flags-app = "flags_app:main"
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
    script: Final[Path] = tmp_path / "console_output.py"
    script.write_text(script_text, encoding="utf-8")
    env: Final[dict[str, str]] = pipx_subprocess_env() | {"PIPX_DEFAULT_BACKEND": "pip", "PYTHONIOENCODING": encoding}

    direct_output: Final[bytes] = subprocess.run(
        [sys.executable, script],
        env=env,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout

    assert (
        subprocess.run(
            [sys.executable, "-m", "pipx", "run", script],
            env=env,
            stdout=subprocess.PIPE,
            check=True,
        ).stdout
        == direct_output
    )


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
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_with_requirements(script_text: str, expected_output: str, tmp_path: Path) -> None:
    script: Final[Path] = tmp_path / "test.py"
    out: Final[Path] = tmp_path / "output.txt"
    script.write_text(
        textwrap.dedent(script_text.format(out=str(out))).strip(),
        encoding="utf-8",
    )
    run_pipx_cli_exit(["run", script.as_uri()])
    assert out.read_text() == expected_output


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_script_with_uv_ignores_uv_toml_beside_script(tmp_path: Path) -> None:
    # uv fails on a malformed config file it discovers, so success proves it never read the one beside the script; a
    # sibling of PIPX_HOME, since a uv.toml above PIPX_HOME would still apply
    (script_dir := tmp_path / "scripts").mkdir()
    (script_dir / "uv.toml").write_text("index-url = [\n")
    out: Final[Path] = tmp_path / "output.txt"
    (script := script_dir / "test.py").write_text(
        f"# /// script\n# dependencies = []\n# ///\nfrom pathlib import Path\nPath({str(out)!r}).write_text('ran')\n"
    )

    run_pipx_cli_exit(["run", "--backend", "uv", str(script)], assert_exit=0)

    assert out.read_text() == "ran"


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_script_uv_releases_cache_lock_before_handover(tmp_path: Path, mocker: MockerFixture) -> None:
    def handover(_cmd: Sequence[str | Path], env: dict[str, str]) -> NoReturn:
        # raises Timeout while held; exec_app waits for the script on Windows, so the lock would outlive the handover
        with VenvContainer(paths.CTX.venv_cache).venv_lock(Path(env["VIRTUAL_ENV"])).acquire(timeout=0):
            raise SystemExit(0)

    mocker.patch("pipx.commands.run_uv.exec_app", autospec=True, side_effect=handover)
    (script := tmp_path / "test.py").write_text("# /// script\n# dependencies = []\n# ///\n")

    run_pipx_cli_exit(["run", "--backend", "uv", str(script)], assert_exit=0)


@pytest.fixture
def uv_script(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # the temp env must be active while running
    tmp_path: Path,
) -> Path:
    if shutil.which("uv") is None:
        pytest.skip("needs the uv binary")
    (script := tmp_path / "test.py").write_text("# /// script\n# dependencies = []\n# ///\n")
    return script


@pytest.fixture
def run_beside_running_uv_script(uv_script: Path, mocker: MockerFixture) -> Callable[[list[str], str], Path]:
    # exec_app waits for the script on Windows, so the handover runs it and then stands in for it still running there
    # while another pipx process runs the same script
    def run(flags: list[str], planted: str) -> Path:
        venv_dirs: Final[list[Path]] = []

        def handover(cmd: Sequence[str | Path], env: dict[str, str]) -> NoReturn:
            subprocess.run([str(arg) for arg in cmd], env=env, check=True)
            venv_dirs.append(venv_dir := Path(env["VIRTUAL_ENV"]))
            (venv_dir / planted).touch()
            subprocess.run(
                [sys.executable, "-m", "pipx", "run", "--backend", "uv", *flags, str(uv_script)],
                env=pipx_subprocess_env(),
                check=True,
            )
            raise SystemExit(0)

        mocker.patch("pipx.commands.run_uv.exec_app", autospec=True, side_effect=handover)
        run_pipx_cli_exit(["run", "--backend", "uv", str(uv_script)], assert_exit=0)
        # autospec refuses to wrap a mock, so a test patching exec_app again needs the original back
        mocker.stopall()
        return venv_dirs[0]

    return run


@pytest.mark.parametrize(
    ("flags", "planted"),
    [
        pytest.param(["--no-cache"], "running", id="no-cache"),
        pytest.param(["--refresh"], "running", id="refresh"),
        pytest.param([], "pipx_expired_venv", id="expired"),
    ],
)
def test_run_script_uv_keeps_environment_a_running_script_uses(
    run_beside_running_uv_script: Callable[[list[str], str], Path], flags: list[str], planted: str
) -> None:
    assert (run_beside_running_uv_script(flags, planted) / planted).is_file()


def test_run_script_uv_rebuilds_environment_refreshed_while_running(
    run_beside_running_uv_script: Callable[[list[str], str], Path], uv_script: Path, mocker: MockerFixture
) -> None:
    venv_dir: Final[Path] = run_beside_running_uv_script(["--refresh"], "running")

    def handover(_cmd: Sequence[str | Path], env: dict[str, str]) -> NoReturn:
        raise SystemExit((Path(env["VIRTUAL_ENV"]), (venv_dir / "running").exists()))

    mocker.patch("pipx.commands.run_uv.exec_app", autospec=True, side_effect=handover)

    with pytest.raises(SystemExit) as sys_exit:
        run_pipx_cli(["run", "--backend", "uv", str(uv_script)])

    assert sys_exit.value.code == (venv_dir, False)


@pytest.mark.skipif(not WIN, reason="pipx hands the process over to uv elsewhere, so nothing is left to clean up")
def test_run_script_uv_removes_its_own_environment_once_done(
    run_beside_running_uv_script: Callable[[list[str], str], Path],
) -> None:
    venv_dir: Final[Path] = run_beside_running_uv_script(["--no-cache"], "running")

    assert [path for path in paths.CTX.venv_cache.iterdir() if path.is_dir()] == [venv_dir]


@pytest.mark.parametrize(
    ("second_links", "second_flags"),
    [
        pytest.param("new", [], id="changed-find-links"),
        pytest.param("old", ["--refresh"], id="refresh"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_script_uv_rebuilds_for_new_request(
    demodep_version_script: tuple[Path, Path],
    second_links: str,
    second_flags: list[str],
    publish_demodep: Callable[[str, str], Path],
) -> None:
    script, out = demodep_version_script
    run_pipx_cli_exit(
        ["run", "--backend", "uv", f"--pip-args=--find-links={publish_demodep('old', '1.0')}", str(script)],
        assert_exit=0,
    )
    links: Final[Path] = publish_demodep(second_links, "2.0")

    run_pipx_cli_exit(["run", "--backend", "uv", *second_flags, f"--pip-args=--find-links={links}", str(script)])

    assert out.read_text() == "2.0"


@pytest.fixture
def demodep_version_script(tmp_path: Path) -> tuple[Path, Path]:
    out: Final[Path] = tmp_path / "output.txt"
    (script := tmp_path / "test.py").write_text(
        "# /// script\n# dependencies = ['demodep']\n# ///\nfrom importlib.metadata import version\n"
        f"from pathlib import Path\nPath({str(out)!r}).write_text(version('demodep'))\n"
    )
    return script, out


@pytest.fixture
def publish_demodep(tmp_path: Path) -> Callable[[str, str], Path]:
    def publish(links_name: str, version: str) -> Path:
        return write_wheel(tmp_path / links_name, "demodep", version).parent

    return publish


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_rebuilds_after_installer_env_changes(
    demodep_version_script: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    publish_demodep: Callable[[str, str], Path],
) -> None:
    script, out = demodep_version_script
    monkeypatch.setenv("PIP_FIND_LINKS", str(publish_demodep("old", "1.0")))
    run_pipx_cli_exit(["run", "--backend", "pip", str(script)], assert_exit=0)
    monkeypatch.setenv("PIP_FIND_LINKS", str(publish_demodep("new", "2.0")))

    run_pipx_cli_exit(["run", "--backend", "pip", str(script)])

    assert out.read_text() == "2.0"


@pytest.fixture
def run_demodep_script(tmp_path: Path, publish_demodep: Callable[[str, str], Path]) -> Callable[[str], set[Path]]:
    (script := tmp_path / "test.py").write_text("# /// script\n# dependencies = ['demodep']\n# ///\nimport demodep\n")
    links: Final[Path] = publish_demodep("links", "1.0")

    def run(backend: str) -> set[Path]:
        run_pipx_cli_exit(["run", "--backend", backend, f"--pip-args=--find-links={links}", str(script)], assert_exit=0)
        return {path for path in paths.CTX.venv_cache.iterdir() if path.is_dir()}

    return run


@pytest.mark.parametrize(
    ("backend", "variable", "value"),
    [
        pytest.param("pip", "PIP_TIMEOUT", "60", id="pip-timeout"),
        pytest.param("pip", "PIP_timeout", "60", id="pip-timeout-lower-case"),
        pytest.param("pip", "PIP_NO-COLOR", "1", id="pip-no-color-dashed"),
        pytest.param("uv", "UV_RUN_RECURSION_DEPTH", "1", id="uv-run-recursion-depth"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_cache_key_ignores_unrelated_installer_env(
    monkeypatch: pytest.MonkeyPatch,
    run_demodep_script: Callable[[str], set[Path]],
    backend: str,
    variable: str,
    value: str,
) -> None:
    first: Final[set[Path]] = run_demodep_script(backend)
    monkeypatch.setenv(variable, value)

    assert run_demodep_script(backend) == first


@pytest.mark.parametrize(
    ("backend", "variable", "value"),
    [
        pytest.param("pip", "PIP_PRE", "1", id="pip-pre"),
        pytest.param("pip", "PIP_index_url", "file:///pipx-missing-index", id="pip-index-url-lower-case"),
        pytest.param("pip", "PIP_PIPX_UNLISTED", "1", id="pip-unlisted"),
        pytest.param("uv", "UV_PRERELEASE", "allow", id="uv-prerelease"),
        pytest.param("uv", "UV_PYTHON_INSTALL_MIRROR", "https://mirror.invalid", id="uv-python-install-mirror"),
        pytest.param("uv", "UV_PIPX_UNLISTED", "1", id="uv-unlisted"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_cache_key_follows_resolution_installer_env(
    monkeypatch: pytest.MonkeyPatch,
    run_demodep_script: Callable[[str], set[Path]],
    backend: str,
    variable: str,
    value: str,
) -> None:
    first: Final[set[Path]] = run_demodep_script(backend)
    monkeypatch.setenv(variable, value)

    assert len(run_demodep_script(backend) - first) == 1


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_with_requirements_and_cli_with_pip_backend(tmp_path: Path) -> None:
    script: Final[Path] = tmp_path / "test.py"
    out: Final[Path] = tmp_path / "output.txt"
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


@pytest.fixture
def pycowsay_script(tmp_path: Path) -> tuple[Path, Path]:
    output: Final[Path] = tmp_path / "output.txt"
    (script := tmp_path / "test.py").write_text(
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
    return script, output


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_script_cooldown(
    package_cache_dir: Path, pycowsay_script: tuple[Path, Path], caplog: pytest.LogCaptureFixture
) -> None:
    script, output = pycowsay_script

    run_pipx_cli_exit(
        [
            "run",
            "--backend",
            "pip",
            "--cooldown",
            "7",
            f"--pip-args=--no-index --find-links={package_cache_dir}",
            script.as_uri(),
        ],
        assert_exit=0,
    )

    assert (output.read_text(encoding="utf-8"), "--uploaded-prior-to P7D" in caplog.text) == ("done", True)


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_script_resolves_relative_find_links(
    root: Path, pycowsay_script: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    script, output = pycowsay_script
    monkeypatch.chdir(root)

    run_pipx_cli_exit(
        [
            "run",
            "--backend",
            "pip",
            f"--pip-args=--no-index --find-links=.pipx_tests/package_cache/{PACKAGE_CACHE_DIR_NAME}",
            str(script),
        ],
        assert_exit=0,
    )

    assert output.read_text(encoding="utf-8") == "done"


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_with_requirements_old(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    script: Final[Path] = tmp_path / "test.py"
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


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_correct_traceback(capfd: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    script: Final[Path] = tmp_path / "test.py"
    script.write_text(
        textwrap.dedent(
            """
                raise RuntimeError("Should fail")
            """
        ).strip()
    )

    with pytest.raises(SystemExit):
        run_pipx_cli(["run", str(script)])

    assert "test.py" in capfd.readouterr().err


@pytest.mark.parametrize(
    "header",
    [
        pytest.param("", id="plain"),
        pytest.param('# /// script\n# dependencies = ["packaging"]\n# ///\nimport packaging\n', id="with-requirements"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_with_args(tmp_path: Path, header: str) -> None:
    script: Final[Path] = tmp_path / "test.py"
    out: Final[Path] = tmp_path / "output.txt"
    script.write_text(
        f"{header}import sys\nfrom pathlib import Path\nPath({str(out)!r}).write_text(str(int(sys.argv[1]) + 1))"
    )

    run_pipx_cli_exit(["run", script.as_uri(), "1"])

    assert out.read_text() == "2"


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_with_failing_requirements(capfd: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    script: Final[Path] = tmp_path / "test.py"
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
    assert run_pipx_cli(["run", str(script)]) != 0
    assert "Error installing will_fail @ git+https://0.0.0.0/will_fail.git." in capfd.readouterr().err

    # a venv kept from the failed install would run the script, which then fails with ModuleNotFoundError
    assert run_pipx_cli(["run", str(script)]) != 0

    err: Final[str] = capfd.readouterr().err
    assert "ModuleNotFoundError: No module named 'will_fail'" not in err
    assert "Error installing will_fail @ git+https://0.0.0.0/will_fail.git." in err


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_script_interrupted_venv_creation_expires_cache(
    inline_script: Path,
    mocker: MockerFixture,
    capfd: pytest.CaptureFixture[str],
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None],
) -> None:
    def interrupt() -> None:
        raise KeyboardInterrupt

    before_venv_subprocess(paths.CTX.venv_cache, interrupt)
    assert run_pipx_cli(["run", "--backend", "pip", str(inline_script)]) == 1
    mocker.stopall()
    mocker.patch("os.execvpe", autospec=True, side_effect=execvpe_via_subprocess)

    run_pipx_cli_exit(["run", "--backend", "pip", str(inline_script)], assert_exit=0)

    assert capfd.readouterr().out.splitlines()[-1] == "installed"


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_package_install_failure_expires_cache(package_cache_dir: Path) -> None:
    # the find links carry a current pip: when this test builds the session's shared libs, a bare --no-index would
    # fail their pip reinstall and leave the base interpreter's bundled pip for later tests on this worker
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={package_cache_dir}"

    assert run_pipx_cli(["run", "--backend", "pip", pip_args, "--spec", "pipx-missing-package", "missing-app"]) == 1

    assert len(list(paths.CTX.venv_cache.glob("*/pipx_expired_venv"))) == 1


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_app_not_found_keeps_cache(caplog: pytest.LogCaptureFixture) -> None:
    assert run_pipx_cli(["run", "--spec", "pycowsay", "pycowsayy"]) == 1
    caplog.set_level(logging.INFO)

    run_pipx_cli_exit(["run", "--spec", "pycowsay", "pycowsay", "hi"], assert_exit=0)

    assert "Reusing cached venv" in caplog.text


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_pip_args_forwarded_to_shared_libs(
    capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    # an empty env makes the next command upgrade the shared libs, which --no-index must then fail
    assert shared_libs.SHARED_LIBS.needs_upgrade

    assert run_pipx_cli(["run", "--verbose", "--pip-args=--no-index", "pycowsay", "hello"]) != 0

    assert "ERROR: Could not find a version that satisfies the requirement pip" in capsys.readouterr().err
    assert "Upgrading shared libraries in" in caplog.text
    assert "Failed to upgrade shared libraries" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_with_invalid_requirement(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    script: Final[Path] = tmp_path / "test.py"
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

    assert run_pipx_cli(["run", script.as_uri()]) == 1

    assert "Invalid requirement this is an invalid requirement" in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
@pytest.mark.skipif(sys.platform.startswith("win"), reason="uses file descriptor")
def test_run_script_by_file_descriptor(monkeypatch: pytest.MonkeyPatch, hello_script: tuple[Path, Path]) -> None:
    script, out = hello_script
    read_fd, write_fd = os.pipe()
    os.write(write_fd, script.read_bytes())
    os.close(write_fd)
    monkeypatch.chdir(script.parent)

    try:
        run_pipx_cli_exit(["run", f"/dev/fd/{read_fd}"])
    finally:
        os.close(read_fd)

    assert out.read_text() == "Hello, world!"


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="uses windows version format")
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_with_windows_python_version(tmp_path: Path) -> None:
    script: Final[Path] = tmp_path / "test.py"
    out: Final[Path] = tmp_path / "output.txt"
    script.write_text(
        textwrap.dedent(
            f"""
                import sys
                from pathlib import Path
                Path({str(out)!r}).write_text(sys.version)
            """
        ).strip()
    )
    version: Final[str] = f"{sys.version_info.major}.{sys.version_info.minor}"

    run_pipx_cli_exit(["run", script.as_uri(), "--python", version])

    assert version in out.read_text()


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_verify_script_name_provided(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    (tmp_path / "black").mkdir()

    run_pipx_cli_exit(["run", "black"])

    assert "black" in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_shared_lib_as_app(capfd: pytest.CaptureFixture[str]) -> None:
    run_pipx_cli_exit(["run", "pip", "--help"])

    assert "pip <command> [options]" in capfd.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_local_path_entry_point(
    caplog: pytest.LogCaptureFixture,
    empty_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(empty_project.parent)
    caplog.set_level(logging.INFO)

    run_pipx_cli_exit(["run", f".{os.sep}{empty_project.name}"])

    assert "Using discovered entry point for 'pipx run'" in caplog.text


@pytest.fixture
def vcs_project(root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[str, str], str]:
    def create(old: str, new: str) -> str:
        project: Final[Path] = tmp_path / "vcs-project"
        shutil.copytree(root / "testdata" / "empty_project", project)
        pyproject: Final[Path] = project / "pyproject.toml"
        pyproject.write_text(pyproject.read_text().replace(old, new))
        # uv clones through `git submodule`, a shell script needing the platform utilities the sandboxed PATH drops
        monkeypatch.setenv("PATH", os.environ["PATH_ORIG"])
        git: Final[str | None] = shutil.which("git")
        assert git is not None
        for git_args in (
            ["init", "--quiet"],
            ["add", "."],
            [
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
        ):
            subprocess.run([git, *git_args], cwd=project, check=True)
        return f"git+{project.as_uri()}"

    return create


@pytest.mark.parametrize("backend", [pytest.param("pip", id="pip"), pytest.param("uv", id="uv")])
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_vcs_url_infers_app_name(
    vcs_project: Callable[[str, str], str],
    caplog: pytest.LogCaptureFixture,
    backend: str,
) -> None:
    command: Final[list[str]] = [
        "run",
        "--backend",
        backend,
        vcs_project("empty_project.main:cli", "empty_project.main:main"),
    ]
    run_pipx_cli_exit(command, assert_exit=0)
    run_pipx_cli_exit(command, assert_exit=0)

    assert caplog.text.count("Determined package name: empty-project") == 1
    assert "Reusing cached venv" in caplog.text


@pytest.mark.parametrize("backend", [pytest.param("pip", id="pip"), pytest.param("uv", id="uv")])
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_vcs_url_runs_sole_script_of_other_name(
    vcs_project: Callable[[str, str], str],
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    backend: str,
) -> None:
    # drop the pipx.run entry point as well: it matches on package name and would hide the console script lookup
    declared: Final[str] = (
        'scripts.empty-project = "empty_project.main:cli"\n'
        'entry-points."pipx.run".empty-project = "empty_project.main:cli"'
    )
    command: Final[list[str]] = [
        "run",
        "--backend",
        backend,
        vcs_project(declared, 'scripts.renamed = "empty_project.main:main"'),
    ]
    run_pipx_cli_exit(command, assert_exit=0)
    assert "NOTE: running app 'renamed' from 'empty-project'" in capsys.readouterr().out

    run_pipx_cli_exit(command, assert_exit=0)
    assert "Reusing cached venv" in caplog.text


@pytest.mark.parametrize(
    "source_args",
    [
        pytest.param(["--spec", "./dist/tool-1.0-py3-none-any.whl"], id="dot-slash"),
        pytest.param(["--spec", "dist/tool-1.0-py3-none-any.whl"], id="bare"),
        pytest.param(["--pip-args=--find-links=dist"], id="find-links"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_relative_path_keys_cache_per_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str], source_args: list[str]
) -> None:
    for checkout in ("first", "second"):
        (dist := tmp_path / checkout / "dist").mkdir(parents=True)
        with zipfile.ZipFile(dist / "tool-1.0-py3-none-any.whl", "w") as archive:
            archive.writestr("tool.py", f"def main():\n    print('built in {checkout}')\n")
            archive.writestr("tool-1.0.dist-info/METADATA", "Metadata-Version: 2.1\nName: tool\nVersion: 1.0\n")
            archive.writestr(
                "tool-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
            )
            archive.writestr("tool-1.0.dist-info/entry_points.txt", "[console_scripts]\ntool = tool:main\n")
            archive.writestr("tool-1.0.dist-info/RECORD", "")
    monkeypatch.chdir(tmp_path / "first")
    run_pipx_cli_exit(["run", *source_args, "tool"], assert_exit=0)
    monkeypatch.chdir(tmp_path / "second")
    capfd.readouterr()

    run_pipx_cli_exit(["run", *source_args, "tool"], assert_exit=0)

    assert capfd.readouterr().out.splitlines()[-1] == "built in second"


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_uv_dash_app_is_not_a_uv_option() -> None:
    # uv rejects the operand as a usage error instead of reading -n as --no-cache and running pycowsay
    run_pipx_cli_exit(["run", "--backend", "uv", "--", "-n", "pycowsay", "hi"], assert_exit=2)


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_with() -> None:
    run_pipx_cli_exit(["run", "--refresh", "--with", "black", "pycowsay", "--help"])

    assert list(paths.CTX.venv_cache.rglob("black-*.dist-info"))


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_with_cooldown(
    package_cache_dir: Path, empty_project_wheel: Path, caplog: pytest.LogCaptureFixture
) -> None:
    run_pipx_cli_exit(
        [
            "run",
            "--backend",
            "pip",
            "--cooldown",
            "7",
            "--with",
            str(empty_project_wheel),
            f"--pip-args=--no-index --find-links={package_cache_dir}",
            PKG["pycowsay"]["spec"],
            "hello",
        ],
        assert_exit=0,
    )

    assert (
        bool(list(paths.CTX.venv_cache.rglob("empty_project-*.dist-info"))),
        "--uploaded-prior-to P7D" in caplog.text,
    ) == (True, True)


@pytest.mark.parametrize("backend", [pytest.param("pip", id="pip"), pytest.param("uv", id="uv")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_run_with_pins_app_dependency(
    make_project_with_dependency: Callable[[str], Path], tmp_path: Path, mocker: MockerFixture, backend: str
) -> None:
    mocker.patch("os.execvpe", autospec=True, side_effect=SystemExit(0))

    run_pipx_cli_exit([
        "run",
        "--backend",
        backend,
        "--spec",
        str(make_wheel_in(make_project_with_dependency("black") / "pyproject.toml", tmp_path).file),
        "--with",
        "black==22.8.0",
        "empty-project",
    ])

    assert [path.name for path in paths.CTX.venv_cache.rglob("black-*.dist-info")] == ["black-22.8.0.dist-info"]


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_with_app_extra_exposes_nothing(local_extras_wheel: Path, mocker: MockerFixture) -> None:
    mocker.patch("os.execvpe", autospec=True, side_effect=SystemExit(0))

    run_pipx_cli_exit(["run", "--spec", str(local_extras_wheel), "--with", f"{local_extras_wheel}[cow]", "repeatme"])

    assert list(paths.CTX.bin_dir.iterdir()) == []


@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_run_with_cache(caplog: pytest.LogCaptureFixture) -> None:
    run_pipx_cli_exit(["run", "--refresh", "--with", "black", "pycowsay", "args"], assert_exit=0)

    caplog.set_level(logging.DEBUG)
    caplog.clear()
    run_pipx_cli_exit(["run", "--verbose", "--with", "black", "pycowsay", "args"], assert_exit=0)
    assert "Reusing cached venv" in caplog.text


def test_maybe_script_content_accepts_url_query_string(mocker: MockerFixture) -> None:
    mocker.patch("pipx.commands.run.download_script", autospec=True, return_value="print('hi')")

    assert maybe_script_content("https://example.invalid/tool.py?raw=1", is_path=False) == "print('hi')"


@pytest.mark.parametrize("command", [pytest.param("install", id="install"), pytest.param("run", id="run")])
@pytest.mark.usefixtures("pipx_temp_env", "exec_via_subprocess")
def test_script_url_cut_short_is_rejected(
    truncated_script_url: str, capsys: pytest.CaptureFixture[str], command: str
) -> None:
    assert run_pipx_cli([command, truncated_script_url]) == 1

    assert f"Script {truncated_script_url} ended 80 bytes short of its Content-Length." in " ".join(
        capsys.readouterr().err.split()
    )


@pytest.fixture
def truncated_script_url() -> Iterator[str]:
    with _serving(_TruncatingHandler) as port:
        yield f"http://127.0.0.1:{port}/tool.py"


class _TruncatingHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Length", "100")
        self.end_headers()
        self.wfile.write(b"print('first half')\n")
        self.close_connection = True

    def log_message(self, format: str, *args: object) -> None:  # ruff:ignore[builtin-argument-shadowing]  # overrides the stdlib signature
        pass


@pytest.mark.parametrize(
    ("first", "second"),
    [
        pytest.param((["black", "isort"], [], []), (["blackisort"], [], []), id="requirements"),
        pytest.param(([], ["-q", "--pre"], []), ([], ["-q--pre"], []), id="pip-short-options"),
        pytest.param(
            ([], ["--index-url", "https://example.invalid"], []),
            ([], ["--index-urlhttps://example.invalid"], []),
            id="pip-long-options",
        ),
        pytest.param(([], [], ["--upgrade", "--copies"]), ([], [], ["--upgrade--copies"]), id="venv-options"),
        pytest.param(
            ([], ["--system-site-packages"], []),
            ([], [], ["--system-site-packages"]),
            id="pip-venv-boundary",
        ),
        pytest.param(([], [""], []), ([], [], []), id="empty-argument"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_run_cache_keeps_argument_boundaries(
    cache_lock_path: Callable[[list[str], list[str], list[str]], Path],
    first: tuple[list[str], list[str], list[str]],
    second: tuple[list[str], list[str], list[str]],
) -> None:
    assert cache_lock_path(*first) != cache_lock_path(*second)


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_cache_key_is_stable(cache_lock_path: Callable[[list[str], list[str], list[str]], Path]) -> None:
    assert cache_lock_path(["black", "isort"], ["-q"], []) == cache_lock_path(["black", "isort"], ["-q"], [])


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        pytest.param("XDG_CONFIG_HOME", "/pipx-tests/config", id="xdg-config-home"),
        pytest.param("SSL_CERT_FILE", "/pipx-tests/ca.pem", id="ssl-cert-file"),
        pytest.param("HTTPS_PROXY", "http://proxy.invalid:3128", id="https-proxy"),
        pytest.param("https_proxy", "http://proxy.invalid:3128", id="https-proxy-lower-case"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_run_cache_key_follows_tool_env(
    cache_lock_path: Callable[[list[str], list[str], list[str]], Path],
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
    value: str,
) -> None:
    monkeypatch.delenv(variable, raising=False)
    first: Final[Path] = cache_lock_path(["black"], [], [])
    monkeypatch.setenv(variable, value)

    assert cache_lock_path(["black"], [], []) != first


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_cache_key_ignores_unrelated_env(
    cache_lock_path: Callable[[list[str], list[str], list[str]], Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    first: Final[Path] = cache_lock_path(["black"], [], [])
    monkeypatch.setenv("PIPX_TESTS_UNRELATED", "1")

    assert cache_lock_path(["black"], [], []) == first


@pytest.fixture
def cache_lock_path(mocker: MockerFixture) -> Callable[[list[str], list[str], list[str]], Path]:
    # stop at the filesystem boundary before installing conflicting argument sets
    lock: Final = mocker.patch("filelock.FileLock", autospec=True)
    # Python before 3.14 does not configure a dunder of an autospec through keyword arguments
    lock.return_value.__enter__.side_effect = OSError("cache lock unavailable")

    def capture(dependencies: list[str], pip_args: list[str], venv_args: list[str]) -> Path:
        with pytest.raises(OSError, match="cache lock unavailable"):
            run_package(
                "pycowsay",
                "pycowsay",
                dependencies,
                [],
                "python3",
                pip_args=pip_args,
                venv_args=venv_args,
                pypackages=False,
                verbose=False,
                use_cache=True,
                python_args=[],
                refresh=False,
                infer_app_name=False,
                backend=None,
                env_backend=None,
                resolved_backend="pip",
                no_path_check=True,
                cooldown_days=None,
            )
        return lock.call_args.args[0]

    return capture


@pytest.fixture
def plant_secret() -> Callable[[bytes], Path]:
    def plant(secret: bytes) -> Path:
        paths.CTX.venv_cache.mkdir(parents=True, exist_ok=True)
        secret_path: Final[Path] = paths.CTX.venv_cache / ".run-key"
        secret_path.write_bytes(secret)
        secret_path.chmod(0o600)
        return secret_path

    return plant


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_cache_name_depends_on_secret(
    cache_lock_path: Callable[[list[str], list[str], list[str]], Path], plant_secret: Callable[[bytes], Path]
) -> None:
    plant_secret(b"a" * 32)
    first: Final[Path] = cache_lock_path(["black"], [], [])
    plant_secret(b"b" * 32)

    assert cache_lock_path(["black"], [], []) != first


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_cache_name_is_stable_for_a_secret(
    cache_lock_path: Callable[[list[str], list[str], list[str]], Path], plant_secret: Callable[[bytes], Path]
) -> None:
    plant_secret(b"a" * 32)
    first: Final[Path] = cache_lock_path(["black"], [], [])
    plant_secret(b"b" * 32)
    other: Final[Path] = cache_lock_path(["black"], [], [])
    plant_secret(b"a" * 32)

    assert cache_lock_path(["black"], [], []) == first != other


@pytest.mark.skipif(sys.platform == "win32", reason="Windows keeps the secret private through profile ACLs")
@pytest.mark.usefixtures("pipx_temp_env")
def test_run_cache_secret_is_private(cache_lock_path: Callable[[list[str], list[str], list[str]], Path]) -> None:
    cache_lock_path(["black"], [], [])

    assert (paths.CTX.venv_cache / ".run-key").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    ("secret", "mode"),
    [
        pytest.param(b"a" * 32, 0o644, id="world-readable"),
        pytest.param(b"a" * 32, 0o640, id="group-readable"),
        pytest.param(b"short", 0o600, id="truncated"),
    ],
)
@pytest.mark.skipif(sys.platform == "win32", reason="Windows has no mode bits to check")
@pytest.mark.usefixtures("pipx_temp_env")
def test_run_cache_secret_replaces_unusable(
    cache_lock_path: Callable[[list[str], list[str], list[str]], Path],
    plant_secret: Callable[[bytes], Path],
    secret: bytes,
    mode: int,
) -> None:
    secret_path: Final[Path] = plant_secret(secret)
    secret_path.chmod(mode)
    cache_lock_path(["black"], [], [])

    assert secret_path.read_bytes() != secret


@pytest.mark.skipif(sys.platform == "win32", reason="Windows has no owner to check")
@pytest.mark.usefixtures("pipx_temp_env")
def test_run_cache_secret_replaces_foreign_owned(
    cache_lock_path: Callable[[list[str], list[str], list[str]], Path],
    plant_secret: Callable[[bytes], Path],
    mocker: MockerFixture,
) -> None:
    secret_path: Final[Path] = plant_secret(b"a" * 32)
    mocker.patch("os.geteuid", return_value=secret_path.stat().st_uid + 1)
    cache_lock_path(["black"], [], [])

    assert secret_path.read_bytes() != b"a" * 32


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_cache_secret_keeps_the_one_a_concurrent_run_wrote(
    cache_lock_path: Callable[[list[str], list[str], list[str]], Path],
    plant_secret: Callable[[bytes], Path],
    mocker: MockerFixture,
) -> None:
    plant_secret(b"a" * 32)
    expected: Final[Path] = cache_lock_path(["black"], [], [])
    plant_secret(b"b" * 32)
    own: Final[Path] = cache_lock_path(["black"], [], [])
    (paths.CTX.venv_cache / ".run-key").unlink()

    def concurrent_run_wins(size: int) -> bytes:
        plant_secret(b"a" * 32)
        return b"b" * size

    mocker.patch("secrets.token_bytes", side_effect=concurrent_run_wins)

    assert cache_lock_path(["black"], [], []) == expected != own


@pytest.mark.usefixtures("pipx_temp_env")
def test_run_cache_without_usable_secret_logs_fallback(
    cache_lock_path: Callable[[list[str], list[str], list[str]], Path],
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    mocker.patch("tempfile.mkstemp", side_effect=PermissionError(13, "Permission denied"))
    caplog.set_level(logging.DEBUG)
    cache_lock_path(["black"], [], [])

    assert "run cache names are not keyed with a secret" in caplog.text
