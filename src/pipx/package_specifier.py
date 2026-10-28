# Valid package specifiers for pipx:
#   PEP508-compliant
#   git+<URL>
#   <URL>
#   <pypi_package_name>
#   <pypi_package_name><version_specifier>
#   <local_path>

from __future__ import annotations

__lazy_modules__ = ["packaging.specifiers", "packaging.utils", "pathlib", "pipx.util", "re", "tomllib", "urllib.parse"]

import logging
import re
import tomllib
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from packaging.specifiers import SpecifierSet
from packaging.utils import InvalidName, canonicalize_name

from pipx.emojis import hazard
from pipx.util import PipxError, pipx_wrap, redact_url_credentials

if TYPE_CHECKING:
    from packaging.requirements import Requirement

logger = logging.getLogger(__name__)

_LOCAL_FILE_SCHEMES: Final[frozenset[str]] = frozenset({"file", "git+file", "hg+file"})
_PIP_PATH_OPTIONS: Final[frozenset[str]] = frozenset({"-c", "--constraint", "-f", "--find-links"})
_PIP_ATTACHED_PATH_OPTIONS: Final[frozenset[str]] = frozenset({"-c", "-f"})
_SHORT_OPTION_LEN: Final[int] = 2
# pip's and uv's spellings, since a uv environment records options as uv pip install accepts them
_PIP_INDEX_VALUE_OPTIONS: Final[frozenset[str]] = frozenset({
    "-f",
    "-i",
    "--allow-insecure-host",
    "--default-index",
    "--extra-index-url",
    "--find-links",
    "--index",
    "--index-strategy",
    "--index-url",
    "--keyring-provider",
    "--trusted-host",
})


@dataclass(frozen=True)
class ParsedPackage:
    valid_pep508: Requirement | None
    valid_url: str | None
    valid_local_path: str | None


def _split_path_extras(package_spec: str) -> tuple[str, str]:
    """Returns (path, extras_string)"""
    # a bracket can be part of a directory name, so only a trailing group on a path that does not exist is extras
    if Path(package_spec).expanduser().exists():
        return (package_spec, "")
    package_spec_extras_re = re.search(
        r"""
        (.+)           # the path
        (\[[^\[\]]+\])  # one trailing [extras] group
        $
        """,
        package_spec,
        re.VERBOSE,
    )
    if package_spec_extras_re:
        return (package_spec_extras_re.group(1), package_spec_extras_re.group(2))
    return (package_spec, "")


def _check_package_path(package_path: str) -> tuple[Path, bool]:
    pkg_path: Final[Path] = Path(package_path).expanduser()
    pkg_path_exists = pkg_path.exists()

    return (pkg_path, pkg_path_exists)


def _parse_specifier(package_spec: str) -> ParsedPackage:
    """Parse package_spec as would be given to pipx"""
    # Match pip's PyPI precedence by checking local paths only for names that PyPI rejects.
    valid_pep508 = _requirement(package_spec)
    valid_url = None
    valid_local_path = None

    if valid_pep508 and _is_archive_name(valid_pep508.name):
        # It might be a local archive
        (package_path, package_path_exists) = _check_package_path(valid_pep508.name)

        if package_path_exists:
            if valid_pep508.specifier or valid_pep508.url or valid_pep508.marker:
                msg = f"Only extras can follow the local archive {package_path}"
                raise PipxError(msg)
            # keep the extras as typed so the bare and ./ spellings store the same spec
            valid_local_path = f"{package_path.resolve()}{_split_path_extras(package_spec.strip())[1]}"
        else:
            msg = f"{package_path} does not exist"
            raise PipxError(msg)

    # If this looks like a URL, treat it as such.
    if not valid_pep508:
        parsed_url = urllib.parse.urlsplit(package_spec)
        if parsed_url.scheme and (
            parsed_url.netloc or (parsed_url.scheme in _LOCAL_FILE_SCHEMES and parsed_url.path.startswith("/"))
        ):
            valid_url = package_spec

    if not valid_pep508 and not valid_url:
        (package_path_str, package_extras_str) = _split_path_extras(package_spec)
        (package_path, package_path_exists) = _check_package_path(package_path_str)
        if package_path_exists:
            valid_local_path = str(package_path.resolve()) + package_extras_str

    if not valid_pep508 and not valid_url and not valid_local_path:
        msg = f"Unable to parse package spec: {redact_url_credentials(package_spec)}"
        raise PipxError(msg)

    if valid_pep508 and valid_local_path:
        # It is a valid local path without "./"
        # Use valid_local_path
        valid_pep508 = None

    return ParsedPackage(
        valid_pep508=valid_pep508,
        valid_url=valid_url,
        valid_local_path=valid_local_path,
    )


