"""Heuristic security screening for custom skill writes and installs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .types import SKILL_MD_FILE

_PROMPT_INJECTION_PATTERNS = (
    re.compile(r"\bignore\s+(all\s+)?(previous|earlier|above)\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\b(disregard|override)\s+(the\s+)?system\s+prompt\b", re.IGNORECASE),
    re.compile(r"\breveal\s+(the\s+)?system\s+prompt\b", re.IGNORECASE),
    re.compile(r"\bdeveloper\s+message\b", re.IGNORECASE),
)
_EXFILTRATION_PATTERNS = (
    re.compile(r"(169\.254\.169\.254|metadata\.google\.internal)", re.IGNORECASE),
    re.compile(r"\b(send|post|upload|exfiltrat\w*|curl|wget)\b.{0,120}\b(api[_ -]?key|token|secret|password|\.env|id_rsa|/etc/passwd|/\.ssh/)\b", re.IGNORECASE | re.DOTALL),
)
_DESTRUCTIVE_SCRIPT_PATTERNS = (
    re.compile(r"\brm\s+-rf\s+/\b"),
    re.compile(r"\bmkfs(\.\w+)?\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
    re.compile(r"\b(shutdown|reboot)\b", re.IGNORECASE),
)
_WARN_PATTERNS = (
    re.compile(r"\b(os\.system|subprocess\.(run|popen|call)|child_process\.exec)\b", re.IGNORECASE),
    re.compile(r"\b(requests\.(post|put)|fetch\(|axios\.(post|put)|curl|wget)\b", re.IGNORECASE),
)


@dataclass(slots=True)
class ScanResult:
    decision: str
    reason: str


def scan_skill_content(
    content: str,
    *,
    executable: bool = False,
    location: str = SKILL_MD_FILE,
) -> ScanResult:
    """Scan skill content with deterministic guardrails.

    This intentionally uses a conservative rule-based pass so installs and edits
    never depend on an external moderation model.
    """

    for pattern in _PROMPT_INJECTION_PATTERNS:
        if pattern.search(content):
            return ScanResult("block", f"Prompt-injection pattern detected in {location}.")

    for pattern in _EXFILTRATION_PATTERNS:
        if pattern.search(content):
            return ScanResult("block", f"Potential credential exfiltration detected in {location}.")

    if executable:
        for pattern in _DESTRUCTIVE_SCRIPT_PATTERNS:
            if pattern.search(content):
                return ScanResult("block", f"Destructive executable pattern detected in {location}.")

    for pattern in _WARN_PATTERNS:
        if pattern.search(content):
            return ScanResult("warn", f"Potentially sensitive execution or network pattern detected in {location}.")

    return ScanResult("allow", "No risky patterns detected.")
