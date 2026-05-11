"use client";

import {
  CheckCircle2Icon,
  ClipboardListIcon,
  PencilIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Locale, Translations } from "@/core/i18n";
import { useI18n } from "@/core/i18n/hooks";
import {
  approvePendingPlan,
  isPlanPendingApproval,
} from "@/core/threads/plan-approval";
import type { PlanState } from "@/core/threads/types";

type PlanApprovalCopy = Translations["planApproval"];

function planStatusLabel(
  status: string | undefined,
  labels: PlanApprovalCopy["status"],
) {
  switch (status) {
    case "draft":
      return labels.draft;
    case "awaiting_approval":
      return labels.awaiting_approval;
    case "needs_revision":
      return labels.needs_revision;
    case "approved":
      return labels.approved;
    case "executing":
      return labels.executing;
    case "completed":
      return labels.completed;
    case "blocked":
      return labels.blocked;
    default:
      return labels.unknown;
  }
}

function formatDateTime(value?: string | null, locale?: Locale) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(locale);
}

function PlanApprovalList({
  title,
  items,
}: {
  title: string;
  items?: string[];
}) {
  const cleanItems = (items ?? []).filter(Boolean);
  if (cleanItems.length === 0) {
    return null;
  }
  return (
    <section className="space-y-2">
      <div className="text-sm font-medium">{title}</div>
      <ol className="space-y-2">
        {cleanItems.map((item, index) => (
          <li
            key={`${title}-${index}-${item}`}
            className="bg-muted/40 flex min-w-0 gap-2 rounded-lg px-3 py-2 text-sm"
          >
            <span className="text-muted-foreground shrink-0 font-mono text-xs">
              {index + 1}.
            </span>
            <span className="min-w-0 break-words">{item}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function focusMessageInput() {
  requestAnimationFrame(() => {
    document
      .querySelector<HTMLTextAreaElement>("textarea[name='message']")
      ?.focus();
  });
}

export function PlanApprovalCard({
  plan,
  threadId,
  onSubmit,
  isLoading = false,
}: {
  plan?: PlanState | null;
  threadId: string;
  onSubmit?: (text: string) => Promise<void>;
  isLoading?: boolean;
}) {
  const { t, locale } = useI18n();
  const copy = t.planApproval;
  const [approving, setApproving] = useState(false);
  const [optimisticPlan, setOptimisticPlan] = useState<PlanState | null>(null);

  useEffect(() => {
    setOptimisticPlan(null);
  }, [plan?.updated_at, plan?.status]);

  const visiblePlan = optimisticPlan ?? plan;

  if (!visiblePlan) {
    return null;
  }

  const revisions = visiblePlan.revisions ?? [];
  const canApprove = isPlanPendingApproval(visiblePlan);
  const isBusy = approving || isLoading;

  const handleApprove = async () => {
    if (!canApprove || isBusy) return;
    setApproving(true);
    try {
      const nextPlan = await approvePendingPlan(
        threadId,
        visiblePlan,
        copy.approveAndExecute,
      );
      if (nextPlan) {
        setOptimisticPlan(nextPlan);
      }
      await onSubmit?.(copy.executionMessage);
      toast.success(copy.approvedToast);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : copy.approvalFailed);
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="min-w-0 max-w-full overflow-hidden rounded-2xl border bg-background p-4">
      <div className="mb-4 flex min-w-0 items-start justify-between gap-3">
        <div className="flex min-w-0 gap-3">
          <div className="bg-muted flex size-9 shrink-0 items-center justify-center rounded-full">
            <ClipboardListIcon className="size-4" />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold">{copy.title}</div>
            <div className="text-muted-foreground mt-1 min-w-0 break-words text-sm">
              {visiblePlan.summary ?? copy.noItems}
            </div>
          </div>
        </div>
        <Badge variant="outline" className="shrink-0">
          {planStatusLabel(visiblePlan.status, copy.status)}
        </Badge>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg bg-muted/50 p-2">
          <div className="text-muted-foreground">{copy.updated}</div>
          <div className="mt-1 min-w-0 break-words font-mono">
            {formatDateTime(visiblePlan.updated_at, locale)}
          </div>
        </div>
        <div className="rounded-lg bg-muted/50 p-2">
          <div className="text-muted-foreground">{copy.revisions}</div>
          <div className="mt-1 font-mono">
            {String(visiblePlan.revision_count ?? revisions.length ?? 0)}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <PlanApprovalList title={copy.phases} items={visiblePlan.phases} />
        <PlanApprovalList
          title={copy.deliverables}
          items={visiblePlan.deliverables}
        />
        <PlanApprovalList
          title={copy.openQuestions}
          items={visiblePlan.open_questions}
        />
        <PlanApprovalList
          title={copy.acceptanceCriteria}
          items={visiblePlan.acceptance_criteria}
        />
        <PlanApprovalList title={copy.risks} items={visiblePlan.risk_points} />
      </div>

      {canApprove && (
        <>
          <div className="text-muted-foreground mt-4 rounded-lg bg-muted/40 px-3 py-2 text-xs leading-5">
            {copy.approvalHint}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button size="sm" onClick={() => void handleApprove()} disabled={isBusy}>
              <CheckCircle2Icon className="size-4" />
              {copy.approveAndExecute}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={focusMessageInput}
              disabled={isBusy}
            >
              <PencilIcon className="size-4" />
              {copy.revisePlan}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
