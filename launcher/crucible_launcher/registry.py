from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

BUILTIN_DIR = Path(__file__).parent / "manifests"
USER_DIR = Path(os.environ.get("CRUCIBLE_TOOLS", "~/.crucible/tools")).expanduser()
PROJECT_DIR = Path.cwd() / ".crucible" / "tools"


@dataclass(frozen=True)
class Install:
    brew: str | None = None
    cask: str | None = None
    pipx: str | None = None
    pip: str | None = None
    cargo: str | None = None
    go: str | None = None
    docker: str | None = None
    lima: str | None = None
    winget: str | None = None
    scoop: str | None = None
    choco: str | None = None
    powershell: str | None = None  # path to a .ps1 to run
    script: str | None = None      # path to a shell script run via `bash`
    notes: str | None = None


@dataclass(frozen=True)
class Tool:
    name: str
    category: str
    command: str
    help: str = ""
    args: list[str] = field(default_factory=list)
    install: Install = field(default_factory=Install)
    requires_sudo: bool = False
    macos_only: bool = False
    windows_only: bool = False
    linux_only: bool = False
    source: Path | None = None  # which manifest file it came from


def _parse(path: Path) -> Tool:
    data = tomllib.loads(path.read_text())
    install_data = data.pop("install", {}) or {}
    install = Install(**{k: v for k, v in install_data.items() if k in Install.__dataclass_fields__})
    return Tool(
        name=data["name"],
        category=data.get("category", "Misc"),
        command=data["command"],
        help=data.get("help", ""),
        args=list(data.get("args", [])),
        install=install,
        requires_sudo=bool(data.get("requires_sudo", False)),
        macos_only=bool(data.get("macos_only", False)),
        windows_only=bool(data.get("windows_only", False)),
        linux_only=bool(data.get("linux_only", False)),
        source=path,
    )


def _scan(directory: Path) -> list[Tool]:
    if not directory.exists():
        return []
    out: list[Tool] = []
    for entry in sorted(directory.glob("*.toml")):
        if entry.name.startswith("_"):
            continue
        try:
            out.append(_parse(entry))
        except Exception as exc:  # narrow: a bad manifest shouldn't kill the launcher
            print(f"[crucible] skipping {entry}: {exc}")
    return out


def load_categories() -> dict[str, str]:
    cats_path = BUILTIN_DIR / "_categories.toml"
    if not cats_path.exists():
        return {}
    data = tomllib.loads(cats_path.read_text())
    return {c["name"]: c.get("description", "") for c in data.get("category", [])}


def load_tools() -> list[Tool]:
    tools: dict[str, Tool] = {}
    # later sources override earlier ones (project > user > builtin)
    for directory in (BUILTIN_DIR, USER_DIR, PROJECT_DIR):
        for tool in _scan(directory):
            tools[tool.name] = tool
    return sorted(tools.values(), key=lambda t: (t.category, t.name))


def by_category(tools: list[Tool]) -> dict[str, list[Tool]]:
    out: dict[str, list[Tool]] = {}
    for t in tools:
        out.setdefault(t.category, []).append(t)
    return out
