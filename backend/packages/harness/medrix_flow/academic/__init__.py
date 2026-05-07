"""Academic research pipeline for literature-heavy report generation."""

from .adapters import AcademicSourceAdapter, build_default_adapters
from .formatters import format_apa7_reference, format_bibtex_entry
from .repository import AcademicRepository
from .service import AcademicResearchService
from .types import (
    AcademicGraph,
    EvidenceCardRecord,
    OutlineNodeRecord,
    PaperAuthor,
    PaperEdgeRecord,
    PaperRecord,
    ReferenceEntry,
    ReportExportRecord,
    ResearchProject,
    SearchQueryRecord,
)

__all__ = [
    "AcademicGraph",
    "AcademicRepository",
    "AcademicResearchService",
    "AcademicSourceAdapter",
    "EvidenceCardRecord",
    "OutlineNodeRecord",
    "PaperAuthor",
    "PaperEdgeRecord",
    "PaperRecord",
    "ReferenceEntry",
    "ReportExportRecord",
    "ResearchProject",
    "SearchQueryRecord",
    "build_default_adapters",
    "format_apa7_reference",
    "format_bibtex_entry",
]
