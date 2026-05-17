from helpers import run_pipx_cli, skip_if_windows
from package_info import PKG
from pipx import paths
from pipx.commands.run_pip import _main_package_install_spec
from pipx.pipx_metadata_file import PipxMetadata


def test_runpip_main_package_install_spec_handles_options():
    assert (
        _main_package_install_spec(
            [
                "install",
                "--force-reinstall",
                "--index-url",
                "https://example.invalid/simple",
                PKG["pycowsay"]["spec"],
            ],
            "pycowsay",
        )
        == PKG["pycowsay"]["spec"]
    )


def test_runpip(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["runpip", "pycowsay", "list"])


def test_runpip_splits_single_argument(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["runpip", "pycowsay", "list --format=freeze"])


def test_runpip_install_refreshes_main_package_metadata(pipx_temp_env, tmp_path):
    local_project = tmp_path / "local-pycowsay"
    local_project.mkdir()
    (local_project / "pyproject.toml").write_text(
        """
[build-system]
build-backend = "setuptools.build_meta"
requires = ["setuptools"]

[project]
name = "pycowsay"
version = "0.0.0.1"

[project.scripts]
pycowsay = "pycowsay_local:main"
""".lstrip(),
        encoding="utf-8",
    )
    (local_project / "pycowsay_local.py").write_text(
        """
def main():
    pass
""".lstrip(),
        encoding="utf-8",
    )

    assert not run_pipx_cli(["install", "--editable", local_project.as_posix()])

    metadata = PipxMetadata(paths.ctx.venvs / "pycowsay")
    initial_main_package = metadata.main_package
    assert initial_main_package.package_or_url == local_project.as_posix()
    assert "--editable" in initial_main_package.pip_args

    assert not run_pipx_cli(["runpip", "pycowsay", "install", PKG["pycowsay"]["spec"], "--force-reinstall"])

    metadata = PipxMetadata(paths.ctx.venvs / "pycowsay")
    updated_main_package = metadata.main_package
    assert updated_main_package.package_or_url == PKG["pycowsay"]["spec"]
    assert updated_main_package.package_version == PKG["pycowsay"]["spec"].split("==")[-1]
    assert updated_main_package.pip_args == []
    assert updated_main_package.include_apps == initial_main_package.include_apps
    assert updated_main_package.include_dependencies == initial_main_package.include_dependencies
    assert updated_main_package.pinned == initial_main_package.pinned


@skip_if_windows
def test_runpip_global(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", "--global", "pycowsay"])
    assert not run_pipx_cli(["runpip", "--global", "pycowsay", "list"])