def _requirement(package_spec: str) -> Requirement | None:
    from packaging.requirements import (  # ruff:ignore[import-outside-top-level]  # parser slows startup
        InvalidRequirement,
        Requirement,
    )

    try:
        return Requirement(package_spec)
    except InvalidRequirement:
        return None


def _is_archive_name(name: str) -> bool:
    # same extensions and case folding as pip's is_archive_file (pip._internal.utils.filetypes)
    return name.lower().endswith((
        ".whl",
        ".zip",
        ".tar.bz2",
        ".tbz",
        ".tar.gz",
        ".tgz",
        ".tar",
        ".tar.xz",
        ".txz",
        ".tlz",
        ".tar.lz",
        ".tar.lzma",
    ))


def package_or_url_from_pep508(requirement: Requirement, *, remove_version_specifiers: bool = False) -> str:
    requirement.marker = None
    requirement.name = canonicalize_name(requirement.name)
    if remove_version_specifiers:
        requirement.specifier = SpecifierSet("")
    return str(requirement)


def _parsed_package_to_package_or_url(parsed_package: ParsedPackage, *, remove_version_specifiers: bool) -> str:
    if parsed_package.valid_pep508 is not None:
        if parsed_package.valid_pep508.marker is not None:
            logger.warning(
                pipx_wrap(
                    f"""
                    {hazard}  Ignoring environment markers
                    ({parsed_package.valid_pep508.marker}) in package
                    specification. Use pipx options to specify this type of
                    information.
                    """,
                    subsequent_indent=" " * 4,
                )
            )
        package_or_url = package_or_url_from_pep508(
            parsed_package.valid_pep508,
            remove_version_specifiers=remove_version_specifiers,
        )
    elif parsed_package.valid_url is not None:
        package_or_url = parsed_package.valid_url
    elif parsed_package.valid_local_path is not None:
        package_or_url = parsed_package.valid_local_path

    logger.info("cleaned package spec: %s", redact_url_credentials(package_or_url))
    return package_or_url


def parse_specifier_for_install(package_spec: str, pip_args: list[str]) -> tuple[str, list[str]]:
    """Return package_or_url and pip_args suitable for pip install

    Specifically:
    * Strip any markers (e.g. python_version > "3.4")
    * Ensure --editable is removed for any package_spec not a local path
    * Convert local paths to absolute paths
    """
    pip_args = pip_args.copy()
    parsed_package = _parse_specifier(package_spec)
    package_or_url = _parsed_package_to_package_or_url(parsed_package, remove_version_specifiers=False)
    if "--editable" in pip_args and not parsed_package.valid_local_path:
        logger.warning(
            pipx_wrap(
                f"""
                {hazard}  Ignoring --editable install option. pipx disallows it
                for anything but a local path, to avoid having to create a new
                src/ directory.
                """,
                subsequent_indent=" " * 4,
            )
        )
        pip_args.remove("--editable")

    for index in range(len(pip_args)):
        option = pip_args[index]
        if (
            len(option) > _SHORT_OPTION_LEN
            and (option_name := option[:2]) in _PIP_ATTACHED_PATH_OPTIONS
            and option[2] != "="
        ):
            value = option[2:]
            if not urllib.parse.urlsplit(value).scheme:
                pip_args[index] = f"{option_name}{Path(value).expanduser().resolve()}"
            continue

        option_name, separator, value = option.partition("=")
        if option_name not in _PIP_PATH_OPTIONS:
            continue

        if separator:
            if not urllib.parse.urlsplit(value).scheme:
                pip_args[index] = f"{option_name}={Path(value).expanduser().resolve()}"
            continue

        argument_index = index + 1
        if argument_index < len(pip_args) and not urllib.parse.urlsplit(pip_args[argument_index]).scheme:
            pip_args[argument_index] = str(Path(pip_args[argument_index]).expanduser().resolve())

    return package_or_url, pip_args


