"""R section — code-generation red-team primitives."""
from __future__ import annotations

from .dep_confusion import DepConfusionProbe
from .license_launderer import LicenseLaundererProbe, LicenseScanner
from .pkg_hallucinator import HallucinatedPkgDetector, PkgHallucinatorProbe
from .secret_completer import SecretLeakProbe
from .vuln_injector import VulnPatternMatcher, VulnProbeBattery

__all__ = [
    "DepConfusionProbe",
    "HallucinatedPkgDetector",
    "LicenseLaundererProbe",
    "LicenseScanner",
    "PkgHallucinatorProbe",
    "SecretLeakProbe",
    "VulnPatternMatcher",
    "VulnProbeBattery",
]
