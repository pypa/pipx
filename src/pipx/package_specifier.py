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
import os
import re
import stat
import sys
import tomllib
import urllib.parse
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

from packaging.specifiers import SpecifierSet
from packaging.utils import InvalidName, canonicalize_name

from pipx.emojis import hazard
from pipx.util import PipxError, pipx_wrap, redact_url_credentials

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from packaging.requirements import Requirement

logger = logging.getLogger(__name__)

_LOCAL_FILE_SCHEMES: Final[frozenset[str]] = frozenset({"file", "git+file", "hg+file"})
# pip install's long options, from pip's cli/cmdoptions.py and commands/install.py
_PIP_LONG_VALUE_OPTIONS: Final[frozenset[str]] = frozenset({
    "--abi",
    "--all-releases",
    "--build-constraint",
    "--cache-dir",
    "--cert",
    "--client-cert",
    "--config-settings",
    "--constraint",
    "--default-timeout",
    "--editable",
    "--exists-action",
    "--extra-index-url",
    "--find-links",
    "--group",
    "--implementation",
    "--index-url",
    "--keyring-provider",
    "--local-log",
    "--log",
    "--log-file",
    "--no-binary",
    "--only-binary",
    "--only-final",
    "--platform",
    "--prefix",
    "--progress-bar",
    "--proxy",
    "--pypi-url",
    "--python",
    "--python-version",
    "--refresh-package",
    "--report",
    "--requirement",
    "--requirements-from-script",
    "--resume-retries",
    "--retries",
    "--root",
    "--root-user-action",
    "--source",
    "--source-dir",
    "--source-directory",
    "--src",
    "--target",
    "--timeout",
    "--trusted-host",
    "--upgrade-strategy",
    "--uploaded-prior-to",
    "--use-deprecated",
    "--use-feature",
})
_PIP_LONG_FLAGS: Final[frozenset[str]] = frozenset({
    "--break-system-packages",
    "--check-build-dependencies",
    "--compile",
    "--debug",
    "--disable-pip-version-check",
    "--dry-run",
    "--force-reinstall",
    "--help",
    "--ignore-installed",
    "--ignore-requires-python",
    "--isolated",
    "--no-build-isolation",
    "--no-cache-dir",
    "--no-clean",
    "--no-color",
    "--no-compile",
    "--no-dependencies",
    "--no-deps",
    "--no-index",
    "--no-input",
    "--no-proxy-env",
    "--no-python-version-warning",
    "--no-require-hashes",
    "--no-user",
    "--no-warn-conflicts",
    "--no-warn-script-location",
    "--only-dependencies",
    "--only-deps",
    "--pre",
    "--prefer-binary",
    "--quiet",
    "--require-hashes",
    "--require-venv",
    "--require-virtualenv",
    "--upgrade",
    "--use-pep517",
    "--user",
    "--verbose",
    "--version",
})
# uv pip install's own flags, recorded for a uv environment
_LONG_FLAGS: Final[frozenset[str]] = _PIP_LONG_FLAGS | {
    "--all-extras",
    "--check",
    "--compile-bytecode",
    "--exact",
    "--managed-python",
    "--no-break-system-packages",
    "--no-build",
    "--no-cache",
    "--no-config",
    "--no-editable",
    "--no-managed-python",
    "--no-progress",
    "--no-python-downloads",
    "--no-sources",
    "--no-verify-hashes",
    "--offline",
    "--refresh",
    "--reinstall",
    "--require-build-hashes",
    "--strict",
    "--system",
    "--system-certs",
}
# a later upgrade or reinstall replays what pipx records, possibly as root, so a one-shot input or an output location
# recorded here would be read or written again after its directory has changed hands
_PIP_ONE_SHOT_OPTIONS: Final[frozenset[str]] = frozenset({
    "-r",
    "--requirement",
    "--requirements",
    "--requirements-from-script",
    "-t",
    "--target",
    "--root",
    "--prefix",
    "--src",
    "--source",
    "--source-dir",
    "--source-directory",
    "--report",
    "--log",
    "--log-file",
    "--local-log",
    "--cache-dir",
})
# recorded options naming what to install from or what to trust, by file or directory
_PIP_SOURCE_PATH_OPTIONS: Final[frozenset[str]] = frozenset({
    "-b",
    "-c",
    "-f",
    "--build-constraint",
    "--build-constraints",
    "--cert",
    "--client-cert",
    "--constraint",
    "--constraints",
    "--find-links",
})
# pip writes --report - to stdout
_PIP_STDOUT_VALUE: Final[str] = "-"


@dataclass(frozen=True)
class ParsedPackage:
    valid_pep508: Requirement | None
    valid_url: str | None
    valid_local_path: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class _PipArgument:
    name: str
    value: str | None = None
    # "=" or "" when the value shares the option's token, None when the value is a token of its own
    separator: str | None = None

    @property
    def tokens(self) -> list[str]:
        if self.value is None:
            return [self.name]
        if self.separator is None:
            return [self.name, self.value]
        return [f"{self.name}{self.separator}{self.value}"]


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

    return package_or_url, absolute_path_pip_args(pip_args, Path.cwd())


