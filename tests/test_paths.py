from pathlib import Path
from typing import Final

import pytest
from pytest_mock import MockerFixture

from helpers import skip_if_windows
from pipx import paths


@pytest.mark.parametrize(
    ("attribute", "override_name"),
    [
        pytest.param("bin_dir", "OVERRIDE_PIPX_BIN_DIR", id="bin"),
        pytest.param("man_dir", "OVERRIDE_PIPX_MAN_DIR", id="man"),
        pytest.param("shared_libs", "OVERRIDE_PIPX_SHARED_LIBS", id="shared"),
    ],
)
def test_context_resolves_base_path_once(
    pipx_temp_env: None,
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
def test_context_preserves_home_symlink(
    pipx_temp_env: None,
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
