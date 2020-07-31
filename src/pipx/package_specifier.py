# Valid package specifiers for pipx:
#   PEP508-compliant
#   git+<URL>
#   <URL>
#   <pypi_package_name>
#   <pypi_package_name><version_specifier>

import logging
from pathlib import Path
from typing import NamedTuple, Optional

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from pipx.util import PipxError


class ParsedPackage(NamedTuple):
    valid_pep508: bool
    valid_url: bool
    valid_local_path: bool


def _parse_specifier(package_spec: str) -> ParsedPackage:
    """Parse package_spec as would be given to pip/pipx

    For ParsedPackage.package_or_url:
    * Strip any version specifiers (e.g. package == 1.5.4)
    * Strip any markers (e.g. python_version > 3.4)
    * Convert local paths to absolute paths
    """
    # NOTE: If package_spec is valid pypi name, pip will always treat it as a
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
        valid_pep508 = False
    else:
        # valid PEP508 package specification
        valid_pep508 = package_req
        if package_req.url:
            package_or_url = package_req.url
        else:
            if package_req.extras:
                package_or_url = canonicalize_name(
                    package_req.name + "[" + ",".join(sorted(package_req.extras)) + "]"
                )
            else:
                package_or_url = canonicalize_name(package_req.name)

    # NOTE: packaging currently (2020-07-19) does basic syntax checks on the URL.
    #   Some examples of what it will not catch:
    #       - invalid RCS string (e.g. "gat+https://...")
    #       - non-existent scheme (e.g. "zzzzz://...")
    if not valid_pep508:
        try:
            package_req = Requirement("notapackagename @ " + package_spec)
        except InvalidRequirement:
            valid_url = None
        else:
            valid_url = package_spec

    if not valid_pep508 and not valid_url:
        package_path = Path(package_spec)
        try:
            package_path_exists = package_path.exists()
        except OSError:
            package_path_exists = False

        if package_path_exists:
            valid_local_path = str(package_path.resolve())

    if not valid_pep508 and not valid_url and not valid_local_path:
        raise PipxError(f"Unable to parse package spec: {package_spec}")

    return ParsedPackage(
        valid_pep508=valid_pep508,
        valid_url=valid_url,
        valid_local_path=valid_local_path,
    )


def package_is_local_path(package_spec: str) -> bool:
    return _parse_specifier(package_spec).valid_local_path is not None


def parse_specifier_for_metadata(package_spec: str) -> str:
    """Return package_or_url suitable for pipx metadata

    Specifically:
    * Strip any version specifiers (e.g. package == 1.5.4)
    * Strip any markers (e.g. python_version > 3.4)
    * Convert local paths to absolute paths
    """
    parsed_package = _parse_specifier(package_spec).package_or_url
    if parsed_package.valid_pep508 is not None:
        if parsed_package.valid_pep508.url:
            package_or_url = parsed_package.valid_pep508.url
        else:
            if parsed_package.valid_pep508.extras:
                package_or_url = canonicalize_name(
                    parsed_package.valid_pep508.name
                    + "["
                    + ",".join(sorted(parsed_package.valid_pep508.extras))
                    + "]"
                )
            else:
                package_or_url = canonicalize_name(parsed_package.valid_pep508.name)
    elif parsed_package.valid_url is not None:
        package_or_url = parsed_package.valid_url
    elif parsed_package.valid_local_path is not None:
        package_or_url = parsed_package.valid_local_path

    logging.info(f"cleaned package spec: {package_or_url}")

    return package_or_url


def valid_pypi_name(package_spec: str) -> Optional[str]:
    try:
        package_req = Requirement(package_spec)
    except InvalidRequirement:
        # not a valid PEP508 package specification
        return None

    return package_req.name