def absolute_path_pip_args(pip_args: list[str], base: Path) -> list[str]:
    return _render(_absolute_paths(_parse_pip_args(pip_args), base))


def _render(arguments: Iterable[_PipArgument]) -> list[str]:
    return [token for argument in arguments for token in argument.tokens]


def _absolute_paths(arguments: list[_PipArgument], base: Path) -> list[_PipArgument]:
    return [
        replace(argument, value=_absolute_path_value(argument.value, base))
        if argument.value is not None
        and (argument.name in _PIP_ONE_SHOT_OPTIONS or argument.name in _PIP_SOURCE_PATH_OPTIONS)
        else argument
        for argument in arguments
    ]


def _absolute_path_value(value: str, base: Path) -> str:
    if value == _PIP_STDOUT_VALUE or urllib.parse.urlsplit(value).scheme:
        return value
    return str((base / Path(value).expanduser()).resolve())


def _parse_pip_args(pip_args: list[str]) -> list[_PipArgument]:
    # read as pip's optparse does, so recording, replay and index handling all see the same options
    parsed: Final[list[_PipArgument]] = []
    arguments: Final[Iterator[str]] = iter(pip_args)
    for argument in arguments:
        if argument.startswith("--"):
            parsed.append(_long_option(argument, arguments))
        elif argument.startswith("-") and argument != "-":
            parsed.extend(_short_options(argument, arguments))
        else:
            parsed.append(_PipArgument(name=argument))
    return parsed


def _long_option(argument: str, arguments: Iterator[str]) -> _PipArgument:
    spelled, separator, value = argument.partition("=")
    if (name := _long_option_name(spelled)) is None or (separator and name in _LONG_FLAGS):
        # pip rejects an unknown or ambiguous option, and a value given to a flag, so keep those as typed
        return _PipArgument(name=argument)
    if name in _LONG_FLAGS:
        return _PipArgument(name=name)
    if separator:
        return _PipArgument(name=name, value=value, separator=separator)
    return _PipArgument(name=name, value=next(arguments, None))


def _long_option_name(spelled: str) -> str | None:
    # uv's own options taking a value; uv takes no abbreviations, and its full names must not be read as one of pip's,
    # such as --index for --index-url
    uv_value_options: Final[frozenset[str]] = frozenset({
        "--allow-insecure-host",
        "--build-constraints",
        "--color",
        "--config-file",
        "--config-setting",
        "--config-settings-package",
        "--constraints",
        "--default-index",
        "--directory",
        "--exclude",
        "--exclude-newer",
        "--exclude-newer-package",
        "--excludes",
        "--extra",
        "--fork-strategy",
        "--index",
        "--index-strategy",
        "--link-mode",
        "--no-build-isolation-package",
        "--no-editable-package",
        "--no-sources-package",
        "--output-format",
        "--override",
        "--overrides",
        "--prerelease",
        "--prerelease-package",
        "--project",
        "--python-platform",
        "--reinstall-package",
        "--requirements",
        "--resolution",
        "--torch-backend",
        "--upgrade-group",
        "--upgrade-package",
    })
    if spelled in _PIP_LONG_VALUE_OPTIONS or spelled in uv_value_options or spelled in _LONG_FLAGS:
        return spelled
    # pip, through optparse, takes any unambiguous prefix of its own long options
    match [option for option in _PIP_LONG_VALUE_OPTIONS | _PIP_LONG_FLAGS if option.startswith(spelled)]:
        case [option]:
            return option
        case _:
            return None


def _short_options(argument: str, arguments: Iterator[str]) -> list[_PipArgument]:
    # optparse reads -qr FILE as -q -r FILE: flags up to the first option taking a value, which takes the rest; pip's
    # and uv's short options together, as neither assigns a letter differently
    for index, letter in enumerate(argument[1:], start=1):
        if letter in "hnqvIUV":
            continue
        if letter not in "bcefiprtCP":
            return [_PipArgument(name=argument)]
        flags: Final[list[_PipArgument]] = [_PipArgument(name=argument[:index])] if index > 1 else []
        name: Final[str] = f"-{letter}"
        if not (attached := argument[index + 1 :]):
            return [*flags, _PipArgument(name=name, value=next(arguments, None))]
        if attached.startswith("="):
            # uv reads -f=DIR as -f DIR while pip reads the value =DIR, so give both the same separate value
            return [*flags, _PipArgument(name=name, value=attached[1:])]
        return [*flags, _PipArgument(name=name, value=attached, separator="")]
    return [_PipArgument(name=argument)]


def recordable_pip_args(pip_args: list[str]) -> list[str]:
    return _render(_without_one_shot(_parse_pip_args(pip_args)))


def _without_one_shot(arguments: list[_PipArgument]) -> list[_PipArgument]:
    return [argument for argument in arguments if argument.name not in _PIP_ONE_SHOT_OPTIONS]


def replayable_pip_args(pip_args: list[str], venv_dir: Path) -> list[str]:
    # the record's installer ran in the venv root, so a relative path resolves there, never against the caller's
    # working directory, which another account may control
    return _render(_absolute_paths(_without_one_shot(_parse_pip_args(pip_args)), venv_dir))


