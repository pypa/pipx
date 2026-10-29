from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest
from platformdirs import user_cache_path, user_log_path

from helpers import SKIP_IF_WINDOWS
from pipx import paths

if TYPE_CHECKING:
    from collections.abc import Iterator
    from unittest.mock import MagicMock

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
    resolve: Final[MagicMock] = mocker.spy(Path, "resolve")
    paths.CTX.make_local()
    expected: Final[Path | None] = getattr(paths, override_name)
    assert expected is not None

    assert (
        getattr(paths.CTX, attribute),
        getattr(paths.CTX, attribute),
        sum(call.args[0] == expected for call in resolve.call_args_list),
    ) == (expected, expected, 1)


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_context_preserves_home_symlink(without_pipx_home: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target: Final[Path] = tmp_path / "target"
    target.mkdir()
    home: Final[Path] = tmp_path / "home"
    home.symlink_to(target, target_is_directory=True)
    without_pipx_home.setenv("PIPX_HOME", str(home))
    paths.CTX.make_local()

    assert (paths.CTX.home, paths.CTX.venvs) == (home, home / "venvs")


@pytest.fixture
def without_pipx_home(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    with monkeypatch.context() as scoped:
        scoped.setattr(paths, "OVERRIDE_PIPX_HOME", None)
        scoped.delenv("PIPX_HOME", raising=False)
        yield scoped
    paths.CTX.make_local()


@pytest.mark.usefixtures("pipx_temp_env")
def test_context_keeps_cache_and_logs_out_of_fallback_home(
    without_pipx_home: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fallback: Final[Path] = tmp_path / "legacy"
    fallback.mkdir()
    without_pipx_home.setattr(paths, "FALLBACK_PIPX_HOMES", [fallback])
    paths.CTX.make_local()

    assert (paths.CTX.home, paths.CTX.venv_cache, paths.CTX.logs, paths.CTX.trash) == (
        fallback,
        user_cache_path("pipx"),
        user_log_path("pipx"),
        fallback / ".trash",
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_context_keeps_cache_and_logs_inside_explicit_home(
    without_pipx_home: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home: Final[Path] = tmp_path / "home"
    without_pipx_home.setenv("PIPX_HOME", str(home))
    paths.CTX.make_local()

    assert (paths.CTX.venv_cache, paths.CTX.logs) == (home / ".cache", home / "logs")


@pytest.mark.usefixtures("pipx_temp_env")
def test_context_uses_platform_dirs_without_any_home(without_pipx_home: pytest.MonkeyPatch, tmp_path: Path) -> None:
    default: Final[Path] = tmp_path / "default"
    without_pipx_home.setattr(paths, "FALLBACK_PIPX_HOMES", [tmp_path / "absent"])
    without_pipx_home.setattr(paths, "DEFAULT_PIPX_HOME", default)
    paths.CTX.make_local()

    assert (paths.CTX.home, paths.CTX.venv_cache, paths.CTX.logs) == (
        default,
        user_cache_path("pipx"),
        user_log_path("pipx"),
    )


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_context_honors_xdg_cache_home(without_pipx_home: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache: Final[Path] = tmp_path / "xdg-cache"
    without_pipx_home.setattr(paths, "FALLBACK_PIPX_HOMES", [tmp_path / "absent"])
    without_pipx_home.setenv("XDG_CACHE_HOME", str(cache))
    paths.CTX.make_local()

    assert paths.CTX.venv_cache == cache / "pipx"
