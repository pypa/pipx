from __future__ import annotations

from pathlib import Path

from docutils.core import publish_string
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        del version, build_data
        if self.target_name != "wheel":
            return

        root = Path(self.root)
        (output := root / "build" / "man").mkdir(parents=True, exist_ok=True)
        source = "\n".join(
            line
            for line in (root / "docs" / "man" / "pipx.1.rst").read_text(encoding="utf-8").splitlines()
            if line.strip() != ":orphan:"
        )
        (output / "pipx.1").write_bytes(
            publish_string(source, writer="manpage", settings_overrides={"report_level": 5})
        )


__all__ = [
    "CustomBuildHook",
]