def trusted_recorded_pip_args(pip_args: list[str], venv_dir: Path) -> list[str]:
    for argument in _parse_pip_args(pip_args):
        if (location := _changeable_source(argument, venv_dir)) is not None:
            recorded: Final[str] = " ".join(map(redact_url_credentials, argument.tokens))
            msg = (
                f"{venv_dir.name}: refusing to replay the recorded {recorded}: another account can change {location}, "
                "and with it what gets installed. Move the file or directory to a place only you and root can change, "
                "or pass the options again with --pip-args to use them for this run."
            )
            # a wrapped line would split a long path
            raise PipxError(msg, wrap_message=False)
    return pip_args


def _changeable_source(argument: _PipArgument, base: Path) -> Path | None:
    if argument.value is None:
        return None
    if argument.name in _PIP_SOURCE_PATH_OPTIONS:
        # uv splits a --find-links value on commas, pip takes it whole
        values: set[str] = {argument.value, *argument.value.split(",")}
    elif argument.name in {
        "-i",
        "--default-index",
        "--extra",
        "--extra-index-url",
        "--index",
        "--index-url",
        "--pypi-url",
    }:
        # index options whose value can be a local directory, with pip reading uv's --extra as --extra-index-url; uv
        # takes a named index as name=url
        name, separator, url = argument.value.partition("=")
        values = {argument.value, url} if separator and re.fullmatch(r"[A-Za-z0-9._-]+", name) else {argument.value}
    else:
        return None
    return next(filter(None, (_changeable_by_others(value, base) for value in sorted(values))), None)


def _changeable_by_others(value: str, base: Path) -> Path | None:
    if sys.platform == "win32":
        return None
    url: Final[urllib.parse.SplitResult] = urllib.parse.urlsplit(value)
    if url.scheme not in {"", "file"}:
        return None
    # the installer runs in the venv root, where a relative index directory resolves
    path: Final[Path] = base / (urllib.parse.unquote(url.path) if url.scheme else value)
    trusted: Final[set[int]] = {0, os.geteuid()}
    # the sticky bit keeps others from replacing an entry they do not own, but not from adding one where none exists
    has_existing_child = False
    for location in (path, *path.parents):
        try:
            status = location.stat()
        except OSError:
            continue
        if status.st_uid not in trusted or (
            status.st_mode & stat.S_IWOTH and not (has_existing_child and status.st_mode & stat.S_ISVTX)
        ):
            return location
        has_existing_child = True
    return None


def resolve_local_path(package_spec: str) -> str:
    return _parse_specifier(package_spec).valid_local_path or package_spec


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


def source_without_extras(package_spec: str) -> str:
    """Return what package_spec installs from, without its extras: a normalized requirement, a URL or a local path."""
    parsed_package: Final[ParsedPackage] = _parse_specifier(package_spec)
    if parsed_package.valid_pep508 is not None:
        parsed_package.valid_pep508.extras = set()
        return package_or_url_from_pep508(parsed_package.valid_pep508)
    if parsed_package.valid_url is not None:
        return parsed_package.valid_url
    return _split_path_extras(cast("str", parsed_package.valid_local_path))[0]


def add_extras(package_or_url: str, package_name: str, extras: set[str]) -> str:
    """Return package_or_url with extras merged into the ones it already requests."""
    parsed_package: Final[ParsedPackage] = _parse_specifier(package_or_url)
    if parsed_package.valid_pep508 is not None:
        parsed_package.valid_pep508.extras |= extras
        return str(parsed_package.valid_pep508)
    merged: Final[str] = ",".join(sorted(get_extras(package_or_url) | extras))
    if parsed_package.valid_url is not None:
        return f"{package_name}[{merged}] @ {parsed_package.valid_url}"
    return f"{_split_path_extras(cast('str', parsed_package.valid_local_path))[0]}[{merged}]"


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
    # pip's and uv's spellings, since a uv environment records options as uv pip install accepts them
    value_options: Final[frozenset[str]] = frozenset({
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
        "--pypi-url",
        "--trusted-host",
    })
    index_args: list[str] = []
    other_args: list[str] = []
    for argument in _parse_pip_args(pip_args):
        if argument.name in value_options and argument.value is None:
            msg = f"Missing value for {argument.name!r} in --pip-args."
            raise PipxError(msg)
        is_index: bool = argument.name in value_options or argument.name == "--no-index"
        (index_args if is_index else other_args).extend(argument.tokens)
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
    "absolute_path_pip_args",
    "add_extras",
    "extract_index_options",
    "fix_package_name",
    "get_extras",
    "local_project_name",
    "package_spec_satisfied",
    "parse_specifier_for_install",
    "parse_specifier_for_metadata",
    "parse_specifier_for_upgrade",
    "recordable_pip_args",
    "replace_index_options",
    "replayable_pip_args",
    "resolve_local_path",
    "source_without_extras",
    "static_project_name",
    "trusted_recorded_pip_args",
    "valid_pypi_name",
    "wheel_project_name",
]
