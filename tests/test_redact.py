from __future__ import annotations

import pytest

from pipx.redact import redact_url_credentials


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            "pip --index-url https://alice:s3cr3t@host/simple",
            "pip --index-url https://****:****@host/simple",
            id="user-and-password",
        ),
        pytest.param("pip git+https://t0ken@host/repo.git", "pip git+https://****@host/repo.git", id="token"),
        pytest.param("pip foo @ https://host/a@b.whl", "pip foo @ https://host/a@b.whl", id="no-credentials"),
        pytest.param("https://host?x=a@b", "https://host?x=a@b", id="at-in-query"),
        pytest.param("https://host#egg=x@1", "https://host#egg=x@1", id="at-in-fragment"),
        pytest.param("https://u:p@w@host/x", "https://****:****@host/x", id="unescaped-at-in-password"),
        pytest.param("https://t0ken:@host/simple", "https://****:****@host/simple", id="token-with-empty-password"),
        pytest.param(
            "git+https://t0ken:x-oauth-basic@host/repo.git",
            "git+https://****:****@host/repo.git",
            id="token-with-placeholder-password",
        ),
        pytest.param("git+ssh://git@github.com/a/b", "git+ssh://****@github.com/a/b", id="bare-user"),
        pytest.param(
            "https://alice:correct horse@host/simple", "https://****:****@host/simple", id="space-in-password"
        ),
        pytest.param("https://alice:correct\thorse@host/simple", "https://****:****@host/simple", id="tab-in-password"),
        pytest.param("see https://host\nfetching foo@1.0/x", "see https://host\nfetching foo@1.0/x", id="line-break"),
        pytest.param(
            "--index-url https://t0ken@host --trusted-host x:y@z",
            "--index-url https://****@z",
            id="token-then-later-colon-and-at",
        ),
        pytest.param(
            "--index-url https://a:b@one/s --extra-index-url https://c@two/s",
            "--index-url https://****:****@one/s --extra-index-url https://****@two/s",
            id="two-urls",
        ),
    ],
)
def test_redact_url_credentials_masks_userinfo(text: str, expected: str) -> None:
    assert redact_url_credentials(text) == expected
