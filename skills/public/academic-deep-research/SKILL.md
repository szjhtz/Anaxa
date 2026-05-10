---
name: academic-deep-research
description: Use this skill for academic reports, literature reviews, experiment reports, user-selected reference styles, innovation-point mining, or when the user wants a topic turned into a paper-backed evidence bundle instead of generic web research.
---

# Academic Deep Research

Use this skill when the user asks for:

- academic reports or literature reviews
- experiment reports with professional references
- references in a specific user-requested style or richer scholarly citations
- innovation-point mining based on papers
- a research knowledge base, evidence map, or local literature store

## Core Rules

1. Prefer the `academic_research` tool over ad hoc web browsing when the task is literature-heavy.
2. When the user asks for latest datasets, benchmarks, leaderboards, baselines, or experiment-ready evidence, call `dataset_benchmark_discovery` before drafting conclusions.
3. For large academic tasks, delegate to `task` with `subagent_type="academic-researcher"` so the main thread stays clean.
4. Do not invent references, DOI metadata, datasets, benchmark scores, or claims that are not grounded in generated evidence.
5. Treat the generated `report.md`, `references.md`, `references.bib`, `evidence_map.json`, and `dataset_benchmark_map.json` as source material with different roles: literature support is not the same as executed experiment support.
6. When writing final prose in chat, use the artifact bundle first and only then polish wording.
7. Follow the user's requested reference style. Use APA 7 only when no style is specified.
8. For manuscript-style requests, default to LaTeX + PDF and prefer `manuscript_export` so writing, citation audit, PDF compilation, and artifact presentation happen in one enforced step.
9. Read or audit `references.bib` before inserting inline LaTeX citations. Use exact BibTeX keys only; do not use `\nocite{*}` unless the user explicitly asks to list every reference without inline citation placement.
10. If citation or PDF generation fails, report the exact failed tool and error. Do not claim tools are unavailable when file tools, `manuscript_export`, `citation_audit`, or `present_files` are available.

## Recommended Workflow

### 1. Start Structured Research

If the user gives a research topic, run:

- `academic_research(topic=..., scope=...)`

If the task depends on datasets, benchmarks, or baselines, first run:

- `dataset_benchmark_discovery(topic=..., scope=...)`

This will automatically:

- expand queries
- retrieve and normalize papers
- deduplicate and rank them
- produce a report bundle

The benchmark discovery bundle records candidate datasets, license/access
status, metrics, baseline/SOTA hints, and risks. It does not download gated
data or make leaderboard claims final.

### 2. Build Manuscript Bundle When Requested

For a paper, manuscript, review article draft, or experiment paper:

- create or reuse `references.bib`
- use `dataset_benchmark_map.json` to name candidate datasets/benchmarks only after checking access and version/date
- use `experiment_lab` outputs for executed results, ablations, robustness checks, and error analysis
- keep experimental claims unsupported unless `claim_support_matrix.json` marks them `supported_by_experiment`
- write LaTeX with exact BibTeX keys from `references.bib`
- call `manuscript_export(tex_content=..., bibtex_content=..., filename_stem="manuscript")`
- if `manuscript_export` reports missing keys, unsupported claims, blocked `\nocite{*}`, or compile errors, fix the inputs and retry before final delivery
- use `citation_audit` and `present_files` only as fallback tools for narrower manual checks or existing files

### 3. Escalate to Subagent When Needed

If the task is large, multi-part, or the user wants a full report, use:

- `task(description=..., prompt=..., subagent_type="academic-researcher")`

The subagent should use `academic_research` as its primary tool and then summarize the bundle.

### 4. Output Discipline

When summarizing the generated academic bundle:

- mention `project_id`
- mention how many core papers and formatted references were retained
- mention citation audit status for manuscript outputs
- mention any evidence gaps
- point the user to the artifacts instead of rewriting everything inline

## What Good Looks Like

- the report is evidence-backed rather than generic
- the references list is materially richer than a normal web-search answer
- reference entries are normalized, deduplicated, and formatted in the requested style
- innovation directions are tied to literature gaps, not speculation
