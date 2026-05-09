# 全自动科研助手 — 改进实施计划（交付给 GPT 实现）

## 项目背景

MedrixFlow 是基于 LangGraph 的多代理科研系统，已实现 11 阶段研究生命周期（intake → literature → novelty_check → evidence_verified → experiment_planned → experiment_running → results_synthesized → manuscript_draft → review → revision → final_bundle）和配套工具（`academic_research`、`experiment_lab`、`research_assistant`、`manuscript_export`、`citation_audit`）。

**现状问题**：当前系统是**被动编排**——用户必须手动逐步调用工具来推进流程。目标是升级为**全自动科研助手**：用户说"帮我研究 XX 课题"即可自动完成 文献调研 → 假设形成 → 实验设计 → 实验执行 → 结果分析 → 成稿写作 → 引用审计 → PDF 导出 的闭环。

## 核心设计决策

- **执行模式**: 同步阻塞版本优先。`run_pipeline` 在一次 tool call 中推进多个阶段，通过 `max_stages` 参数防止 LangGraph tool call 超时，遇到 gate 或 `max_stages` 到达就返回当前状态，由 lead agent 决定是否续推。
- **LLM 模型选择**: 可配置。在 `config.yaml` 的 `research` 段新增 `manuscript_model` 字段；不配置时继承当前线程模型。通过 `Callable` 注入 service，避免 service 层直接依赖 model factory。
- **向后兼容**: 所有新行为通过可选参数/回调注入；旧调用路径保持不变。

---

## 关键文件位置速查

| 层 | 文件 |
|---|---|
| 编排 | `backend/packages/harness/medrix_flow/research/orchestrator.py` |
| 服务 | `backend/packages/harness/medrix_flow/research/service.py` |
| 类型 | `backend/packages/harness/medrix_flow/research/types.py` |
| 工具 | `backend/packages/harness/medrix_flow/tools/builtins/research_assistant_tool.py` |
| Prompt | `backend/packages/harness/medrix_flow/agents/lead_agent/prompt.py` (L242-271) |
| 路由 | `backend/app/gateway/routers/research.py` |
| 前端 hooks | `frontend/src/core/research/hooks.ts` |
| 前端 API | `frontend/src/core/research/api.ts` |
| 学术适配器 | `backend/packages/harness/medrix_flow/academic/adapters.py` |
| 测试 | `backend/tests/test_research_*.py` |

---

# P0 — 最小可行闭环（1-2 周）

## P0.1 新增 `PipelineRunResult` 类型

**文件**: `backend/packages/harness/medrix_flow/research/types.py`

在 `RESEARCH_STAGES` 定义附近新增：

```python
from typing import Literal
from pydantic import BaseModel

PipelineStatus = Literal["completed", "blocked_on_gate", "stopped_at_max_stages", "error", "cancelled"]

class PipelineStageEvent(BaseModel):
    stage: ResearchStage
    entered_at: str       # ISO timestamp
    completed_at: str | None = None
    outputs: dict[str, Any] = {}
    artifacts: list[str] = []
    error: str | None = None

class PipelineRunResult(BaseModel):
    quest_id: str
    status: PipelineStatus
    stages_executed: list[PipelineStageEvent]
    final_stage: ResearchStage
    blocked_gate: str | None = None      # e.g. "pre_review"
    error: str | None = None
    message: str                          # human-readable summary
```

**验收**: 类型可被 pydantic 序列化；字段名与 Router 响应模型一致。

---

## P0.2 新增 `run_pipeline` 编排方法

**文件**: `backend/packages/harness/medrix_flow/research/orchestrator.py`

在 `ResearchQuestOrchestrator` 中新增：

```python
from collections.abc import Awaitable, Callable
from .types import PipelineRunResult, PipelineStageEvent, ResearchQuestSnapshot

ContentGenerator = Callable[[str, "ResearchQuestSnapshot"], Awaitable[str]]
ReviewerGenerator = Callable[[str, "ResearchQuestSnapshot"], Awaitable[dict]]

async def run_pipeline(
    self,
    quest_id: str,
    *,
    auto_gates: list[str] | None = None,
    max_stages: int = 11,
    content_generator: ContentGenerator | None = None,
    reviewer_generator: ReviewerGenerator | None = None,
) -> PipelineRunResult:
    """循环推进 quest 直到 final_bundle 或遇到阻塞。

    - auto_gates: 允许自动批准的 gate 列表（如 ["experiment_execution"]）
    - max_stages: 本次调用最多推进的阶段数，防止 tool call 超时
    - content_generator: 当 manuscript_draft section content 为空时调用
    - reviewer_generator: 当 review 阶段需要 LLM 评审时调用
    """
```

