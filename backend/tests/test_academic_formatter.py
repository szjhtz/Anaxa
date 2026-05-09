import pytest

from medrix_flow.academic.formatters import (
    format_apa7_reference,
    format_bibtex_entry,
    format_reference,
    normalize_reference_style,
    reference_style_label,
)
from medrix_flow.academic.quality import hydrate_quality_metadata
from medrix_flow.academic.types import PaperAuthor, PaperRecord
from medrix_flow.runtime.utils import now_iso


def _paper(
    *,
    title: str,
    authors: list[PaperAuthor],
    year: int | None,
    venue: str | None,
    doi: str | None = None,
    provider: str = "openalex",
    arxiv_id: str | None = None,
) -> PaperRecord:
    return hydrate_quality_metadata(
        PaperRecord(
            paper_id="paper-1",
            project_id="project-1",
            canonical_id="paper-1",
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            abstract="A detailed abstract.",
            doi=doi,
            arxiv_id=arxiv_id,
            provider=provider,
            provider_id="provider-1",
            source_url="https://arxiv.org/abs/2501.12345" if provider == "arxiv" else "https://example.org/paper-1",
            oa_url=None,
            metadata_only=False,
            keywords=[],
            methods=[],
            populations=[],
            conflict_flags=[],
            raw_source={},
            created_at=now_iso(),
            updated_at=now_iso(),
        )
    )


def test_format_apa7_reference_handles_complete_journal_entry():
    paper = _paper(
        title="foundation models for clinical reasoning",
        authors=[
            PaperAuthor(display_name="Alice Smith", given_name="Alice", family_name="Smith", ordinal=0),
            PaperAuthor(display_name="Bob Lee", given_name="Bob", family_name="Lee", ordinal=1),
        ],
        year=2025,
        venue="Journal of Medical AI",
        doi="10.1000/example.doi",
    )

    entry = format_apa7_reference(paper)

    assert "Smith, A." in entry.formatted_text
    assert "& Lee, B." in entry.formatted_text
    assert "(2025)." in entry.formatted_text
    assert "Journal of Medical AI." in entry.formatted_text
    assert entry.formatted_text.endswith("https://doi.org/10.1000/example.doi")
    assert entry.included_in_final is True


def test_format_apa7_reference_falls_back_when_author_or_year_missing():
    paper = _paper(
        title="understudied benchmark behavior",
        authors=[],
        year=None,
        venue=None,
        provider="arxiv",
        arxiv_id="2501.12345",
    )

    entry = format_apa7_reference(paper)

    assert entry.formatted_text.startswith("Understudied benchmark behavior (n.d.).")
    assert "arXiv." in entry.formatted_text
    assert entry.completeness in {"missing-author", "missing-year", "missing-venue"}


def test_format_bibtex_entry_emits_expected_fields():
    paper = _paper(
        title="benchmarking multimodal retrieval",
        authors=[PaperAuthor(display_name="Carol Ng", given_name="Carol", family_name="Ng", ordinal=0)],
        year=2024,
        venue="Proceedings of Example Conference",
        doi="10.2000/demo",
    )

    bibtex = format_bibtex_entry(paper)

    assert bibtex.startswith("@inproceedings")
    assert "title = {benchmarking multimodal retrieval}" in bibtex.lower()
    assert "author = {Ng, Carol}" in bibtex
    assert "doi = {10.2000/demo}" in bibtex


def test_reference_style_aliases_and_labels_are_normalized():
    assert normalize_reference_style("APA") == "apa7"
    assert normalize_reference_style("GB/T 7714") == "gbt7714"
    assert normalize_reference_style("mla") == "mla9"
    assert reference_style_label("gbt7714") == "GB/T 7714"

    with pytest.raises(ValueError, match="Unsupported reference style"):
        normalize_reference_style("made-up-style")


def test_format_reference_honors_non_apa_style():
    paper = _paper(
        title="benchmarking multimodal retrieval",
        authors=[PaperAuthor(display_name="Carol Ng", given_name="Carol", family_name="Ng", ordinal=0)],
        year=2024,
        venue="Proceedings of Example Conference",
        doi="10.2000/demo",
    )

    entry = format_reference(paper, "GB/T 7714")

    assert entry.style == "gbt7714"
    assert "benchmarking multimodal retrieval[C]" in entry.formatted_text
    assert "Proceedings of Example Conference, 2024." in entry.formatted_text
    assert entry.formatted_text.endswith("https://doi.org/10.2000/demo")


def test_format_reference_can_emit_bibtex_as_reference_entry():
    paper = _paper(
        title="benchmarking multimodal retrieval",
        authors=[PaperAuthor(display_name="Carol Ng", given_name="Carol", family_name="Ng", ordinal=0)],
        year=2024,
        venue="Proceedings of Example Conference",
        doi="10.2000/demo",
    )

    entry = format_reference(paper, "bibtex")

    assert entry.style == "bibtex"
    assert entry.formatted_text.startswith("@inproceedings")
    assert "author = {Ng, Carol}" in entry.formatted_text
