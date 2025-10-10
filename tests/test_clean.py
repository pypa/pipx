"""Unit tests for the clean command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from pipx.commands.clean_cmd import (
    _cache_cleanup,
    _cleanup_directory,
    _confirm_action,
    _full_cleanup,
    _logs_cleanup,
    _trash_cleanup,
    _venvs_cleanup,
    clean,
)
from pipx.constants import (
    EXIT_CODE_CACHE_CLEANUP_FAIL,
    EXIT_CODE_FULL_CLEANUP_FAIL,
    EXIT_CODE_LOGS_CLEANUP_FAIL,
    EXIT_CODE_OK,
    EXIT_CODE_TRASH_CLEANUP_FAIL,
    EXIT_CODE_VENVS_CLEANUP_FAIL,
)
from pipx.paths import ctx


@pytest.fixture
def mock_venv_container():
    """Mock VenvContainer for testing venv cleanup."""
    with patch("pipx.commands.clean_cmd.VenvContainer") as mock_container:
        yield mock_container


class TestCleanupDirectory:
    """Tests for _cleanup_directory helper function."""

    def test_cleanup_existing_directory(self, pipx_temp_env, capsys):
        """Test cleaning up an existing directory."""
        test_dir = ctx.home / "test_dir"
        test_dir.mkdir(parents=True)
        (test_dir / "test_file.txt").touch()

        result = _cleanup_directory(
            path=test_dir,
            description="test directory",
            error_code=EXIT_CODE_CACHE_CLEANUP_FAIL,
            verbose=False,
        )

        assert result == EXIT_CODE_OK
        assert not test_dir.exists()
        captured = capsys.readouterr()
        assert "test directory" in captured.out.lower()
        assert "removed" in captured.out.lower()

    def test_cleanup_nonexistent_directory_verbose(self, pipx_temp_env, capsys):
        """Test cleaning up a non-existent directory with verbose output."""
        test_dir = ctx.home / "nonexistent"

        result = _cleanup_directory(
            path=test_dir,
            description="nonexistent directory",
            error_code=EXIT_CODE_CACHE_CLEANUP_FAIL,
            verbose=True,
        )

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        assert "skipping" in captured.out.lower()
        assert "doesn't exist" in captured.out.lower()

    def test_cleanup_nonexistent_directory_not_verbose(self, pipx_temp_env, capsys):
        """Test cleaning up a non-existent directory without verbose output."""
        test_dir = ctx.home / "nonexistent"

        result = _cleanup_directory(
            path=test_dir,
            description="nonexistent directory",
            error_code=EXIT_CODE_CACHE_CLEANUP_FAIL,
            verbose=False,
        )

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_cleanup_directory_with_error(self, pipx_temp_env, capsys):
        """Test cleanup when removal fails."""
        test_dir = ctx.home / "test_dir"
        test_dir.mkdir(parents=True)

        with patch("pipx.commands.clean_cmd.rmdir") as mock_rmdir:
            mock_rmdir.side_effect = PermissionError("Permission denied")

            result = _cleanup_directory(
                path=test_dir,
                description="test directory",
                error_code=EXIT_CODE_CACHE_CLEANUP_FAIL,
                verbose=False,
            )

        assert result == EXIT_CODE_CACHE_CLEANUP_FAIL
        captured = capsys.readouterr()
        assert "error" in captured.out.lower()
        assert "permission denied" in captured.out.lower()

    def test_cleanup_directory_verbose_output(self, pipx_temp_env, capsys):
        """Test verbose output includes path information."""
        test_dir = ctx.home / "test_dir"
        test_dir.mkdir(parents=True)

        result = _cleanup_directory(
            path=test_dir,
            description="test directory",
            error_code=EXIT_CODE_CACHE_CLEANUP_FAIL,
            verbose=True,
        )

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        assert str(test_dir) in captured.out
        assert "path:" in captured.out.lower()


class TestConfirmAction:
    """Tests for _confirm_action helper function."""

    def test_confirm_yes(self, monkeypatch):
        """Test confirmation with 'yes'."""
        monkeypatch.setattr("builtins.input", lambda _: "yes")
        assert _confirm_action("Continue?") is True

    def test_confirm_y(self, monkeypatch):
        """Test confirmation with 'y'."""
        monkeypatch.setattr("builtins.input", lambda _: "y")
        assert _confirm_action("Continue?") is True

    def test_confirm_no(self, monkeypatch):
        """Test confirmation with 'no'."""
        monkeypatch.setattr("builtins.input", lambda _: "no")
        assert _confirm_action("Continue?") is False

    def test_confirm_n(self, monkeypatch):
        """Test confirmation with 'n'."""
        monkeypatch.setattr("builtins.input", lambda _: "n")
        assert _confirm_action("Continue?") is False

    def test_confirm_empty(self, monkeypatch):
        """Test confirmation with empty input (defaults to no)."""
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert _confirm_action("Continue?") is False

    def test_confirm_invalid_then_yes(self, monkeypatch, capsys):
        """Test confirmation with invalid input followed by yes."""
        responses = iter(["invalid", "maybe", "y"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))

        assert _confirm_action("Continue?") is True
        captured = capsys.readouterr()
        assert captured.out.count("Please answer") == 2

    def test_confirm_case_insensitive(self, monkeypatch):
        """Test confirmation is case-insensitive."""
        monkeypatch.setattr("builtins.input", lambda _: "YES")
        assert _confirm_action("Continue?") is True

        monkeypatch.setattr("builtins.input", lambda _: "No")
        assert _confirm_action("Continue?") is False


class TestCacheCleanup:
    """Tests for _cache_cleanup function."""

    def test_cache_cleanup_success(self, pipx_temp_env, capsys):
        """Test successful cache cleanup."""
        cache_subdir = ctx.venv_cache / "test_cache"
        cache_subdir.mkdir(parents=True, exist_ok=True)
        (ctx.venv_cache / "file.txt").touch()

        result = _cache_cleanup(verbose=False)

        assert result == EXIT_CODE_OK
        assert not ctx.venv_cache.exists()

    def test_cache_cleanup_nonexistent(self, pipx_temp_env):
        """Test cache cleanup when directory doesn't exist."""
        if ctx.venv_cache.exists():
            ctx.venv_cache.rmdir()

        result = _cache_cleanup(verbose=False)

        assert result == EXIT_CODE_OK

    def test_cache_cleanup_verbose(self, pipx_temp_env, capsys):
        """Test cache cleanup with verbose output."""
        cache_subdir = ctx.venv_cache / "test_cache"
        cache_subdir.mkdir(parents=True, exist_ok=True)

        result = _cache_cleanup(verbose=True)

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        assert "cache" in captured.out.lower()


