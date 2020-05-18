from typing import Optional, Callable
from pipx import constants
from pipx.colors import bold
from pipx.commands.common import get_package_summary
from pipx.emojies import sleep
from pipx.venv import VenvContainer

Pool: Optional[Callable]
try:
    # Instantiating a Pool() attempts to import multiprocessing.synchronize,
    # which fails if the underlying OS does not support semaphores.
    # Here, we import ahead of time to decide which Pool implementation to use:
    # one backed by Processes (the default), or one backed by Threads
    import multiprocessing.synchronize  # noqa: F401
except ImportError:
    Pool = None
else:
    from multiprocessing import Pool


def list_packages(venv_container: VenvContainer):
    dirs = list(sorted(venv_container.iter_venv_dirs()))
    if not dirs:
        print(f"nothing has been installed with pipx {sleep}")
        return

    print(f"venvs are in {bold(str(venv_container))}")
    print(f"apps are exposed on your $PATH at {bold(str(constants.LOCAL_BIN_DIR))}")

    venv_container.verify_shared_libs()

    if Pool:
        with Pool() as p:
            for package_summary in p.map(get_package_summary, dirs):
                print(package_summary)
    else:
        for d in dirs:
            package_summary = get_package_summary(d)
            print(package_summary)
