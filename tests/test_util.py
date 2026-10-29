from __future__ import annotations

from typing import Final

from pipx.redact import redact_url_credentials
from pipx.util import full_package_description


def test_full_package_description_of_bare_spec_hides_url_credentials() -> None:
    spec: Final[str] = "helper @ http://u:s3cr3ttok@host/helper-1.0-py3-none-any.whl"

    assert full_package_description(spec, spec) == redact_url_credentials(spec)
