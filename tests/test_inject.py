import pytest  # type: ignore

from helpers import mock_legacy_venv, run_pipx_cli


def test_simple(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black"])


@pytest.mark.parametrize("metadata_version", [None, "0.1"])
def test_simple_legacy_venv(pipx_temp_env, capsys, metadata_version):
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    assert not run_pipx_cli(["inject", "pycowsay", "black"])


def test_spec(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "pylint==2.3.1"])


@pytest.mark.parametrize("with_suffix,", [(False,), (True,)])
def test_include_apps(pipx_temp_env, capsys, with_suffix):
    install_args = []
    suffix = ""

    if with_suffix:
        suffix = "_x"
        install_args = [f"--suffix={suffix}"]

    assert not run_pipx_cli(["install", "pycowsay", *install_args])
    assert run_pipx_cli(["inject", f"pycowsay{suffix}", "black", "--include-deps"])

    if suffix:
        assert run_pipx_cli(
            ["inject", "pycowsay", "black", "--include-deps", "--include-apps"]
        )

    assert not run_pipx_cli(
        ["inject", f"pycowsay{suffix}", "black", "--include-deps", "--include-apps"]
    )
