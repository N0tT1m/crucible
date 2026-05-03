"""redbox TUI — single Textual app, multiple screens.

Screens:
  dashboard    — recent runs, cost, refusal rates
  live         — streaming run viewer
  browser      — result browser + diff viewer
  builder      — pipeline builder
  plugin_mgr   — toggle / configure plugins

Entry: `redbox tui` (CLI command). Without textual installed, the entry
point prints a clear install hint and exits with code 1.
"""
from __future__ import annotations


def have_textual() -> bool:
    try:
        import textual  # noqa: F401
    except ImportError:
        return False
    return True


__all__ = ["have_textual"]
