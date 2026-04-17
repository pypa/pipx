from __future__ import annotations

import sys

import pytest

from pipx.util import run_subprocess


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        pytest.param(None, "subprocess", id="defaults_to_subprocess"),
        pytest.param("import", "import", id="preserves_explicit"),
    ],
)
def test_subprocess_keyring_provider(monkeypatch: pytest.MonkeyPatch, env_value: str | None, expected: str) -> None:
    if env_value is not None:
        monkeypatch.setenv("PIP_KEYRING_PROVIDER", env_value)
    else:
        monkeypatch.delenv("PIP_KEYRING_PROVIDER", raising=False)

    result = run_subprocess([sys.executable, "-c", "import os; print(os.environ['PIP_KEYRING_PROVIDER'])"])

    assert result.stdout.strip() == expected


def test_subprocess_pythonsafepath_set_for_python_commands() -> None:
    """Test that PYTHONSAFEPATH is set for Python subprocess calls to prevent CWD shadowing (issue #1575)."""
    result = run_subprocess(
        [sys.executable, "-c", "import os, sys; sys.stdout.write(os.environ.get('PYTHONSAFEPATH', ''))"]
    )

    assert result.stdout == "1"
