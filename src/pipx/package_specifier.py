# Valid package specifiers for pipx:
#   PEP508-compliant
#   git+<URL>
#   <URL>
#   <pypi_package_name>
#   <pypi_package_name><version_specifier>

import logging
from pathlib import Path
from typing import Optional

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from pipx.util import PipxError


def parse_specifier(package_spec: str) -> str:
    """Return package_or_url suitable for pipx metadata

    Specifically:
    * Strip any version specifiers (e.g. package == 1.5.4)
    * Strip any markers (e.g. python_version > 3.4)
    * Convert local paths to absolute paths
    """
    # NOTE: If package_spec to valid pypi name, pip will always treat it as a
    #       pypi package, not checking for local path.
    #       We replicate pypi precedence here (only non-valid-pypi names
    #       initiate check for local path, e.g. './package-name')

    valid_pep508 = False
    valid_url = False
    valid_local_path = False
    package_or_url = ""

    try:
        package_req = Requirement(package_spec)
    except InvalidRequirement:
        # not a valid PEP508 package specification
        valid_pep508 = False
    else:
        # valid PEP508 package specification
        valid_pep508 = True
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
            valid_url = False
        else:
            valid_url = True
            package_or_url = package_spec

    if not valid_pep508 and not valid_url:
        package_path = Path(package_spec)
        try:
            package_path_exists = package_path.exists()
        except OSError:
            package_path_exists = False

        if package_path_exists:
            valid_local_path = True
            package_or_url = str(package_path.resolve())

    if not valid_pep508 and not valid_url and not valid_local_path:
        raise PipxError(f"Unable to parse package spec: {package_spec}")

    logging.info(f"cleaned package spec: {package_or_url}")

    return package_or_url


def valid_pypi_name(package_spec: str) -> Optional[str]:
    try:
        package_req = Requirement(package_spec)
    except InvalidRequirement:
        # not a valid PEP508 package specification
        return None

    return package_req.name
