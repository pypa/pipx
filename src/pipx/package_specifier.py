# Valid package specifiers for pipx:
#   git+<URL>
#   <URL>
#   <pypi_package_name>
#   <pypi_package_name><version_specifier>

from pathlib import Path
from packaging.requirements import Requirement, InvalidRequirement
from packaging.utils import canonicalize_name


def parse_specifier(package_spec: str) -> str:
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
            package_or_url = package_spec.url
        else:
            if package_spec.extras:
                package_or_url = canonicalize_name(
                    package_spec.name + "[" + ",".join(package_spec.extras) + "]"
                )
            else:
                package_or_url = canonicalize_name(package_spec.name)

    if not valid_pep508:
        try:
            package_req = Requirement("notapackagename @ " + package_spec)
        except InvalidRequirement as e:
            valid_url = False
        else:
            valid_url = True
            package_or_url = package_spec

    if not valid_pep508 and not valid_url:
        package_path = Path(package_spec)
        if package_path.exists:
            valid_local_path = True
            package_or_url = str(package_path.resolve())

    return package_or_url
