# Anaxa 3.0

[English](./README_en.md) | **中文**

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
  <b>可审计、可暂停、可接管的自动科研助手与研究工作台</b><br/>
  文献检索 · 证据映射 · 实验闭环 · LaTeX/PDF 成稿 · 人工 Gate
</p>

---

## Anaxa 是什么

Anaxa 是一个面向科研工作流的开源智能体系统。它不是单纯的聊天机器人，也不是无人监管的自动发论文机器，而是把文献检索、证据审计、实验执行、论文写作、同行评审式检查和最终产物打包放进同一个可追踪的研究生命周期中。

系统的核心目标是让科研任务从“对话里临时生成一段文字”升级为“每一步都有来源、产物、状态和人工接管点”的工作台。普通聊天仍然是入口，但复杂研究任务会被路由到后端的学术检索、实验、论文导出和研究编排工具。

适合的场景包括：

- 系统综述、related work、课题背景调研和参考文献整理。
- 需要 claim-level 证据绑定的论文草稿、实验报告和研究备忘录。
- CS/AI、数据科学、生物信息和实证研究中的可复现实验分析。
- LaTeX 论文 bundle、BibTeX、citation audit 和 PDF 的一键交付。
- 长任务、阶段性科研项目和需要人工批准的自动化研究流程。

## 核心科研流程

Anaxa 的研究链路围绕 `ResearchQuest` 展开。它把一个科研任务拆成可检查、可恢复的阶段：

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

每个阶段都会把输入、输出、工具调用、artifact、失败原因和 gate 决策写入研究 ledger。对于风险较高的步骤，例如外部代码执行、长实验、自动修改实验代码和最终论文发布，系统默认要求 human gate，而不是直接放任模型继续推进。

## 关键能力

### 学术检索与引用体系

- `academic_research` 负责多源文献检索、元数据规范化、去重、证据卡生成、参考文献导出和 coverage audit。
- 支持 Semantic Scholar、OpenAlex、Crossref、arXiv、DBLP、OpenReview、ACL Anthology 等来源组合。
- References 按用户选择的格式输出，支持 APA 7、MLA 9、Chicago、GB/T 7714、plain text 和 BibTeX。
- 综述、survey、manuscript 类任务会启用更严格的质量画像：更高的 reference 目标、正文引用密度检查、离题文献过滤和自动补检索。

### Claim-Level Evidence Map

Anaxa 不把“文末列了参考文献”视为合格引用。核心论断需要绑定到具体证据：

```text
claim -> paper_id -> citation_key -> snippet/page/abstract evidence -> support_status -> confidence
```

没有全文 PDF 时，系统会降级使用标题、摘要和元数据，但会在 audit 中标记为弱证据。缺失 citation key、滥用 `\nocite{*}`、正文无段落级引用、unsupported claim 或作者过程说明残留，都会在 `citation_audit.json` 中暴露，并可阻断最终 PDF release。

### 实验闭环

- `experiment_lab` 提供 Python-first 的实验执行、指标记录、图表生成和结果 bundle 导出。
- 支持 baseline、ablation、seed、metric、failure summary、branch ranking 和 reproducibility ledger。
- CS/AI 任务可覆盖回归、分类、聚类、降维、诊断图、模型评估和论文级结果摘要。
- 生物信息任务可覆盖 bulk 表达、差异分析、富集分析、单细胞起步流程和常见科研图。
- 实证研究方法 skill 可把 DID、IV、RDD、PSM/IPW、DML、target trial、TMLE 等方法要求转成实验 metadata 和 gate。

### 论文成稿与 PDF 导出

论文、综述、实验论文和正式研究报告默认走 LaTeX bundle：

- `manuscript.tex`
- `references.bib`
- `citation_audit.json`
- `manuscript.pdf`

高层工具 `manuscript_export` 会统一完成落盘、citation audit、LaTeX 编译和 artifacts 展示。底层仍保留 `write_file`、`citation_audit` 和 `present_files`，但正式论文交付优先使用高层出口，避免模型只在聊天里说“无法生成文件”。

当前 PDF 链路优先使用 `tectonic`。如果编译器缺失或 LaTeX 编译失败，系统应返回明确的工具错误，并保留 `.tex`、`.bib` 和 audit 文件供继续修复。

### 质量审计与自动修复

`ResearchQualityAudit` 覆盖投稿前常见质量风险：

- 文献覆盖不足。
- 正文引用密度过低。
- 离题或跨领域外围文献混入。
- 定量证据、benchmark、case study 或实验结果不足。
- 评估框架缺少实施挑战与解决方案。
- 重复表达、绝对化措辞、过渡缺失和过程说明残留。

默认策略是先自动补检索、补证据、补 benchmark、重写薄弱章节；修复预算耗尽后再阻塞到人工 gate，并返回具体补救报告。

### Thread Artifacts 与对话级记忆

