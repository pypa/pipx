# Valid package specifiers for pipx:
#   PEP508-compliant
#   git+<URL>
#   <URL>
#   <pypi_package_name>
#   <pypi_package_name><version_specifier>

import logging
import textwrap
from pathlib import Path
from typing import List, NamedTuple, Optional, Set, Tuple

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from pipx.emojies import hazard
from pipx.util import PipxError


class ParsedPackage(NamedTuple):
    valid_pep508: Optional[Requirement]
    valid_url: Optional[str]
    valid_local_path: Optional[str]


def _parse_specifier(package_spec: str) -> ParsedPackage:
    """Parse package_spec as would be given to pipx
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
        pass
    else:
        # valid PEP508 package specification
        valid_pep508 = package_req

    # NOTE: packaging currently (2020-07-19) only does basic syntax checks on URL.
    #   Some examples of what it will not catch:
    #       - invalid RCS string (e.g. "gat+https://...")
    #       - non-existent scheme (e.g. "zzzzz://...")
    if not valid_pep508:
        try:
            package_req = Requirement("notapackagename @ " + package_spec)
        except InvalidRequirement:
            # not a valid url
            pass
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


def _extras_to_str(extras: Set):
    if extras:
        return "[" + ",".join(sorted(extras)) + "]"
    else:
        return ""


def package_is_local_path(package_spec: str) -> bool:
    return _parse_specifier(package_spec).valid_local_path is not None


def parse_specifier_for_install(
    package_spec: str, pip_args: List[str]
) -> Tuple[str, List[str]]:
    """Return package_or_url and pip_args suitable for pip install

    Specifically:
    * Strip any markers (e.g. python_version > 3.4)
    * Ensure --editable is removed for any package_spec not a local path
    * Convert local paths to absolute paths
    """
    parsed_package = _parse_specifier(package_spec)
    if parsed_package.valid_pep508 is not None:
        if parsed_package.valid_pep508.url:
            package_or_url = parsed_package.valid_pep508.url
        else:
            package_or_url = canonicalize_name(parsed_package.valid_pep508.name)
            package_or_url += _extras_to_str(parsed_package.valid_pep508.extras)
            if parsed_package.valid_pep508.specifier:
                package_or_url = package_or_url + str(
                    parsed_package.valid_pep508.specifier
                )
            if parsed_package.valid_pep508.marker:
                logging.warning(
                    textwrap.fill(
                        f"{hazard}  Ignoring environment markers "
                        f"({parsed_package.valid_pep508.marker}) in package "
                        "specification. Use pipx options to specify this type of "
                        "information.",
                        subsequent_indent="    ",
                    )
                )
    elif parsed_package.valid_url is not None:
        package_or_url = parsed_package.valid_url
    elif parsed_package.valid_local_path is not None:
        package_or_url = parsed_package.valid_local_path

    logging.info(f"cleaned package spec: {package_or_url}")

    if "--editable" in pip_args and not parsed_package.valid_local_path:
        logging.warning(
            textwrap.fill(
                f"{hazard}  Ignoring --editable install option. pipx disallows it "
                "for anything but a local path, to avoid having to create a new "
                "src/ directory.",
                subsequent_indent="    ",
            )
        )
        pip_args.remove("--editable")

    return (package_or_url, pip_args)


def parse_specifier_for_metadata(package_spec: str) -> str:
    """Return package_or_url suitable for pipx metadata

    Specifically:
    * Strip any version specifiers (e.g. package == 1.5.4)
    * Strip any markers (e.g. python_version > 3.4)
    * Convert local paths to absolute paths
    """
    parsed_package = _parse_specifier(package_spec)
    if parsed_package.valid_pep508 is not None:
        if parsed_package.valid_pep508.url:
            package_or_url = parsed_package.valid_pep508.url
        else:
            package_or_url = canonicalize_name(parsed_package.valid_pep508.name)
            package_or_url += _extras_to_str(parsed_package.valid_pep508.extras)
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
