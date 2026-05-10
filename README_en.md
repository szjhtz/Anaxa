# Anaxa 3.0

**English** | [中文](./README.md)

<p align="center">
  <img src="./Anaxa%20logo.jpg" alt="Anaxa" width="96">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-3.0-111827?style=for-the-badge" alt="Version 3.0">
  <img src="https://img.shields.io/badge/Orchestration-LangGraph-blue?style=for-the-badge&logo=python" alt="LangGraph">
  <img src="https://img.shields.io/badge/Frontend-Next.js%2016-black?style=for-the-badge&logo=next.js" alt="Next.js">
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react" alt="React 19">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python" alt="Python 3.12">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

<p align="center">
  <b>An auditable, interruptible, human-steerable research copilot and workspace</b><br/>
  Literature Retrieval · Evidence Maps · Experiment Loops · LaTeX/PDF Manuscripts · Human Gates
</p>

---

## What Is Anaxa

Anaxa is an open-source agent system for scientific research workflows. It is not just a chat UI, and it is not an unsupervised paper-writing machine. It brings literature retrieval, evidence auditing, experiment execution, manuscript drafting, reviewer-style checks, and final artifact bundling into one traceable research lifecycle.

The goal is to move research assistance from "a model writes a long answer in chat" to "each step has sources, artifacts, status, failure records, and handoff points." Chat remains the main entry point, but research-heavy requests are routed to backend tools for academic search, experiments, manuscript export, and staged orchestration.

Anaxa is built for:

- Literature reviews, related work, research background, and reference curation.
- Manuscript drafts, experiment reports, and research memos with claim-level evidence.
- Reproducible analysis for CS/AI, data science, bioinformatics, and empirical research.
- One-shot LaTeX paper bundles with BibTeX, citation audit, and PDF output.
- Long-running research projects that require stage tracking and human approval.

## Core Research Workflow

Anaxa organizes complex research work around a `ResearchQuest`. A quest moves through explicit, recoverable stages:

```text
intake
  -> literature
  -> novelty_check
  -> evidence_verified
  -> experiment_planned
  -> experiment_running
  -> results_synthesized
  -> manuscript_draft
  -> review
  -> revision
  -> final_bundle
```

Each stage records inputs, outputs, tool calls, artifacts, failure reasons, and gate decisions in a research ledger. Risky actions such as external code execution, long experiments, automatic experiment-code modification, and final manuscript release require human gates by default.

## Key Capabilities

### Academic Retrieval and References

- `academic_research` handles multi-source paper retrieval, metadata normalization, deduplication, evidence-card generation, reference export, and coverage audits.
- Supported source families include Semantic Scholar, OpenAlex, Crossref, arXiv, DBLP, OpenReview, and ACL Anthology.
- References follow the user's requested style, including APA 7, MLA 9, Chicago, GB/T 7714, plain text, and BibTeX.
- Review, survey, and manuscript tasks activate a stricter quality profile with higher reference targets, citation-density checks, off-topic reference filtering, and automatic search repair.

### Claim-Level Evidence Map

Anaxa does not treat a bibliography at the end of a paper as sufficient evidence. Important claims should be bound to concrete support:

```text
claim -> paper_id -> citation_key -> snippet/page/abstract evidence -> support_status -> confidence
```

When full-text PDFs are unavailable, the system can fall back to title, abstract, and metadata evidence, but the audit marks that evidence as weaker. Missing citation keys, overuse of `\nocite{*}`, paragraphs without citations, unsupported claims, and leftover process notes are surfaced in `citation_audit.json` and can block final PDF release.

### Experiment Loop

- `experiment_lab` provides Python-first experiment execution, metric tracking, figure generation, and result-bundle export.
- It supports baselines, ablations, seeds, metrics, failure summaries, branch ranking, and a reproducibility ledger.
- CS/AI workflows cover regression, classification, clustering, dimensionality reduction, diagnostics, model evaluation, and paper-ready result summaries.
- Bioinformatics workflows cover bulk expression, differential analysis, enrichment, single-cell starter workflows, and common scientific figures.
- Empirical-research skills can translate DID, IV, RDD, PSM/IPW, DML, target-trial, and TMLE requirements into experiment metadata and gates.

