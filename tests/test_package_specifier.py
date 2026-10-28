from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from pipx.package_specifier import (
    extract_index_options,
    fix_package_name,
    get_extras,
    package_spec_satisfied,
    parse_specifier_for_install,
    parse_specifier_for_metadata,
    parse_specifier_for_upgrade,
    replace_index_options,
    static_project_name,
    valid_pypi_name,
    wheel_project_name,
)
from pipx.util import PipxError

if TYPE_CHECKING:
    from collections.abc import Callable

TEST_DATA_PATH = "./testdata/test_package_specifier"


@pytest.mark.parametrize(
    ("pip_args", "expected"),
    [
        pytest.param(
            ["--no-cache-dir", "--index-url", "https://index.example/simple", "--pre"],
            ["--index-url", "https://index.example/simple"],
            id="separate-value",
        ),
        pytest.param(
            ["-ihttps://index.example/simple", "-f", "https://files.example", "--no-index"],
            ["-ihttps://index.example/simple", "-f", "https://files.example", "--no-index"],
            id="short-options",
        ),
        pytest.param(
            ["--extra-index-url=https://extra.example/simple", "--trusted-host", "extra.example"],
            ["--extra-index-url=https://extra.example/simple", "--trusted-host", "extra.example"],
            id="attached-value",
        ),
        pytest.param(
            [
                "--default-index",
                "https://index.example/simple",
                "--index=https://extra.example/simple",
                "--allow-insecure-host",
                "extra.example",
                "--index-strategy",
                "unsafe-best-match",
                "--keyring-provider",
                "subprocess",
                "--compile-bytecode",
            ],
            [
                "--default-index",
                "https://index.example/simple",
                "--index=https://extra.example/simple",
                "--allow-insecure-host",
                "extra.example",
                "--index-strategy",
                "unsafe-best-match",
                "--keyring-provider",
                "subprocess",
            ],
            id="uv-spellings",
        ),
    ],
)
def test_extract_index_options(pip_args: list[str], expected: list[str]) -> None:
    assert extract_index_options(pip_args) == expected


@pytest.mark.parametrize(
    "option",
    [
        "-f",
        "-i",
        "--allow-insecure-host",
        "--default-index",
        "--extra-index-url",
        "--find-links",
        "--index",
        "--index-strategy",
        "--index-url",
        "--keyring-provider",
        "--trusted-host",
    ],
)
def test_extract_index_options_missing_value(option: str) -> None:
    with pytest.raises(PipxError, match=re.escape(f"Missing value for {option!r} in --pip-args.")):
        extract_index_options(["--no-cache-dir", option])


@pytest.mark.parametrize(
    ("pip_args", "index_args", "expected"),
    [
        pytest.param(
            ["--no-cache-dir", "--index-url", "https://old.example/simple", "--pre"],
            ["--find-links", "/wheels"],
            ["--no-cache-dir", "--pre", "--find-links", "/wheels"],
            id="pip-spellings",
        ),
        pytest.param(
            [
                "--default-index",
                "https://old.example/simple",
                "--index=https://extra.example/simple",
                "--compile-bytecode",
            ],
            ["--default-index", "https://new.example/simple"],
            ["--compile-bytecode", "--default-index", "https://new.example/simple"],
            id="uv-spellings",
        ),
    ],
)
def test_replace_index_options(pip_args: list[str], index_args: list[str], expected: list[str]) -> None:
    assert replace_index_options(pip_args, index_args) == expected


