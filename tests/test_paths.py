from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest
from platformdirs import user_cache_path, user_log_path

from helpers import skip_if_windows
from pipx import paths

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    ("attribute", "override_name"),
    [
        pytest.param("bin_dir", "OVERRIDE_PIPX_BIN_DIR", id="bin"),
        pytest.param("man_dir", "OVERRIDE_PIPX_MAN_DIR", id="man"),
        pytest.param("shared_libs", "OVERRIDE_PIPX_SHARED_LIBS", id="shared"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_context_resolves_base_path_once(
    mocker: MockerFixture,
    attribute: str,
    override_name: str,
) -> None:
    resolve = mocker.spy(Path, "resolve")
    paths.ctx.make_local()
    expected = getattr(paths, override_name)
    assert expected is not None

    assert (getattr(paths.ctx, attribute), getattr(paths.ctx, attribute)) == (expected, expected)
    assert sum(call.args[0] == expected for call in resolve.call_args_list) == 1


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_context_preserves_home_symlink(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target: Final[Path] = tmp_path / "target"
    target.mkdir()
    home: Final[Path] = tmp_path / "home"
    home.symlink_to(target, target_is_directory=True)
    with monkeypatch.context() as scoped:
        scoped.setattr(paths, "OVERRIDE_PIPX_HOME", None)
        scoped.setenv("PIPX_HOME", str(home))
        paths.ctx.make_local()

        assert (paths.ctx.home, paths.ctx.venvs) == (home, home / "venvs")

    paths.ctx.make_local()


@pytest.mark.usefixtures("pipx_temp_env")
def test_context_keeps_cache_and_logs_out_of_fallback_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fallback: Final[Path] = tmp_path / "legacy"
    fallback.mkdir()
    with monkeypatch.context() as scoped:
        scoped.setattr(paths, "OVERRIDE_PIPX_HOME", None)
        scoped.delenv("PIPX_HOME", raising=False)
        scoped.setattr(paths, "FALLBACK_PIPX_HOMES", [fallback])
        paths.ctx.make_local()

        assert (paths.ctx.home, paths.ctx.venv_cache, paths.ctx.logs, paths.ctx.trash) == (
            fallback,
            Path(user_cache_path("pipx")),
            Path(user_log_path("pipx")),
            fallback / ".trash",
        )

    paths.ctx.make_local()


@pytest.mark.usefixtures("pipx_temp_env")
def test_context_keeps_cache_and_logs_inside_explicit_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    home: Final[Path] = tmp_path / "home"
    with monkeypatch.context() as scoped:
        scoped.setattr(paths, "OVERRIDE_PIPX_HOME", None)
        scoped.setenv("PIPX_HOME", str(home))
        paths.ctx.make_local()

        assert (paths.ctx.venv_cache, paths.ctx.logs) == (home / ".cache", home / "logs")

    paths.ctx.make_local()


@pytest.mark.usefixtures("pipx_temp_env")
def test_context_uses_platform_dirs_without_any_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    default: Final[Path] = tmp_path / "default"
    with monkeypatch.context() as scoped:
        scoped.setattr(paths, "OVERRIDE_PIPX_HOME", None)
        scoped.delenv("PIPX_HOME", raising=False)
        scoped.setattr(paths, "FALLBACK_PIPX_HOMES", [tmp_path / "absent"])
        scoped.setattr(paths, "DEFAULT_PIPX_HOME", default)
        paths.ctx.make_local()

        assert (paths.ctx.home, paths.ctx.venv_cache, paths.ctx.logs) == (
            default,
            Path(user_cache_path("pipx")),
            Path(user_log_path("pipx")),
        )

    paths.ctx.make_local()


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_context_honors_xdg_cache_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cache: Final[Path] = tmp_path / "xdg-cache"
    with monkeypatch.context() as scoped:
        scoped.setattr(paths, "OVERRIDE_PIPX_HOME", None)
        scoped.delenv("PIPX_HOME", raising=False)
        scoped.setattr(paths, "FALLBACK_PIPX_HOMES", [tmp_path / "absent"])
        scoped.setenv("XDG_CACHE_HOME", str(cache))
        paths.ctx.make_local()

        assert paths.ctx.venv_cache == cache / "pipx"

    paths.ctx.make_local()
