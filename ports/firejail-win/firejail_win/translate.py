"""Translate firejail-style profiles into a Windows-native sandbox plan.

Produces a `Plan` dataclass that the runner consumes:
  - file_deny / file_readonly  → ACL changes on Job Object handle
  - net_deny                    → WFP block rule for the AppContainer SID
  - capabilities                → AppContainer capabilities (always restrictive)
  - sandbox                     → if true, hand off to Windows Sandbox
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROFILES_DIR = Path(__file__).parent / "profiles"


@dataclass
class Plan:
    file_deny: list[str] = field(default_factory=list)
    file_readonly: list[str] = field(default_factory=list)
    net_deny: bool = False
    private_temp: bool = False
    job_limits: dict[str, int] = field(default_factory=dict)
    appcontainer: bool = True
    sandbox: bool = False
    warnings: list[str] = field(default_factory=list)


def _expand(p: str) -> str:
    return os.path.expandvars(os.path.expanduser(p)).rstrip("\\/")


def parse(text: str) -> Plan:
    plan = Plan()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        head, _, rest = line.partition(" ")
        head = head.lower()
        if head == "include":
            inc = PROFILES_DIR / rest
            if inc.exists():
                _merge(plan, parse(inc.read_text()))
            continue
        if head == "net":
            plan.net_deny = rest.strip() == "none"
        elif head == "private-tmp":
            plan.private_temp = True
        elif head == "read-only":
            plan.file_readonly.append(_expand(rest))
        elif head == "blacklist":
            plan.file_deny.append(_expand(rest))
        elif head == "memory-limit":
            plan.job_limits["ProcessMemoryLimit"] = int(rest)
        elif head == "cpu-limit":
            plan.job_limits["CpuRate"] = int(rest)
        elif head == "sandbox":
            plan.sandbox = True
        elif head in {"caps.drop", "seccomp", "noroot", "nogroups"}:
            plan.warnings.append(f"linux-only directive ignored: {raw}")
        else:
            plan.warnings.append(f"unknown directive: {raw}")
    return plan


def _merge(into: Plan, other: Plan) -> None:
    into.file_deny.extend(other.file_deny)
    into.file_readonly.extend(other.file_readonly)
    if other.net_deny:
        into.net_deny = True
    if other.private_temp:
        into.private_temp = True
    if other.sandbox:
        into.sandbox = True
    into.job_limits.update(other.job_limits)
    into.warnings.extend(other.warnings)


def to_wsb(plan: Plan, target_cmd: list[str]) -> str:
    """Render a Windows Sandbox configuration (.wsb) when --sandbox is used."""
    networking = "Disable" if plan.net_deny else "Default"
    cmd_xml = "&amp;".join(target_cmd)
    return f"""<Configuration>
  <Networking>{networking}</Networking>
  <ClipboardRedirection>Disable</ClipboardRedirection>
  <PrinterRedirection>Disable</PrinterRedirection>
  <ProtectedClient>Enable</ProtectedClient>
  <LogonCommand>
    <Command>{cmd_xml}</Command>
  </LogonCommand>
</Configuration>
"""
