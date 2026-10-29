from __future__ import annotations

import json
import shutil
import subprocess
from typing import TYPE_CHECKING, Final

import pytest

from helpers import SKIP_IF_WINDOWS, app_name, file_or_symlink, mock_legacy_venv, run_pipx_cli, write_wheel
from package_info import PKG
from pipx import paths
from pipx.commands import common
from pipx.constants import WINDOWS
from pipx.redact import redact_url_credentials
from pipx.wrap import pipx_wrap

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture


@pytest.mark.usefixtures("installed_pycowsay")
def test_uninject_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["uninject", "--output", "json", "pycowsay", "black"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["uninject"],
            "data": {
                "packages": [
                    {
                        "environment": "pycowsay",
                        "location": str(paths.CTX.venvs / "pycowsay"),
                        "package": "black",
                        "status": "uninjected",
                        "version": "22.8.0",
                    }
                ],
                "skipped": [],
            },
            "pipx_result_version": "1",
            "errors": [],
            "exit_code": 0,
            "status": "success",
        },
        "",
    )


@pytest.mark.usefixtures("installed_pycowsay")
def test_uninject_json_reports_unknown_package(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["uninject", "--output", "json", "pycowsay", "missing"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["uninject"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_uninject_failed",
                    "environment": "pycowsay",
                    "message": "missing is not in the pycowsay venv. Skipping.",
                    "package": "missing",
                }
            ],
            "exit_code": 1,
            "pipx_result_version": "1",
            "status": "error",
        },
        "",
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_json_reports_missing_environment(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["uninject", "--output", "json", "missing", "black"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["uninject"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_uninject_failed",
                    "environment": "missing",
                    "message": "Virtual environment missing does not exist.",
                    "package": None,
                }
            ],
            "exit_code": 1,
            "pipx_result_version": "1",
            "status": "error",
        },
        "",
    )


@pytest.mark.usefixtures("installed_pycowsay")
def test_uninject_json_reports_missing_metadata(capsys: pytest.CaptureFixture[str]) -> None:
    mock_legacy_venv("pycowsay")

    assert run_pipx_cli(["uninject", "--output", "json", "pycowsay", "black"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["uninject"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_uninject_failed",
                    "environment": "pycowsay",
                    "message": pipx_wrap(
                        """
                        Can't uninject from Virtual Environment 'pycowsay'.
                        'pycowsay' has no internal pipx metadata.
                        pipx versions before 0.15.0.0 did not record it.
                        Uninstall and install 'pycowsay' manually to fix it.
                        """
                    ),
                    "package": None,
                }
            ],
            "exit_code": 1,
            "pipx_result_version": "1",
            "status": "error",
        },
        "",
    )


@pytest.mark.usefixtures("installed_pycowsay")
def test_uninject_json_reports_main_package(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["uninject", "--output", "json", "pycowsay", "pycowsay"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["uninject"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_uninject_failed",
                    "environment": "pycowsay",
                    "message": pipx_wrap(
                        """
                        pycowsay is the main package of pycowsay
                        venv. Use `pipx uninstall pycowsay` to uninstall instead of uninject.
                        """,
                        subsequent_indent=" " * 4,
                    ),
                    "package": "pycowsay",
                }
            ],
            "exit_code": 1,
            "pipx_result_version": "1",
            "status": "error",
        },
        "",
    )