- 每个 chat/thread 都有独立的 `workspace`、`uploads`、`outputs` 和 `memory.json`。
- 新建对话从空记忆开始，不会继承其他对话的用户画像或研究状态。
- 当前对话的报告、BibTeX、PDF、图表、表格和审计文件会落到 thread-scoped outputs，并通过 artifact 面板发现、预览和下载。
- 后端保留旧 memory API 作为兼容层，但前端不再提供全局记忆设置页。

### 功能配置只读展示

前端设置中的“功能”页集中展示当前后端配置：

- Agents：默认编排器、系统 agent、自定义 agent 和 subagent。
- Tools：MCP server、transport、enabled 状态、命令或 URL 摘要、redacted env/header keys。
- Skills：公共和自定义 skill 的名称、描述、分类、启用状态和 license。

这个页面是只读清单，不提供新增、删除、编辑、启用、停用或测试连接操作。底层管理 API 仍为脚本化管理和兼容场景保留。

## 系统架构

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

请求路由：

- `/api/langgraph/*` -> LangGraph Server：agent 交互、thread、SSE streaming、long-running run。
- `/api/*` -> Gateway API：配置、features、academic、research、experiments、uploads、artifacts、runs。
- `/` -> Frontend：Next.js Web UI。

运行时数据主要存储在 `backend/.medrix-flow` 或 `MEDRIX_FLOW_HOME` 指向的目录中。每个 thread 的虚拟文件系统会映射为 `/mnt/user-data/{workspace,uploads,outputs}`。

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 与 pnpm
- uv
- nginx
- Docker 可选；使用容器沙箱或 `make up` 时需要
- `tectonic` 可选；用于稳定生成 LaTeX PDF

### 本地开发

```bash
make setup
make doctor
make install
make dev
```

启动后访问：

```text
http://localhost:1000
```

本地开发服务：

- Frontend: `http://localhost:3000`
- Gateway API: `http://localhost:8001`
- LangGraph Server: `http://localhost:2024`
- Nginx unified entry: `http://localhost:1000`

### Docker 生产模式

```bash
make up
```

默认映射到：

```text
http://localhost:1000
```

如设置 `PORT`，Docker Compose 会把 `${PORT}` 映射到容器内的 `1000`。停止服务：

```bash
make down
```

### 常用命令

| 命令 | 说明 |
|---|---|
| `make setup` | 幂等初始化本地配置和环境文件 |
| `make doctor` | 检查配置、环境变量、沙箱和数据库可写性 |
| `make install` | 安装 backend 与 frontend 依赖 |
| `make dev` | 启动开发模式，支持热重载 |
| `make dev-daemon` | 后台启动开发服务 |
| `make start` | 本地生产模式启动 |
| `make stop` | 停止本地服务 |
| `make up` | 构建并启动 Docker 生产服务 |
| `make down` | 停止 Docker 生产服务 |
| `make verify` | 跑 backend lint/test、frontend lint/typecheck/unit/build |

## 配置

### 模型与应用配置

主配置文件是 `config.yaml`，模板为 `config.example.yaml`。默认查找顺序包括：

1. `MEDRIX_FLOW_CONFIG_PATH`
2. `backend/config.yaml`
3. 仓库根目录 `config.yaml`

模型、工具组、沙箱 provider、checkpointer、memory、research gate 和质量策略都通过该文件配置。可使用：

```bash
make config-upgrade
```

把新字段合并到已有配置。

### Extensions 配置

MCP server 和 skills 的启用状态存放在 `extensions_config.json`，也可以通过 `MEDRIX_FLOW_EXTENSIONS_CONFIG_PATH` 指定路径。

前端“功能”页通过：

```text
GET /api/features
```

只读展示 agents、MCP tools 和 skills。敏感环境变量和 header 只显示 key 与 configured 状态，不显示真实值。

### 兼容技术标识

Anaxa 3.0 已完成用户可见品牌迁移，但为了避免破坏已有脚本、数据目录、环境变量和 import 路径，以下技术标识仍保留：

- Python import package: `medrix_flow`
- Python distribution / workspace package names中的兼容命名
- Environment variables: `MEDRIX_FLOW_*`
- Runtime directory: `.medrix-flow`
- Admin header: `x-medrix-admin-token`
- 部分 Docker container、Compose project 和 cleanup prefix

这些名称是兼容层，不代表新的产品品牌。

## API 概览

### Feature Inventory

| Route | 说明 |
|---|---|
| `GET /api/features` | 只读聚合 agents、MCP tools、skills |

### Academic Research

| Route | 说明 |
|---|---|
| `POST /api/academic/projects` | 创建或复用学术项目 |
| `POST /api/academic/projects/{project_id}/ingest` | 多源检索、规范化、去重和证据池构建 |
| `POST /api/academic/projects/{project_id}/synthesize` | 生成报告、references、evidence map 和 audit |
| `GET /api/academic/projects/{project_id}` | 读取项目快照 |
| `GET /api/academic/projects/{project_id}/references` | 导出参考文献 |
| `GET /api/academic/projects/{project_id}/graph` | 读取文献/证据图 |

