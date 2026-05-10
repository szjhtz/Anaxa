"""Deterministic BibTeX and LaTeX citation auditing utilities."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_BIBTEX_ENTRY_RE = re.compile(r"@\s*([A-Za-z]+)\s*[{(]\s*([^,\s{}()]+)\s*,", re.MULTILINE)
_LATEX_CITE_RE = re.compile(
    r"\\(?P<command>(?:[A-Za-z]*cite[A-Za-z]*|nocite))\s*(?:\[[^\]]*\]\s*){0,2}\{(?P<keys>[^{}]+)\}",
    re.MULTILINE,
)
_UNESCAPED_COMMENT_RE = re.compile(r"(?<!\\)%.*")
_IGNORED_BIBTEX_ENTRY_TYPES = {"comment", "preamble", "string"}
_EXPERIMENTAL_CLAIM_TERMS = {
    "ablation",
    "accuracy",
    "auc",
    "auroc",
    "baseline",
    "benchmark",
    "experiment",
    "experimental",
    "f1",
    "metric",
    "outperform",
    "performance",
    "result",
    "robust",
    "sota",
    "state-of-the-art",
    "superior",
}
_SUPPORTED_STATUSES = {"supported", "verified", "supported_by_experiment", "supported_by_literature"}
_EXPERIMENT_STATUSES = {"supported_by_experiment", "experiment-supported", "experiment_supported"}


@dataclass(frozen=True)
class CitationAuditResult:
    """Structured result for a LaTeX/BibTeX citation audit."""

    status: str
    bibtex_path: str
    tex_path: str | None
    citation_keys: list[str]
    cited_keys: list[str]
    missing_keys: list[str]
    unused_keys: list[str]
    nocite_all: bool
    violations: list[str] = field(default_factory=list)
    unsupported_claims: list[str] = field(default_factory=list)
    paragraph_count: int = 0
    uncited_paragraph_count: int = 0
    author_notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "bibtex_path": self.bibtex_path,
            "tex_path": self.tex_path,
            "citation_keys": self.citation_keys,
            "cited_keys": self.cited_keys,
            "missing_keys": self.missing_keys,
            "unused_keys": self.unused_keys,
            "nocite_all": self.nocite_all,
            "violations": self.violations,
            "unsupported_claims": self.unsupported_claims,
            "paragraph_count": self.paragraph_count,
            "uncited_paragraph_count": self.uncited_paragraph_count,
            "author_notes": self.author_notes,
        }


def extract_bibtex_keys(source: str) -> list[str]:
    """Extract citation keys from BibTeX source without model inference."""

    keys: list[str] = []
    seen: set[str] = set()
    for match in _BIBTEX_ENTRY_RE.finditer(source):
        entry_type = match.group(1).lower()
        key = match.group(2).strip()
        if not key or entry_type in _IGNORED_BIBTEX_ENTRY_TYPES or key in seen:
            continue
        keys.append(key)
        seen.add(key)
    return keys


def extract_latex_citations(source: str) -> tuple[list[str], bool]:
    """Extract cited BibTeX keys from LaTeX source and flag ``\\nocite{*}``."""

    stripped = "\n".join(_UNESCAPED_COMMENT_RE.sub("", line) for line in source.splitlines())
    cited: list[str] = []
    seen: set[str] = set()
    nocite_all = False

    for match in _LATEX_CITE_RE.finditer(stripped):
        command = match.group("command").lower()
        raw_keys = match.group("keys")
        for raw_key in raw_keys.split(","):
            key = raw_key.strip()
            if not key:
                continue
            if command == "nocite" and key == "*":
                nocite_all = True
                continue
            if key not in seen:
                cited.append(key)
                seen.add(key)

    return cited, nocite_all


def find_unsupported_claims(claims: Any) -> list[str]:
    """Return claim texts that are explicitly marked unsupported or lack evidence."""

    if isinstance(claims, dict):
        candidates = claims.get("claims", claims.get("claim_table", claims.get("items", [])))
    else:
        candidates = claims

    unsupported: list[str] = []
    if not isinstance(candidates, list):
        return unsupported

    for item in candidates:
        if not isinstance(item, dict):
            continue
        claim_text = str(item.get("claim") or item.get("text") or item.get("statement") or "").strip()
        status = str(item.get("support_status") or item.get("status") or "").strip().lower()
        evidence = item.get("evidence") or item.get("citations") or item.get("citation_keys") or item.get("artifact_path")
        evidence_type = str(item.get("evidence_type") or item.get("support_type") or "").strip().lower()
        experimental_claim = _is_experimental_claim(claim_text, item)
        lacks_evidence = evidence in (None, "", []) and status not in _SUPPORTED_STATUSES
        literature_only_experimental_claim = experimental_claim and status not in _EXPERIMENT_STATUSES and evidence_type != "experiment"
        if status in {"unsupported", "contradicted", "missing"} or lacks_evidence:
            unsupported.append(claim_text or json.dumps(item, ensure_ascii=False, sort_keys=True))
        elif literature_only_experimental_claim:
            unsupported.append(claim_text or json.dumps(item, ensure_ascii=False, sort_keys=True))

    return unsupported


def _is_experimental_claim(claim_text: str, item: dict[str, Any]) -> bool:
    text = " ".join(
        [
            claim_text,
            str(item.get("section") or ""),
            str(item.get("claim_type") or ""),
            str(item.get("evidence_type") or ""),
        ]
    ).lower()
    return any(term in text for term in _EXPERIMENTAL_CLAIM_TERMS)


def find_author_notes(source: str) -> list[str]:
    notes = []
    lowered = source.lower()
    for pattern in (
        "bibliography keys are synchronized",
        "citation keys are synchronized",
        "cannot actually",
        "i cannot",
        "i can't",
        "as an ai",
    ):
        if pattern in lowered:
            notes.append(pattern)
    return notes


def citation_paragraph_stats(source: str) -> tuple[int, int]:
    stripped = "\n".join(_UNESCAPED_COMMENT_RE.sub("", line) for line in source.splitlines())
    body_match = re.search(r"\\begin\{document\}(?P<body>.*)\\end\{document\}", stripped, flags=re.DOTALL)
    body = body_match.group("body") if body_match else stripped
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", body)
        if len(re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?", "", paragraph).strip()) >= 80
    ]
    uncited = [paragraph for paragraph in paragraphs if not _LATEX_CITE_RE.search(paragraph)]
    return len(paragraphs), len(uncited)


def audit_latex_citations(
    *,
    bibtex_path: Path,
    tex_path: Path | None = None,
    claim_map_path: Path | None = None,
    allow_nocite_all: bool = False,
) -> CitationAuditResult:
    """Audit LaTeX citations against a BibTeX file."""

    bibtex_source = bibtex_path.read_text(encoding="utf-8")
    citation_keys = extract_bibtex_keys(bibtex_source)
    cited_keys: list[str] = []
    nocite_all = False
    paragraph_count = 0
    uncited_paragraph_count = 0
    author_notes: list[str] = []

    if tex_path is not None:
        tex_source = tex_path.read_text(encoding="utf-8")
        cited_keys, nocite_all = extract_latex_citations(tex_source)
        paragraph_count, uncited_paragraph_count = citation_paragraph_stats(tex_source)
        author_notes = find_author_notes(tex_source)

    missing_keys = sorted(key for key in cited_keys if key not in set(citation_keys))
    unused_keys = sorted(key for key in citation_keys if key not in set(cited_keys))

    unsupported_claims: list[str] = []
    if claim_map_path is not None and claim_map_path.exists():
        claim_map = json.loads(claim_map_path.read_text(encoding="utf-8"))
        unsupported_claims = find_unsupported_claims(claim_map)

    violations: list[str] = []
    if not citation_keys:
        violations.append("No BibTeX citation keys were found.")
    if missing_keys:
        violations.append(f"Missing BibTeX keys cited in LaTeX: {', '.join(missing_keys)}.")
    if nocite_all and not allow_nocite_all:
        violations.append(r"\nocite{*} is not allowed unless the user explicitly asks to include every reference.")
    if tex_path is not None and not cited_keys and not (nocite_all and allow_nocite_all):
        violations.append("No inline LaTeX citations were found in the manuscript body.")
    if paragraph_count and uncited_paragraph_count / paragraph_count > 0.5:
        violations.append(f"Too many manuscript paragraphs lack inline citations: {uncited_paragraph_count}/{paragraph_count}.")
    if unsupported_claims:
        violations.append(f"Unsupported manuscript claims: {len(unsupported_claims)}.")
    if author_notes:
        violations.append("Author/tool process notes remain in manuscript text: " + ", ".join(author_notes) + ".")

    return CitationAuditResult(
        status="fail" if violations else "pass",
        bibtex_path=str(bibtex_path),
        tex_path=str(tex_path) if tex_path is not None else None,
        citation_keys=citation_keys,
        cited_keys=cited_keys,
        missing_keys=missing_keys,
        unused_keys=unused_keys,
        nocite_all=nocite_all,
        violations=violations,
        unsupported_claims=unsupported_claims,
        paragraph_count=paragraph_count,
        uncited_paragraph_count=uncited_paragraph_count,
        author_notes=author_notes,
    )


def write_citation_audit(result: CitationAuditResult, output_path: Path) -> Path:
    """Write a citation audit JSON file and return its path."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
