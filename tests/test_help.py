from helpers import run_pipx_cli
from pipx.main import get_command_parser


def test_help(capsys):
    try:
        run_pipx_cli(["--help"])
    except SystemExit:
        flag_capture = capsys.readouterr()
        assert "usage: pipx [-h]" in flag_capture.out

    try:
        run_pipx_cli(["help"])
    except SystemExit:
        command_capture = capsys.readouterr()
        assert "usage: pipx [-h]" in command_capture.out

    assert flag_capture == command_capture


def test_help_with_subcommands(capsys):
    parser, _ = get_command_parser()
    # The following line generates an attribute error from the linter, but executes normally
    valid_commands = parser._subparsers._actions[4].choices.keys()  # First four actions contain None
    for command in valid_commands:
        try:
            run_pipx_cli([command, "--help"])
        except SystemExit:
            flag_capture = capsys.readouterr()
            assert "usage: pipx " + command in flag_capture.out

        try:
            run_pipx_cli(["help", command])
        except SystemExit:
            command_capture = capsys.readouterr()
            assert "usage: pipx " + command in flag_capture.out

        assert flag_capture == command_capture


def test_help_with_multiple_subcommands(capsys):
    try:
        run_pipx_cli(["install", "cowsaypy", "black", "--help"])
    except SystemExit:
        flag_capture = capsys.readouterr()
        assert "usage: pipx install" in flag_capture.out

    try:
        run_pipx_cli(["help", "install", "cowsaypy", "black"])
    except SystemExit:
        command_capture = capsys.readouterr()
        assert "usage: pipx install" in flag_capture.out

    assert flag_capture == command_capture

    try:
        run_pipx_cli(["interpreter", "list", "--help"])
    except SystemExit:
        flag_capture = capsys.readouterr()
        assert "usage: pipx interpreter list" in flag_capture.out

    try:
        run_pipx_cli(["help", "interpreter", "list"])
    except SystemExit:
        command_capture = capsys.readouterr()
        assert "usage: pipx interpreter list" in flag_capture.out

    assert flag_capture == command_capture

    try:
        run_pipx_cli(["interpreter", "prune", "--help"])
    except SystemExit:
        flag_capture = capsys.readouterr()
        assert "usage: pipx interpreter prune" in flag_capture.out

    try:
        run_pipx_cli(["help", "interpreter", "prune"])
    except SystemExit:
        command_capture = capsys.readouterr()
        assert "usage: pipx interpreter prune" in flag_capture.out

    assert flag_capture == command_capture

    try:
        run_pipx_cli(["interpreter", "upgrade", "--help"])
    except SystemExit:
        flag_capture = capsys.readouterr()
        assert "usage: pipx interpreter upgrade" in flag_capture.out

    try:
        run_pipx_cli(["help", "interpreter", "upgrade"])
    except SystemExit:
        command_capture = capsys.readouterr()
        assert "usage: pipx interpreter upgrade" in flag_capture.out

    assert flag_capture == command_capture
