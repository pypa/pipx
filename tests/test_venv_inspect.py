from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from packaging.utils import canonicalize_name

from helpers import skip_if_windows
from pipx import venv_inspect

if TYPE_CHECKING:
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


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("-t/some/dir", id="target-option"),
        pytest.param("-rdrop", id="requirement-option"),
        pytest.param("../escape", id="path"),
        pytest.param("a b", id="space"),
    ],
)
def test_not_required_packages_skips_invalid_distribution_names(tmp_path: Path, name: str) -> None:
    _write_dist_info(tmp_path, "top-package")
    (egg_info := tmp_path / "extra.egg-info").mkdir()
    (egg_info / "PKG-INFO").write_text(f"Name: {name}\nVersion: 1.0\n", encoding="utf-8")

    assert venv_inspect.not_required_packages([str(tmp_path)], {}) == {"top-package"}


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


def test_inspect_venv_reads_first_record_of_a_name_on_sys_path(tmp_path: Path, mocker: MockerFixture) -> None:
    site_packages = tmp_path / "site-packages"
    _write_dist_info(site_packages, "root-package")
    later = tmp_path / "base-site-packages" / "root_package-99.dist-info"
    later.mkdir(parents=True)
    (later / "METADATA").write_text("Name: root-package\nVersion: 99\n", encoding="utf-8")
    mocker.patch.object(
        venv_inspect,
        "fetch_info_in_venv",
        autospec=True,
        return_value=([str(site_packages), str(later.parent)], {"python_full_version": "3.10.0"}, "3.10.0"),
    )

    result = venv_inspect.inspect_venv("root-package", set(), tmp_path / "bin", tmp_path / "python", tmp_path / "man")

    assert result.package_version == "1.0"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("man/inside.1", [str(Path("man1") / "inside.1")], id="inside"),
        pytest.param("{outside}", [], id="absolute-outside"),
        pytest.param("../outside.1", [], id="parent-outside"),
    ],
)
def test_inspect_venv_copies_editable_man_pages_only_from_the_project(
    editable_project: Path, source: str, expected: list[str]
) -> None:
    source = source.format(outside=editable_project.parent / "outside.1")

    assert _inspect_editable_man_pages(editable_project, source) == expected


@skip_if_windows
@pytest.mark.parametrize(
    "target",
    [
        pytest.param("../../outside.1", id="out-of-the-project"),
        pytest.param("link.1", id="symlink-loop"),
    ],
)
def test_inspect_venv_skips_editable_man_page_symlink(editable_project: Path, target: str) -> None:
    (editable_project / "man" / "link.1").symlink_to(target)

    assert _inspect_editable_man_pages(editable_project, "man/link.1") == []


@pytest.fixture
def editable_project(tmp_path: Path, mocker: MockerFixture) -> Path:
    project = tmp_path / "project"
    (project / "man").mkdir(parents=True)
    (project / "man" / "inside.1").touch()
    (tmp_path / "outside.1").touch()
    site_packages = tmp_path / "site-packages"
    _write_dist_info(site_packages, "root-package")
    (site_packages / "root-package-1.0.dist-info" / "direct_url.json").write_text(
        json.dumps({"url": project.as_uri(), "dir_info": {"editable": True}}), encoding="utf-8"
    )
    mocker.patch.object(
        venv_inspect,
        "fetch_info_in_venv",
        autospec=True,
        return_value=([str(site_packages)], {"python_full_version": "3.10.0"}, "3.10.0"),
    )
    return project


def _inspect_editable_man_pages(project: Path, source: str) -> list[str]:
    (project / "setup.cfg").write_text(f"[options.data_files]\nshare/man/man1 =\n    {source}\n", encoding="utf-8")
    venv = project.parent
    return venv_inspect.inspect_venv(
        "root-package", set(), venv / "bin", venv / "python", venv / "share" / "man"
    ).man_pages


@pytest.mark.parametrize(
    ("root_requirements", "shared_requirements", "expected"),
    [
        pytest.param(("left", "right"), (), ["first-app", "second-app"], id="first-then-second"),
        pytest.param(("right", "left"), (), ["first-app", "second-app"], id="second-then-first"),
        pytest.param(("shared", "left", "right"), (), ["first-app", "second-app"], id="base-then-extras"),
        pytest.param(("left", "right"), ("root",), ["first-app", "second-app"], id="cycle-to-root"),
        pytest.param(
            ("left", "right", 'third-app; extra == "other"'),
            ("root[other]",),
            ["first-app", "second-app", "third-app"],
            id="cycle-enables-root-extra",
        ),
    ],
)
def test_inspect_venv_follows_extras_of_revisited_dependency(
    extras_venv: Path, root_requirements: tuple[str, ...], shared_requirements: tuple[str, ...], expected: list[str]
) -> None:
    result = _inspect_extras_venv(extras_venv, root_requirements, shared_requirements)

    assert sorted(result.apps_of_dependencies) == expected


