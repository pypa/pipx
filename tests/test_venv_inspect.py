from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from packaging.utils import canonicalize_name

from pipx import venv_inspect

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


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
        return_value=([str(site_packages)], {"python_full_version": "3.10.0"}, "3.10.0"),
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
        return_value=([str(site_packages)], {"python_full_version": "3.10.0"}, "3.10.0"),
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


@pytest.mark.parametrize("reverse", [False, True], ids=["first-second", "second-first"])
@pytest.mark.parametrize("graph", ["diamond", "base-first", "cycle", "root-extra"])
def test_inspect_venv_combines_dependency_extras(
    tmp_path: Path, mocker: MockerFixture, graph: str, *, reverse: bool
) -> None:
    site_packages = tmp_path / "site-packages"
    dependencies = ("left", "right") if not reverse else ("right", "left")
    if graph == "base-first":
        dependencies = ("shared", *dependencies)
    if graph == "root-extra":
        dependencies = (*dependencies, 'third-app; extra == "other"')
    _write_dist_info(site_packages, "root", dependencies)
    _write_dist_info(site_packages, "left", ("shared[first]",))
    _write_dist_info(site_packages, "right", ("shared[second]",))
    requirements = ('first-app; extra == "first"', 'second-app; extra == "second"')
    if graph == "cycle":
        requirements = (*requirements, "root")
    if graph == "root-extra":
        requirements = (*requirements, "root[other]")
    _write_dist_info(site_packages, "shared", requirements)
    bin_path = tmp_path / "bin"
    bin_path.mkdir()
    apps = ("first-app", "second-app", "third-app") if graph == "root-extra" else ("first-app", "second-app")
    for name in apps:
        _write_dist_info(site_packages, name)
    for name in ("root", *apps):
        (site_packages / f"{name}-1.0.dist-info" / "entry_points.txt").write_text(
            f"[console_scripts]\n{name} = app:main\n", encoding="utf-8"
        )
        (bin_path / name).touch()
    man_path = tmp_path / "share" / "man"
    manual = man_path / "man1" / "second-app.1"
    completion = tmp_path / "share" / "bash-completion" / "completions" / "second-app"
    for resource in (manual, completion):
        resource.parent.mkdir(parents=True)
        resource.touch()
    (site_packages / "second-app-1.0.dist-info" / "RECORD").write_text(
        "../share/man/man1/second-app.1,,\n../share/bash-completion/completions/second-app,,\n", encoding="utf-8"
    )
    mocker.patch.object(
        venv_inspect,
        "fetch_info_in_venv",
        autospec=True,
        return_value=([str(site_packages)], {"python_full_version": "3.13.0"}, "3.13.0"),
    )

    result = venv_inspect.inspect_venv("root", set(), bin_path, tmp_path / "python", man_path)

    assert result.apps == ["root"]
    assert sorted(result.apps_of_dependencies) == list(apps)
    assert result.man_paths_of_dependencies == {"second-app": [manual]}
    assert result.completion_paths_of_dependencies == {"second-app": [completion]}
