from __future__ import annotations

import base64
import hashlib
import re
import stat
import sys
import urllib.parse
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Final, cast
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import canonicalize_name

from pipx.util import PipxError

if TYPE_CHECKING:
    from collections.abc import Iterator

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

_APP_NAME: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]*")
_INLINE_METADATA: Final[re.Pattern[str]] = re.compile(
    r"""
    ^\#\ ///\ (?P<type>[a-zA-Z0-9-]+)$ \s
    (?P<content> (^\#(|\ .*)$ \s)+? )
    ^\#\ ///$
    """,
    re.VERBOSE | re.MULTILINE,
)


@dataclass(frozen=True)
class ScriptMetadata:
    dependencies: tuple[str, ...]
    requires_python: str | None


@dataclass(frozen=True)
class _Script:
    app: str
    content: str
    metadata: ScriptMetadata


def read_script_metadata(content: str | Path) -> ScriptMetadata | None:
    text: Final[str] = (content.read_text(encoding="utf-8") if isinstance(content, Path) else content).removeprefix(
        "\ufeff"
    )
    normalized_text: Final[str] = text.replace("\r\n", "\n")
    matches: Final[list[re.Match[str]]] = [
        match for match in _INLINE_METADATA.finditer(normalized_text) if match.group("type") == "script"
    ]
    if not matches:
        if any(match.group("type") == "pyproject" for match in _INLINE_METADATA.finditer(normalized_text)):
            raise ValueError("Use `# /// script` instead of the obsolete `# /// pyproject` metadata block")
        return None
    if len(matches) > 1:
        raise ValueError("Multiple `# /// script` metadata blocks found")

    raw: Final[dict[str, str | list[str]]] = cast(
        "dict[str, str | list[str]]",
        tomllib.loads(
            "".join(
                line[2:] if line.startswith("# ") else line[1:]
                for line in matches[0].group("content").splitlines(keepends=True)
            )
        ),
    )
    dependencies: Final[str | list[str]] = raw.get("dependencies", [])
    if not isinstance(dependencies, list) or not all(isinstance(dependency, str) for dependency in dependencies):
        raise PipxError("Inline script `dependencies` must be an array of strings.")
    normalized: Final[list[str]] = []
    for dependency in dependencies:
        try:
            normalized.append(str(Requirement(dependency)))
        except InvalidRequirement as error:
            raise PipxError(f"Invalid requirement {dependency}: {error}") from error

    requires_python: Final[str | None] = _normalize_requires_python(raw.get("requires-python"))
    return ScriptMetadata(tuple(normalized), requires_python)


def script_name_from_spec(package_spec: str, expected_apps: tuple[str, ...]) -> str | None:
    if not _is_script_spec(package_spec):
        return None
    if len(expected_apps) > 1:
        raise PipxError("A script can provide one --app name.")
    app: Final[str] = _script_app(package_spec, expected_apps)
    if _APP_NAME.fullmatch(app) is None:
        raise PipxError(f"Invalid script app name {app!r}. Pass --app with a portable command name.")
    return canonicalize_name(app)


@contextmanager
def installable_script(package_name: str, package_or_url: str, expected_apps: tuple[str, ...]) -> Iterator[str]:
    if (resolved_name := script_name_from_spec(package_or_url, expected_apps)) is None:
        yield package_or_url
        return
    if canonicalize_name(package_name) != resolved_name:
        raise PipxError(f"Script app {resolved_name!r} does not match package name {package_name!r}.")

    script: Final[_Script] = _read_script(package_or_url, expected_apps)
    with TemporaryDirectory(prefix="pipx-script-") as directory:
        yield str(_write_wheel(Path(directory), package_name, script))


def _is_script_spec(package_spec: str) -> bool:
    path: Final[Path] = Path(package_spec).expanduser()
    if path.is_file():
        return path.suffix.lower() == ".py" or (not path.suffix and _has_inline_script_metadata(path))
    parsed: Final[urllib.parse.SplitResult] = urllib.parse.urlsplit(package_spec)
    return parsed.scheme in {"http", "https"} and parsed.path.lower().endswith(".py")