**实现要点**:
1. 每次循环开始前检查 `quest.status`，若为 `"cancelled"` 立即返回 `PipelineRunResult(status="cancelled", ...)`
2. 调用 `self._service.advance_quest(quest_id)` 推进到下一阶段
3. 若返回的 `ResearchAdvanceResult` 包含 pending gate：
   - 若 gate key 在 `auto_gates` 中，自动调用 `service.record_gate_decision(quest_id, gate_key, "approve")` 继续
   - 否则返回 `status="blocked_on_gate"`, `blocked_gate=<key>`
4. 推进到 `manuscript_draft` 前，若提供了 `content_generator`，透传给 service（见 P0.3）
5. 推进到 `review` 前，若提供了 `reviewer_generator`，透传给 service（见 P1.2）
6. 每个阶段完成后 append 一个 `PipelineStageEvent`
7. 推进次数达到 `max_stages` 或当前 stage == `final_bundle`，返回 `status="completed"` 或 `"stopped_at_max_stages"`

**验收**: 新增 `backend/tests/test_research_pipeline.py`，覆盖：
- 全链路 happy path（mock content_generator 和 reviewer_generator）
- `max_stages=3` 截断
- 遇到非自动 gate 阻塞
- `quest.status="cancelled"` 中途终止

---

## P0.3 `manuscript_draft` 接受可注入的 content_generator

**文件**: `backend/packages/harness/medrix_flow/research/service.py` (L588-621)

修改 `_stage_manuscript_draft` 签名：

```python
async def _stage_manuscript_draft(
    self,
    quest: ResearchQuest,
    inputs: dict[str, Any],
    artifacts: list[str],
    content_generator: ContentGenerator | None = None,  # 新增
) -> dict[str, Any]:
```

**实现要点**:
1. 当 `sections` 为空时仍使用现有默认 5 个章节骨架
2. 对每个 section，若 `payload.get("content")` 为空 **且** `content_generator is not None`：
   - 取 `quest_snapshot = await self.get_snapshot(quest.quest_id)`
   - `content = await content_generator(section_key, quest_snapshot)`
3. 若 generator 抛异常或返回空字符串，fallback 为空内容（不阻塞流程），并在返回值加 `"content_generation_errors": [...]`
4. 将 generator 通过 `advance_quest` 的 `inputs` 或 service 构造参数向下传递（选后者更干净）

**`advance_quest` 的改造**: 增加可选 kwargs `content_generator` 和 `reviewer_generator`，在 `_apply_stage` 中分流到对应 stage handler。

**验收**: 在 `test_research_service.py` 新增：
- `test_manuscript_draft_auto_fills_content` — mock generator 返回固定字符串，验证 section.content 非空
- `test_manuscript_draft_generator_failure_fallback` — generator 抛异常不阻塞

---

## P0.4 `results_synthesized` 增加假设对比与显著性摘要

**文件**: `backend/packages/harness/medrix_flow/research/service.py` (L569-586)

修改 `_stage_results_synthesized`：

```python
async def _stage_results_synthesized(
    self,
    quest: ResearchQuest,
    inputs: dict[str, Any],
    artifacts: list[str],
) -> dict[str, Any]:
    metrics = inputs.get("metrics") if isinstance(inputs.get("metrics"), dict) else {}
    branches = await self._repository.list_experiment_branches(quest.quest_id)
    hypotheses = await self._repository.list_hypotheses(quest.quest_id)  # 从 novelty_check 取

    hypothesis_outcomes = []
    for h in hypotheses:
        outcome = self._evaluate_hypothesis(h, branches, metrics)
        # outcome in {"supported", "refuted", "inconclusive"}
        hypothesis_outcomes.append({
            "hypothesis_id": h.id,
            "statement": h.statement,
            "outcome": outcome,
            "evidence_metric_keys": [...],
        })

    significance_summary = self._summarize_significance(metrics)
    # 纯确定性：检查 metrics 中 *_p_value / *_ci_lower / *_ci_upper 键
    # 返回 {"has_significance_data": bool, "significant_keys": [...], "alpha": 0.05}

    # ... 保留现有 metrics 聚合到 branches 的逻辑 ...

    return {
        "branch_count": len(branches),
        "metric_keys": sorted(metrics),
        "artifact_count": len(artifacts),
        "hypothesis_outcomes": hypothesis_outcomes,
        "significance_summary": significance_summary,
    }
```