### Manuscript and PDF Export

Manuscript, review, survey, and experiment-paper requests default to a LaTeX bundle:

- `manuscript.tex`
- `references.bib`
- `citation_audit.json`
- `manuscript.pdf`

The high-level `manuscript_export` tool handles file writing, citation audit, LaTeX compilation, and artifact presentation as one operation. Lower-level tools such as `write_file`, `citation_audit`, and `present_files` are still available, but final manuscript delivery should prefer the high-level export path instead of leaving file generation to ad hoc chat behavior.

The PDF path currently prefers `tectonic`. If the compiler is missing or LaTeX compilation fails, the system should return the exact tool error and keep the `.tex`, `.bib`, and audit files for repair.

### Quality Audit and Auto-Repair

`ResearchQualityAudit` checks common pre-submission risks:

- Insufficient literature coverage.
- Low in-text citation density.
- Off-topic or cross-domain references.
- Missing quantitative evidence, benchmark evidence, case studies, or experimental results.
- Evaluation frameworks without implementation challenges and mitigations.
- Repeated phrasing, over-absolute wording, weak transitions, and process-note residue.

The default policy is to repair first: expand search, add evidence, look for benchmarks, rewrite weak sections, and only then block at a human gate if the repair budget is exhausted.

### Thread Artifacts and Thread-Scoped Memory

- Each chat/thread has isolated `workspace`, `uploads`, `outputs`, and `memory.json` storage.
- A new chat starts with empty private memory and does not inherit a global user profile or another thread's research state.
- Reports, BibTeX files, PDFs, figures, tables, and audit files are written to thread-scoped outputs and discovered by the artifact panel.
- Legacy memory APIs remain for compatibility, but the frontend no longer exposes a shared memory settings page.

### Read-Only Feature Inventory

The frontend settings panel includes a read-only "Features" page that reflects backend configuration:

- Agents: default orchestrator, system agents, custom agents, and subagents.
- Tools: MCP servers, transport, enabled state, command or URL summaries, and redacted env/header keys.
- Skills: public and custom skills with name, description, category, enabled state, and license.

This page is an inventory, not an editor. It does not provide create, delete, edit, enable, disable, or connection-test controls. Existing backend management APIs remain available for scripts and compatibility.

## Architecture

```text
                  http://localhost:1000
                          |
                          v
                  +----------------+
                  |     Nginx      |
                  | reverse proxy  |
                  +---+--------+---+
                      |        |
      /api/langgraph/*|        |/api/*
                      v        v
        +----------------+   +------------------+
        | LangGraph      |   | Gateway API      |
        | Server :2024   |   | FastAPI :8001    |
        |                |   |                  |
        | Lead agent     |   | models/setup     |
        | middleware     |   | features         |
        | tools          |   | academic         |
        | subagents      |   | research         |
        +-------+--------+   | experiments      |
                |            | artifacts/runs   |
                |            +---------+--------+
                |                      |
                v                      v
        +----------------+   +------------------+
        | Sandbox / VFS  |   | SQLite / files   |
        | /mnt/user-data |   | .medrix-flow     |
        +----------------+   +------------------+

        +----------------------------------------+
        | Frontend :3000                         |
        | Next.js 16 / React 19 / Tailwind CSS 4 |
        +----------------------------------------+
```

Request routing:

- `/api/langgraph/*` -> LangGraph Server for agent interaction, threads, SSE streaming, and long-running runs.
- `/api/*` -> Gateway API for setup, features, academic research, research quests, experiments, uploads, artifacts, and runs.
- `/` -> Frontend, served by Next.js.

Runtime data is stored under `backend/.medrix-flow` or the directory pointed to by `MEDRIX_FLOW_HOME`. Each thread maps a virtual filesystem to `/mnt/user-data/{workspace,uploads,outputs}`.

## Quick Start

### Requirements

- Python 3.12+
- Node.js and pnpm
- uv
- nginx
- Docker, optional for container sandboxing or `make up`
- `tectonic`, optional but recommended for reliable LaTeX PDF generation

### Local Development

```bash
make setup
make doctor
make install
make dev
```

