from pathlib import Path

import pytest  # type: ignore[import-not-found]

from pipx.package_specifier import (
    fix_package_name,
    parse_specifier_for_install,
    parse_specifier_for_metadata,
    parse_specifier_for_upgrade,
    valid_pypi_name,
)
from pipx.util import PipxError

TEST_DATA_PATH = "./testdata/test_package_specifier"


@pytest.mark.parametrize(
    "package_spec_in,package_name_out",
    [
        ("Black", "black"),
        ("https://github.com/ambv/black/archive/18.9b0.zip", None),
        ("black @ https://github.com/ambv/black/archive/18.9b0.zip", None),
        ("black-18.9b0-py36-none-any.whl", None),
        ("black-18.9b0.tar.gz", None),
    ],
)
def test_valid_pypi_name(package_spec_in, package_name_out):
    assert valid_pypi_name(package_spec_in) == package_name_out


@pytest.mark.parametrize(
    "package_spec_in,package_name,package_spec_out",
    [
        (
            "https://github.com/ambv/black/archive/18.9b0.zip",
            "black",
            "https://github.com/ambv/black/archive/18.9b0.zip",
        ),
        (
            "nox@https://github.com/ambv/black/archive/18.9b0.zip",
            "black",
            "black@ https://github.com/ambv/black/archive/18.9b0.zip",
        ),
        (
            "nox[extra]@https://github.com/ambv/black/archive/18.9b0.zip",
            "black",
            "black[extra]@ https://github.com/ambv/black/archive/18.9b0.zip",
        ),
    ],
)
def test_fix_package_name(package_spec_in, package_name, package_spec_out):
    assert fix_package_name(package_spec_in, package_name) == package_spec_out


_ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize(
    "package_spec_in,package_or_url_correct,valid_spec",
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
            "nox@ git+https://github.com/cs01/nox.git@5ea70723e9e6",
            True,
        ),
        (
            "https://github.com/ambv/black/archive/18.9b0.zip",
            "https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            "black@https://github.com/ambv/black/archive/18.9b0.zip",
            "black@ https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            "black @ https://github.com/ambv/black/archive/18.9b0.zip",
            "black@ https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            "black[extra] @ https://github.com/ambv/black/archive/18.9b0.zip",
            "black[extra]@ https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            'my-project[cli] @ git+ssh://git@bitbucket.org/my-company/myproject.git ; python_version<"3.8"',
            "my-project[cli]@ git+ssh://git@bitbucket.org/my-company/myproject.git",
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
def test_parse_specifier_for_metadata(package_spec_in, package_or_url_correct, valid_spec, monkeypatch, root):
    monkeypatch.chdir(root)
    if valid_spec:
        package_or_url = parse_specifier_for_metadata(package_spec_in)
        assert package_or_url == package_or_url_correct
    else:
        # print package_spec_in for info in case no error is raised
        print(f"package_spec_in = {package_spec_in}")
        with pytest.raises(PipxError, match=r"^Unable to parse package spec"):
            package_or_url = parse_specifier_for_metadata(package_spec_in)


@pytest.mark.parametrize(
    "package_spec_in,package_or_url_correct,valid_spec",
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
            "nox@ git+https://github.com/cs01/nox.git@5ea70723e9e6",
            True,
        ),
        (
            "https://github.com/ambv/black/archive/18.9b0.zip",
            "https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            "black@https://github.com/ambv/black/archive/18.9b0.zip",
            "black@ https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            "black @ https://github.com/ambv/black/archive/18.9b0.zip",
            "black@ https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            "black[extra] @ https://github.com/ambv/black/archive/18.9b0.zip",
            "black[extra]@ https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            'my-project[cli] @ git+ssh://git@bitbucket.org/my-company/myproject.git ; python_version<"3.8"',
            "my-project[cli]@ git+ssh://git@bitbucket.org/my-company/myproject.git",
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
def test_parse_specifier_for_upgrade(package_spec_in, package_or_url_correct, valid_spec, monkeypatch, root):
    monkeypatch.chdir(root)
    if valid_spec:
        package_or_url = parse_specifier_for_upgrade(package_spec_in)
        assert package_or_url == package_or_url_correct
    else:
        # print package_spec_in for info in case no error is raised
        print(f"package_spec_in = {package_spec_in}")
        with pytest.raises(PipxError, match=r"^Unable to parse package spec"):
            package_or_url = parse_specifier_for_upgrade(package_spec_in)


@pytest.mark.parametrize(
    "package_spec_in,pip_args_in,package_spec_expected,pip_args_expected,warning_str",
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
    caplog,
    package_spec_in,
    pip_args_in,
    package_spec_expected,
    pip_args_expected,
    warning_str,
    monkeypatch,
    root,
):
    monkeypatch.chdir(root)
    [package_or_url_out, pip_args_out] = parse_specifier_for_install(package_spec_in, pip_args_in)
    if warning_str is not None:
        assert warning_str in caplog.text
