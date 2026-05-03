"""Reporters — turn an A5 run into an output artifact.

Built-in:
  TerminalReporter  — rich table to stdout (used by the CLI today).
  JsonReporter      — full run dump as JSON.
  HtmlReporter      — single-file HTML report.
  DiffViewer        — I5 side-by-side comparison across models on the
                      same payloads.
  AuditReporter     — S4 framework-tagged compliance report (HTML).
"""
from __future__ import annotations

from .audit import AuditReporter
from .diff_viewer import DiffRow, DiffViewer
from .html_reporter import HtmlReporter
from .json_reporter import JsonReporter
from .terminal_reporter import TerminalReporter

__all__ = [
    "AuditReporter",
    "DiffRow",
    "DiffViewer",
    "HtmlReporter",
    "JsonReporter",
    "TerminalReporter",
]