**判定规则**（`_evaluate_hypothesis`）:
- 若假设中声明的 `primary_metric` 在 branch.metrics 中 **且** 方向（>= baseline/<= baseline）满足 → `supported`
- 若方向相反 → `refuted`
- 否则 → `inconclusive`

**验收**: `test_research_service.py` 新增 `test_results_synthesized_hypothesis_outcomes`：
- 构造包含 `primary_metric: "accuracy"` 的假设 + branch metrics `{"accuracy": 0.85}` + baseline `{"accuracy": 0.70}`
- 验证 outcome == "supported"
- 无 metrics 时 outcome == "inconclusive"

---

## P0.5 `research_assistant` 工具新增 `action="run_pipeline"`

**文件**: `backend/packages/harness/medrix_flow/tools/builtins/research_assistant_tool.py`

在 tool 定义中新增 action 分支：

```python
# 在 action schema 中加入 "run_pipeline"
# 在 tool docstring 中清晰区分：
#   - action=advance: 手动推进单个阶段（用户掌控节奏）
#   - action=run_pipeline: 一键全流程（用户说"帮我完成整个研究"时）

elif action == "run_pipeline":
    quest_id = params.get("quest_id")
    auto_gates = params.get("auto_gates", [])  # 默认不自动批任何 gate
    max_stages = params.get("max_stages", 5)   # 默认一次推 5 个阶段

    # 构造 content_generator：通过 model factory 创建 manuscript LLM
    content_generator = _build_content_generator(
        model_name=config.research.manuscript_model or config.model_name
    )

    result = await orchestrator.run_pipeline(
        quest_id=quest_id,
        auto_gates=auto_gates,
        max_stages=max_stages,
        content_generator=content_generator,
    )
    return result.model_dump()
```

**`_build_content_generator`** 新增辅助函数（同文件内）:

```python
def _build_content_generator(model_name: str) -> ContentGenerator:
    async def generate(section_key: str, snapshot: ResearchQuestSnapshot) -> str:
        llm = create_chat_model(model_name)
        prompt = _manuscript_prompt_for(section_key, snapshot)
        response = await llm.ainvoke(prompt)
        return response.content
    return generate
```

**Config 扩展**: 在 `backend/packages/harness/medrix_flow/config/app_config.py` (或对应配置模型) 的 `ResearchConfig` 中新增：

```python
class ResearchConfig(BaseModel):
    manuscript_model: str | None = None  # None = 继承线程模型
    default_auto_gates: list[str] = []
    default_max_stages: int = 5
```

**验收**: 
- `test_research_assistant_tool.py` 新增 `test_run_pipeline_action` — mock orchestrator，验证 action 正确分发
- `test_lead_agent_research_routing_prompt.py` 验证 prompt 不会破坏现有路由

---

## P0.6 Lead Agent prompt 增加"一键研究"路由规则

**文件**: `backend/packages/harness/medrix_flow/agents/lead_agent/prompt.py` (L242-271)

在 `<research_routing_system>` block 中，紧接 "Use `research_assistant` only when..." 之后插入：

```text
- When the user explicitly asks for end-to-end autonomous research (e.g. "帮我完成整个研究",
  "全自动研究", "从头到尾研究 XX", "一键科研", "autopilot research"),
  call `research_assistant` with `action="run_pipeline"` after creating the quest.
  The pipeline will advance through literature → hypothesis → experiment → manuscript
  stages. It stops at any human-approval gate (experiment_execution, pre_review,
  final_release) and returns control so you can ask the user to approve.
  Do NOT use `run_pipeline` for background research, single-stage advances, or when
  the user wants to control each step manually — use `action="advance"` instead.
```