class TestLogsCleanup:
    """Tests for _logs_cleanup function."""

    def test_logs_cleanup_success(self, pipx_temp_env):
        """Test successful logs cleanup."""
        ctx.logs.mkdir(parents=True, exist_ok=True)
        (ctx.logs / "pipx.log").touch()
        (ctx.logs / "old.log").touch()

        result = _logs_cleanup(verbose=False)

        assert result == EXIT_CODE_OK
        assert not ctx.logs.exists()

    def test_logs_cleanup_nonexistent(self, pipx_temp_env):
        """Test logs cleanup when directory doesn't exist."""
        if ctx.logs.exists():
            ctx.logs.rmdir()

        result = _logs_cleanup(verbose=False)

        assert result == EXIT_CODE_OK

    def test_logs_cleanup_verbose(self, pipx_temp_env, capsys):
        """Test logs cleanup with verbose output."""
        ctx.logs.mkdir(parents=True, exist_ok=True)
        (ctx.logs / "pipx.log").touch()

        result = _logs_cleanup(verbose=True)

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        assert "logs" in captured.out.lower()


class TestTrashCleanup:
    """Tests for _trash_cleanup function."""

    def test_trash_cleanup_success(self, pipx_temp_env):
        """Test successful trash cleanup."""
        trash_subdir = ctx.trash / "deleted_venv"
        trash_subdir.mkdir(parents=True, exist_ok=True)
        (ctx.trash / "old_file").touch()

        result = _trash_cleanup(verbose=False)

        assert result == EXIT_CODE_OK
        assert not ctx.trash.exists()

    def test_trash_cleanup_nonexistent(self, pipx_temp_env):
        """Test trash cleanup when directory doesn't exist."""
        if ctx.trash.exists():
            ctx.trash.rmdir()

        result = _trash_cleanup(verbose=False)

        assert result == EXIT_CODE_OK

    def test_trash_cleanup_verbose(self, pipx_temp_env, capsys):
        """Test trash cleanup with verbose output."""
        trash_subdir = ctx.trash / "deleted_venv"
        trash_subdir.mkdir(parents=True, exist_ok=True)

        result = _trash_cleanup(verbose=True)

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        assert "trash" in captured.out.lower()