@pytest.mark.parametrize(
    ("package_spec_in", "package_name_out"),
    [
        ("Black", "black"),
        ("https://github.com/ambv/black/archive/18.9b0.zip", None),
        ("black @ https://github.com/ambv/black/archive/18.9b0.zip", None),
        ("black-18.9b0-py36-none-any.whl", None),
        ("black-18.9b0.tar.gz", None),
        ("black-18.9b0.zip", None),
        ("black-18.9b0.tar", None),
        ("black-18.9b0.tgz", None),
        ("black-18.9b0.tar.bz2", None),
        ("black-18.9b0.tbz", None),
        ("black-18.9b0.tar.xz", None),
        ("black-18.9b0.txz", None),
        ("black-18.9b0.tlz", None),
        ("black-18.9b0.tar.lz", None),
        ("black-18.9b0.tar.lzma", None),
        ("black-18.9b0.TAR.GZ", None),
    ],
)
def test_valid_pypi_name(package_spec_in: str, package_name_out: str | None) -> None:
    assert valid_pypi_name(package_spec_in) == package_name_out


@pytest.mark.parametrize(
    "name", [pytest.param("pkg-1.0.tar.xz", id="lowercase"), pytest.param("Pkg-1.0.TAR.XZ", id="uppercase")]
)
def test_parse_specifier_for_install_bare_archive(name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (archive := tmp_path / name).touch()
    monkeypatch.chdir(tmp_path)
    assert parse_specifier_for_install(name, []) == (str(archive.resolve()), [])


def test_parse_specifier_for_install_missing_bare_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(PipxError, match=r"pkg-1\.0\.tar\.xz does not exist"):
        parse_specifier_for_install("pkg-1.0.tar.xz", [])


@pytest.mark.parametrize(
    ("package_spec", "installed_spec", "expected"),
    [
        ("black>=22,<23", "black==22.8.0", True),
        ("black<22", "black==22.8.0", False),
        ("Black", "black==22.8.0", True),
        ("black[colorama]", "black==22.8.0", False),
        ("black[colorama]", "black[colorama]==22.8.0", True),
        ("black @ https://example.com/black.whl", "black==22.8.0", False),
        ("https://example.com/black.whl", "black==22.8.0", False),
    ],
)
def test_package_spec_satisfied(package_spec: str, installed_spec: str, expected: bool) -> None:
    assert package_spec_satisfied(package_spec, "black", "22.8.0", installed_spec) is expected


@pytest.mark.parametrize(
    ("package_spec_in", "package_name", "package_spec_out"),
    [
        (
            "https://github.com/ambv/black/archive/18.9b0.zip",
            "black",
            "https://github.com/ambv/black/archive/18.9b0.zip",
        ),
        (
            "nox@https://github.com/ambv/black/archive/18.9b0.zip",
            "black",
            "black @ https://github.com/ambv/black/archive/18.9b0.zip",
        ),
        (
            "nox[extra]@https://github.com/ambv/black/archive/18.9b0.zip",
            "black",
            "black[extra] @ https://github.com/ambv/black/archive/18.9b0.zip",
        ),
        ("black-18.9b0.tar.xz", "black", "black-18.9b0.tar.xz"),
        ("Black-18.9b0.TAR.XZ", "black", "Black-18.9b0.TAR.XZ"),
    ],
)
def test_fix_package_name(package_spec_in: str, package_name: str, package_spec_out: str) -> None:
    assert fix_package_name(package_spec_in, package_name) == package_spec_out


@pytest.fixture
def bare_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (archive := tmp_path / "repeatme-0.1-py3-none-any.whl").touch()
    monkeypatch.chdir(tmp_path)
    return archive


@pytest.mark.parametrize(
    "extras",
    [
        pytest.param("", id="none"),
        pytest.param("[cow]", id="single"),
        pytest.param("[tools,cow]", id="unsorted"),
        pytest.param(" [tools, cow]", id="spaced"),
    ],
)
def test_parse_specifier_bare_archive_matches_explicit_path(bare_archive: Path, extras: str) -> None:
    assert parse_specifier_for_metadata(f"{bare_archive.name}{extras}") == parse_specifier_for_metadata(
        f"./{bare_archive.name}{extras.lstrip()}"
    )


def test_parse_specifier_bare_archive_extras_before_trailing_space(bare_archive: Path) -> None:
    assert parse_specifier_for_metadata(f"{bare_archive.name}[cow] ") == f"{bare_archive}[cow]"


def test_get_extras_bare_archive(bare_archive: Path) -> None:
    assert get_extras(f"{bare_archive.name}[tools,cow]") == {"cow", "tools"}


@pytest.mark.parametrize(
    "suffix",
    [
        pytest.param("==0.1", id="specifier"),
        pytest.param("; python_version > '3'", id="marker"),
        pytest.param(" @ https://example.com/repeatme-0.1-py3-none-any.whl", id="url"),
    ],
)
def test_parse_specifier_bare_archive_rejects_non_extras(bare_archive: Path, suffix: str) -> None:
    with pytest.raises(PipxError, match=r"^Only extras can follow the local archive"):
        parse_specifier_for_metadata(f"{bare_archive.name}[cow]{suffix}")


_ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize(
    ("package_spec_in", "package_or_url_correct", "valid_spec"),
    [
        ("pipx", "pipx", True),
        ("PiPx_stylized.name", "pipx-stylized-name", True),
        ("pipx==0.15.0", "pipx==0.15.0", True),
        ("pipx>=0.15.0", "pipx>=0.15.0", True),
        ("pipx<=0.15.0", "pipx<=0.15.0", True),
        ('pipx;python_version>="3.6"', "pipx", True),
        ('pipx==0.15.0;python_version>="3.6"', "pipx==0.15.0", True),
        ("pipx[extra1]", "pipx[extra1]", True),
        ("pipx[extra1, extra2]", "pipx[extra1,extra2]", True),
        ("src/pipx", str((_ROOT / "src" / "pipx").resolve()), True),
        (
            "git+https://github.com/cs01/nox.git@5ea70723e9e6",
            "git+https://github.com/cs01/nox.git@5ea70723e9e6",
            True,
        ),
        (
            "nox@git+https://github.com/cs01/nox.git@5ea70723e9e6",
            "nox @ git+https://github.com/cs01/nox.git@5ea70723e9e6",
            True,
        ),
        (
            "https://github.com/ambv/black/archive/18.9b0.zip",
            "https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            "black@https://github.com/ambv/black/archive/18.9b0.zip",
            "black @ https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            "black @ https://github.com/ambv/black/archive/18.9b0.zip",
            "black @ https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            "black[extra] @ https://github.com/ambv/black/archive/18.9b0.zip",
            "black[extra] @ https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            'my-project[cli] @ git+ssh://git@bitbucket.org/my-company/myproject.git ; python_version<"3.8"',
            "my-project[cli] @ git+ssh://git@bitbucket.org/my-company/myproject.git",
            True,
        ),
        ("path/doesnt/exist", "non-existent-path", False),
        (
            "https:/github.com/ambv/black/archive/18.9b0.zip",
            "URL-syntax-error-slash",
            False,
        ),
    ],
)
def test_parse_specifier_for_metadata(
    package_spec_in: str,
    package_or_url_correct: str,
    valid_spec: bool,
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
) -> None:
    monkeypatch.chdir(root)
    if valid_spec:
        package_or_url = parse_specifier_for_metadata(package_spec_in)
        assert package_or_url == package_or_url_correct
    else:
        # print package_spec_in for info in case no error is raised
        with pytest.raises(PipxError, match=r"^Unable to parse package spec"):
            package_or_url = parse_specifier_for_metadata(package_spec_in)


@pytest.mark.parametrize(
    ("package_spec_in", "package_or_url_correct", "valid_spec"),
    [
        ("pipx", "pipx", True),
        ("PiPx_stylized.name", "pipx-stylized-name", True),
        ("pipx==0.15.0", "pipx", True),
        ("pipx>=0.15.0", "pipx", True),
        ("pipx<=0.15.0", "pipx", True),
        ('pipx;python_version>="3.6"', "pipx", True),
        ('pipx==0.15.0;python_version>="3.6"', "pipx", True),
        ("pipx[extra1]", "pipx[extra1]", True),
        ("pipx[extra1, extra2]", "pipx[extra1,extra2]", True),
        ("src/pipx", str((_ROOT / "src" / "pipx").resolve()), True),
        (
            "git+https://github.com/cs01/nox.git@5ea70723e9e6",
            "git+https://github.com/cs01/nox.git@5ea70723e9e6",
            True,
        ),
        (
            "nox@git+https://github.com/cs01/nox.git@5ea70723e9e6",
            "nox @ git+https://github.com/cs01/nox.git@5ea70723e9e6",
            True,
        ),
        (
            "https://github.com/ambv/black/archive/18.9b0.zip",
            "https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            "black@https://github.com/ambv/black/archive/18.9b0.zip",
            "black @ https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            "black @ https://github.com/ambv/black/archive/18.9b0.zip",
            "black @ https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            "black[extra] @ https://github.com/ambv/black/archive/18.9b0.zip",
            "black[extra] @ https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            'my-project[cli] @ git+ssh://git@bitbucket.org/my-company/myproject.git ; python_version<"3.8"',
            "my-project[cli] @ git+ssh://git@bitbucket.org/my-company/myproject.git",
            True,
        ),
        ("path/doesnt/exist", "non-existent-path", False),
        (
            "https:/github.com/ambv/black/archive/18.9b0.zip",
            "URL-syntax-error-slash",
            False,
        ),
    ],
)
def test_parse_specifier_for_upgrade(
    package_spec_in: str,
    package_or_url_correct: str,
    valid_spec: bool,
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
) -> None:
    monkeypatch.chdir(root)
    if valid_spec:
        package_or_url = parse_specifier_for_upgrade(package_spec_in)
        assert package_or_url == package_or_url_correct
    else:
        # print package_spec_in for info in case no error is raised
        with pytest.raises(PipxError, match=r"^Unable to parse package spec"):
            package_or_url = parse_specifier_for_upgrade(package_spec_in)


@pytest.mark.parametrize(
    ("package_spec_in", "pip_args_in", "package_spec_expected", "pip_args_expected", "warning_str"),
    [
        ('pipx==0.15.0;python_version>="3.6"', [], "pipx==0.15.0", [], None),
        ("pipx==0.15.0", ["--editable"], "pipx==0.15.0", [], "Ignoring --editable"),
        (
            'pipx==0.15.0;python_version>="3.6"',
            [],
            "pipx==0.15.0",
            [],
            'Ignoring environment markers (python_version >= "3.6") in package',
        ),
        (
            "pipx==0.15.0",
            ["--no-cache-dir", "--editable"],
            "pipx==0.15.0",
            ["--no-cache-dir"],
            "Ignoring --editable",
        ),
        (
            "git+https://github.com/cs01/nox.git@5ea70723e9e6",
            ["--editable"],
            "git+https://github.com/cs01/nox.git@5ea70723e9e6",
            [],
            "Ignoring --editable",
        ),
        (
            "https://github.com/ambv/black/archive/18.9b0.zip",
            ["--editable"],
            "https://github.com/ambv/black/archive/18.9b0.zip",
            [],
            "Ignoring --editable",
        ),
        (
            "src/pipx",
            ["--editable"],
            str(Path("src/pipx").resolve()),
            ["--editable"],
            None,
        ),
        (
            TEST_DATA_PATH + "/local_extras",
            [],
            str(Path(TEST_DATA_PATH + "/local_extras").resolve),
            [],
            None,
        ),
        (
            TEST_DATA_PATH + "/local_extras[cow]",
            [],
            str(Path(TEST_DATA_PATH + "/local_extras").resolve) + "[cow]",
            [],
            None,
        ),
        (
            TEST_DATA_PATH + "/local_extras",
            ["--editable"],
            str(Path(TEST_DATA_PATH + "/local_extras").resolve),
            ["--editable"],
            None,
        ),
        (
            TEST_DATA_PATH + "/local_extras[cow]",
            ["--editable"],
            str(Path(TEST_DATA_PATH + "/local_extras").resolve) + "[cow]",
            ["--editable"],
            None,
        ),
    ],
)
def test_parse_specifier_for_install(
    package_spec_in: str,
    pip_args_in: list[str],
    package_spec_expected: str,  # ruff:ignore[unused-function-argument]  # expected columns kept in the case table; test only checks warnings
    pip_args_expected: list[str],  # ruff:ignore[unused-function-argument]  # expected columns kept in the case table; test only checks warnings
    warning_str: str | None,
    *,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
) -> None:
    monkeypatch.chdir(root)
    parse_specifier_for_install(package_spec_in, pip_args_in)
    if warning_str is not None:
        assert warning_str in caplog.text


@pytest.mark.parametrize(
    ("pip_args_in", "pip_args_expected"),
    [
        (
            ["-c", "https://example.com/constraints.txt"],
            ["-c", "https://example.com/constraints.txt"],
        ),
        (
            ["-chttps://example.com/constraints.txt"],
            ["-chttps://example.com/constraints.txt"],
        ),
        (
            ["--constraint", "https://example.com/constraints.txt"],
            ["--constraint", "https://example.com/constraints.txt"],
        ),
        (
            ["--constraint=https://example.com/constraints.txt"],
            ["--constraint=https://example.com/constraints.txt"],
        ),
        (
            ["-c", "constraints.txt"],
            ["-c", str(Path("constraints.txt").resolve())],
        ),
        (
            ["-cconstraints.txt"],
            [f"-c{Path('constraints.txt').resolve()}"],
        ),
        (
            ["--constraint=constraints.txt"],
            [f"--constraint={Path('constraints.txt').resolve()}"],
        ),
    ],
    ids=[
        "short-separated-url",
        "short-attached-url",
        "long-separated-url",
        "long-equals-url",
        "short-separated-path",
        "short-attached-path",
        "long-equals-path",
    ],
)
def test_parse_specifier_for_install_constraint_args(
    pip_args_in: list[str],
    pip_args_expected: list[str],
) -> None:
    _, pip_args_out = parse_specifier_for_install("pipx", pip_args_in)
    assert pip_args_out == pip_args_expected


@pytest.mark.parametrize(
    "package_spec",
    [
        "git+file:///tmp/project@main",
        "hg+file:///tmp/project@default",
        "file:///opt/wheels/demo-1-py3-none-any.whl",
        "file:///opt/wheels%20with%20spaces/demo-1.tar.gz#sha256=abc",
        "file:///C:/wheels/demo-1-py3-none-any.whl",
    ],
    ids=["git", "mercurial", "file", "file-quoted-space", "file-windows-drive"],
)
def test_parse_specifier_for_install_accepts_local_url(package_spec: str) -> None:
    assert parse_specifier_for_install(package_spec, []) == (package_spec, [])


@pytest.mark.parametrize(
    "package_spec",
    ["file:relative.whl", "git+file:relative", "https:/example.com/demo.whl"],
    ids=["file", "git", "https-single-slash"],
)
def test_parse_specifier_for_install_rejects_hostless_relative_url(package_spec: str) -> None:
    with pytest.raises(PipxError, match="Unable to parse package spec"):
        parse_specifier_for_install(package_spec, [])


@pytest.mark.parametrize(
    ("pip_args_in", "pip_args_expected"),
    [
        (
            ["-f", "https://example.com/wheels"],
            ["-f", "https://example.com/wheels"],
        ),
        (
            ["-fhttps://example.com/wheels"],
            ["-fhttps://example.com/wheels"],
        ),
        (
            ["--find-links", "https://example.com/wheels"],
            ["--find-links", "https://example.com/wheels"],
        ),
        (
            ["--find-links=https://example.com/wheels"],
            ["--find-links=https://example.com/wheels"],
        ),
        (
            ["-f", "wheels"],
            ["-f", str(Path("wheels").resolve())],
        ),
        (
            ["-fwheels"],
            [f"-f{Path('wheels').resolve()}"],
        ),
        (
            ["--find-links=wheels"],
            [f"--find-links={Path('wheels').resolve()}"],
        ),
    ],
    ids=[
        "short-separated-url",
        "short-attached-url",
        "long-separated-url",
        "long-equals-url",
        "short-separated-path",
        "short-attached-path",
        "long-equals-path",
    ],
)
def test_parse_specifier_for_install_find_links_args(
    pip_args_in: list[str],
    pip_args_expected: list[str],
) -> None:
    _, pip_args_out = parse_specifier_for_install("pipx", pip_args_in)
    assert pip_args_out == pip_args_expected


@pytest.mark.parametrize(
    ("pyproject", "expected"),
    [
        pytest.param(b'[project]\nname = "Foo_Bar.X"\n', "Foo_Bar.X", id="static"),
        pytest.param(b'[project]\nname = "demo"\ndynamic = ["version"]\n', "demo", id="other-field-dynamic"),
        pytest.param(None, None, id="no-pyproject"),
        pytest.param(b"", None, id="no-project-table"),
        pytest.param(b'[project]\nversion = "1"\n', None, id="no-name"),
        pytest.param(b"[project]\nname = 1\n", None, id="name-not-string"),
        pytest.param(b'[project]\nname = "-bad-"\n', None, id="name-invalid"),
        pytest.param(b'[project]\nname = "demo"\ndynamic = ["name"]\n', None, id="name-dynamic"),
        pytest.param(b'[project]\nname = "demo"\ndynamic = "name"\n', None, id="dynamic-not-list"),
        pytest.param(b"[project\n", None, id="invalid-toml"),
        pytest.param(b'[project]\nname = "\xff"\n', None, id="not-utf8"),
    ],
)
def test_static_project_name(tmp_path: Path, pyproject: bytes | None, expected: str | None) -> None:
    if pyproject is not None:
        (tmp_path / "pyproject.toml").write_bytes(
            b'[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n' + pyproject
        )

    assert static_project_name(f"{tmp_path}[extra]") == expected


@pytest.mark.parametrize(
    ("build_system", "expected"),
    [
        pytest.param('requires = ["hatchling"]\nbuild-backend = "hatchling.build"', "demo", id="hatchling"),
        pytest.param('requires = ["flit_core>=3.2,<4"]\nbuild-backend = "flit_core.buildapi"', "demo", id="flit-core"),
        pytest.param('requires = ["pdm-backend"]\nbuild-backend = "pdm.backend"', "demo", id="pdm-backend"),
        pytest.param('requires = ["uv_build>=0.8"]\nbuild-backend = "uv_build"', "demo", id="uv-build"),
        pytest.param('requires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"', "demo", id="setuptools"),
        pytest.param(
            'requires = ["setuptools>=40,<70"]\nbuild-backend = "setuptools.build_meta"',
            "demo",
            id="setuptools-61-allowed",
        ),
        pytest.param(
            'requires = ["poetry-core==2.1.*"]\nbuild-backend = "poetry.core.masonry.api"', "demo", id="poetry-core-2"
        ),
        pytest.param(
            'requires = ["poetry-core>=2.1"]\nbuild-backend = "poetry.core.masonry.api"',
            "demo",
            id="poetry-core-above-2",
        ),
        pytest.param(
            'requires = ["poetry-core>=1,<2"]\nbuild-backend = "poetry.core.masonry.api"', None, id="poetry-core-1"
        ),
        pytest.param(
            'requires = ["setuptools<61"]\nbuild-backend = "setuptools.build_meta"', None, id="setuptools-before-61"
        ),
        pytest.param(
            'requires = ["flit_core==3.1.*"]\nbuild-backend = "flit_core.buildapi"', None, id="flit-core-before-3.2"
        ),
        pytest.param(
            'requires = ["setuptools===custom"]\nbuild-backend = "setuptools.build_meta"', None, id="arbitrary-equality"
        ),
        pytest.param('requires = ["wheel"]\nbuild-backend = "setuptools.build_meta"', None, id="backend-not-required"),
        pytest.param('build-backend = "setuptools.build_meta"', None, id="no-requires"),
        pytest.param(
            'requires = ["setuptools"]\nbuild-backend = "setuptools.build_meta:__legacy__"', None, id="legacy"
        ),
        pytest.param('requires = ["maturin"]\nbuild-backend = "maturin"', None, id="unknown-backend"),
        pytest.param('requires = ["hatchling"]\nbuild-backend = ["hatchling.build"]', None, id="backend-not-string"),
        pytest.param(
            'requires = []\nbuild-backend = "hatchling.build"\nbackend-path = ["."]', None, id="in-tree-backend"
        ),
        pytest.param('requires = ["setuptools"]', None, id="no-backend"),
    ],
)
def test_static_project_name_build_backend(tmp_path: Path, build_system: str, expected: str | None) -> None:
    (tmp_path / "pyproject.toml").write_text(
        f'[build-system]\n{build_system}\n[project]\nname = "demo"\n', encoding="utf-8"
    )

    assert static_project_name(str(tmp_path)) == expected


def test_static_project_name_unreadable_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").mkdir()

    assert static_project_name(str(tmp_path)) is None


@pytest.mark.parametrize(
    ("entries", "expected"),
    [
        pytest.param({"foo_bar_x-1.dist-info/METADATA": "Name: Foo_Bar.X\n"}, "Foo_Bar.X", id="declared"),
        pytest.param({"foo_bar_x/__init__.py": ""}, None, id="no-dist-info"),
        pytest.param({"nested/foo_bar_x-1.dist-info/METADATA": "Name: Foo_Bar.X\n"}, None, id="nested-dist-info"),
        pytest.param(
            {"foo-1.dist-info/METADATA": "Name: foo\n", "bar-1.dist-info/METADATA": "Name: bar\n"},
            None,
            id="multiple-dist-info",
        ),
        pytest.param({"foo_bar_x-1.dist-info/METADATA": "Version: 1\n"}, None, id="no-name"),
        pytest.param({"foo_bar_x-1.dist-info/METADATA": "Name: -bad-\n"}, None, id="name-invalid"),
        pytest.param({"foo_bar_x-1.dist-info/METADATA": "Name: f\u00e9\n"}, None, id="name-not-ascii"),
    ],
)
def test_wheel_project_name(
    make_wheel: Callable[[dict[str, str]], Path], entries: dict[str, str], expected: str | None
) -> None:
    assert wheel_project_name(f"{make_wheel(entries)}[extra]") == expected


@pytest.mark.parametrize("content", [pytest.param(b"not a zip", id="not-a-zip"), pytest.param(None, id="missing")])
def test_wheel_project_name_unreadable(tmp_path: Path, content: bytes | None) -> None:
    wheel = tmp_path / "foo-1-py3-none-any.whl"
    if content is not None:
        wheel.write_bytes(content)

    assert wheel_project_name(str(wheel)) is None


def test_wheel_project_name_ignores_other_archives(
    make_wheel: Callable[[dict[str, str]], Path], tmp_path: Path
) -> None:
    archive = make_wheel({"foo_bar_x-1.dist-info/METADATA": "Name: Foo_Bar.X\n"}).rename(tmp_path / "foo_bar_x-1.zip")

    assert wheel_project_name(str(archive)) is None
