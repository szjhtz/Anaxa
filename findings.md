# 发现与决策

## 需求
- 实现完整 catch-up plan，保持现有聊天主链路不动，同时把 runtime、feedback、skills 生命周期、setup/doctor、测试与 CI 补齐。

## 已实现结果
- `P0`：
  - 新增 `medrix_flow.runtime` 运行时层，包含 `RunManager`、SQLite `RunStore` / `RunEventStore` / `FeedbackRepo`、stream bridge。
  - gateway 增加 lifespan bootstrap、service 层和 `/api/threads/{thread_id}/runs*` / feedback 端点。
  - 按 checkpoint message count 做 pre/post diff，只持久化 run 期间新增消息。
  - persistence 失败维持 best-effort，不打断 streaming。
- `P1`：
  - 前端 `useThreadStream` 捕获 `run_id`，并做 run register / complete sideband 调用。
  - 当前会话最后一条 assistant 消息显示 thumbs up/down，历史消息不回填。
  - 前端单测已切到 Vitest，并补 run/feedback 相关测试。
  - 新增 Playwright smoke，覆盖聊天流、feedback toggle、sidebar 非回归。
  - `make setup` / `make doctor` 已落地并复用共享 setup service。
- `P2`：
  - skills 现已拆成 `storage` + `service` + `security_scanner` + `installer`。
  - custom skills 支持 install / read / update / delete / history / rollback。
  - 成功变更后刷新 skills cache 和 prompt cache。
  - 新增非破坏性 upstream drift workflow，只输出 ahead/behind 和 touched modules 报告。

## 技术决策
| 决策 | 理由 |
|------|------|
| 用 gateway sideband 注册现有 LangGraph run | 不改写主聊天流，且能先把 run/feedback 能力补齐 |
| 在 run 完成/中断时按 checkpoint message count diff 持久化 | 满足“只落新增消息”的要求，且顺应现有 thread state |
| skills 扫描使用规则引擎 | 测试稳定、部署简单，不引入额外模型依赖 |
| Playwright 直接跑真实页面，浏览器侧 mock LangGraph/gateway 请求 | 覆盖现有 `useStream` 路径，同时避免搭整套后端模型环境 |

## 仍然有意延期的项
- Stateless `/api/runs/*`
- 基于 runs 的 thread history UI 重写
- 完整 auth/authz
- SQLAlchemy/Alembic/Postgres
- docs/blog/Nextra parity
- 额外 IM channel / search provider parity

## 验证结果
- backend:
  - `uv run ruff check app/gateway packages/harness/medrix_flow/skills packages/harness/medrix_flow/agents/lead_agent/prompt.py tests/test_skills_lifecycle.py tests/test_runtime_runs.py`
  - `uv run pytest tests/test_runtime_runs.py tests/test_skills_archive_root.py tests/test_skills_lifecycle.py tests/test_skills_loader.py tests/test_skills_router.py -q`
  - `uv run python -m compileall app packages/harness/medrix_flow/skills packages/harness/medrix_flow/setup`
- frontend:
  - `pnpm lint`
  - `pnpm typecheck`
  - `pnpm test:unit`
  - `pnpm test:e2e`

## 风险
- 当前 skill scanner 是规则型实现，能挡掉明显的 prompt injection / exfiltration / destructive script，但还不是语义级审查。
- `completeThreadRun(..., "error")` 仍沿用前一轮 sideband 设计；如果将来前端 stop/cancel 在 LangGraph SDK 层统一映射成 error，可能需要再细分 interrupted 状态。
