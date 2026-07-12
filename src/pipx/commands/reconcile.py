from dataclasses import replace
from pathlib import Path

from packaging.utils import canonicalize_name

from pipx import paths
from pipx.backends import PIP, resolve_backend_name
from pipx.commands.common import package_name_from_spec
from pipx.commands.install import install
from pipx.commands.reinstall import reinstall
from pipx.constants import EXIT_CODE_OK, ExitCode
from pipx.package_specifier import parse_specifier_for_install
from pipx.reconcile import ReconcileAction, ToolRequest, ToolState, plan_tool_request
from pipx.util import PipxError
from pipx.venv import Venv, VenvContainer


def reconcile_install(
    package_specs: list[str],
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str,
    pip_args: list[str],
    venv_args: list[str],
    verbose: bool,
    *,
    force: bool,
    include_dependencies: bool,
    preinstall_packages: list[str] | None,
    suffix: str,
    backend: str | None,
    env_backend: str | None,
    upgrade_strategy: str | None,
) -> ExitCode:
    if preinstall_packages:
        raise PipxError("--exact does not support --preinstall because pipx does not record preinstalled packages")

    venv_container = VenvContainer(paths.ctx.venvs)
    for package_spec in package_specs:
        package_name = package_name_from_spec(
            package_spec,
            python,
            pip_args=pip_args,
            verbose=verbose,
            backend=backend,
            env_backend=env_backend,
        )
        venv_dir = venv_container.get_venv_dir(f"{package_name}{suffix}")
        normalized_package_spec, normalized_pip_args = parse_specifier_for_install(package_spec, pip_args)
        requested_backend = (
            PIP
            if canonicalize_name(package_name) == PIP
            else resolve_backend_name(cli_value=backend, env_value=env_backend)[0]
        )
        request = ToolRequest(
            package_name=package_name,
            package_spec=normalized_package_spec,
            python=Path(python).resolve(),
            backend=requested_backend,
            pip_args=tuple(normalized_pip_args),
            venv_args=tuple(venv_args),
            include_dependencies=include_dependencies,
        )
        venv = Venv(venv_dir, verbose=verbose) if venv_dir.is_dir() and any(venv_dir.iterdir()) else None
        state = _tool_state(venv) if venv is not None else None
        plan = plan_tool_request(request, state)
        if state is not None and state.pinned and plan.action is not ReconcileAction.NOOP:
            raise PipxError(
                f"pipx cannot reconcile pinned package {package_name}; run `pipx unpin {package_name}` first"
            )
        if plan.action is ReconcileAction.NOOP:
            assert state is not None
            assert venv is not None
            if state.package_spec != normalized_package_spec:
                venv.pipx_metadata.main_package = replace(
                    venv.pipx_metadata.main_package,
                    package_or_url=normalized_package_spec,
                )
                venv.pipx_metadata.write()
            print(f"{package_name} {state.version} satisfies {package_spec}")
        elif plan.action in (ReconcileAction.INSTALL, ReconcileAction.UPGRADE):
            install(
                venv_dir,
                [package_name],
                [package_spec],
                local_bin_dir,
                local_man_dir,
                python,
                pip_args,
                venv_args,
                verbose,
                force=force if plan.action is ReconcileAction.INSTALL else False,
                reinstall=False,
                include_dependencies=include_dependencies,
                preinstall_packages=None,
                suffix=suffix,
                python_flag_passed=True,
                backend=requested_backend,
                env_backend=None,
                upgrade=plan.action is ReconcileAction.UPGRADE,
                upgrade_strategy=upgrade_strategy if plan.action is ReconcileAction.UPGRADE else None,
                always_upgrade=plan.action is ReconcileAction.UPGRADE,
            )
        else:
            print(f"Reinstalling {package_name} to reconcile {', '.join(reason.value for reason in plan.reasons)}")
            reinstall(
                venv_dir=venv_dir,
                local_bin_dir=local_bin_dir,
                local_man_dir=local_man_dir,
                python=python,
                verbose=verbose,
                python_flag_passed=True,
                backend=requested_backend,
                env_backend=None,
                package_spec=package_spec,
                pip_args=pip_args,
                venv_args=venv_args,
                include_dependencies=include_dependencies,
            )
    return EXIT_CODE_OK


def _tool_state(venv: Venv) -> ToolState:
    package = venv.pipx_metadata.main_package
    if package.package is None:
        raise PipxError(f"{venv.name} has no main package in its metadata")
    return ToolState(
        package_name=package.package,
        package_spec=package.package_or_url or package.package,
        version=package.package_version,
        source_interpreter=venv.pipx_metadata.source_interpreter,
        backend=venv.pipx_metadata.backend,
        pip_args=tuple(package.pip_args),
        venv_args=tuple(venv.pipx_metadata.venv_args),
        include_dependencies=package.include_dependencies,
        pinned=package.pinned,
    )


__all__ = [
    "reconcile_install",
]