### Research Quest

| Route | 说明 |
|---|---|
| `GET /api/research/quests` | 列出 research quests |
| `POST /api/research/quests` | 创建 research quest |
| `GET /api/research/quests/{quest_id}` | 读取 quest snapshot |
| `POST /api/research/quests/{quest_id}/advance` | 推进一个阶段 |
| `POST /api/research/quests/{quest_id}/gate` | 记录人工 gate 决策 |
| `GET /api/research/quests/{quest_id}/evidence` | 读取证据映射 |
| `GET /api/research/quests/{quest_id}/experiments` | 读取实验关联 |
| `GET /api/research/quests/{quest_id}/manuscript` | 读取 manuscript workspace |

### Experiments

| Route | 说明 |
|---|---|
| `POST /api/experiments/projects` | 创建实验项目 |
| `POST /api/experiments/projects/{project_id}/execute` | 执行实验流程 |
| `POST /api/experiments/projects/{project_id}/export` | 导出实验 bundle |
| `GET /api/experiments/projects/{project_id}` | 读取实验项目 |
| `GET /api/experiments/projects/{project_id}/artifacts` | 读取实验产物 |

### Threads, Runs, Files

| Route | 说明 |
|---|---|
| `GET /api/threads/{thread_id}/runs` | 查看当前 thread 的 runs |
| `POST /api/threads/{thread_id}/runs/{run_id}/cancel` | 取消 run |
| `GET /api/threads/{thread_id}/runs/{run_id}/messages` | 读取 run messages |
| `POST /api/threads/{thread_id}/uploads` | 上传文件到 thread |
| `GET /api/threads/{thread_id}/uploads/list` | 列出上传文件 |
| `GET /api/threads/{thread_id}/artifacts` | 列出 outputs artifacts |
| `GET /api/threads/{thread_id}/artifacts/{path}` | 读取或下载 artifact |
| `GET /api/threads/{thread_id}/memory` | 读取当前 thread 的私有记忆 |
| `POST /api/threads/{thread_id}/memory/reload` | 重新加载当前 thread 的记忆 |

## 内置工具与 Skills

内置工具：

- `academic_research`：文献检索、证据卡、references 和 audit。
- `research_assistant`：研究生命周期、ledger、gate、quality audit 和 `run_pipeline`。
- `experiment_lab`：实验执行、图表、指标和 reproducibility bundle。
- `manuscript_export`：LaTeX/BibTeX/audit/PDF 一键导出。
- `citation_audit`：LaTeX citation key、正文引用和 claim 支持检查。
- `present_files`：展示 artifacts，并对 `.tex` 尝试 PDF 预览。
- `ask_clarification`：需要用户确认时生成结构化选项。
- `visual_quality_check` / `visual_refinement_check`：视觉产物质量门控。
- sandbox tools：`bash`、`ls`、`read_file`、`write_file`、`str_replace`。

Skills 从 `skills/public` 和 `skills/custom` 发现，并根据 `extensions_config.json` 注入。当前公共 skills 覆盖学术写作、文献整理、实证研究方法、科研图、数据分析、技术图示、PPT、PDF、插件/技能创建等场景。

## 安全与部署

- 生产环境应设置 `MEDRIX_FLOW_ENV=production`。
- 通过 Nginx 暴露 UI/API 时，应设置 `MEDRIX_FLOW_UI_PASSWORD`；否则受保护页面和 API 会 fail closed。
- 脚本化管理可设置 `MEDRIX_GATEWAY_ADMIN_TOKEN`，通过 `x-medrix-admin-token` 请求头访问受保护接口。
- 本地沙箱适合可信开发环境；生产或不可信代码执行应切换到 `AioSandboxProvider` 或 provisioner/Kubernetes 模式。
- Bash 工具调用会经过安全审计和路径隔离；thread 虚拟路径限制在 `/mnt/user-data`。
- 外部代码执行、长实验、自动修改实验代码和最终论文 release 默认应经过 human gate。

## 项目结构

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

## 开发与验证

后端：

```bash
cd backend
make lint
make test
```

前端：

```bash
cd frontend
pnpm lint
pnpm typecheck
pnpm test:unit
BETTER_AUTH_SECRET=local-dev-secret pnpm build
```

全量本地验证：

```bash
make verify
```

## 许可证与致谢

本项目使用 MIT License。Anaxa 的工程基础吸收了 LangGraph、Next.js、FastAPI、开源 agent 工具生态和多个科研自动化项目中的思想，但项目目标始终是“科研副驾驶”：让模型参与研究，而不是替代研究者的判断、证据责任和最终署名责任。