class TestVenvsCleanup:
    """Tests for _venvs_cleanup function."""

    def test_venvs_cleanup_success(self, pipx_temp_env, mock_venv_container, capsys):
        """Test successful cleanup of all venvs."""
        venv_names = ["package1", "package2", "package3"]
        venv_paths = []

        for name in venv_names:
            venv_dir = ctx.venvs / name
            venv_dir.mkdir(parents=True, exist_ok=True)
            (venv_dir / "pyvenv.cfg").touch()
            venv_paths.append(venv_dir)

        mock_instance = mock_venv_container.return_value
        mock_instance.iter_venv_dirs.return_value = venv_paths

        result = _venvs_cleanup(verbose=False)

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        assert "3" in captured.out
        assert "package" in captured.out.lower()

    def test_venvs_cleanup_no_packages(self, pipx_temp_env, mock_venv_container, capsys):
        """Test cleanup when no packages are installed."""
        mock_instance = mock_venv_container.return_value
        mock_instance.iter_venv_dirs.return_value = []

        result = _venvs_cleanup(verbose=False)

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_venvs_cleanup_no_packages_verbose(self, pipx_temp_env, mock_venv_container, capsys):
        """Test cleanup with no packages and verbose output."""
        mock_instance = mock_venv_container.return_value
        mock_instance.iter_venv_dirs.return_value = []

        result = _venvs_cleanup(verbose=True)

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        assert "no installed packages" in captured.out.lower()

    def test_venvs_cleanup_with_failures(self, pipx_temp_env, mock_venv_container, capsys):
        """Test cleanup when some packages fail to remove."""
        venv_names = ["package1", "package2", "package3"]
        venv_paths = []

        for name in venv_names:
            venv_dir = ctx.venvs / name
            venv_dir.mkdir(parents=True, exist_ok=True)
            venv_paths.append(venv_dir)

        mock_instance = mock_venv_container.return_value
        mock_instance.iter_venv_dirs.return_value = venv_paths

        call_count = {"count": 0}

        def rmdir_side_effect(path):
            call_count["count"] += 1
            if call_count["count"] == 2:
                raise PermissionError("Cannot remove package2")

        with patch("pipx.commands.clean_cmd.rmdir", side_effect=rmdir_side_effect):
            result = _venvs_cleanup(verbose=False)

        assert result == EXIT_CODE_VENVS_CLEANUP_FAIL
        captured = capsys.readouterr()
        assert "failed" in captured.out.lower()
        assert "package2" in captured.out

    def test_venvs_cleanup_with_failures_verbose(self, pipx_temp_env, mock_venv_container, capsys):
        """Test cleanup failure with verbose output."""
        venv_names = ["package1", "package2", "package3"]
        venv_paths = []

        for name in venv_names:
            venv_dir = ctx.venvs / name
            venv_dir.mkdir(parents=True, exist_ok=True)
            venv_paths.append(venv_dir)

        mock_instance = mock_venv_container.return_value
        mock_instance.iter_venv_dirs.return_value = venv_paths

        call_count = {"count": 0}

        def rmdir_side_effect(path, safe_rm):
            call_count["count"] += 1
            if call_count["count"] == 2:
                raise PermissionError("Cannot remove package2")

        with patch("pipx.commands.clean_cmd.rmdir", side_effect=rmdir_side_effect):
            result = _venvs_cleanup(verbose=True)

        assert result == EXIT_CODE_VENVS_CLEANUP_FAIL
        captured = capsys.readouterr()
        assert "failed" in captured.out.lower()
        assert "package2" in captured.out
        assert "Cannot remove package2" in captured.out

    def test_venvs_cleanup_verbose(self, pipx_temp_env, mock_venv_container, capsys):
        """Test cleanup with verbose output."""
        venv_names = ["package1", "package2", "package3"]
        venv_paths = []

        for name in venv_names:
            venv_dir = ctx.venvs / name
            venv_dir.mkdir(parents=True, exist_ok=True)
            venv_paths.append(venv_dir)

        mock_instance = mock_venv_container.return_value
        mock_instance.iter_venv_dirs.return_value = venv_paths

        result = _venvs_cleanup(verbose=True)

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        for package in venv_names:
            assert package in captured.out


