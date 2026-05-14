from pipx.util import _fix_subprocess_env


def test_pip_target_removed_from_env() -> None:
    env = {"PATH": "/usr/bin", "PIP_TARGET": "/some/custom/target"}
    result = _fix_subprocess_env(env)
    assert "PIP_TARGET" not in result


def test_pip_user_disabled_in_env() -> None:
    env = {"PATH": "/usr/bin", "PIP_USER": "1"}
    result = _fix_subprocess_env(env)
    assert result["PIP_USER"] == "0"
