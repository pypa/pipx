import pytest  # type: ignore

from helpers import mock_legacy_venv, run_pipx_cli
from package_info import PKG


def test_inject_simple(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])


def test_inject_simple_global(pipx_temp_env, capsys):
    assert not run_pipx_cli(["--global", "install", "pycowsay"])
    assert not run_pipx_cli(["--global", "inject", "pycowsay", PKG["black"]["spec"]])


@pytest.mark.parametrize("metadata_version", [None, "0.1"])
def test_inject_simple_legacy_venv(pipx_temp_env, capsys, metadata_version):
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    if metadata_version is not None:
        assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    else:
        # no metadata in venv should result in PipxError with message
        assert run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
        assert "Please uninstall and install" in capsys.readouterr().err


def test_inject_tricky_character(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "jaraco.clipboard==2.0.1"])


def test_spec(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "pylint==2.3.1"])


@pytest.mark.parametrize("with_suffix,", [(False,), (True,)])
def test_inject_include_apps(pipx_temp_env, capsys, with_suffix):
    install_args = []
    suffix = ""

    if with_suffix:
        suffix = "_x"
        install_args = [f"--suffix={suffix}"]

    assert not run_pipx_cli(["install", "pycowsay", *install_args])
    assert run_pipx_cli(
        ["inject", f"pycowsay{suffix}", PKG["black"]["spec"], "--include-deps"]
    )

    if suffix:
        assert run_pipx_cli(
            [
                "inject",
                "pycowsay",
                PKG["black"]["spec"],
                "--include-deps",
                "--include-apps",
            ]
        )

    assert not run_pipx_cli(
        [
            "inject",
            f"pycowsay{suffix}",
            PKG["black"]["spec"],
            "--include-deps",
            "--include-apps",
        ]
    )
