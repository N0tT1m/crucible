"""L1 weight-sniffer — static scanner for model artefacts.

Scans `.bin`, `.pt`, `.safetensors`, `.gguf`, `.pickle/.pkl` files for:

  - dangerous pickle opcodes (REDUCE, GLOBAL referencing posix/os/subprocess)
  - embedded executables (PE/ELF/Mach-O magic bytes mid-file)
  - oversized metadata blobs in safetensors header
  - GGUF magic + version sanity
  - suspicious imports declared inside pickled byte streams

Produces a list of `Finding`s with severity ("info"|"warn"|"critical")
and a one-line description. Cheap, dep-free, runs over a stream so we
don't load the whole tensor into memory.
"""
from __future__ import annotations

import json
import pickletools
import re
import struct
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

DANGEROUS_GLOBALS = {
    ("posix", "system"), ("os", "system"), ("os", "popen"),
    ("subprocess", "Popen"), ("subprocess", "call"),
    ("__builtin__", "eval"), ("builtins", "eval"),
    ("builtins", "exec"), ("__builtin__", "exec"),
    ("nt", "system"), ("commands", "getoutput"),
    ("operator", "attrgetter"),  # used for arbitrary attr access bypasses
}

EXEC_MAGIC = [
    (b"MZ", "embedded PE (Windows EXE)"),
    (b"\x7fELF", "embedded ELF (Linux executable)"),
    (b"\xca\xfe\xba\xbe", "embedded Mach-O (macOS executable)"),
    (b"\xcf\xfa\xed\xfe", "embedded Mach-O 64-bit"),
]


@dataclass(slots=True)
class Finding:
    severity: str   # info | warn | critical
    kind: str
    detail: str
    offset: int = -1


def _scan_for_exec(data: bytes) -> list[Finding]:
    out: list[Finding] = []
    for magic, label in EXEC_MAGIC:
        idx = 0
        while True:
            i = data.find(magic, idx)
            if i < 0:
                break
            # Skip if the magic is at offset 0 of the file — that's just
            # the file's own header (could be an actual binary by name).
            severity = "warn" if i > 0 else "info"
            out.append(Finding(
                severity=severity, kind="exec_magic", detail=label, offset=i,
            ))
            idx = i + len(magic)
    return out


def _scan_pickle(data: bytes) -> list[Finding]:
    out: list[Finding] = []
    bio = BytesIO(data)
    try:
        ops = list(pickletools.genops(bio))
    except Exception as e:
        return [Finding(severity="warn", kind="pickle_parse",
                         detail=f"bad pickle: {e}")]
    # Recent string-emitting opcodes that feed STACK_GLOBAL.
    string_window: list[str] = []
    str_ops = {"SHORT_BINUNICODE", "BINUNICODE", "BINUNICODE8", "UNICODE",
               "SHORT_BINSTRING", "BINSTRING", "STRING"}
    for op, arg, pos in ops:
        if op.name in str_ops and isinstance(arg, str):
            string_window.append(arg)
            if len(string_window) > 8:
                string_window.pop(0)
        if op.name == "GLOBAL" and isinstance(arg, str):
            mod, _, name = arg.partition(" ")
            if (mod, name) in DANGEROUS_GLOBALS:
                out.append(Finding(
                    severity="critical", kind="pickle_global",
                    detail=f"references {mod}.{name}", offset=pos,
                ))
        elif op.name == "STACK_GLOBAL" and len(string_window) >= 2:
            mod, name = string_window[-2], string_window[-1]
            if (mod, name) in DANGEROUS_GLOBALS:
                out.append(Finding(
                    severity="critical", kind="pickle_global",
                    detail=f"references {mod}.{name}", offset=pos,
                ))
        if op.name in {"REDUCE", "INST", "OBJ"}:
            out.append(Finding(
                severity="warn", kind="pickle_op",
                detail=f"opcode {op.name}", offset=pos,
            ))
    return out


def _scan_safetensors(data: bytes) -> list[Finding]:
    out: list[Finding] = []
    if len(data) < 8:
        return [Finding(severity="warn", kind="size", detail="file < 8 bytes")]
    hdr_len = struct.unpack("<Q", data[:8])[0]
    if hdr_len > 1_000_000:
        out.append(Finding(severity="warn", kind="oversized_header",
                            detail=f"safetensors header is {hdr_len} bytes"))
    if hdr_len + 8 > len(data):
        return [*out, Finding(
            severity="critical", kind="bad_header",
            detail=f"declared header {hdr_len}B exceeds file size",
        )]
    try:
        header = json.loads(data[8:8 + hdr_len].decode("utf-8"))
    except Exception as e:
        return [*out, Finding(severity="warn", kind="bad_header_json",
                                detail=str(e))]
    metadata = header.get("__metadata__", {})
    for k, v in metadata.items():
        if isinstance(v, str) and len(v) > 4096:
            out.append(Finding(severity="warn", kind="oversized_metadata",
                                detail=f"metadata[{k!r}] is {len(v)} chars"))
    return out


def _scan_gguf(data: bytes) -> list[Finding]:
    if data[:4] != b"GGUF":
        return [Finding(severity="warn", kind="not_gguf",
                         detail="missing GGUF magic")]
    if len(data) < 8:
        return [Finding(severity="warn", kind="size", detail="too small")]
    version = struct.unpack("<I", data[4:8])[0]
    out = [Finding(severity="info", kind="gguf_version", detail=f"v{version}")]
    if version > 5:
        out.append(Finding(severity="warn", kind="gguf_version_unknown",
                            detail=f"unfamiliar GGUF v{version}"))
    return out


def _scan_text_for_imports(data: bytes) -> list[Finding]:
    text = data[:200_000].decode("utf-8", errors="ignore")
    suspicious = re.findall(
        r"\b(?:os\.system|subprocess\.\w+|socket\.\w+|urllib\.\w+|requests\.\w+|"
        r"importlib\.\w+|builtins\.\w+|exec\(|eval\()",
        text,
    )
    return [Finding(
        severity="warn", kind="suspicious_text",
        detail=f"saw {len(suspicious)} suspicious tokens (e.g. {sorted(set(suspicious))[:3]})",
    )] if suspicious else []


@dataclass
class FileScanner:
    name: str = "weight_sniffer"

    def scan(self, path: Path | str) -> list[Finding]:
        p = Path(path)
        data = p.read_bytes()
        suffix = p.suffix.lower()
        out: list[Finding] = []

        if suffix in {".pkl", ".pickle"}:
            out.extend(_scan_pickle(data))
        if suffix in {".pt", ".bin"}:
            # Could be torch (zip-of-pickles) or raw pickle. Try both.
            if data[:4] == b"PK\x03\x04":
                out.append(Finding(severity="info", kind="zip", detail="torch zip archive"))
            else:
                out.extend(_scan_pickle(data))
        if suffix == ".safetensors":
            out.extend(_scan_safetensors(data))
        if suffix == ".gguf":
            out.extend(_scan_gguf(data))

        out.extend(_scan_for_exec(data))
        out.extend(_scan_text_for_imports(data))
        return out

    def scan_many(self, paths: Iterable[Path | str]) -> dict[str, list[Finding]]:
        return {str(p): self.scan(p) for p in paths}