@pytest.mark.usefixtures("installed_pycowsay")
def test_uninject_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["inject", "pycowsay", "black"])
    capsys.readouterr()

    assert not run_pipx_cli(["uninject", "-qq", "pycowsay", "black"])

    assert "Uninjected package" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "scope",
    [
        pytest.param([], id="user"),
        pytest.param(["--global"], id="global", marks=SKIP_IF_WINDOWS),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_simple(capsys: pytest.CaptureFixture[str], scope: list[str]) -> None:
    assert not run_pipx_cli(["install", *scope, "pycowsay"])
    assert not run_pipx_cli(["inject", *scope, "pycowsay", PKG["black"]["spec"]])

    assert not run_pipx_cli(["uninject", *scope, "pycowsay", "black"])

    uninject_output: Final[str] = capsys.readouterr().out
    assert not run_pipx_cli(["list", *scope, "--include-injected"])
    assert ("Uninjected package black" in uninject_output, "black" in capsys.readouterr().out) == (True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_with_include_apps(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"], "--include-deps", "--include-apps"])
    assert not run_pipx_cli(["uninject", "pycowsay", "black", "--verbose"])
    assert "removed file" in caplog.text


@pytest.mark.skipif(not WINDOWS, reason="Windows-specific test")
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_running_app() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"], "--include-apps"])
    app: Final[Path] = paths.CTX.bin_dir / app_name("black")

    # the context manager closes the three pipes; leaking them trips the ResourceWarning that filterwarnings errors on
    with subprocess.Popen(
        [app, "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        try:
            assert process.poll() is None
            assert not run_pipx_cli(["uninject", "pycowsay", "black"])
            assert not app.exists()
        finally:
            process.terminate()
            process.wait(timeout=10)


@pytest.mark.parametrize(
    "suffix",
    [
        pytest.param("@1", id="canonical"),
        pytest.param("_x", id="non-canonical"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_with_suffix_removes_apps(
    empty_project_wheel: Path,
    local_extras_wheel: Path,
    suffix: str,
) -> None:
    assert not run_pipx_cli(["install", str(empty_project_wheel), f"--suffix={suffix}"])
    assert not run_pipx_cli([
        "inject",
        f"empty-project{suffix}",
        f"{local_extras_wheel}[cow]",
        "--include-deps",
        "--with-suffix",
    ])
    app_paths: Final[set[Path]] = {paths.CTX.bin_dir / app_name(f"{app}{suffix}") for app in ("pycowsay", "repeatme")}
    assert all(file_or_symlink(path) for path in app_paths)

    assert not run_pipx_cli(["uninject", f"empty-project{suffix}", f"repeatme{suffix}"])

    assert not any(file_or_symlink(path) for path in app_paths)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_man_page() -> None:
    # pycowsay ships man6/pycowsay.6
    man_page_paths: Final[list[Path]] = [paths.CTX.man_dir / man_page for man_page in PKG["pycowsay"]["man_pages"]]
    assert not run_pipx_cli(["install", PKG["black"]["spec"]])
    assert not run_pipx_cli(["inject", "black", "pycowsay", "--include-apps"])
    assert all(path.exists() for path in man_page_paths)

    assert not run_pipx_cli(["uninject", "black", "pycowsay"])

    assert not any(file_or_symlink(path) for path in man_page_paths)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_completion_scripts(local_completion_wheel: Path, empty_project_wheel: Path) -> None:
    completion_paths: Final[list[Path]] = [
        paths.CTX.completion_dir / "bash-completion/completions" / "local-completion",
        paths.CTX.completion_dir / "zsh/site-functions" / "_local-completion",
        paths.CTX.completion_dir / "fish/vendor_completions.d" / "local-completion.fish",
    ]
    assert not run_pipx_cli(["install", str(empty_project_wheel)])
    assert not run_pipx_cli(["inject", "empty-project", str(local_completion_wheel), "--include-apps"])
    assert all(file_or_symlink(path) for path in completion_paths)

    assert not run_pipx_cli(["uninject", "empty-project", "local-completion"])

    assert not any(file_or_symlink(path) for path in completion_paths)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_removes_dependency_app_symlinks(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "requests==2.31.0", "--include-deps", "--include-apps"])
    assert "normalizer" in capsys.readouterr().out

    assert not run_pipx_cli(["uninject", "pycowsay", "requests", "--verbose"])

    assert ("removed file" in caplog.text, "normalizer" in caplog.text) == (True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_removes_selected_dependency_resources(
    local_extras_wheel: Path,
    empty_project_wheel: Path,
) -> None:
    package: Final[str] = f"{local_extras_wheel}[tools]"
    assert not run_pipx_cli(["install", str(empty_project_wheel)])
    assert not run_pipx_cli(["inject", "empty-project", package, "--include-resources-from", "pycowsay"])
    exposed_paths: Final[tuple[Path, ...]] = (
        paths.CTX.bin_dir / app_name("repeatme"),
        paths.CTX.bin_dir / app_name("pycowsay"),
        paths.CTX.man_dir / "man6" / "pycowsay.6",
    )
    assert all(file_or_symlink(path) for path in exposed_paths)

    assert not run_pipx_cli(["uninject", "empty-project", "repeatme"])

    assert not any(file_or_symlink(path) for path in exposed_paths)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_keeps_resources_the_main_package_exposes(local_extras_wheel: Path) -> None:
    assert not run_pipx_cli(["install", "pycowsay==0.0.0.2"])
    assert not run_pipx_cli([
        "inject",
        "pycowsay",
        f"{local_extras_wheel}[cow]",
        "--include-resources-from",
        "pycowsay",
    ])

    assert not run_pipx_cli(["uninject", "pycowsay", "repeatme"])

    assert all(
        file_or_symlink(path)
        for path in (paths.CTX.bin_dir / app_name("pycowsay"), paths.CTX.man_dir / "man6" / "pycowsay.6")
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_leave_deps(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["uninject", "pycowsay", "black", "--leave-deps", "--verbose"])

    assert (
        "Uninjected package black from venv pycowsay" in capsys.readouterr().out,
        "Dependencies of uninstalled package:" in caplog.text,
    ) == (True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_preserves_shared_deps(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["pylint"]["spec"]])

    assert not run_pipx_cli(["uninject", "pycowsay", "black"])

    capsys.readouterr()
    assert not run_pipx_cli(["list", "--include-injected"])
    listed: Final[str] = capsys.readouterr().out
    assert ("pylint" in listed, "black" in listed) == (True, False)


@pytest.mark.usefixtures("installed_pycowsay")
def test_uninject_editable_removes_its_dependencies(tmp_path: Path) -> None:
    # a src layout puts the project's own egg-info on the venv's search path until the uninstall drops its .pth
    (tmp_path / "src" / "editable_dep").mkdir(parents=True)
    (tmp_path / "src" / "editable_dep" / "__init__.py").touch()
    (tmp_path / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n\n'
        '[project]\nname = "editable-dep"\nversion = "0.1"\ndependencies = ["six"]\n',
        encoding="utf-8",
    )
    assert not run_pipx_cli(["inject", "pycowsay", "--editable", str(tmp_path)])

    assert not run_pipx_cli(["uninject", "pycowsay", "editable-dep"])

    assert not list((paths.CTX.venvs / "pycowsay").rglob("six-*.dist-info"))


@pytest.mark.parametrize(
    "backend",
    [
        pytest.param("pip", id="pip"),
        pytest.param(
            "uv", id="uv", marks=pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_removes_all_orphaned_dependencies(backend: str) -> None:
    assert not run_pipx_cli(["install", "pycowsay", "--backend", backend])
    venv_dir: Final[Path] = paths.CTX.venvs / "pycowsay"
    installed_before: Final[set[str]] = {path.name for path in venv_dir.rglob("*.dist-info")}
    assert not run_pipx_cli(["inject", "pycowsay", "requests==2.31.0"])

    assert not run_pipx_cli(["uninject", "pycowsay", "requests"])

    assert {path.name for path in venv_dir.rglob("*.dist-info")} == installed_before


@pytest.mark.usefixtures("installed_pycowsay")
def test_uninject_reports_failed_dependency_uninstall(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["inject", "pycowsay", "requests==2.31.0"])
    capsys.readouterr()
    # pip refuses to uninstall a distribution without a RECORD file
    next((paths.CTX.venvs / "pycowsay").rglob("urllib3-*.dist-info/RECORD")).unlink()

    assert run_pipx_cli(["uninject", "pycowsay", "requests"])

    assert "Error uninstalling certifi, charset-normalizer, idna, urllib3." in capsys.readouterr().err


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_removes_copied_app_named_before_last_dot(
    mocker: MockerFixture, empty_project_wheel: Path, dotted_app_wheel: Path
) -> None:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    assert not run_pipx_cli(["install", str(empty_project_wheel), "--suffix=@1"])
    assert not run_pipx_cli(["inject", "empty-project@1", str(dotted_app_wheel), "--include-apps", "--with-suffix"])
    # the name pipx 1.17.14 gave the app, with the suffix before the last dot
    legacy: Final[Path] = (paths.CTX.bin_dir / "tool.12@1").rename(paths.CTX.bin_dir / "tool@1.12")

    assert not run_pipx_cli(["uninject", "empty-project@1", "foo-bar-x@1"])

    assert not legacy.exists()


@pytest.mark.usefixtures("installed_pycowsay")
def test_uninject_unknown_package_hides_url_credentials(capsys: pytest.CaptureFixture[str]) -> None:
    masked: Final[str] = redact_url_credentials("git+https://u:s3cr3ttok@host/org/plugin-git")

    assert run_pipx_cli(["uninject", "--output", "json", "pycowsay", "git+https://u:s3cr3ttok@host/org/plugin.git"])

    assert json.loads(capsys.readouterr().out)["errors"] == [
        {
            "code": "package_uninject_failed",
            "environment": "pycowsay",
            "message": f"{masked} is not in the pycowsay venv. Skipping.",
            "package": masked,
        }
    ]


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninject_keeps_an_app_name_taken_over_during_the_uninstall(
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None], tmp_path: Path
) -> None:
    assert not run_pipx_cli(["install", str(write_wheel(tmp_path / "wheels", "alpha", "1"))])
    assert not run_pipx_cli(["inject", "alpha", str(write_wheel(tmp_path / "wheels", "beta", "1")), "--include-apps"])
    beta: Final[Path] = paths.CTX.bin_dir / "beta"
    (other := tmp_path / "other").touch()

    def take_over_dangling_name() -> None:
        if not beta.exists():
            beta.unlink()
            beta.symlink_to(other)

    before_venv_subprocess(paths.CTX.venvs / "alpha", take_over_dangling_name)

    assert not run_pipx_cli(["uninject", "alpha", "beta"])

    assert beta.resolve() == other.resolve()
