# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.7.0+  | :white_check_mark: |
| < 1.7.0 | :x:                |

## Reporting a Vulnerability

**Do not open a public issue for a security problem.** Use GitHub's private vulnerability reporting through
[the advisory form](https://github.com/pypa/pipx/security/advisories/new), or the
[Tidelift security contact](https://tidelift.com/security), which coordinates the fix and disclosure with us.

## Scope

pipx turns what its user asks for into installer and interpreter runs: package specs, recorded metadata, manifests and
configuration become `pip`, `uv` and `python` invocations, and the resulting environments expose commands on `PATH`. The
boundary this policy cares about is between the user who runs pipx and everyone else.

pipx trusts the invoking user and everything they control or choose: the command line, environment variables, pipx, pip
and uv configuration, `PIPX_HOME` and the metadata in it, the packages, URLs, manifests, snapshots and lock files they
pass, the package indexes they configure, and the interpreters they select. Packages run code while they build and after
they install; that is how Python packaging works and not a pipx vulnerability.

**In scope**

- Files another local account can write, such as in a shared `/tmp`, changing what pipx installs, runs or exposes when
    the user did not name them. pipx does not look up the current directory or its parents for configuration or tool
    selection (see [Project scope](../docs/explanation/scope.rst)), so a lookup there is a bug in pipx.
- pipx dropping or replacing the index, source or backend the user recorded, so a later install resolves the package
    somewhere the user did not choose.
- Files and directories pipx creates with wider permissions than intended, for example logs or metadata that hold
    credentials.
- Documented instructions that, followed as written, let another local account run code as the user.

**Out of scope**

- An attacker who already controls the user's command line, environment, configuration, `PIPX_HOME` or executables.
- A malicious or compromised package, package index, manifest or repository the user chose to use. Report malware on
    PyPI to [PyPI security](https://pypi.org/security/).
- Behavior that pip, uv or CPython document and that pipx uses as documented. Report those to the project that owns
    them; pipx mitigates where it can.
- Credentials that appear only in the user's own terminal output.
- Test code, unreleased code on `main`, and Python versions pipx no longer supports.

If you cannot tell which side a finding falls on, report it privately and we will assess it.