**验收**: `test_lead_agent_research_routing_prompt.py` 新增断言：
- prompt 包含 `run_pipeline` 关键词
- 现有 `academic_research`/`experiment_lab`/`research_assistant` 路由规则未被破坏

---

# P1 — 体验与稳定性（2-4 周）

## P1.1 假设 → 实验设计自动推导

**文件**: `backend/packages/harness/medrix_flow/research/service.py` (L493-539，`_stage_experiment_planned`)

当 `branch_payloads` 为空时，从 novelty_check 产生的 hypotheses 派生分支：

```python
if not branch_payloads:
    hypotheses = await self._repository.list_hypotheses(quest.quest_id)
    if hypotheses:
        branch_payloads = [
            {
                "branch_key": f"hyp-{h.id}",
                "title": f"Test: {h.statement[:60]}",
                "hypothesis_id": h.id,
                "primary_metric": h.proposed_metric or "accuracy",
                "baseline_condition": h.baseline_condition or "default",
                "status": "planned",
            }
            for h in hypotheses
        ]
    else:
        # 保留现有通用 baseline 分支逻辑
        branch_payloads = [...]
```

**验收**: `test_experiment_planned_auto_derives_from_hypotheses`

---

## P1.2 LLM 驱动的同行评审（可选）

**文件**: `backend/packages/harness/medrix_flow/research/service.py` (L623-647, `_stage_review`)

增加 `reviewer_generator` 可选回调：

```python
async def _stage_review(
    self,
    quest: ResearchQuest,
    inputs: dict[str, Any],
    reviewer_generator: ReviewerGenerator | None = None,
) -> dict[str, Any]:
    profiles = ["methodology", "domain", "citation-integrity", "devils-advocate"]
    for profile in profiles:
        if reviewer_generator is not None:
            try:
                report = await reviewer_generator(profile, snapshot)
                # report: {"score": float, "verdict": str, "findings": [...], "required_actions": [...]}
            except Exception as e:
                report = self._heuristic_review(profile, ...)  # fallback
        else:
            report = self._heuristic_review(profile, ...)
        # ... 存储 ...
```

**验收**: mock reviewer_generator 返回固定 JSON，验证 report.findings 来自 LLM

---

## P1.3 流式进度 API（SSE）

**文件**: `backend/app/gateway/routers/research.py`

新增端点：

```python
@router.post("/quests/{quest_id}/run")
async def run_pipeline_stream(
    quest_id: str,
    request: RunPipelineRequest,
    service: ResearchQuestService = Depends(get_research_service),
):
    async def event_stream():
        orchestrator = ResearchQuestOrchestrator(service)
        # 将 run_pipeline 改造为 AsyncGenerator[PipelineStageEvent, ...] 版本
        async for event in orchestrator.run_pipeline_stream(quest_id, ...):
            yield f"data: {event.model_dump_json()}\n\n"
        yield "event: done\ndata: {}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

**注意**: 为了保持 P0 同步版本简单，此处**新增** `run_pipeline_stream` 方法（生成器版本），与 P0 的同步 `run_pipeline` 共存。

**验收**: `test_research_router.py` 新增 SSE 测试，使用 httpx AsyncClient 验证事件序列

---

## P1.4 前端 SSE 消费 hook

**文件**: `frontend/src/core/research/hooks.ts`

新增：

```typescript
export function useResearchPipelineStream(questId: string | null) {
  const [events, setEvents] = useState<PipelineStageEvent[]>([]);
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle');

  const start = useCallback((options: RunPipelineOptions) => {
    if (!questId) return;
    const es = new EventSource(`/api/research/quests/${questId}/run`);
    setStatus('running');
    es.onmessage = (e) => setEvents(prev => [...prev, JSON.parse(e.data)]);
    es.addEventListener('done', () => { setStatus('done'); es.close(); });
    es.onerror = () => { setStatus('error'); es.close(); };
    return () => es.close();
  }, [questId]);

  return { events, status, start };
}
```

同时在 `frontend/src/components/workspace/research/research-dashboard.tsx` 中渲染进度时间线。

**验收**: 前端 unit test mock EventSource；手动测试端到端

---

## P1.5 任务取消 API

**文件**: `backend/app/gateway/routers/research.py`

```python
@router.post("/quests/{quest_id}/cancel")
async def cancel_quest(quest_id: str, service: ResearchQuestService = Depends(...)):
    await service.mark_cancelled(quest_id)
    return {"status": "cancelled"}
