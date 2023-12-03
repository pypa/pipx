# Valid package specifiers for pipx:
#   PEP508-compliant
#   git+<URL>
#   <URL>
#   <pypi_package_name>
#   <pypi_package_name><version_specifier>
#   <local_path>

import logging
import re
import urllib.parse
from pathlib import Path
from typing import List, NamedTuple, Optional, Set, Tuple

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

from pipx.emojis import hazard
from pipx.util import PipxError, pipx_wrap

logger = logging.getLogger(__name__)

ARCHIVE_EXTENSIONS = (".whl", ".tar.gz", ".zip")


class ParsedPackage(NamedTuple):
    valid_pep508: Optional[Requirement]
    valid_url: Optional[str]
    valid_local_path: Optional[str]


def _split_path_extras(package_spec: str) -> Tuple[str, str]:
    """Returns (path, extras_string)"""
    package_spec_extras_re = re.search(r"(.+)(\[.+\])", package_spec)
    if package_spec_extras_re:
        return (package_spec_extras_re.group(1), package_spec_extras_re.group(2))
    else:
        return (package_spec, "")


def _check_package_path(package_path: str) -> Tuple[Path, bool]:
    pkg_path = Path(package_path)
    pkg_path_exists = pkg_path.exists()

    return (pkg_path, pkg_path_exists)


def _parse_specifier(package_spec: str) -> ParsedPackage:
    """Parse package_spec as would be given to pipx"""
    # If package_spec is valid pypi name, pip will always treat it as a
    #       pypi package, not checking for local path.
    #       We replicate pypi precedence here (only non-valid-pypi names
    #       initiate check for local path, e.g. './package-name')
    valid_pep508 = None
    valid_url = None
    valid_local_path = None

    try:
        package_req = Requirement(package_spec)
    except InvalidRequirement:
        # not a valid PEP508 package specification
        pass
    else:
        # valid PEP508 package specification
        valid_pep508 = package_req

    if valid_pep508 and package_req.name.endswith(ARCHIVE_EXTENSIONS):
        # It might be a local archive
        (package_path, package_path_exists) = _check_package_path(package_req.name)

        if package_path_exists:
            valid_local_path = str(package_path.resolve())
        else:
            raise PipxError(f"{package_path} does not exist")

    # If this looks like a URL, treat it as such.
    if not valid_pep508:
        parsed_url = urllib.parse.urlsplit(package_spec)
        if parsed_url.scheme and parsed_url.netloc:
            valid_url = package_spec

    # Treat the input as a local path if it does not look like a PEP 508
    # specifier nor a URL. In this case we want to split out the extra part.
    if not valid_pep508 and not valid_url:
        (package_path_str, package_extras_str) = _split_path_extras(package_spec)
        (package_path, package_path_exists) = _check_package_path(package_path_str)
        if package_path_exists:
            valid_local_path = str(package_path.resolve()) + package_extras_str

    if not valid_pep508 and not valid_url and not valid_local_path:
        raise PipxError(f"Unable to parse package spec: {package_spec}")

    if valid_pep508 and valid_local_path:
        # It is a valid local path without "./"
        # Use valid_local_path
        valid_pep508 = None

    return ParsedPackage(
        valid_pep508=valid_pep508,
        valid_url=valid_url,
        valid_local_path=valid_local_path,
    )


def package_or_url_from_pep508(requirement: Requirement, remove_version_specifiers: bool = False) -> str:
    requirement.marker = None
    requirement.name = canonicalize_name(requirement.name)
    if remove_version_specifiers:
        requirement.specifier = SpecifierSet("")
    return str(requirement)


def _parsed_package_to_package_or_url(parsed_package: ParsedPackage, remove_version_specifiers: bool) -> str:
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

    logger.info(f"cleaned package spec: {package_or_url}")
    return package_or_url


def parse_specifier_for_install(package_spec: str, pip_args: List[str]) -> Tuple[str, List[str]]:
    """Return package_or_url and pip_args suitable for pip install

    Specifically:
    * Strip any markers (e.g. python_version > "3.4")
    * Ensure --editable is removed for any package_spec not a local path
    * Convert local paths to absolute paths
    """
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

    return (package_or_url, pip_args)


def parse_specifier_for_metadata(package_spec: str) -> str:
    """Return package_or_url suitable for pipx metadata

    Specifically:
    * Strip any markers (e.g. python_version > 3.4)
    * Convert local paths to absolute paths
    """
    parsed_package = _parse_specifier(package_spec)
    package_or_url = _parsed_package_to_package_or_url(parsed_package, remove_version_specifiers=False)
    return package_or_url


def parse_specifier_for_upgrade(package_spec: str) -> str:
    """Return package_or_url suitable for pip upgrade

    Specifically:
    * Strip any version specifiers (e.g. package == 1.5.4)
    * Strip any markers (e.g. python_version > 3.4)
    * Convert local paths to absolute paths
    """
    parsed_package = _parse_specifier(package_spec)
    package_or_url = _parsed_package_to_package_or_url(parsed_package, remove_version_specifiers=True)
    return package_or_url


def get_extras(package_spec: str) -> Set[str]:
    parsed_package = _parse_specifier(package_spec)
    if parsed_package.valid_pep508 and parsed_package.valid_pep508.extras is not None:
        return parsed_package.valid_pep508.extras
    elif parsed_package.valid_local_path:
        (_, package_extras_str) = _split_path_extras(parsed_package.valid_local_path)
        return Requirement("notapackage" + package_extras_str).extras

    return set()


def valid_pypi_name(package_spec: str) -> Optional[str]:
    try:
        package_req = Requirement(package_spec)
    except InvalidRequirement:
        # not a valid PEP508 package specification
        return None

    if package_req.url or package_req.name.endswith(ARCHIVE_EXTENSIONS):
        # package name supplied by user might not match package found in URL,
        # also if package name ends with archive extension, it might be a local archive file,
        #   so force package name determination the long way
        return None

    return canonicalize_name(package_req.name)


def fix_package_name(package_or_url: str, package_name: str) -> str:
    try:
        package_req = Requirement(package_or_url)
    except InvalidRequirement:
        # not a valid PEP508 package specification
        return package_or_url

    if package_req.name.endswith(ARCHIVE_EXTENSIONS):
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