@pytest.fixture
def extras_venv(tmp_path: Path, mocker: MockerFixture) -> Path:
    site_packages = tmp_path / "site-packages"
    (tmp_path / "bin").mkdir()
    _write_dist_info(site_packages, "left", ("shared[first]",))
    _write_dist_info(site_packages, "right", ("shared[second]",))
    for name in ("first-app", "second-app", "third-app"):
        _write_app(tmp_path, name)
    for resource in ("man/man1/second-app.1", "bash-completion/completions/second-app"):
        (resource_path := tmp_path / "share" / resource).parent.mkdir(parents=True)
        resource_path.touch()
    (site_packages / "second-app-1.0.dist-info" / "RECORD").write_text(
        "../share/man/man1/second-app.1,,\n../share/bash-completion/completions/second-app,,\n", encoding="utf-8"
    )
    mocker.patch.object(
        venv_inspect,
        "fetch_info_in_venv",
        autospec=True,
        return_value=([str(site_packages)], {"python_full_version": "3.13.0"}, "3.13.0"),
    )
    return tmp_path


def _write_app(venv_root: Path, name: str, requirements: tuple[str, ...] = ()) -> None:
    site_packages = venv_root / "site-packages"
    _write_dist_info(site_packages, name, requirements)
    (site_packages / f"{name}-1.0.dist-info" / "entry_points.txt").write_text(
        f"[console_scripts]\n{name} = app:main\n", encoding="utf-8"
    )
    (venv_root / "bin" / name).touch()


def _inspect_extras_venv(
    venv_root: Path, root_requirements: tuple[str, ...], shared_requirements: tuple[str, ...] = ()
) -> venv_inspect.VenvMetadata:
    _write_app(venv_root, "root", root_requirements)
    _write_dist_info(
        venv_root / "site-packages",
        "shared",
        ('first-app; extra == "first"', 'second-app; extra == "second"', *shared_requirements),
    )
    return venv_inspect.inspect_venv(
        "root", set(), venv_root / "bin", venv_root / "python", venv_root / "share" / "man"
    )


def test_inspect_venv_exposes_resources_of_revisited_dependency_extra(extras_venv: Path) -> None:
    result = _inspect_extras_venv(extras_venv, ("left", "right"))

    assert (result.man_paths_of_dependencies, result.completion_paths_of_dependencies) == (
        {"second-app": [extras_venv / "share" / "man" / "man1" / "second-app.1"]},
        {"second-app": [extras_venv / "share" / "bash-completion" / "completions" / "second-app"]},
    )


@pytest.mark.parametrize(
    ("metadata_files", "expected"),
    [
        pytest.param({"installed-files.txt": "../../bin/other\n"}, ["other"], id="installed-files-only"),
        pytest.param(
            {"installed-files.txt": "../../bin/other\n", "RECORD": "root_package/__init__.py,,\n"},
            [],
            id="installed-files-beside-record",
        ),
    ],
)
def test_inspect_venv_reads_installed_files_only_without_record(
    other_app_venv: Path, metadata_files: dict[str, str], expected: list[str]
) -> None:
    for name, content in metadata_files.items():
        (other_app_venv / "lib" / "site-packages" / "root-package-1.0.dist-info" / name).write_text(
            content, encoding="utf-8"
        )

    assert _inspect_root_package(other_app_venv).apps == expected


@skip_if_windows
def test_inspect_venv_skips_installed_files_entry_in_a_symlink_loop(other_app_venv: Path) -> None:
    site_packages = other_app_venv / "lib" / "site-packages"
    (site_packages / "root-package-1.0.dist-info" / "installed-files.txt").write_text(
        "loop\n../../bin/other\n", encoding="utf-8"
    )
    (loop := site_packages / "loop").symlink_to(loop)

    assert _inspect_root_package(other_app_venv).apps == ["other"]


@pytest.fixture
def other_app_venv(tmp_path: Path, mocker: MockerFixture) -> Path:
    site_packages = tmp_path / "lib" / "site-packages"
    _write_dist_info(site_packages, "root-package")
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "other").touch()
    mocker.patch.object(
        venv_inspect,
        "fetch_info_in_venv",
        autospec=True,
        return_value=([str(site_packages)], {"python_full_version": "3.10.0"}, "3.10.0"),
    )
    return tmp_path


def _inspect_root_package(venv: Path) -> venv_inspect.VenvMetadata:
    return venv_inspect.inspect_venv("root-package", set(), venv / "bin", venv / "python", venv / "man")


def test_inspect_venv_ignores_resources_that_name_no_file(tmp_path: Path, mocker: MockerFixture) -> None:
    site_packages = tmp_path / "lib" / "site-packages"
    _write_dist_info(site_packages, "root-package")
    dist_info = site_packages / "root-package-1.0.dist-info"
    (dist_info / "entry_points.txt").write_text(
        "[console_scripts]\napp = root:main\n.. = root:main\n../lib = root:main\n", encoding="utf-8"
    )
    sections = ("bin", "share/man/man1", "share/bash-completion/completions")
    (dist_info / "RECORD").write_text(
        "".join(f"../../{section}/{name},,\n" for section in sections for name in ("app", "..")), encoding="utf-8"
    )
    for section in sections:
        (tmp_path / section).mkdir(parents=True)
        (tmp_path / section / "app").touch()
    mocker.patch.object(
        venv_inspect,
        "fetch_info_in_venv",
        autospec=True,
        return_value=([str(site_packages)], {"python_full_version": "3.10.0"}, "3.10.0"),
    )

    result = venv_inspect.inspect_venv(
        "root-package", set(), tmp_path / "bin", tmp_path / "python", tmp_path / "share" / "man"
    )

    assert (result.apps, [Path(page) for page in result.man_pages], [Path(c) for c in result.completions]) == (
        ["app"],
        [Path("man1/app")],
        [Path("bash-completion/completions/app")],
    )