def parse_specifier_for_metadata(package_spec: str) -> str:
    """Return package_or_url suitable for pipx metadata

    Specifically:
    * Strip any markers (e.g. python_version > 3.4)
    * Convert local paths to absolute paths
    """
    parsed_package = _parse_specifier(package_spec)
    return _parsed_package_to_package_or_url(parsed_package, remove_version_specifiers=False)


def parse_specifier_for_upgrade(package_spec: str) -> str:
    """Return package_or_url suitable for pip upgrade

    Specifically:
    * Strip any version specifiers (e.g. package == 1.5.4)
    * Strip any markers (e.g. python_version > 3.4)
    * Convert local paths to absolute paths
    """
    parsed_package = _parse_specifier(package_spec)
    return _parsed_package_to_package_or_url(parsed_package, remove_version_specifiers=True)


def get_extras(package_spec: str) -> set[str]:
    parsed_package = _parse_specifier(package_spec)
    if parsed_package.valid_pep508 and parsed_package.valid_pep508.extras is not None:
        return parsed_package.valid_pep508.extras
    if parsed_package.valid_local_path:
        from packaging.requirements import Requirement  # ruff:ignore[import-outside-top-level]  # parser slows startup

        (_, package_extras_str) = _split_path_extras(parsed_package.valid_local_path)
        return Requirement("notapackage" + package_extras_str).extras

    return set()


def valid_pypi_name(package_spec: str) -> str | None:
    if (package_req := _requirement(package_spec)) is None:
        return None

    if package_req.url or _is_archive_name(package_req.name):
        # package name supplied by user might not match package found in URL,
        # also if package name ends with archive extension, it might be a local archive file,
        #   so force package name determination the long way
        return None

    return canonicalize_name(package_req.name)


def local_project_name(package_spec: str) -> str | None:
    """Return the name a local project directory or wheel declares statically, or ``None`` for a URL or index spec."""
    # Path() reads a URL as a relative path (http://host/x is http:/host/x), so files below the working directory could
    # otherwise name the environment for a remote spec
    if (local_path := _parse_specifier(package_spec).valid_local_path) is None:
        return None
    return static_project_name(local_path) or wheel_project_name(local_path)


def static_project_name(package_spec: str) -> str | None:
    """Return the name a local project directory declares statically in its pyproject.toml, if any."""
    try:
        with (Path(_split_path_extras(package_spec)[0]) / "pyproject.toml").open("rb") as file:
            pyproject = tomllib.load(file)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None
    if not (
        _backend_reads_project_table(pyproject.get("build-system"))
        and isinstance(project := pyproject.get("project"), dict)
        and isinstance(name := project.get("name"), str)
        and isinstance(dynamic := project.get("dynamic", []), list)
        and "name" not in dynamic
    ):
        return None
    return _valid_name(name)


def _backend_reads_project_table(build_system: object) -> bool:
    # older poetry-core, setuptools and flit-core build from their own tables and ignore [project]
    minimum_versions: Final[dict[str, tuple[str, str | None]]] = {
        "flit_core.buildapi": ("flit-core", "3.2"),
        "hatchling.build": ("hatchling", None),
        "pdm.backend": ("pdm-backend", None),
        "poetry.core.masonry.api": ("poetry-core", "2"),
        "setuptools.build_meta": ("setuptools", "61"),
        "uv_build": ("uv-build", None),
    }
    if not (
        isinstance(build_system, dict)
        and "backend-path" not in build_system
        and isinstance(backend := build_system.get("build-backend"), str)
        and (known := minimum_versions.get(backend)) is not None
        and isinstance(requires := build_system.get("requires"), list)
    ):
        return False
    distribution, minimum = known
    return minimum is None or any(
        canonicalize_name(requirement.name) == distribution and _newest_allowed_reaches(requirement.specifier, minimum)
        for requirement in filter(None, (_requirement(entry) for entry in requires if isinstance(entry, str)))
    )