```

**Service 侧**: 新增 `mark_cancelled(quest_id)` 方法，设置 `quest.status = "cancelled"`。`orchestrator.run_pipeline` 每次循环前检查该状态。

**验收**: `test_research_router.py` 验证 cancel 后 run_pipeline 立即返回 `status="cancelled"`

---

# P2 — 高级能力（一个月+）

## P2.1 bioRxiv/medRxiv 学术适配器

**文件**: `backend/packages/harness/medrix_flow/academic/adapters.py`

参考现有 `PubMedAdapter` 模式，新增 `BioRxivAdapter` 和 `MedRxivAdapter`：
- API: `https://api.biorxiv.org/details/biorxiv/{doi}` 和 `https://api.biorxiv.org/covid19/` (已被替换为通用 search)
- 返回结构统一为 `AcademicPaper` 数据类
- 在 `AcademicSearchService` 的源列表中注册

**验收**: `test_academic_adapters.py` 新增 mock HTTP 测试

---

## P2.2 学术 PDF 解析工具

**文件**: 新增 `backend/packages/harness/medrix_flow/tools/builtins/academic_pdf_parser_tool.py`

基于 GROBID（Docker）或 `science-parse` 提取：
- 标题、作者、摘要
- 引用列表（结构化）
- 图表 caption
- Section 结构与层级
- 公式（LaTeX）

输出 JSON 写入 sandbox `/mnt/user-data/outputs/`。

**验收**: 用 fixture PDF 测试解析结果字段完整性

---

## P2.3 端到端集成测试

**文件**: 新增 `backend/tests/test_research_e2e_pipeline.py`

场景：
1. in-memory SQLite repository
2. mock academic adapter 返回 3 篇假论文
3. mock LLM content_generator 返回固定章节
4. mock experiment_lab 返回固定 metrics
5. 调用 `run_pipeline(auto_gates=["experiment_execution","pre_review","final_release"])`
6. 断言：final_stage == "final_bundle"，manuscript 有 5 个 section，每个 section.content 非空，review 报告数 == 4

**验收**: CI 中运行，时长 < 30s

---

## P2.4 Autoresearch 服务端状态机

**文件**: 新增 `backend/packages/harness/medrix_flow/research/autoresearch.py`

```python
class AutoresearchLoop:
    def __init__(
        self,
        experiment_service: ExperimentService,
        *,
        max_iterations: int = 10,
        improvement_threshold: float = 0.01,
        primary_metric: str = "accuracy",
    ): ...

    async def run(
        self,
        baseline_config: ExperimentConfig,
        idea_generator: Callable[[IterationHistory], Awaitable[ExperimentConfig]],
    ) -> AutoresearchResult:
        """baseline → iter1 → compare → keep/discard → iter2 → ..."""
```

**停止条件**:
- 达到 `max_iterations`
- 连续 3 次无改进 (improvement < threshold)
- 显式 cancel

**验收**: 单元测试验证 keep/discard 决策逻辑、停止条件触发

---

# 新增/修改文件一览表

