"""Translate firejail-style profiles into macOS Seatbelt .sb files.

Only the directives that have a coherent macOS analogue are handled.
Unknown directives are surfaced as a warning so the user knows they're
silently dropped, not silently honored.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROFILES_DIR = Path(__file__).parent / "profiles"


@dataclass
class Sandbox:
    deny_default: bool = True
    network: str = "allow"        # allow | deny | local
    read_only: list[str] = field(default_factory=list)
    blacklist: list[str] = field(default_factory=list)
    whitelist: list[str] = field(default_factory=list)
    private_tmp: bool = False
    private_dev: bool = False
    no_exec: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _expand(p: str) -> str:
    return os.path.expandvars(os.path.expanduser(p)).rstrip("/")


def parse(text: str) -> Sandbox:
    sb = Sandbox()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        head, _, rest = line.partition(" ")
        head = head.lower()
        if head == "include":
            inc = PROFILES_DIR / rest
            if inc.exists():
                _merge(sb, parse(inc.read_text()))
            continue
        if head == "net":
            sb.network = "deny" if rest.strip() == "none" else "allow"
        elif head == "private-tmp":
            sb.private_tmp = True
        elif head == "private-dev":
            sb.private_dev = True
        elif head == "read-only":
            sb.read_only.append(_expand(rest))
        elif head == "blacklist":
            sb.blacklist.append(_expand(rest))
        elif head == "whitelist":
            sb.whitelist.append(_expand(rest))
        elif head == "noexec":
            sb.no_exec.append(_expand(rest))
        elif head in {"caps.drop", "seccomp", "nogroups", "noroot"}:
            # No direct macOS analogue; Seatbelt is profile-based, not capability-based.
            sb.warnings.append(f"ignored linux-only directive: {raw}")
        else:
            sb.warnings.append(f"unknown directive: {raw}")
    return sb


def _merge(into: Sandbox, other: Sandbox) -> None:
    into.read_only.extend(other.read_only)
    into.blacklist.extend(other.blacklist)
    into.whitelist.extend(other.whitelist)
    into.no_exec.extend(other.no_exec)
    if other.network == "deny":
        into.network = "deny"
    if other.private_tmp:
        into.private_tmp = True
    if other.private_dev:
        into.private_dev = True
    into.warnings.extend(other.warnings)


def to_sbpl(sb: Sandbox) -> str:
    """Render a Seatbelt sandbox profile (TinyScheme-flavored)."""
    out: list[str] = ["(version 1)"]
    out.append("(deny default)" if sb.deny_default else "(allow default)")
    out.append("(allow process-fork)")
    out.append("(allow process-exec)")
    out.append("(allow signal (target self))")
    out.append("(allow file-read-metadata)")
    out.append("(allow sysctl-read)")

    if sb.network == "deny":
        out.append("(deny network*)")
    else:
        out.append("(allow network*)")

    # default-allow read on system paths so the binary actually runs
    for p in ("/usr", "/System", "/Library", "/private/etc", "/bin", "/sbin"):
        out.append(f'(allow file-read* (subpath "{p}"))')

    for p in sb.read_only:
        out.append(f'(allow file-read* (subpath "{p}"))')
        out.append(f'(deny  file-write* (subpath "{p}"))')

    for p in sb.blacklist:
        out.append(f'(deny file-read*  (subpath "{p}"))')
        out.append(f'(deny file-write* (subpath "{p}"))')

    for p in sb.whitelist:
        out.append(f'(allow file-read*  (subpath "{p}"))')
        out.append(f'(allow file-write* (subpath "{p}"))')

    if sb.private_tmp:
        out.append('(deny file-write* (subpath "/tmp"))')
    if sb.private_dev:
        out.append('(deny file-read* (subpath "/dev"))')

    return "\n".join(out) + "\n"
