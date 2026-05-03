"""M section — computer-use / browser-agent attacks.

  dom_injector       : M1 — DOM-shaped HTML pages targeting a11y APIs
                       (aria-label, hidden inputs, shadow DOM, slots).
  a11y_poisoner      : M2 — pages where visible UI says X but the
                       accessibility tree says Y.
  ui_redress         : M3 — overlay/clickjack synthesis (uses E5).
  fake_chrome        : M4 — counterfeit browser surfaces inside page body.
  sandbox            : M5 — instrumented browser agent runtime
                       (Playwright optional).
"""
from __future__ import annotations

from .a11y_poisoner import A11yTreePoisoner
from .dom_injector import DomInjectorVector
from .fake_chrome import FakeChromeVector
from .ui_redress import UIRedressVector

__all__ = [
    "A11yTreePoisoner",
    "DomInjectorVector",
    "FakeChromeVector",
    "UIRedressVector",
]
