from pipx.pipx_metadata_file import PipxMetadata, PackageInfo


# test to make sure we never have duplicate injected packages
#   this might happen during reinstall_all if we don't properly uninstall
#       injected packages or don't remove their metadata


def test_pipx_metadata_file_create(tmp_path):
    venv_temp = tmp_path / "venv1"
    pipx_metadata = PipxMetadata(venv_temp)
    package_info = PackageInfo(
        package="test_package",
        package_or_url="test_package_url",
        pip_args=[],
        include_apps=True,
        include_dependencies=True,
        apps=[],
        app_paths=[],
        apps_of_dependencies=[],
        app_paths_of_dependencies=[],
        package_version="0.0.0",
    )
