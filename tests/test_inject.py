import logging
import re
import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest

from helpers import PIPX_METADATA_LEGACY_VERSIONS, mock_legacy_venv, run_pipx_cli, skip_if_windows
from package_info import PKG
from pipx import paths
from pipx.pipx_metadata_file import PipxMetadata


def test_inject_rejects_pylock(
    pipx_temp_env: None,
    make_pylock: Callable[[str, str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock_file = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    capsys.readouterr()

    assert run_pipx_cli(["inject", "pycowsay", "black"])

    error = " ".join(capsys.readouterr().err.split())
    assert (
        "Cannot inject into locked environment pycowsay" in error and "`pipx reinstall pycowsay`" in error,
        PipxMetadata(paths.ctx.venvs / "pycowsay").injected_packages,
    ) == (True, {})


# Note that this also checks that packages used in other tests can be injected individually
@pytest.mark.parametrize(
    "pkg_spec",
    [
        PKG["black"]["spec"],
        PKG["nox"]["spec"],
        PKG["pylint"]["spec"],
        PKG["ipython"]["spec"],
        "jaraco.clipboard==2.0.1",  # tricky character
    ],
)
def test_inject_single_package(pipx_temp_env, capsys, caplog, pkg_spec):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", pkg_spec])

    # Check arguments have been parsed correctly
    assert f"Injecting packages: {[pkg_spec]!r}" in caplog.text

    # Check it's actually being installed and into correct venv
    captured = capsys.readouterr()
    injected = re.findall(r"injected package (.+?) into venv pycowsay", captured.out)
    pkg_name = pkg_spec.split("=", 1)[0].replace(".", "-")  # assuming spec is always of the form <name>==<version>
    assert set(injected) == {pkg_name}


@skip_if_windows
def test_inject_simple_global(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "--global", "pycowsay"])
    assert not run_pipx_cli(["inject", "--global", "pycowsay", PKG["black"]["spec"]])


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
def test_inject_simple_legacy_venv(pipx_temp_env, capsys, metadata_version):
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    if metadata_version is not None:
        assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    else:
        # no metadata in venv should result in PipxError with message
        assert run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
        assert "Please uninstall and install" in capsys.readouterr().err


@pytest.mark.parametrize("with_suffix", [False, True])
def test_inject_include_apps(pipx_temp_env, capsys, with_suffix):
    install_args = []
    suffix = ""

    if with_suffix:
        suffix = "_x"
        install_args = [f"--suffix={suffix}"]

    assert not run_pipx_cli(["install", "pycowsay", *install_args])
    assert not run_pipx_cli(["inject", f"pycowsay{suffix}", PKG["black"]["spec"], "--include-deps"])

    if suffix:
        assert run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"], "--include-deps"])

    assert not run_pipx_cli(["inject", f"pycowsay{suffix}", PKG["black"]["spec"], "--include-deps"])


@pytest.mark.parametrize(
    "with_packages",
    [
        (),  # no extra packages
        ("black",),  # duplicate from requirements file
        ("ipython",),  # additional package
    ],
)
def test_inject_with_req_file(pipx_temp_env, capsys, caplog, tmp_path, with_packages):
    caplog.set_level(logging.INFO)

    req_file = tmp_path / "inject-requirements.txt"
    req_file.write_text(
        textwrap.dedent(
            f"""
                {PKG["black"]["spec"]} # a comment inline
                {PKG["nox"]["spec"]}

                {PKG["pylint"]["spec"]}
                # comment on separate line
            """
        ).strip()
    )
    assert not run_pipx_cli(["install", "pycowsay"])

    assert not run_pipx_cli(
        ["inject", "pycowsay", *(PKG[pkg]["spec"] for pkg in with_packages), "--requirement", str(req_file)]
    )

    packages = [
        ("black", PKG["black"]["spec"]),
        ("nox", PKG["nox"]["spec"]),
        ("pylint", PKG["pylint"]["spec"]),
    ]
    packages.extend((pkg, PKG[pkg]["spec"]) for pkg in with_packages)
    packages = sorted(set(packages))

    # Check arguments and files have been parsed correctly
    assert f"Injecting packages: {[p for _, p in packages]!r}" in caplog.text

    # Check they're actually being installed and into correct venv
    captured = capsys.readouterr()
    injected = re.findall(r"injected package (.+?) into venv pycowsay", captured.out)
    assert set(injected) == {pkg for pkg, _ in packages}


def test_force_inject_reinstalls_without_storing_force(pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"], "--pip-args=--no-cache-dir"])

    caplog.clear()
    assert not run_pipx_cli(
        [
            "inject",
            "pycowsay",
            PKG["black"]["spec"],
            "--force",
            "--verbose",
            "--pip-args=--no-cache-dir",
        ]
    )

    assert "--force-reinstall" in caplog.text

    metadata = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert metadata.injected_packages["black"].pip_args == ["--no-cache-dir"]
