"""Tests for one-shot manuscript export."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

manuscript_export_tool_module = importlib.import_module("medrix_flow.tools.builtins.manuscript_export_tool")


def _make_runtime(outputs_path: str) -> SimpleNamespace:
    return SimpleNamespace(
        state={"thread_data": {"outputs_path": outputs_path}},
        context={"thread_id": "thread-1"},
    )


def _tex(citation: str = r"\cite{smith2024}") -> str:
    return rf"""
\documentclass{{article}}
\begin{{document}}
Supported claim {citation}.
\bibliographystyle{{plain}}
\bibliography{{references}}
\end{{document}}
"""


def _bib() -> str:
    return """
@article{smith2024,
  title = {A paper},
  author = {Smith, Jane},
  journal = {Journal},
  year = {2024}
}
"""


def _stub_latex_compile(monkeypatch, pdf_bytes: bytes = b"%PDF-1.4") -> None:
    def prepare(tex_path: Path) -> Path:
        preview_dir = tex_path.parent / ".latex-preview"
        preview_dir.mkdir()
        preview_path = preview_dir / tex_path.name
        preview_path.write_text(tex_path.read_text(encoding="utf-8"), encoding="utf-8")
        return preview_path

    def compile_pdf(tex_path: Path, output_dir: Path | None = None) -> Path:
        pdf_path = (output_dir or tex_path.parent) / tex_path.with_suffix(".pdf").name
        pdf_path.write_bytes(pdf_bytes)
        return pdf_path

    monkeypatch.setattr(manuscript_export_tool_module, "prepare_latex_preview", prepare)
    monkeypatch.setattr(manuscript_export_tool_module, "compile_latex_to_pdf", compile_pdf)


def test_manuscript_export_writes_bundle_and_pdf(tmp_path, monkeypatch):
    outputs_dir = tmp_path / "threads" / "thread-1" / "user-data" / "outputs"
    outputs_dir.mkdir(parents=True)
    _stub_latex_compile(monkeypatch)

    result = manuscript_export_tool_module.manuscript_export_tool.func(
        runtime=_make_runtime(str(outputs_dir)),
        tex_content=_tex(),
        bibtex_content=_bib(),
        filename_stem="paper",
        tool_call_id="tc-1",
    )

    assert result.update["artifacts"] == [
        "/mnt/user-data/outputs/paper.pdf",
        "/mnt/user-data/outputs/paper.tex",
        "/mnt/user-data/outputs/references.bib",
        "/mnt/user-data/outputs/citation_audit.json",
    ]
    assert (outputs_dir / "paper.pdf").read_bytes() == b"%PDF-1.4"
    assert (outputs_dir / "paper.tex").exists()
    assert (outputs_dir / "references.bib").exists()
    assert json.loads((outputs_dir / "citation_audit.json").read_text(encoding="utf-8"))["status"] == "pass"
    assert result.update["messages"][0].content.startswith("PASS:")


def test_manuscript_export_blocks_missing_citation_key(tmp_path, monkeypatch):
    outputs_dir = tmp_path / "threads" / "thread-1" / "user-data" / "outputs"
    outputs_dir.mkdir(parents=True)
    monkeypatch.setattr(
        manuscript_export_tool_module,
        "compile_latex_to_pdf",
        lambda _tex_path, _output_dir=None: (_ for _ in ()).throw(AssertionError("should not compile")),
    )

    result = manuscript_export_tool_module.manuscript_export_tool.func(
        runtime=_make_runtime(str(outputs_dir)),
        tex_content=_tex(r"\cite{missing2025}"),
        bibtex_content=_bib(),
        filename_stem="paper",
        tool_call_id="tc-1",
    )

    assert result.update["artifacts"] == [
        "/mnt/user-data/outputs/citation_audit.json",
        "/mnt/user-data/outputs/paper.tex",
        "/mnt/user-data/outputs/references.bib",
    ]
    assert not (outputs_dir / "paper.pdf").exists()
    assert "citation audit blocked PDF generation" in result.update["messages"][0].content
    audit = json.loads((outputs_dir / "citation_audit.json").read_text(encoding="utf-8"))
    assert audit["missing_keys"] == ["missing2025"]


def test_manuscript_export_blocks_nocite_all_by_default(tmp_path):
    outputs_dir = tmp_path / "threads" / "thread-1" / "user-data" / "outputs"
    outputs_dir.mkdir(parents=True)

    result = manuscript_export_tool_module.manuscript_export_tool.func(
        runtime=_make_runtime(str(outputs_dir)),
        tex_content=_tex(r"\nocite{*}"),
        bibtex_content=_bib(),
        filename_stem="paper",
        tool_call_id="tc-1",
    )

    assert not (outputs_dir / "paper.pdf").exists()
    assert r"\nocite{*} is not allowed" in result.update["messages"][0].content


def test_manuscript_export_blocks_unsupported_claim_map(tmp_path):
    outputs_dir = tmp_path / "threads" / "thread-1" / "user-data" / "outputs"
    outputs_dir.mkdir(parents=True)
    claim_map = {
        "claims": [
            {
                "claim": "The method is universally superior.",
                "support_status": "unsupported",
                "evidence": [],
            }
        ]
    }

    result = manuscript_export_tool_module.manuscript_export_tool.func(
        runtime=_make_runtime(str(outputs_dir)),
        tex_content=_tex(),
        bibtex_content=_bib(),
        claim_map_json=json.dumps(claim_map),
        filename_stem="paper",
        tool_call_id="tc-1",
    )

    audit = json.loads((outputs_dir / "citation_audit.json").read_text(encoding="utf-8"))
    assert audit["unsupported_claims"] == ["The method is universally superior."]
    assert not (outputs_dir / "paper.pdf").exists()
    assert "Unsupported claims: 1" in result.update["messages"][0].content


def test_manuscript_export_allows_nocite_all_when_explicit(tmp_path, monkeypatch):
    outputs_dir = tmp_path / "threads" / "thread-1" / "user-data" / "outputs"
    outputs_dir.mkdir(parents=True)
    _stub_latex_compile(monkeypatch)

    result = manuscript_export_tool_module.manuscript_export_tool.func(
        runtime=_make_runtime(str(outputs_dir)),
        tex_content=_tex(r"\nocite{*}"),
        bibtex_content=_bib(),
        filename_stem="paper",
        allow_nocite_all=True,
        tool_call_id="tc-1",
    )

    assert result.update["artifacts"][0] == "/mnt/user-data/outputs/paper.pdf"
    assert json.loads((outputs_dir / "citation_audit.json").read_text(encoding="utf-8"))["status"] == "pass"


def test_manuscript_export_reports_compile_failure_and_preserves_inputs(tmp_path, monkeypatch):
    outputs_dir = tmp_path / "threads" / "thread-1" / "user-data" / "outputs"
    outputs_dir.mkdir(parents=True)
    stale_pdf = outputs_dir / "paper.pdf"
    stale_pdf.write_bytes(b"stale")

    def prepare(tex_path: Path) -> Path:
        return tex_path

    def fail_compile(_tex_path: Path, _output_dir: Path | None = None) -> Path:
        raise RuntimeError("tectonic failed")

    monkeypatch.setattr(manuscript_export_tool_module, "prepare_latex_preview", prepare)
    monkeypatch.setattr(manuscript_export_tool_module, "compile_latex_to_pdf", fail_compile)

    result = manuscript_export_tool_module.manuscript_export_tool.func(
        runtime=_make_runtime(str(outputs_dir)),
        tex_content=_tex(),
        bibtex_content=_bib(),
        filename_stem="paper",
        tool_call_id="tc-1",
    )

    assert result.update["artifacts"] == [
        "/mnt/user-data/outputs/paper.tex",
        "/mnt/user-data/outputs/references.bib",
        "/mnt/user-data/outputs/citation_audit.json",
    ]
    assert not stale_pdf.exists()
    assert (outputs_dir / "paper.tex").exists()
    assert (outputs_dir / "references.bib").exists()
    assert "LaTeX compilation failed" in result.update["messages"][0].content


def test_manuscript_export_rejects_unsafe_filename_stem(tmp_path):
    outputs_dir = tmp_path / "threads" / "thread-1" / "user-data" / "outputs"
    outputs_dir.mkdir(parents=True)

    result = manuscript_export_tool_module.manuscript_export_tool.func(
        runtime=_make_runtime(str(outputs_dir)),
        tex_content=_tex(),
        bibtex_content=_bib(),
        filename_stem="../outside",
        tool_call_id="tc-1",
    )

    assert "filename_stem must be a filename stem" in result.update["messages"][0].content
    assert not any(outputs_dir.iterdir())