Open:

```text
http://localhost:1000
```

Local services:

- Frontend: `http://localhost:3000`
- Gateway API: `http://localhost:8001`
- LangGraph Server: `http://localhost:2024`
- Unified Nginx entry: `http://localhost:1000`

### Docker Production Mode

```bash
make up
```

Default access:

```text
http://localhost:1000
```

If `PORT` is set, Docker Compose maps `${PORT}` to container port `1000`. Stop the stack with:

```bash
make down
```

### Common Commands

| Command | Description |
|---|---|
| `make setup` | Idempotently create local config and env files |
| `make doctor` | Validate config, env vars, sandbox prerequisites, and DB writability |
| `make install` | Install backend and frontend dependencies |
| `make dev` | Start hot-reload development services |
| `make dev-daemon` | Start development services in the background |
| `make start` | Start local production mode |
| `make stop` | Stop local services |
| `make up` | Build and start Docker production services |
| `make down` | Stop Docker production services |
| `make verify` | Run backend lint/test and frontend lint/typecheck/unit/build checks |

## Configuration

### Model and App Configuration

The main configuration file is `config.yaml`, with `config.example.yaml` as the template. The lookup order includes:

1. `MEDRIX_FLOW_CONFIG_PATH`
2. `backend/config.yaml`
3. Root-level `config.yaml`

Models, tool groups, sandbox provider, checkpointer, memory, research gates, and quality policies are configured there. Use:

```bash
make config-upgrade
```

to merge newly added fields into an existing config.

### Extensions Configuration

MCP servers and skill enablement live in `extensions_config.json`, or in the path specified by `MEDRIX_FLOW_EXTENSIONS_CONFIG_PATH`.

The frontend "Features" page reads:

```text
GET /api/features
```

to show a read-only inventory of agents, MCP tools, and skills. Sensitive environment variables and headers are redacted to key names and configured status only.

### Compatibility Identifiers

Anaxa 3.0 is the user-facing product name. Some technical identifiers remain unchanged to avoid breaking existing scripts, runtime directories, environment variables, and imports:

- Python import package: `medrix_flow`
- Compatibility names in Python distribution and workspace packages
- Environment variables: `MEDRIX_FLOW_*`
- Runtime directory: `.medrix-flow`
- Admin header: `x-medrix-admin-token`
- Some Docker container, Compose project, and cleanup prefixes

These are compatibility identifiers, not the new product brand.

## API Overview

### Feature Inventory

| Route | Description |
|---|---|
| `GET /api/features` | Read-only aggregate of agents, MCP tools, and skills |

### Academic Research

| Route | Description |
|---|---|
| `POST /api/academic/projects` | Create or reuse an academic project |
| `POST /api/academic/projects/{project_id}/ingest` | Retrieve, normalize, deduplicate, and build an evidence pool |
| `POST /api/academic/projects/{project_id}/synthesize` | Generate report, references, evidence map, and audit |
| `GET /api/academic/projects/{project_id}` | Read the project snapshot |
| `GET /api/academic/projects/{project_id}/references` | Export references |
| `GET /api/academic/projects/{project_id}/graph` | Read the literature/evidence graph |

### Research Quest

| Route | Description |
|---|---|
| `GET /api/research/quests` | List research quests |
| `POST /api/research/quests` | Create a research quest |
| `GET /api/research/quests/{quest_id}` | Read the quest snapshot |
| `POST /api/research/quests/{quest_id}/advance` | Advance one lifecycle stage |
| `POST /api/research/quests/{quest_id}/gate` | Record a human gate decision |
| `GET /api/research/quests/{quest_id}/evidence` | Read evidence mappings |
| `GET /api/research/quests/{quest_id}/experiments` | Read linked experiments |
| `GET /api/research/quests/{quest_id}/manuscript` | Read the manuscript workspace |

### Experiments

| Route | Description |
|---|---|
| `POST /api/experiments/projects` | Create an experiment project |
| `POST /api/experiments/projects/{project_id}/execute` | Execute the experiment workflow |
| `POST /api/experiments/projects/{project_id}/export` | Export the experiment bundle |
| `GET /api/experiments/projects/{project_id}` | Read the experiment project |
| `GET /api/experiments/projects/{project_id}/artifacts` | Read experiment artifacts |