def _newest_allowed_reaches(specifier: SpecifierSet, minimum: str) -> bool:
    from packaging.version import InvalidVersion, Version  # ruff:ignore[import-outside-top-level]  # slows startup

    # an isolated build installs the newest version the specifier allows, so it reaches the minimum when the minimum is
    # allowed or a lower bound already sits at or above it
    if specifier.contains(minimum, prereleases=True):
        return True
    for clause in specifier:
        try:
            if clause.operator in {">=", ">", "==", "===", "~="} and Version(
                clause.version.removesuffix(".*")
            ) >= Version(minimum):
                return True
        except InvalidVersion:
            continue
    return False


def wheel_project_name(package_spec: str) -> str | None:
    """Return the name a local wheel declares in its metadata, if it has exactly one top-level ``.dist-info``."""
    if (wheel := Path(_split_path_extras(package_spec)[0])).suffix != ".whl":
        return None
    import zipfile  # ruff:ignore[import-outside-top-level]  # slows startup
    from email.parser import BytesHeaderParser  # ruff:ignore[import-outside-top-level]  # slows startup

    try:
        with zipfile.ZipFile(wheel) as archive:
            match [entry for entry in archive.namelist() if re.fullmatch(r"[^/]+\.dist-info/METADATA", entry)]:
                case [metadata]:
                    name = BytesHeaderParser().parsebytes(archive.read(metadata))["Name"]
                case _:
                    return None
    except (OSError, zipfile.BadZipFile):
        return None
    # a non-ASCII header comes back as an email Header object, never a valid project name
    return _valid_name(name) if isinstance(name, str) else None


def _valid_name(name: str) -> str | None:
    try:
        canonicalize_name(name, validate=True)
    except InvalidName:
        return None
    return name


def package_spec_satisfied(
    package_spec: str,
    package_name: str,
    installed_version: str,
    installed_spec: str,
) -> bool:
    """Return whether an installed package satisfies a named requirement."""
    if (requirement := _requirement(package_spec)) is None or (
        installed_requirement := _requirement(installed_spec)
    ) is None:
        return False
    return (
        requirement.url is None
        and canonicalize_name(requirement.name) == canonicalize_name(package_name)
        and requirement.extras.issubset(installed_requirement.extras)
        and requirement.specifier.contains(installed_version)
    )


def extract_index_options(pip_args: list[str]) -> list[str]:
    return _split_index_options(pip_args)[0]


def replace_index_options(pip_args: list[str], index_args: list[str]) -> list[str]:
    return [*_split_index_options(pip_args)[1], *index_args]


def _split_index_options(pip_args: list[str]) -> tuple[list[str], list[str]]:
    index_args: list[str] = []
    other_args: list[str] = []
    iterator = iter(pip_args)
    for argument in iterator:
        if argument == "--no-index":
            index_args.append(argument)
            continue
        option, separator = argument.partition("=")[:2]
        if option in _PIP_INDEX_VALUE_OPTIONS:
            try:
                index_args.extend([argument] if separator else [argument, next(iterator)])
            except StopIteration as error:
                msg = f"Missing value for {option!r} in --pip-args."
                raise PipxError(msg) from error
        elif len(argument) > _SHORT_OPTION_LEN and argument[:2] in {"-f", "-i"}:
            index_args.append(argument)
        else:
            other_args.append(argument)
    return index_args, other_args


def fix_package_name(package_or_url: str, package_name: str) -> str:
    if (package_req := _requirement(package_or_url)) is None:
        return package_or_url

    if _is_archive_name(package_req.name):
        return str(package_req)

    if canonicalize_name(package_req.name) != canonicalize_name(package_name):
        logger.warning(
            pipx_wrap(
                f"""
                {hazard}  Name supplied in package specifier was
                {package_req.name!r} but package found has name {package_name!r}.
                Using {package_name!r}.
                """,
                subsequent_indent=" " * 4,
            )
        )
    package_req.name = package_name

    return str(package_req)


__all__ = [
    "extract_index_options",
    "fix_package_name",
    "get_extras",
    "local_project_name",
    "package_spec_satisfied",
    "parse_specifier_for_install",
    "parse_specifier_for_metadata",
    "parse_specifier_for_upgrade",
    "replace_index_options",
    "static_project_name",
    "valid_pypi_name",
    "wheel_project_name",
]