| 文件 | 操作 | 优先级 | 预计工作量 |
|------|------|--------|-----------|
| `research/types.py` | 修改（加 PipelineRunResult） | P0 | 0.5d |
| `research/orchestrator.py` | 修改（加 run_pipeline） | P0 | 1d |
| `research/service.py` | 修改（manuscript_draft+results_synthesized 注入 generator） | P0 | 2d |
| `tools/builtins/research_assistant_tool.py` | 修改（加 run_pipeline action + content_generator 工厂） | P0 | 1d |
| `config/app_config.py` | 修改（加 ResearchConfig.manuscript_model） | P0 | 0.5d |
| `agents/lead_agent/prompt.py` | 修改（路由规则） | P0 | 0.25d |
| `tests/test_research_pipeline.py` | 新增 | P0 | 1d |
| `tests/test_research_service.py` | 修改（加 manuscript/results 测试） | P0 | 0.5d |
| `tests/test_research_assistant_tool.py` | 修改（加 run_pipeline 测试） | P0 | 0.25d |
| `research/service.py` (P1) | 修改（experiment_planned 推导 + LLM review） | P1 | 2d |
| `app/gateway/routers/research.py` | 修改（加 /run SSE + /cancel） | P1 | 1.5d |
| `frontend/src/core/research/hooks.ts` | 修改（加 SSE hook） | P1 | 1d |
| `frontend/src/components/workspace/research/research-dashboard.tsx` | 修改（渲染进度） | P1 | 1d |
| `academic/adapters.py` | 修改（加 bioRxiv/medRxiv） | P2 | 1d |
| `tools/builtins/academic_pdf_parser_tool.py` | 新增 | P2 | 2d |
| `research/autoresearch.py` | 新增 | P2 | 2d |
| `tests/test_research_e2e_pipeline.py` | 新增 | P2 | 1d |

---

# P0 风险与备选方案

| 项目 | 风险 | 备选 |
|------|------|------|
| run_pipeline 同步阻塞 | 单次 tool call 超时（LangGraph 默认 ~60s） | `max_stages` 默认 5；lead agent prompt 中说明需要多次调用续推；P1 改为 SSE 异步版本 |
| manuscript_draft LLM 注入 | service 层耦合 LLM | 通过 `Callable` 注入，service 不 import model factory；tool 层组装 generator |
| content_generator 失败 | 生成异常导致流程中断 | try/except + fallback 为空内容，在返回值记录错误，不阻塞 |
| results_synthesized 假设对比 | metrics 可能不含 p_value/CI 键 | 缺键时标记 `inconclusive` + `has_significance_data=false`，不阻塞 |
| research_assistant 新 action | 模型混淆 run_pipeline vs advance | tool docstring 明确区分使用场景；prompt 加反例 |
| prompt 修改 | 影响非科研路由 | 回归测试 `test_lead_agent_research_routing_prompt.py` 保证其他规则不变 |

---

# 验证与验收（端到端手工测试脚本）

**P0 完成后手工验证**:

```bash
cd backend && make test  # 全部通过

# 启动完整服务
cd .. && make dev

# 用户视角测试：在 /workspace/research 或主聊天中输入
"帮我完成一个关于 XX 的自动化研究，auto approve 所有 gate 除了 final_release"
```

**期望**:
1. Lead agent 自动调用 `research_assistant(action="start", topic="XX")` 创建 quest
2. 接着调用 `research_assistant(action="run_pipeline", quest_id=..., auto_gates=["experiment_execution","pre_review"])`
3. 返回阶段摘要，manuscript 章节有 LLM 生成的初稿内容
4. 在 `final_release` gate 前停下，等待用户确认
5. 用户确认后 → PDF 导出

**P1 完成后**:
- 前端 `ResearchDashboard` 显示阶段时间线进度
- 支持中途取消
- SSE 事件流实时推送到前端

**P2 完成后**:
- 支持从 bioRxiv/medRxiv 拉论文
- 支持上传学术 PDF 自动解析
- 支持 autoresearch loop 迭代实验

---

# 实现建议（交付 GPT 的顺序）

**推荐顺序**（GPT 每次实现一项，跑通测试再下一项）：

1. P0.1（类型） → P0.2（orchestrator） → P0.3（manuscript_draft） → P0.4（results_synthesized）
2. P0.5（工具 action） → P0.6（prompt）
3. 端到端手工测试一次
4. P1.1 → P1.2（service 增强）
5. P1.3 → P1.4 → P1.5（前端+流式）
6. P2 视需要排期

**关键注意事项给 GPT**:
- 严格遵循 `backend/CLAUDE.md` 中的 TDD 规定：**每个新功能必须配单测**
- 遵循 harness/app 边界：`medrix_flow/*` 不能 import `app.*`
- 运行 `cd backend && make lint && make test` 作为 PR gate
- 所有新方法/回调使用 `Callable` + `Awaitable` 而非直接 import LLM
- 时间戳统一用 `now_iso()` helper（已存在于 service.py）
- ID 统一用 `uuid.uuid4().hex[:12]` 模式（已存在）
