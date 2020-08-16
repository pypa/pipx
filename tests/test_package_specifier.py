from pathlib import Path

import pytest  # type: ignore

from pipx.package_specifier import (
    parse_specifier_for_install,
    parse_specifier_for_metadata,
)
from pipx.util import PipxError


# TODO: Make sure git+ works with tests, correct in test_install as well
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
        ("src/pipx", str(Path("src/pipx").resolve()), True),
        (
            "git+https://github.com/cs01/nox.git@5ea70723e9e6",
            "git+https://github.com/cs01/nox.git@5ea70723e9e6",
            True,
        ),
        (
            "nox@git+https://github.com/cs01/nox.git@5ea70723e9e6",
            "git+https://github.com/cs01/nox.git@5ea70723e9e6",
            True,
        ),
        (
            "https://github.com/ambv/black/archive/18.9b0.zip",
            "https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            "black@https://github.com/ambv/black/archive/18.9b0.zip",
            "https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        (
            "black @ https://github.com/ambv/black/archive/18.9b0.zip",
            "https://github.com/ambv/black/archive/18.9b0.zip",
            True,
        ),
        ("path/doesnt/exist", "non-existent-path", False,),
        (
            "https:/github.com/ambv/black/archive/18.9b0.zip",
            "URL-syntax-error-slash",
            False,
        ),
    ],
)
def test_parse_specifier_for_metadata(
    package_spec_in, package_or_url_correct, valid_spec
):
    if valid_spec:
        package_or_url = parse_specifier_for_metadata(package_spec_in)
        assert package_or_url == package_or_url_correct
    else:
        # print package_spec_in for info in case no error is raised
        print(f"package_spec_in = {package_spec_in}")
        with pytest.raises(PipxError, match=r"^Unable to parse package spec"):
            package_or_url = parse_specifier_for_metadata(package_spec_in)


@pytest.mark.parametrize(
    "package_spec_in,pip_args_in,package_spec_expected,pip_args_expected,warning_str",
    [
        ('pipx==0.15.0;python_version>="3.6"', [], "pipx==0.15.0", [], None),
        ("pipx==0.15.0", ["--editable"], "pipx==0.15.0", [], "Ignoring --editable",),
        (
            'pipx==0.15.0;python_version>="3.6"',
            [],
            "pipx==0.15.0",
            [],
            'Ignoring environment markers in package specification: python_version >= "3.6"',
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
    ],
)
def test_parse_specifier_for_install(
    caplog,
    package_spec_in,
    pip_args_in,
    package_spec_expected,
    pip_args_expected,
    warning_str,
):
    [package_or_url_out, pip_args_out] = parse_specifier_for_install(
        package_spec_in, pip_args_in
    )
    if warning_str is not None:
        assert warning_str in caplog.text
