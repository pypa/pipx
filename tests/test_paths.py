from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from pipx import paths


@pytest.mark.parametrize(
    ("attribute", "override_name"),
    [
        pytest.param("home", "OVERRIDE_PIPX_HOME", id="home"),
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
