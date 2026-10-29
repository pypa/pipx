from __future__ import annotations

__lazy_modules__ = [
    "packaging.specifiers",
    "packaging.utils",
    "pathlib",
    "pipx.backends._base",
    "pipx.redact",
    "pipx.util",
    "pipx.wrap",
    "re",
    "tomllib",
    "urllib.parse",
]

import logging
import os
import re
import stat
import sys
import tomllib
import urllib.parse
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Final, TypeAlias

from packaging.specifiers import SpecifierSet
from packaging.utils import InvalidName, canonicalize_name

from pipx.backends._base import PIP
from pipx.emojis import HAZARD
from pipx.redact import redact_url_credentials
from pipx.util import PipxError
from pipx.wrap import pipx_wrap

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from packaging.requirements import Requirement

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

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
# pip install's long options taking a value, from pip's cli/cmdoptions.py and commands/install.py
_PIP_VALUE_OPTIONS: Final[frozenset[str]] = frozenset({
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
# a later upgrade or reinstall replays what pipx records, possibly as root, so a one-shot input or an output location
# recorded here would be read or written again after its directory has changed hands
_PIP_ONE_SHOT_OPTIONS: Final[frozenset[str]] = frozenset({
    "-r",
    "--requirement",
    "--requirements",
    "--requirements-from-script",
    "--group",
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
# recorded options naming what to install from, what to trust or where uv reads its configuration, by file or
# directory
_PIP_SOURCE_PATH_OPTIONS: Final[frozenset[str]] = frozenset({
    "-b",
    "-c",
    "-f",
    "--build-constraint",
    "--build-constraints",
    "--cert",
    "--client-cert",
    "--config-file",
    "--constraint",
    "--constraints",
    "--directory",
    "--exclude",
    "--excludes",
    "--find-links",
    "--override",
    "--overrides",
    "--project",
})
# value-taking options a recorded snapshot may carry, as their (uv, pip) spellings
_VALUE_OPTION_SPELLINGS: Final[dict[str, tuple[str, str]]] = {
    **dict.fromkeys(("--default-index", "--index-url", "-i"), ("--default-index", "--index-url")),
    **dict.fromkeys(("--index", "--extra-index-url"), ("--index", "--extra-index-url")),
    **dict.fromkeys(("--find-links", "-f"), ("--find-links", "--find-links")),
    **dict.fromkeys(("--constraints", "--constraint", "-c"), ("--constraints", "--constraint")),
    **dict.fromkeys(("--allow-insecure-host", "--trusted-host"), ("--allow-insecure-host", "--trusted-host")),
    **{option: (option, option) for option in ("--keyring-provider", "--index-strategy", "--prerelease")},
}


def parse_specifier_for_install(package_spec: str, pip_args: list[str]) -> tuple[str, list[str]]:
    pip_args = pip_args.copy()
    parsed_package: Final[_ParsedPackage] = _parse_specifier(package_spec)
    package_or_url: Final[str] = _parsed_package_to_package_or_url(parsed_package, remove_version_specifiers=False)
    if "--editable" in pip_args and not isinstance(parsed_package, _LocalPath):
        _LOGGER.warning(
            pipx_wrap(
                f"""
                {HAZARD}  Ignoring --editable install option. pipx disallows it
                for anything but a local path, to avoid having to create a new
                src/ directory.
                """,
                subsequent_indent=" " * 4,
            )
        )
        pip_args.remove("--editable")

    return package_or_url, absolute_path_pip_args(pip_args, Path.cwd())


def _parse_specifier(package_spec: str) -> _ParsedPackage:
    # match pip's PyPI precedence by checking local paths only for names that PyPI rejects
    if (valid_pep508 := _requirement(package_spec)) is not None:
        if not _is_archive_name(valid_pep508.name):
            return _Pep508(requirement=valid_pep508)
        if not (package_path := Path(valid_pep508.name).expanduser()).exists():
            msg = f"{package_path} does not exist"
            raise PipxError(msg)
        if valid_pep508.specifier or valid_pep508.url or valid_pep508.marker:
            msg = f"Only extras can follow the local archive {package_path}"
            raise PipxError(msg)
        # keep the extras as typed so the bare and ./ spellings store the same spec
        return _LocalPath(path=f"{package_path.resolve()}{_split_path_extras(package_spec.strip())[1]}")

    parsed_url: Final[urllib.parse.SplitResult] = urllib.parse.urlsplit(package_spec)
    if parsed_url.scheme and (
        parsed_url.netloc or (parsed_url.scheme in {"file", "git+file", "hg+file"} and parsed_url.path.startswith("/"))
    ):
        return _Url(url=package_spec)

    package_path_str, package_extras_str = _split_path_extras(package_spec)
    if (package_path := Path(package_path_str).expanduser()).exists():
        return _LocalPath(path=f"{package_path.resolve()}{package_extras_str}")

    msg = f"Unable to parse package spec: {redact_url_credentials(package_spec)}"
    raise PipxError(msg)


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


@dataclass(frozen=True, slots=True, kw_only=True)
class _Pep508:
    requirement: Requirement


@dataclass(frozen=True, slots=True, kw_only=True)
class _Url:
    url: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _LocalPath:
    path: str


_ParsedPackage: TypeAlias = _Pep508 | _Url | _LocalPath


def _split_path_extras(package_spec: str) -> tuple[str, str]:
    # a bracket can be part of a directory name, so only a trailing group on a path that does not exist is extras
    if Path(package_spec).expanduser().exists():
        return package_spec, ""
    if extras_match := re.search(
        r"""
        (.+)           # the path
        (\[[^\[\]]+\])  # one trailing [extras] group
        $
        """,
        package_spec,
        re.VERBOSE,
    ):
        return extras_match.group(1), extras_match.group(2)
    return package_spec, ""


def _parsed_package_to_package_or_url(parsed_package: _ParsedPackage, *, remove_version_specifiers: bool) -> str:
    match parsed_package:
        case _Pep508(requirement=requirement):
            if requirement.marker is not None:
                _LOGGER.warning(
                    pipx_wrap(
                        f"""
                        {HAZARD}  Ignoring environment markers
                        ({requirement.marker}) in package
                        specification. Use pipx options to specify this type of
                        information.
                        """,
                        subsequent_indent=" " * 4,
                    )
                )
            package_or_url = _package_or_url_from_pep508(
                requirement, remove_version_specifiers=remove_version_specifiers
            )
        case _Url(url=url):
            package_or_url = url
        case _LocalPath(path=path):
            package_or_url = path

    _LOGGER.info("cleaned package spec: %s", redact_url_credentials(package_or_url))
    return package_or_url


def _package_or_url_from_pep508(requirement: Requirement, *, remove_version_specifiers: bool = False) -> str:
    requirement.marker = None
    requirement.name = canonicalize_name(requirement.name)
    if remove_version_specifiers:
        requirement.specifier = SpecifierSet("")
    return str(requirement)


def absolute_path_pip_args(pip_args: list[str], base: Path) -> list[str]:
    return _render(_absolute_paths(_parse_pip_args(pip_args), base))


def _render(arguments: Iterable[_PipArgument]) -> list[str]:
    return [token for argument in arguments for token in argument.tokens]


def _absolute_paths(arguments: list[_PipArgument], base: Path) -> list[_PipArgument]:
    # --group takes a group name, with an optional pyproject.toml path in front of it
    return [
        replace(argument, value=_absolute_path_value(argument.value, base))
        if argument.value is not None
        and argument.name != "--group"
        and (argument.name in _PIP_ONE_SHOT_OPTIONS or argument.name in _PIP_SOURCE_PATH_OPTIONS)
        else argument
        for argument in arguments
    ]


def _absolute_path_value(value: str, base: Path) -> str:
    # pip writes --report - to stdout
    if value == "-" or urllib.parse.urlsplit(value).scheme:
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
    if (name := _long_option_name(spelled)) is None:
        return _unresolved_long_option(argument, arguments)
    if separator and name in _LONG_FLAGS:
        # pip rejects a value given to a flag, so keep it as typed
        return _PipArgument(name=argument)
    if name in _LONG_FLAGS:
        return _PipArgument(name=name)
    if separator:
        return _PipArgument(name=name, value=value, separator=separator)
    return _PipArgument(name=name, value=next(arguments, None))


def _unresolved_long_option(argument: str, arguments: Iterator[str]) -> _PipArgument:
    spelled, separator, value = argument.partition("=")
    # an older pip, with fewer options, can take a prefix this table finds ambiguous, so keep it as typed, with the
    # value the option it names there takes; a prefix that could also name a flag, as --b could
    # --break-system-packages, may take none, so the next argument stays its own
    candidates: Final[frozenset[str]] = _prefixed_options(spelled, _PIP_VALUE_OPTIONS | _PIP_LONG_FLAGS)
    if separator and candidates & _PIP_VALUE_OPTIONS:
        return _PipArgument(name=spelled, value=value, separator=separator)
    if candidates and candidates <= _PIP_VALUE_OPTIONS:
        return _PipArgument(name=spelled, value=next(arguments, None))
    # pip rejects an unknown option, so keep it as typed
    return _PipArgument(name=argument)


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
    if spelled in uv_value_options or spelled in _LONG_FLAGS:
        return spelled
    return _pip_long_option_name(spelled)


def _pip_long_option_name(spelled: str) -> str | None:
    if spelled in (pip_options := _PIP_VALUE_OPTIONS | _PIP_LONG_FLAGS):
        return spelled
    match list(_prefixed_options(spelled, pip_options)):
        case [option]:
            return option
        case _:
            return None


def _prefixed_options(spelled: str, options: frozenset[str]) -> frozenset[str]:
    # pip, through optparse, takes any unambiguous prefix of its own long options; "--" alone ends the options
    return frozenset(option for option in options if option.startswith(spelled)) if spelled != "--" else frozenset()


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


def install_specs(install_args: list[str]) -> list[tuple[str, bool]]:
    specs: Final[list[tuple[str, bool]]] = []
    for argument in _parse_pip_args(install_args):
        if argument.name in {"-e", "--editable"} and argument.value is not None:
            specs.append((argument.value, True))
        elif not argument.name.startswith("-"):
            specs.append((argument.name, False))
    return specs


def recordable_pip_args(pip_args: list[str]) -> list[str]:
    return _render(_without_one_shot(_parse_pip_args(pip_args)))


def _without_one_shot(arguments: list[_PipArgument]) -> list[_PipArgument]:
    return [argument for argument in arguments if not _may_name(argument, _PIP_ONE_SHOT_OPTIONS)]


def _may_name(argument: _PipArgument, options: frozenset[str]) -> bool:
    # pip 24.0 reads --requirem as --requirement, a prefix the later --requirements-from-script made ambiguous
    return argument.name in options or (
        argument.value is not None
        and argument.name.startswith("--")
        and _long_option_name(argument.name) is None
        and bool(_prefixed_options(argument.name, options))
    )


def replayable_pip_args(pip_args: list[str], venv_dir: Path) -> list[str]:
    # the record's installer ran in the venv root, so a relative path resolves there, never against the caller's
    # working directory, which another account may control
    return _render(_absolute_paths(_without_one_shot(_parse_pip_args(pip_args)), venv_dir))


def trusted_recorded_pip_args(pip_args: list[str], venv_dir: Path) -> list[str]:
    if (source := changeable_recorded_source(pip_args, venv_dir)) is not None:
        msg: Final[str] = (
            f"{venv_dir.name}: refusing to replay {source}, and with it what gets installed. Move the file or "
            "directory to a place only you and root can change, or pass the options again with --pip-args to use "
            "them for this run."
        )
        # a wrapped line would split a long path
        raise PipxError(msg, wrap_message=False)
    return pip_args


def changeable_recorded_source(pip_args: list[str], venv_dir: Path) -> str | None:
    for argument in _parse_pip_args(pip_args):
        if (location := _changeable_source(argument, venv_dir)) is not None:
            recorded: Final[str] = " ".join(map(redact_url_credentials, argument.tokens))
            return f"the recorded {recorded}: another account can change {location}"
    return None


def _changeable_source(argument: _PipArgument, base: Path) -> Path | None:
    if argument.value is None:
        return None
    if _may_name(argument, _PIP_SOURCE_PATH_OPTIONS):
        # uv splits a --find-links value on commas, pip takes it whole
        values: set[str] = {argument.value, *argument.value.split(",")}
    elif _may_name(
        argument,
        frozenset({"-i", "--default-index", "--extra", "--extra-index-url", "--index", "--index-url", "--pypi-url"}),
    ):
        # index options whose value can be a local directory, with pip reading uv's --extra as --extra-index-url; uv
        # takes a named index as name=url
        name, separator, url = argument.value.partition("=")
        values = {argument.value, url} if separator and re.fullmatch(r"[A-Za-z0-9._-]+", name) else {argument.value}
    else:
        return None
    return next(filter(None, (_changeable_by_others(value, base) for value in sorted(values))), None)


def _changeable_by_others(value: str, base: Path) -> Path | None:
    url: Final[urllib.parse.SplitResult] = urllib.parse.urlsplit(value)
    if url.scheme not in {"", "file"}:
        return None
    # the installer runs in the venv root, where a relative index directory resolves
    return changeable_by_others(base / (urllib.parse.unquote(url.path) if url.scheme else value))


def changeable_by_others(path: Path) -> Path | None:
    if sys.platform == "win32":
        return None
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


def translate_pip_args(pip_args: list[str], backend: str, environment: str) -> tuple[list[str], list[str]]:
    # keeping the recorded index stops a snapshot moved to the other backend from installing from PyPI instead
    to_pip: Final[bool] = backend == PIP
    translated: Final[list[str]] = []
    dropped: Final[list[str]] = []
    arguments: Final[Iterator[str]] = iter(pip_args)
    for argument in arguments:
        flag, value = _split_option(argument if to_pip else _expand_pip_abbreviation(argument), arguments)
        spelling = _VALUE_OPTION_SPELLINGS.get(flag, (flag, flag))
        match spelling[0]:
            case "--no-index":
                translated.append(flag)
            case "--pre" | "--prerelease" if flag == "--pre" or value == "allow":
                translated.extend(["--pre"] if to_pip else ["--prerelease", "allow"])
            case "--prerelease":
                dropped.extend([flag, value])
            case "--index":
                # uv takes a named index as name=url, and the name means nothing to pip
                name, _, url = value.partition("=")
                translated.extend([spelling[to_pip], url if url and re.fullmatch(r"[A-Za-z0-9._-]+", name) else value])
            case "--find-links":
                # uv splits a --find-links value on commas, pip takes it as one location
                translated.extend(
                    part for link in (value.split(",") if to_pip else [value]) for part in (spelling[to_pip], link)
                )
            case "--default-index" | "--constraints":
                translated.extend([spelling[to_pip], value])
            case "--allow-insecure-host" if "://" not in value:
                translated.extend([spelling[to_pip], value])
            case "--keyring-provider" if value in {"disabled", "subprocess"}:
                translated.extend([flag, value])
            case "--index-strategy" if value == "unsafe-best-match":
                pass  # pip always picks the best match across its indexes
            case "--allow-insecure-host" | "--keyring-provider" | "--index-strategy":
                msg = (
                    f"Cannot install {environment} with the {backend} backend: its recorded index option {flag} "
                    f"{redact_url_credentials(value)} has no {backend} equivalent, and dropping it could install from "
                    "a different index."
                )
                raise PipxError(msg)
            case _:
                dropped.append(argument)
    return translated, dropped


def _split_option(argument: str, arguments: Iterator[str]) -> tuple[str, str]:
    flag, _, value = argument.partition("=") if argument.startswith("--") else (argument[:2], "", argument[2:])
    if flag not in _VALUE_OPTION_SPELLINGS:
        return argument, ""
    return flag, value or next(arguments, "")


def _expand_pip_abbreviation(argument: str) -> str:
    # pip accepts any unambiguous prefix of a long option: a pip recording can hold --index-u for --index-url
    flag, separator, value = argument.partition("=")
    if not flag.startswith("--") or (name := _pip_long_option_name(flag)) is None:
        return argument
    return f"{name}{separator}{value}"


def resolve_local_path(package_spec: str) -> str:
    return parsed.path if isinstance(parsed := _parse_specifier(package_spec), _LocalPath) else package_spec


def parse_specifier_for_metadata(package_spec: str) -> str:
    return _parsed_package_to_package_or_url(_parse_specifier(package_spec), remove_version_specifiers=False)


def parse_specifier_for_upgrade(package_spec: str) -> str:
    return _parsed_package_to_package_or_url(_parse_specifier(package_spec), remove_version_specifiers=True)


def get_extras(package_spec: str) -> set[str]:
    match _parse_specifier(package_spec):
        case _Pep508(requirement=requirement):
            return requirement.extras
        case _LocalPath(path=path):
            from packaging.requirements import Requirement  # ruff:ignore[import-outside-top-level]  # parser slows startup

            return Requirement(f"notapackage{_split_path_extras(path)[1]}").extras
        case _Url():
            return set()


def source_without_extras(package_spec: str) -> str:
    match _parse_specifier(package_spec):
        case _Pep508(requirement=requirement):
            requirement.extras = set()
            return _package_or_url_from_pep508(requirement)
        case _Url(url=url):
            return url
        case _LocalPath(path=path):
            return _split_path_extras(path)[0]


def add_extras(package_or_url: str, package_name: str, extras: set[str]) -> str:
    parsed_package: Final[_ParsedPackage] = _parse_specifier(package_or_url)
    if isinstance(parsed_package, _Pep508):
        parsed_package.requirement.extras |= extras
        return str(parsed_package.requirement)
    merged: Final[str] = ",".join(sorted(get_extras(package_or_url) | extras))
    if isinstance(parsed_package, _Url):
        return f"{package_name}[{merged}] @ {parsed_package.url}"
    return f"{_split_path_extras(parsed_package.path)[0]}[{merged}]"


def valid_pypi_name(package_spec: str) -> str | None:
    if (package_req := _requirement(package_spec)) is None:
        return None
    # a URL spec can name a package other than the one it points at, and an archive-like name can be a local file;
    # either way the name has to come from the package itself
    if package_req.url or _is_archive_name(package_req.name):
        return None
    return canonicalize_name(package_req.name)


def local_project_name(package_spec: str) -> str | None:
    # Path() reads a URL as a relative path (http://host/x is http:/host/x), so files below the working directory could
    # otherwise name the environment for a remote spec
    if not isinstance(parsed := _parse_specifier(package_spec), _LocalPath):
        return None
    return static_project_name(parsed.path) or wheel_project_name(parsed.path)


def static_project_name(package_spec: str) -> str | None:
    try:
        with (Path(_split_path_extras(package_spec)[0]) / "pyproject.toml").open("rb") as file:
            pyproject: Final = tomllib.load(file)
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


def _valid_name(name: str) -> str | None:
    try:
        canonicalize_name(name, validate=True)
    except InvalidName:
        return None
    return name


def wheel_project_name(package_spec: str) -> str | None:
    if (wheel := Path(_split_path_extras(package_spec)[0])).suffix != ".whl":
        return None
    import zipfile  # ruff:ignore[import-outside-top-level]  # slows startup
    from email.parser import BytesHeaderParser  # ruff:ignore[import-outside-top-level]  # slows startup

    try:
        with zipfile.ZipFile(wheel) as archive:
            match [entry for entry in archive.namelist() if re.fullmatch(r"[^/]+\.dist-info/METADATA", entry)]:
                case [metadata]:
                    name: Final = BytesHeaderParser().parsebytes(archive.read(metadata))["Name"]
                case _:
                    return None
    except (OSError, zipfile.BadZipFile):
        return None
    # a non-ASCII header comes back as an email Header object, never a valid project name
    return _valid_name(name) if isinstance(name, str) else None


def package_spec_satisfied(package_spec: str, package_name: str, installed_version: str, installed_spec: str) -> bool:
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
    index_args: Final[list[str]] = []
    other_args: Final[list[str]] = []
    for argument in _parse_pip_args(pip_args):
        if argument.name in value_options and argument.value is None:
            msg = f"Missing value for {argument.name!r} in --pip-args."
            raise PipxError(msg)
        is_index: bool = argument.name in value_options or argument.name == "--no-index"
        (index_args if is_index else other_args).extend(argument.tokens)
    return index_args, other_args


def replace_index_options(pip_args: list[str], index_args: list[str]) -> list[str]:
    return [*_split_index_options(pip_args)[1], *index_args]


def fix_package_name(package_or_url: str, package_name: str) -> str:
    if (package_req := _requirement(package_or_url)) is None:
        return package_or_url

    if _is_archive_name(package_req.name):
        return str(package_req)

    if canonicalize_name(package_req.name) != canonicalize_name(package_name):
        _LOGGER.warning(
            pipx_wrap(
                f"""
                {HAZARD}  Name supplied in package specifier was
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
    "changeable_by_others",
    "changeable_recorded_source",
    "extract_index_options",
    "fix_package_name",
    "get_extras",
    "install_specs",
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
    "translate_pip_args",
    "trusted_recorded_pip_args",
    "valid_pypi_name",
    "wheel_project_name",
]
