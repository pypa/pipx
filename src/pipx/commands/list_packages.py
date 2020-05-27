from functools import partial
from pathlib import Path
from typing import Callable, Collection, Optional

from pipx import constants
from pipx.colors import bold
from pipx.commands.common import get_package_summary
from pipx.emojies import sleep
from pipx.venv import VenvContainer

Pool: Optional[Callable]
try:
    import multiprocessing.synchronize  # noqa: F401
    from multiprocessing import Pool
except ImportError:
    Pool = None


def list_packages(venv_container: VenvContainer, include_injected: bool) -> None:
    dirs: Collection[Path] = sorted(venv_container.iter_venv_dirs())
    if not dirs:
        print(f"nothing has been installed with pipx {sleep}")
        return

    print(f"venvs are in {bold(str(venv_container))}")
    print(f"apps are exposed on your $PATH at {bold(str(constants.LOCAL_BIN_DIR))}")

    venv_container.verify_shared_libs()

    if Pool:
        with Pool() as p:
            for package_summary in p.map(
                partial(get_package_summary, include_injected=include_injected), dirs,
            ):
                print(package_summary)
    else:
        for package_summary in map(
            partial(get_package_summary, include_injected=include_injected), dirs,
        ):
            print(package_summary)
