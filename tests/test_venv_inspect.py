import os
from pathlib import Path

from packaging.utils import canonicalize_name
from pytest_mock import MockerFixture

from pipx import venv_inspect


def _write_dist_info(site_packages: Path, name: str, requirements: tuple[str, ...] = ()) -> None:
    dist_info = site_packages / f"{canonicalize_name(name)}-1.0.dist-info"
    dist_info.mkdir(parents=True)
    metadata = [f"Name: {name}", "Version: 1.0"]
    metadata.extend(f"Requires-Dist: {requirement}" for requirement in requirements)
    (dist_info / "METADATA").write_text("\n".join(metadata), encoding="utf-8")


def test_inspect_venv_indexes_distribution_names_once(tmp_path: Path, mocker: MockerFixture) -> None:
    site_packages = tmp_path / "site-packages"
    _write_dist_info(site_packages, "Root_Package", ("dependency-package",))
    _write_dist_info(site_packages, "Dependency_Package")
    nameless_dist_info = site_packages / "nameless-1.0.dist-info"
    nameless_dist_info.mkdir()
    (nameless_dist_info / "METADATA").write_text("Version: 1.0\n", encoding="utf-8")
    mocker.patch.object(
        venv_inspect,
        "fetch_info_in_venv",
        autospec=True,
        return_value=([str(site_packages)], {}, "Python 3.10.0"),
    )
    canonicalize = mocker.spy(venv_inspect, "canonicalize_name")

    result = venv_inspect.inspect_venv(
        "root-package",
        set(),
        tmp_path / "bin",
        tmp_path / "python",
        tmp_path / "man",
    )

    assert result.package_version == "1.0"
    assert [call.args[0] for call in canonicalize.call_args_list].count("Root_Package") == 1
    assert [call.args[0] for call in canonicalize.call_args_list].count("Dependency_Package") == 1


def test_inspect_venv_refreshes_distribution_paths(tmp_path: Path, mocker: MockerFixture) -> None:
    site_packages = tmp_path / "site-packages"
    _write_dist_info(site_packages, "root-package")
    mocker.patch.object(
        venv_inspect,
        "fetch_info_in_venv",
        autospec=True,
        return_value=([str(site_packages)], {}, "Python 3.10.0"),
    )
    args: tuple[str, set[str], Path, Path, Path] = (
        "root-package",
        set(),
        tmp_path / "bin",
        tmp_path / "python",
        tmp_path / "man",
    )

    assert venv_inspect.inspect_venv(*args).package_version == "1.0"

    site_packages_stat = site_packages.stat()
    _write_dist_info(site_packages, "dependency-package")
    (site_packages / "root-package-1.0.dist-info" / "METADATA").write_text(
        "Name: root-package\nVersion: 1.0\nRequires-Dist: dependency-package\n",
        encoding="utf-8",
    )
    os.utime(site_packages, ns=(site_packages_stat.st_atime_ns, site_packages_stat.st_mtime_ns))

    assert venv_inspect.inspect_venv(*args).package_version == "1.0"
