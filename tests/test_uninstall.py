from helpers import run_pipx_cli

from pipx import constants, util


def test_uninstall(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["uninstall", "pycowsay"])


def test_uninstall_suffix(pipx_temp_env, capsys):
    name = "pbr"
    suffix = "_a"
    executable = f"{name}{suffix}{'.exe' if constants.WINDOWS else ''}"

    assert not run_pipx_cli(["install", "pbr", f"--suffix={suffix}"])
    assert (constants.LOCAL_BIN_DIR / executable).exists()

    assert not run_pipx_cli(["uninstall", f"{name}{suffix}"])
    assert not (constants.LOCAL_BIN_DIR / executable).exists()


def test_uninstall_with_missing_interpreter(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])

    _, python_path = util.get_venv_paths(constants.PIPX_LOCAL_VENVS / "pycowsay")
    assert python_path.is_file()
    python_path.unlink()
    assert not python_path.is_file()

    assert not run_pipx_cli(["uninstall", "pycowsay"])
