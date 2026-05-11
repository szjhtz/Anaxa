import { getAPIClient } from "@/core/api";

import type { PlanState } from "./types";

const PENDING_PLAN_STATUSES = new Set([
  "draft",
  "awaiting_approval",
  "needs_revision",
]);

const CHINESE_NEGATIVE_APPROVAL_PHRASES = [
  "不批准",
  "不要批准",
  "别批准",
  "暂不批准",
  "先不批准",
  "不确认",
  "不要确认",
  "别确认",
  "不要执行",
  "别执行",
  "先别执行",
  "不要继续",
  "别继续",
  "不是批准",
  "没有批准",
];

const CHINESE_APPROVAL_PHRASES = [
  "我批准当前计划",
  "批准当前计划",
  "批准这个计划",
  "批准并执行",
  "确认并执行",
  "同意当前计划",
  "按计划执行",
  "继续执行",
  "继续导出",
  "继续生成",
  "可以执行",
  "开始执行",
];

const ENGLISH_NEGATIVE_APPROVAL_PATTERN =
  /\b(do not|don't|dont|not|no|never)\s+(approve|proceed|execute|continue)\b|\bnot\s+approved\b/i;

const ENGLISH_APPROVAL_PATTERNS = [
  /\bi approve (the )?(current )?plan\b/i,
  /\bapprove and execute\b/i,
  /\bapproved[,.\s]+(continue|proceed|execute)\b/i,
  /\bproceed with (the )?(current )?plan\b/i,
  /\bexecute according to (it|the plan)\b/i,
  /\bcontinue (with )?(the )?(current |approved )?plan\b/i,
  /\bcontinue (the )?(export|generation|execution)\b/i,
  /\bcontinue to (export|generate|execute)\b/i,
];

export function isPlanPendingApproval(plan?: PlanState | null) {
  return Boolean(plan?.status && PENDING_PLAN_STATUSES.has(plan.status));
}

export function isExplicitPlanApprovalMessage(text: string) {
  const trimmed = text.trim();
  if (!trimmed) return false;

  const compact = trimmed.toLowerCase().replace(/\s+/g, "");
  if (CHINESE_NEGATIVE_APPROVAL_PHRASES.some((phrase) => compact.includes(phrase))) {
    return false;
  }
  if (ENGLISH_NEGATIVE_APPROVAL_PATTERN.test(trimmed)) {
    return false;
  }

  return (
    CHINESE_APPROVAL_PHRASES.some((phrase) => compact.includes(phrase)) ||
    ENGLISH_APPROVAL_PATTERNS.some((pattern) => pattern.test(trimmed))
  );
}

export function buildApprovedPlan(
  plan: PlanState,
  note: string,
  approvedAt = new Date().toISOString(),
): PlanState {
  const revisions = plan.revisions ?? [];
  const nextPlan: PlanState = {
    ...plan,
    status: "approved",
    updated_at: approvedAt,
    revisions: [
      ...revisions,
      {
        revision_number: (plan.revision_count ?? revisions.length ?? 0) + 1,
        source: "user",
        note,
        status: "approved",
        updated_at: approvedAt,
      },
    ],
  };
  nextPlan.revision_count = nextPlan.revisions?.length ?? plan.revision_count ?? 0;
  return nextPlan;
}

export async function approvePendingPlan(
  threadId: string,
  plan: PlanState | null | undefined,
  note: string,
): Promise<PlanState | null> {
  if (!plan || !isPlanPendingApproval(plan)) {
    return null;
  }
  const nextPlan = buildApprovedPlan(plan, note);
  await getAPIClient().threads.updateState(threadId, {
    values: {
      plan: nextPlan,
    },
  });
  return nextPlan;
}
