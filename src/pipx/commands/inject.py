import sys
import textwrap
from pathlib import Path
from typing import List, Optional

from pipx import constants
from pipx.colors import bold
from pipx.commands.common import package_name_from_spec, run_post_install_actions
from pipx.emojies import stars
from pipx.util import PipxError
from pipx.venv import Venv


def inject(
    venv_dir: Path,
    package_name: Optional[str],
    package_spec: str,
    pip_args: List[str],
    *,
    verbose: bool,
    include_apps: bool,
    include_dependencies: bool,
    force: bool,
):
    if not venv_dir.exists() or not next(venv_dir.iterdir()):
        raise PipxError(
            textwrap.dedent(
                f"""\
            Can't inject {package_spec!r} into nonexistent Virtual Environment {str(venv_dir)!r}.
            Be sure to install the package first with pipx install {venv_dir.name!r}
            before injecting into it."""
            )
        )

    venv = Venv(venv_dir, verbose=verbose)

    # package_spec is anything pip-installable, including package_name, vcs spec,
    #   zip file, or tar.gz file.
    if package_name is None:
        package_name = package_name_from_spec(
            package_spec, venv.python, pip_args=pip_args, verbose=verbose
        )

    venv.install_package(
        package=package_name,
        package_or_url=package_spec,
        pip_args=pip_args,
        include_dependencies=include_dependencies,
        include_apps=include_apps,
        is_main_package=False,
    )
    if include_apps:
        run_post_install_actions(
            venv,
            package_name,
            constants.LOCAL_BIN_DIR,
            venv_dir,
            include_dependencies,
            force=force,
        )

    print(f"  injected package {bold(package_name)} into venv {bold(venv_dir.name)}")
    print(f"done! {stars}", file=sys.stderr)
