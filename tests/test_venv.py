import subprocess
from pathlib import Path

from pytest_mock import MockerFixture

from pipx.venv import Venv


def test_has_app_caches_site_packages(tmp_path: Path, mocker: MockerFixture) -> None:
    venv = Venv(tmp_path / "demo")
    venv.python_path.parent.mkdir(parents=True)
    venv.python_path.touch()
    site_packages = tmp_path / "site-packages"
    dist_info = site_packages / "demo-1.0.dist-info"
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text("Name: demo\nVersion: 1.0\n")
    (dist_info / "entry_points.txt").write_text("[pipx.run]\ndemo = demo:main\n")
    run_subprocess = mocker.patch(
        "pipx.util.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=f"{site_packages}\n", stderr=""),
    )

    assert (venv.has_app("demo", "demo"), venv.has_app("demo", "demo")) == (True, True)
    run_subprocess.assert_called_once()