### Threads, Runs, Files

| Route | Description |
|---|---|
| `GET /api/threads/{thread_id}/runs` | List runs for a thread |
| `POST /api/threads/{thread_id}/runs/{run_id}/cancel` | Cancel a run |
| `GET /api/threads/{thread_id}/runs/{run_id}/messages` | Read run messages |
| `POST /api/threads/{thread_id}/uploads` | Upload files into a thread |
| `GET /api/threads/{thread_id}/uploads/list` | List uploaded files |
| `GET /api/threads/{thread_id}/artifacts` | List output artifacts |
| `GET /api/threads/{thread_id}/artifacts/{path}` | Read or download an artifact |
| `GET /api/threads/{thread_id}/memory` | Read private memory for the current thread |
| `POST /api/threads/{thread_id}/memory/reload` | Reload private memory for the current thread |

## Built-In Tools and Skills

Built-in tools:

- `academic_research`: paper retrieval, evidence cards, references, and audits.
- `research_assistant`: research lifecycle, ledger, gates, quality audits, and `run_pipeline`.
- `experiment_lab`: experiment execution, figures, metrics, and reproducibility bundles.
- `manuscript_export`: one-shot LaTeX/BibTeX/audit/PDF export.
- `citation_audit`: citation key, in-text citation, and claim-support checks for LaTeX.
- `present_files`: artifact presentation and `.tex` PDF preview.
- `ask_clarification`: structured user confirmation.
- `visual_quality_check` / `visual_refinement_check`: visual artifact QA gates.
- sandbox tools: `bash`, `ls`, `read_file`, `write_file`, and `str_replace`.

Skills are discovered from `skills/public` and `skills/custom`, then injected according to `extensions_config.json`. Bundled public skills cover academic writing, citation curation, empirical methods, scientific figures, data analysis, technical diagrams, presentations, PDFs, and skill/plugin creation.

## Safety and Deployment

- Production should set `MEDRIX_FLOW_ENV=production`.
- When exposing the UI/API through Nginx, set `MEDRIX_FLOW_UI_PASSWORD`; otherwise protected pages and APIs fail closed.
- Scripted administration can use `MEDRIX_GATEWAY_ADMIN_TOKEN` with the `x-medrix-admin-token` header.
- Local sandboxing is for trusted development. Production or untrusted code execution should use `AioSandboxProvider` or provisioner/Kubernetes mode.
- Bash tool calls go through safety auditing and path isolation; thread virtual paths are constrained to `/mnt/user-data`.
- External code execution, long experiments, automatic experiment-code modification, and final manuscript release should pass through human gates by default.

## Project Structure

```text
.
├── backend/
│   ├── app/gateway/                 # FastAPI Gateway API
│   ├── packages/harness/medrix_flow/ # LangGraph agents, tools, research, sandbox
│   └── tests/                        # backend tests
├── frontend/
│   ├── src/app/                      # Next.js app routes
│   ├── src/components/               # workspace, settings, artifact UI
│   └── test/                         # frontend tests
├── skills/
│   ├── public/                       # bundled skills
│   └── custom/                       # user skills
├── docker/
│   ├── nginx/                        # local and production reverse proxy config
│   └── provisioner/                  # optional sandbox provisioner
├── scripts/                          # setup, serve, deploy, doctor helpers
├── config.example.yaml               # app config template
└── extensions_config.example.json    # MCP and skills config template
```

## Development and Verification

Backend:

```bash
cd backend
make lint
make test
```

Frontend:

```bash
cd frontend
pnpm lint
pnpm typecheck
pnpm test:unit
BETTER_AUTH_SECRET=local-dev-secret pnpm build
```

Full local verification:

```bash
make verify
```

## License and Acknowledgements

This project is released under the MIT License. Anaxa builds on LangGraph, Next.js, FastAPI, open-source agent tooling, and ideas from scientific automation projects. Its product stance is a research copilot: models can help with research work, but they do not replace the researcher's judgment, evidence responsibility, or authorship responsibility.
