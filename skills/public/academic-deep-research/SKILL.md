---
name: academic-deep-research
description: Use this skill for academic reports, literature reviews, experiment reports, APA references, innovation-point mining, or when the user wants a topic turned into a paper-backed evidence bundle instead of generic web research.
---

# Academic Deep Research

Use this skill when the user asks for:

- academic reports or literature reviews
- experiment reports with professional references
- APA-style references or richer scholarly citations
- innovation-point mining based on papers
- a research knowledge base, evidence map, or local literature store

## Core Rules

1. Prefer the `academic_research` tool over ad hoc web browsing when the task is literature-heavy.
2. For large academic tasks, delegate to `task` with `subagent_type="academic-researcher"` so the main thread stays clean.
3. Do not invent references, DOI metadata, or claims that are not grounded in the generated evidence bundle.
4. Treat the generated `report.md`, `references.md`, `references.bib`, and `evidence_map.json` as the source of truth.
5. When writing final prose in chat, use the artifact bundle first and only then polish wording.
6. For manuscript-style requests, default to LaTeX + PDF: write `manuscript.tex`, keep `references.bib`, generate `citation_audit.json`, and present the `.tex` file so PDF export is attempted.
7. Read or audit `references.bib` before inserting inline LaTeX citations. Use exact BibTeX keys only; do not use `\nocite{*}` unless the user explicitly asks to list every reference without inline citation placement.
8. If citation or PDF generation fails, report the exact failed tool and error. Do not claim tools are unavailable when file tools, `citation_audit`, or `present_files` are available.

## Recommended Workflow

### 1. Start Structured Research

If the user gives a research topic, run:

- `academic_research(topic=..., scope=...)`

This will automatically:

- expand queries
- retrieve and normalize papers
- deduplicate and rank them
- produce a report bundle

### 2. Build Manuscript Bundle When Requested

For a paper, manuscript, review article draft, or experiment paper:

- create or reuse `references.bib`
- write `manuscript.tex` under `/mnt/user-data/outputs`
- call `citation_audit(bibtex_path="/mnt/user-data/outputs/references.bib", tex_path="/mnt/user-data/outputs/manuscript.tex")`
- fix missing keys or unsupported `\nocite{*}` before final delivery
- call `present_files(filepaths=["/mnt/user-data/outputs/manuscript.tex"])`

### 3. Escalate to Subagent When Needed

If the task is large, multi-part, or the user wants a full report, use:

- `task(description=..., prompt=..., subagent_type="academic-researcher")`

The subagent should use `academic_research` as its primary tool and then summarize the bundle.

### 4. Output Discipline

When summarizing the generated academic bundle:

- mention `project_id`
- mention how many core papers and APA references were retained
- mention citation audit status for manuscript outputs
- mention any evidence gaps
- point the user to the artifacts instead of rewriting everything inline

## What Good Looks Like

- the report is evidence-backed rather than generic
- the references list is materially richer than a normal web-search answer
- APA entries are normalized and deduplicated
- innovation directions are tied to literature gaps, not speculation