def _has_inline_script_metadata(path: Path) -> bool:
    try:
        content: Final[str] = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return any(match.group("type") == "script" for match in _INLINE_METADATA.finditer(content.removeprefix("\ufeff")))


def _script_app(package_spec: str, expected_apps: tuple[str, ...]) -> str:
    return expected_apps[0] if expected_apps else Path(urllib.parse.urlsplit(package_spec).path).stem


def _read_script(package_or_url: str, expected_apps: tuple[str, ...]) -> _Script:
    path: Final[Path] = Path(package_or_url).expanduser()
    content: Final[str] = (
        path.read_text(encoding="utf-8") if path.is_file() else _read_url(package_or_url)
    ).removeprefix("\ufeff")
    try:
        metadata: Final[ScriptMetadata | None] = read_script_metadata(content)
    except ValueError as error:
        raise PipxError(f"Invalid inline metadata in script {package_or_url}: {error}.") from error
    if metadata is None:
        raise PipxError(f"Script {package_or_url} has no PEP 723 inline metadata block.")
    return _Script(_script_app(package_or_url, expected_apps), content, metadata)


def _read_url(url: str) -> str:
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode(response.headers.get_content_charset() or "utf-8")
    except OSError as error:
        raise PipxError(f"Unable to read script {url}: {error}") from error


def _normalize_requires_python(value: str | list[str] | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PipxError("Inline script `requires-python` must be a string.")
    try:
        return str(SpecifierSet(value))
    except InvalidSpecifier as error:
        raise PipxError(f"Invalid `requires-python` value {value}: {error}") from error


def _write_wheel(directory: Path, package_name: str, script: _Script) -> Path:
    version: Final[str] = f"0+{hashlib.sha256(script.content.encode()).hexdigest()[:12]}"
    distribution: Final[str] = re.sub(r"[-_.]+", "_", package_name)
    stem: Final[str] = f"{distribution}-{version}"
    dist_info: Final[str] = f"{stem}.dist-info"
    members: Final[dict[str, bytes]] = {
        f"{stem}.data/scripts/{script.app}": _script_bytes(script.content),
        f"{dist_info}/METADATA": _metadata(package_name, version, script.metadata),
        f"{dist_info}/WHEEL": b"Wheel-Version: 1.0\nGenerator: pipx\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    record: Final[str] = f"{dist_info}/RECORD"
    wheel: Final[Path] = directory / f"{stem}-py3-none-any.whl"
    with ZipFile(wheel, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in members.items():
            _write_member(archive, name, data, executable=".data/scripts/" in name)
        archive.writestr(
            record,
            "".join(f"{name},sha256={_digest(data)},{len(data)}\n" for name, data in members.items()) + f"{record},,\n",
        )
    return wheel


def _metadata(package_name: str, version: str, metadata: ScriptMetadata) -> bytes:
    lines: Final[list[str]] = ["Metadata-Version: 2.3", f"Name: {package_name}", f"Version: {version}"]
    if metadata.requires_python is not None:
        lines.append(f"Requires-Python: {metadata.requires_python}")
    lines.extend(f"Requires-Dist: {dependency}" for dependency in metadata.dependencies)
    return ("\n".join(lines) + "\n\n").encode()


def _script_bytes(content: str) -> bytes:
    return ("#!python\n" + (content.partition("\n")[2] if content.startswith("#!") else content)).encode()


def _write_member(archive: ZipFile, name: str, data: bytes, *, executable: bool) -> None:
    info: Final[ZipInfo] = ZipInfo(name)
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | (0o755 if executable else 0o644)) << 16
    archive.writestr(info, data, compress_type=ZIP_DEFLATED)


def _digest(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


__all__ = [
    "ScriptMetadata",
    "installable_script",
    "read_script_metadata",
    "script_name_from_spec",
]