class TestFullCleanup:
    """Tests for _full_cleanup function."""

    def test_full_cleanup_success(self, pipx_temp_env, capsys):
        """Test full cleanup removes everything."""
        venv_dir = ctx.venvs / "package1"
        ctx.venv_cache.mkdir(parents=True, exist_ok=True)
        ctx.logs.mkdir(parents=True, exist_ok=True)
        (ctx.venv_cache / "cache_file").touch()
        (ctx.logs / "log.txt").touch()

        result = _full_cleanup(verbose=False)

        assert result == EXIT_CODE_OK
        assert not ctx.home.exists()
        captured = capsys.readouterr()
        assert "warning" in captured.out.lower()
        assert "all pipx data" in captured.out.lower()

    def test_full_cleanup_warning_message(self, pipx_temp_env, capsys):
        """Test that full cleanup shows appropriate warnings."""
        result = _full_cleanup(verbose=False)

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        assert "warning" in captured.out.lower()
        assert "all installed packages will be lost" in captured.out.lower()

    def test_full_cleanup_with_error(self, pipx_temp_env, capsys):
        """Test full cleanup handles errors when directory cannot be removed."""
        # Ensure the home directory exists and has content
        ctx.home.mkdir(parents=True, exist_ok=True)
        test_file = ctx.home / "test.txt"
        test_file.touch()

        # Verify the directory exists before the test
        assert ctx.home.exists()

        # Patch rmdir in the clean module to raise an exception
        with patch("pipx.commands.clean_cmd.rmdir") as mock_rmdir:
            mock_rmdir.side_effect = Exception("Cannot remove directory")

            result = _full_cleanup(verbose=False)
        assert result == EXIT_CODE_FULL_CLEANUP_FAIL
        captured = capsys.readouterr()
        # The error message should be printed
        assert "error" in captured.out.lower() or "cannot remove" in captured.out.lower()

    def test_full_cleanup_verbose(self, pipx_temp_env, capsys):
        """Test full cleanup with verbose output."""
        venv_dir = ctx.venvs / "package1"
        venv_dir.mkdir(parents=True, exist_ok=True)

        result = _full_cleanup(verbose=True)

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        assert "path:" in captured.out.lower()


class TestCleanCommand:
    """Tests for the main clean command."""

    def test_clean_with_force_no_options(self, pipx_temp_env, capsys):
        """Test clean with force flag and no specific options (full cleanup)."""
        venv_dir = ctx.venvs / "package1"
        venv_dir.mkdir(parents=True, exist_ok=True)

        result = clean(force=True, verbose=False)

        assert result == EXIT_CODE_OK
        assert not ctx.home.exists()

    def test_clean_without_force_cancelled(self, pipx_temp_env, monkeypatch, capsys):
        """Test clean without force when user cancels."""
        monkeypatch.setattr("builtins.input", lambda _: "n")
        ctx.home.mkdir(parents=True, exist_ok=True)

        result = clean(force=False, verbose=False)

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()
        assert ctx.home.exists()

    def test_clean_without_force_confirmed(self, pipx_temp_env, monkeypatch):
        """Test clean without force when user confirms."""
        monkeypatch.setattr("builtins.input", lambda _: "y")
        ctx.home.mkdir(parents=True, exist_ok=True)
        (ctx.home / "some_file").touch()

        result = clean(force=False, verbose=False)

        assert result == EXIT_CODE_OK
        assert not ctx.home.exists()

    def test_clean_cache_only(self, pipx_temp_env, monkeypatch):
        """Test cleaning only cache."""
        monkeypatch.setattr("builtins.input", lambda _: "y")
        ctx.venv_cache.mkdir(parents=True, exist_ok=True)
        ctx.logs.mkdir(parents=True, exist_ok=True)
        ctx.trash.mkdir(parents=True, exist_ok=True)
        ctx.venvs.mkdir(parents=True, exist_ok=True)
        (ctx.venv_cache / "test").touch()
        (ctx.logs / "test.log").touch()
        (ctx.trash / "old").touch()

        result = clean(cache=True, force=False, verbose=False)

        assert result == EXIT_CODE_OK
        assert not ctx.venv_cache.exists()
        assert ctx.logs.exists()
        assert ctx.trash.exists()
        assert ctx.venvs.exists()

    def test_clean_logs_only(self, pipx_temp_env, monkeypatch):
        """Test cleaning only logs."""
        monkeypatch.setattr("builtins.input", lambda _: "y")
        ctx.logs.mkdir(parents=True, exist_ok=True)
        ctx.venv_cache.mkdir(parents=True, exist_ok=True)
        (ctx.venv_cache / "test").touch()
        (ctx.logs / "test.log").touch()

        result = clean(logs=True, force=False, verbose=False)

        assert result == EXIT_CODE_OK
        assert not ctx.logs.exists()
        assert ctx.venv_cache.exists()

    def test_clean_trash_only(self, pipx_temp_env, monkeypatch):
        """Test cleaning only trash."""
        monkeypatch.setattr("builtins.input", lambda _: "y")
        ctx.trash.mkdir(parents=True, exist_ok=True)
        ctx.venvs.mkdir(parents=True, exist_ok=True)
        (ctx.trash / "old").touch()
        (ctx.venvs / "package1").mkdir(parents=True, exist_ok=True)
        (ctx.venvs / "package1" / "pyvenv.cfg").touch()

        result = clean(trash=True, force=False, verbose=False)

        assert result == EXIT_CODE_OK
        assert not ctx.trash.exists()
        assert ctx.venvs.exists()

    def test_clean_venvs_only(self, pipx_temp_env, monkeypatch, mock_venv_container):
        """Test cleaning only venvs."""
        monkeypatch.setattr("builtins.input", lambda _: "y")

        venv_names = ["package1", "package2"]
        venv_paths = []
        for name in venv_names:
            venv_dir = ctx.venvs / name
            venv_dir.mkdir(parents=True, exist_ok=True)
            venv_paths.append(venv_dir)

        mock_instance = mock_venv_container.return_value
        mock_instance.iter_venv_dirs.return_value = venv_paths

        result = clean(venvs=True, force=False, verbose=False)

        assert result == EXIT_CODE_OK

    def test_clean_multiple_options(self, pipx_temp_env, monkeypatch, mock_venv_container):
        """Test cleaning multiple components at once."""
        monkeypatch.setattr("builtins.input", lambda _: "y")
        ctx.venv_cache.mkdir(parents=True, exist_ok=True)
        ctx.logs.mkdir(parents=True, exist_ok=True)
        (ctx.venv_cache / "test").touch()
        (ctx.logs / "test.log").touch()

        venv_names = ["package1", "package2"]
        venv_paths = []
        for name in venv_names:
            venv_dir = ctx.venvs / name
            venv_dir.mkdir(parents=True, exist_ok=True)
            venv_paths.append(venv_dir)

        mock_instance = mock_venv_container.return_value
        mock_instance.iter_venv_dirs.return_value = venv_paths

        result = clean(cache=True, logs=True, venvs=True, force=False, verbose=False)

        assert result == EXIT_CODE_OK
        assert not ctx.venv_cache.exists()
        assert not ctx.logs.exists()

    def test_clean_with_partial_failures(self, pipx_temp_env, monkeypatch):
        """Test clean when some operations fail."""
        monkeypatch.setattr("builtins.input", lambda _: "y")

        with patch("pipx.commands.clean_cmd._cache_cleanup") as mock_cache:
            with patch("pipx.commands.clean_cmd._logs_cleanup") as mock_logs:
                mock_cache.return_value = EXIT_CODE_CACHE_CLEANUP_FAIL
                mock_logs.return_value = EXIT_CODE_OK

                result = clean(cache=True, logs=True, force=False, verbose=False)

        assert result == EXIT_CODE_CACHE_CLEANUP_FAIL

    def test_clean_combines_multiple_failures(self, pipx_temp_env, monkeypatch):
        """Test that multiple failures are combined in exit code."""
        monkeypatch.setattr("builtins.input", lambda _: "y")

        with patch("pipx.commands.clean_cmd._cache_cleanup") as mock_cache:
            with patch("pipx.commands.clean_cmd._logs_cleanup") as mock_logs:
                mock_cache.return_value = EXIT_CODE_CACHE_CLEANUP_FAIL
                mock_logs.return_value = EXIT_CODE_LOGS_CLEANUP_FAIL

                result = clean(cache=True, logs=True, force=False, verbose=False)

        expected = EXIT_CODE_CACHE_CLEANUP_FAIL | EXIT_CODE_LOGS_CLEANUP_FAIL
        assert result == expected

    def test_clean_verbose_mode(self, pipx_temp_env, monkeypatch, capsys):
        """Test clean with verbose output."""
        monkeypatch.setattr("builtins.input", lambda _: "y")
        cache_dir = ctx.venv_cache / "test"
        cache_dir.mkdir(parents=True, exist_ok=True)

        result = clean(cache=True, force=False, verbose=True)

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        assert "path:" in captured.out.lower()

    def test_clean_force_skips_confirmation(self, pipx_temp_env, monkeypatch, capsys):
        """Test that force flag skips confirmation prompt."""
        input_called = {"called": False}

        def mock_input(_):
            input_called["called"] = True
            return "n"

        monkeypatch.setattr("builtins.input", mock_input)

        result = clean(cache=True, force=True, verbose=False)

        assert result == EXIT_CODE_OK
        assert not input_called["called"], "Input should not be called when force=True"

    def test_clean_no_options_requires_confirmation(self, pipx_temp_env, monkeypatch, capsys):
        """Test full cleanup requires confirmation when force not set."""
        monkeypatch.setattr("builtins.input", lambda _: "n")
        ctx.home.mkdir(parents=True, exist_ok=True)
        (ctx.home / "some_file").touch()

        result = clean(force=False, verbose=False)

        assert result == EXIT_CODE_OK
        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()
        assert ctx.home.exists()
        assert (ctx.home / "some_file").exists()

    def test_clean_preserves_unselected_directories(self, pipx_temp_env, monkeypatch):
        """Test that cleaning one component doesn't affect others."""
        monkeypatch.setattr("builtins.input", lambda _: "y")

        ctx.venv_cache.mkdir(parents=True, exist_ok=True)
        ctx.logs.mkdir(parents=True, exist_ok=True)
        ctx.trash.mkdir(parents=True, exist_ok=True)
        (ctx.venv_cache / "cache_file").touch()
        (ctx.logs / "log_file").touch()
        (ctx.trash / "trash_file").touch()
        venv_dir = ctx.venvs / "package1"
        venv_dir.mkdir(parents=True, exist_ok=True)

        result = clean(cache=True, force=False, verbose=False)

        assert result == EXIT_CODE_OK
        assert not ctx.venv_cache.exists()
        assert ctx.logs.exists()
        assert ctx.trash.exists()
        assert ctx.venvs.exists()
