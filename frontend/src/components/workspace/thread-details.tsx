"use client";

import {
  ActivityIcon,
  AlertTriangleIcon,
  BoxIcon,
  BotIcon,
  ChevronDownIcon,
  ClockIcon,
  CodeIcon,
  DownloadIcon,
  FileJsonIcon,
  FileTextIcon,
  FilesIcon,
  GitBranchIcon,
  ListTreeIcon,
  RefreshCwIcon,
  SquareIcon,
  SquareXIcon,
  UserIcon,
  WrenchIcon,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArtifactFileList } from "@/components/workspace/artifacts/artifact-file-list";
import { useArtifacts } from "@/components/workspace/artifacts/context";
import { Tooltip } from "@/components/workspace/tooltip";
import {
  cancelThreadRun,
  type WorkflowNode,
  type WorkflowSnapshot,
} from "@/core/api/runs";
import { useI18n } from "@/core/i18n/hooks";
import { accumulateUsage, formatTokenCount } from "@/core/messages/usage";
import {
  downloadAsFile,
  exportThreadAsJSON,
  exportThreadAsMarkdown,
} from "@/core/threads/export";
import type { AgentThread } from "@/core/threads/types";
import { useThreadWorkflow } from "@/core/workflow";
import { cn } from "@/lib/utils";

import { useThread } from "./messages/context";
import { StreamingIndicator } from "./streaming-indicator";

type ThreadDetailsTriggerProps = {
  threadId: string;
  currentRunId?: string | null;
  streaming: boolean;
};

function formatTime(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDuration(start?: string | null, end?: string | null) {
  if (!start || !end) return "—";
  const startTime = Date.parse(start);
  const endTime = Date.parse(end);
  if (Number.isNaN(startTime) || Number.isNaN(endTime)) return "—";
  const seconds = Math.max(0, Math.round((endTime - startTime) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${seconds % 60}s`;
}

function formatDateTime(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatMaybeTokens(value?: number | null) {
  if (!value || value <= 0) return "未记录";
  return formatTokenCount(value);
}

function getNodeIcon(kind: WorkflowNode["kind"]) {
  switch (kind) {
    case "user":
      return UserIcon;
    case "tool":
      return WrenchIcon;
    case "subagent":
      return GitBranchIcon;
    case "artifact":
      return FilesIcon;
    case "checkpoint":
      return BoxIcon;
    case "error":
      return AlertTriangleIcon;
    case "final":
      return SquareIcon;
    case "agent":
      return BotIcon;
    default:
      return ActivityIcon;
  }
}

function statusLabel(status?: string) {
  switch (status) {
    case "pending":
      return "Pending";
    case "running":
      return "Running";
    case "success":
      return "Complete";
    case "error":
      return "Error";
    case "interrupted":
      return "Interrupted";
    default:
      return status ?? "Unknown";
  }
}

type TreeNode = WorkflowNode & { children: TreeNode[] };

function buildWorkflowTree(workflow: WorkflowSnapshot): TreeNode[] {
  if (workflow.nodes.length > 0 && workflow.edges.length === 0) {
    const chain: TreeNode[] = workflow.nodes.map((node) => ({
      ...node,
      children: [],
    }));
    for (let index = 0; index < chain.length - 1; index += 1) {
      chain[index]?.children.push(chain[index + 1]!);
    }
    return chain[0] ? [chain[0]] : [];
  }

  const nodesById = new Map<string, TreeNode>(
    workflow.nodes.map((node) => [node.id, { ...node, children: [] as TreeNode[] }]),
  );
  const childIds = new Set<string>();

  for (const edge of workflow.edges) {
    const source = nodesById.get(edge.source);
    const target = nodesById.get(edge.target);
    if (!source || !target) continue;
    source.children.push(target);
    childIds.add(target.id);
  }

  const roots = [...nodesById.values()].filter((node) => !childIds.has(node.id));
  if (roots.length > 0) {
    return roots;
  }

  const chain: TreeNode[] = workflow.nodes.map((node) => ({ ...node, children: [] }));
  for (let index = 0; index < chain.length - 1; index += 1) {
    chain[index]?.children.push(chain[index + 1]!);
  }
  return chain[0] ? [chain[0]] : [];
}

function WorkflowTreeNode({
  node,
  depth,
  onOpenArtifact,
}: {
  node: TreeNode;
  depth: number;
  onOpenArtifact: (filepath: string) => void;
}) {
  const Icon = getNodeIcon(node.kind);
  return (
    <div className={cn(depth > 0 && "border-l pl-4")}>
      <div className="relative flex min-w-0 gap-3">
        <div
          className={cn(
            "bg-background z-1 flex size-8 shrink-0 items-center justify-center rounded-full border",
            node.status === "error" && "border-destructive/50 text-destructive",
            node.status === "running" && "border-primary/50 text-primary",
          )}
        >
          <Icon className="size-4" />
        </div>
        <Collapsible className="min-w-0 flex-1 rounded-md border p-3">
          <CollapsibleTrigger className="group flex w-full min-w-0 cursor-pointer items-start justify-between gap-3 text-left">
            <div className="min-w-0 flex-1 overflow-hidden">
              <div className="flex min-w-0 items-center gap-2 overflow-hidden">
                <span className="min-w-0 truncate text-sm font-medium">{node.label}</span>
                <Badge variant="outline" className="shrink-0 text-[10px]">
                  {node.kind}
                </Badge>
              </div>
              <div className="text-muted-foreground mt-1 line-clamp-2 min-w-0 break-words text-xs">
                {node.summary || "No summary available."}
              </div>
            </div>
            <div className="text-muted-foreground flex shrink-0 items-center gap-2 text-xs">
              <span>{formatTime(node.created_at)}</span>
              <ChevronDownIcon className="size-3 transition-transform group-data-[state=open]:rotate-180" />
            </div>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-3 space-y-2 border-t pt-3 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <DetailKV label="Status" value={statusLabel(node.status)} />
              <DetailKV label="Caller" value={node.caller ?? "—"} />
              <DetailKV label="Seq" value={node.seq?.toString() ?? "—"} />
              <DetailKV
                label="Event"
                value={
                  typeof node.metadata?.event_type === "string"
                    ? node.metadata.event_type
                    : "—"
                }
              />
            </div>
            {node.artifact_path && (
              <button
                type="button"
                className="hover:bg-muted flex w-full min-w-0 items-start gap-2 rounded-md border p-2 text-left"
                onClick={() => onOpenArtifact(node.artifact_path!)}
              >
                <FilesIcon className="mt-0.5 size-4 shrink-0" />
                <span
                  className="min-w-0 break-all font-mono text-xs"
                  data-testid="workflow-artifact-path"
                >
                  {node.artifact_path}
                </span>
              </button>
            )}
          </CollapsibleContent>
        </Collapsible>
      </div>
      {node.children.length > 0 && (
        <div className="mt-3 space-y-3 pl-4">
          {node.children.map((child) => (
            <WorkflowTreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              onOpenArtifact={onOpenArtifact}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function WorkflowTree({
  workflow,
  onOpenArtifact,
}: {
  workflow?: WorkflowSnapshot;
  onOpenArtifact: (filepath: string) => void;
}) {
  if (!workflow) {
    return (
      <EmptyDetailsState
        icon={<ListTreeIcon />}
        title="No workflow events yet"
        description="The run is registered, but no visible agent event has been recorded yet."
      />
    );
  }

  const tree = buildWorkflowTree(workflow);

  return (
    <div className="space-y-3">
      <div className="rounded-md border bg-muted/20 p-3">
        <div className="flex min-w-0 items-start gap-3">
          <div className="bg-background flex size-8 shrink-0 items-center justify-center rounded-full border">
            <BotIcon className="size-4" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium">任务 / Run</div>
            <div className="text-muted-foreground mt-1 break-all font-mono text-xs">
              {workflow.run.run_id}
            </div>
          </div>
          <Badge variant="outline" className="shrink-0 text-[10px]">
            {statusLabel(workflow.run.status)}
          </Badge>
        </div>
      </div>
      {tree.map((node) => (
        <WorkflowTreeNode
          key={node.id}
          node={node}
          depth={0}
          onOpenArtifact={onOpenArtifact}
        />
      ))}
      {tree.length === 0 && (
        <EmptyDetailsState
          icon={<ListTreeIcon />}
          title="暂无可视化决策流程"
          description="当前运行还没有记录到可还原的 agent 规划、决策或工具步骤；产出文件请在“产出”页查看。"
        />
      )}
    </div>
  );
}

function DetailKV({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-muted/50 p-2">
      <div className="text-muted-foreground text-[10px] uppercase">{label}</div>
      <div className="min-w-0 break-words font-mono text-xs">{value}</div>
    </div>
  );
}

function EmptyDetailsState({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="text-muted-foreground flex h-56 flex-col items-center justify-center rounded-lg border border-dashed p-6 text-center">
      <div className="mb-3 [&_svg]:size-8">{icon}</div>
      <div className="text-foreground text-sm font-medium">{title}</div>
      <div className="mt-1 max-w-xs text-xs leading-5">{description}</div>
    </div>
  );
}

function StatsSection({
  workflow,
  active,
  streaming,
  threadUsage,
  threadDuration,
  artifactCount,
  eventCount,
  onCancelRun,
}: {
  workflow?: WorkflowSnapshot;
  active: boolean;
  streaming: boolean;
  threadUsage: ReturnType<typeof accumulateUsage>;
  threadDuration: string;
  artifactCount: number;
  eventCount: number;
  onCancelRun: () => void;
}) {
  const { t } = useI18n();
  const run = workflow?.run;
  const lastEventAt = run?.last_event_at ?? run?.updated_at;
  const usage = workflow?.usage;
  return (
    <div className="space-y-4">
      <section className="space-y-2">
        <div className="text-sm font-medium">当前 Run</div>
        <div className="grid grid-cols-2 gap-2">
          <DetailKV label="Status" value={streaming ? "Streaming" : statusLabel(run?.status)} />
          <DetailKV label="Run" value={run?.run_id ?? "—"} />
          <DetailKV label="Started" value={formatDateTime(run?.created_at)} />
          <DetailKV label="Last Event" value={formatDateTime(lastEventAt)} />
          <DetailKV label="Duration" value={formatDuration(run?.created_at, lastEventAt)} />
          <DetailKV label="Events" value={String(eventCount)} />
          <DetailKV label="Artifacts" value={String(artifactCount)} />
          <DetailKV label={t.tokenUsage.total} value={formatMaybeTokens(usage?.total_tokens)} />
          <DetailKV label={t.tokenUsage.input} value={formatMaybeTokens(usage?.input_tokens)} />
          <DetailKV label={t.tokenUsage.output} value={formatMaybeTokens(usage?.output_tokens)} />
        </div>
        {(active || streaming) && (
          <Button
            className="w-full justify-start"
            variant="outline"
            onClick={onCancelRun}
          >
            <SquareXIcon className="size-4" />
            停止当前任务
          </Button>
        )}
      </section>
      <section className="space-y-2">
        <div className="text-sm font-medium">整个对话</div>
        <div className="grid grid-cols-2 gap-2">
          <DetailKV label={t.tokenUsage.total} value={formatMaybeTokens(threadUsage?.totalTokens)} />
          <DetailKV label={t.tokenUsage.input} value={formatMaybeTokens(threadUsage?.inputTokens)} />
          <DetailKV label={t.tokenUsage.output} value={formatMaybeTokens(threadUsage?.outputTokens)} />
          <DetailKV label="Total Duration" value={threadDuration} />
        </div>
      </section>
    </div>
  );
}

function ExportMenu({
  workflow,
  onExportThread,
}: {
  workflow?: WorkflowSnapshot;
  onExportThread: (format: "markdown" | "json") => void;
}) {
  const { t } = useI18n();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" aria-label="导出">
          <DownloadIcon className="size-4" />
          导出
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={() => onExportThread("markdown")}>
          <FileTextIcon className="size-4" />
          {t.common.exportAsMarkdown}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => onExportThread("json")}>
          <FileJsonIcon className="size-4" />
          {t.common.exportAsJSON}
        </DropdownMenuItem>
        <DropdownMenuItem
          disabled={!workflow}
          onSelect={() => exportWorkflow(workflow)}
        >
          <DownloadIcon className="size-4" />
          导出运行轨迹 JSON
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function RunSummary({
  workflow,
  active,
  streaming,
}: {
  workflow?: WorkflowSnapshot;
  active: boolean;
  streaming: boolean;
}) {
  const run = workflow?.run;
  const lastEventAt = run?.last_event_at ?? run?.updated_at;
  return (
    <div className="grid grid-cols-2 gap-2">
      <DetailKV label="Status" value={streaming ? "Streaming" : statusLabel(run?.status)} />
      <DetailKV label="Run" value={run?.run_id ?? "—"} />
      <DetailKV label="Last Event" value={formatTime(lastEventAt)} />
      <DetailKV label="Duration" value={formatDuration(run?.created_at, lastEventAt)} />
      {active && !streaming && (
        <div className="bg-primary/5 text-primary col-span-2 flex items-center gap-2 rounded-md border border-primary/20 p-2 text-xs">
          <StreamingIndicator size="sm" />
          Backend run is still active. The details panel is polling for new events.
        </div>
      )}
      {run?.error && (
        <div className="border-destructive/30 bg-destructive/5 text-destructive col-span-2 rounded-md border p-2 text-xs">
          {run.error}
        </div>
      )}
    </div>
  );
}

function exportWorkflow(workflow?: WorkflowSnapshot) {
  if (!workflow) return;
  downloadAsFile(
    JSON.stringify(workflow, null, 2),
    `workflow-${workflow.run.run_id}.json`,
    "application/json;charset=utf-8",
  );
}

export function ThreadDetailsTrigger({
  threadId,
  currentRunId,
  streaming,
}: ThreadDetailsTriggerProps) {
  const { t } = useI18n();
  const { thread } = useThread();
  const { artifacts, latestArtifact, setOpen: setArtifactsOpen, select } = useArtifacts();
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState("flow");
  const { workflow, run, runs, active, isFetching, refetch } = useThreadWorkflow({
    threadId,
    currentRunId,
    enabled: open || streaming,
  });

  const messages = thread.messages;
  const artifactCount =
    workflow?.artifacts.length !== undefined && workflow.artifacts.length > 0
      ? workflow.artifacts.length
      : artifacts.length;
  const threadUsage = useMemo(() => accumulateUsage(messages), [messages]);
  const threadDuration = useMemo(() => {
    if (runs.length === 0) return "—";
    const timestamps = runs
      .flatMap((item) => [Date.parse(item.created_at), Date.parse(item.updated_at)])
      .filter((value) => !Number.isNaN(value));
    if (timestamps.length === 0) return "—";
    return formatDuration(
      new Date(Math.min(...timestamps)).toISOString(),
      new Date(Math.max(...timestamps)).toISOString(),
    );
  }, [runs]);
  const eventCount = workflow?.events.length ?? 0;

  const agentThread = useMemo(
    () =>
      ({
        thread_id: threadId,
        updated_at: new Date().toISOString(),
        values: thread.values,
      }) as AgentThread,
    [thread.values, threadId],
  );

  const openArtifact = useCallback(
    (filepath: string) => {
      select(filepath);
      setArtifactsOpen(true);
    },
    [select, setArtifactsOpen],
  );

  const handleExportThread = useCallback(
    (format: "markdown" | "json") => {
      if (messages.length === 0) {
        toast.error(t.conversation.noMessages);
        return;
      }
      if (format === "markdown") {
        exportThreadAsMarkdown(agentThread, messages);
      } else {
        exportThreadAsJSON(agentThread, messages);
      }
      toast.success(t.common.exportSuccess);
    },
    [agentThread, messages, t],
  );

  const handleCancelRun = useCallback(async () => {
    const runId = run?.run_id ?? currentRunId;
    if (!runId) return;
    try {
      await cancelThreadRun(threadId, runId);
      await refetch();
      toast.success("已请求停止当前任务");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "停止任务失败");
    }
  }, [currentRunId, refetch, run?.run_id, threadId]);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <Tooltip content="查看工作流、产出文件、统计和运行日志">
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            className="text-muted-foreground hover:text-foreground relative"
            data-testid="thread-details-trigger"
          >
            {(streaming || active) && (
              <span className="bg-primary absolute top-1.5 left-1.5 size-2 rounded-full">
                <span className="bg-primary absolute inset-0 animate-ping rounded-full opacity-50" />
              </span>
            )}
            <ActivityIcon />
            详情
            {artifactCount > 0 && (
              <Badge variant="secondary" className="h-5 min-w-5 px-1.5 text-[10px]">
                {artifactCount}
              </Badge>
            )}
          </Button>
        </SheetTrigger>
      </Tooltip>
      <SheetContent className="w-[92vw] gap-0 p-0 sm:max-w-xl">
        <SheetHeader className="border-b pr-12">
          <div className="flex items-center justify-between gap-3">
            <div>
              <SheetTitle>详情</SheetTitle>
              <SheetDescription>
                Agent 工作流、工具调用、产出文件与运行日志
              </SheetDescription>
            </div>
            <Button size="icon-sm" variant="ghost" onClick={() => void refetch()}>
              <RefreshCwIcon className={cn("size-4", isFetching && "animate-spin")} />
            </Button>
          </div>
        </SheetHeader>
        <Tabs value={tab} onValueChange={setTab} className="min-h-0 flex-1 gap-0">
          <div className="border-b px-4 py-2">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="flow" onClick={() => setTab("flow")}>
                流程
              </TabsTrigger>
              <TabsTrigger value="files" onClick={() => setTab("files")}>
                产出
              </TabsTrigger>
              <TabsTrigger value="stats" onClick={() => setTab("stats")}>
                统计
              </TabsTrigger>
              <TabsTrigger value="logs" onClick={() => setTab("logs")}>
                日志
              </TabsTrigger>
            </TabsList>
          </div>

          <ScrollArea className="min-h-0 flex-1">
            <div className="p-4">
              <TabsContent value="flow" className="mt-0 space-y-4">
                <RunSummary workflow={workflow} active={active} streaming={streaming} />
                <WorkflowTree workflow={workflow} onOpenArtifact={openArtifact} />
              </TabsContent>

              <TabsContent value="files" className="mt-0">
                {artifactCount > 0 ? (
                  <ArtifactFileList
                    files={artifacts.length > 0 ? artifacts : workflow?.artifacts.map((item) => item.filepath) ?? []}
                    threadId={threadId}
                    latestFilepath={latestArtifact ?? workflow?.artifacts[0]?.filepath}
                    onRefresh={() => void refetch()}
                  />
                ) : (
                  <EmptyDetailsState
                    icon={<FilesIcon />}
                    title="暂无产出文件"
                    description="当 agent 生成 PDF、表格、图片或代码文件后，会显示在这里。"
                  />
                )}
              </TabsContent>

              <TabsContent value="stats" className="mt-0">
                <StatsSection
                  workflow={workflow}
                  active={active}
                  streaming={streaming}
                  threadUsage={threadUsage}
                  threadDuration={threadDuration}
                  artifactCount={artifactCount}
                  eventCount={eventCount}
                  onCancelRun={() => void handleCancelRun()}
                />
              </TabsContent>

              <TabsContent value="logs" className="mt-0 space-y-3">
                <div className="flex justify-end">
                  <ExportMenu
                    workflow={workflow}
                    onExportThread={handleExportThread}
                  />
                </div>
                {workflow?.events.length ? (
                  <div className="space-y-2">
                    {workflow.events.map((event) => (
                      <Collapsible key={event.seq} className="min-w-0 rounded-md border p-3">
                        <CollapsibleTrigger className="group flex w-full cursor-pointer items-start justify-between gap-3 text-left">
                          <div className="min-w-0 flex-1 overflow-hidden">
                            <div className="flex min-w-0 items-center gap-2 overflow-hidden text-sm font-medium">
                              <CodeIcon className="size-4" />
                              <span>#{event.seq}</span>
                              <span className="min-w-0 truncate">{event.event_type}</span>
                            </div>
                            <div className="text-muted-foreground mt-1 line-clamp-2 break-words text-xs">{event.summary}</div>
                          </div>
                          <div className="text-muted-foreground flex shrink-0 items-center gap-2 text-xs">
                            <ClockIcon className="size-3" />
                            {formatTime(event.created_at)}
                          </div>
                        </CollapsibleTrigger>
                        <CollapsibleContent className="mt-3 overflow-hidden rounded-md bg-muted/50 p-2">
                          <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-all text-xs">
                            {JSON.stringify(event.content, null, 2)}
                          </pre>
                        </CollapsibleContent>
                      </Collapsible>
                    ))}
                  </div>
                ) : (
                  <EmptyDetailsState
                    icon={<CodeIcon />}
                    title="暂无运行日志"
                    description="运行开始后，工具调用、子任务、文件产出和状态事件会逐步记录。"
                  />
                )}
              </TabsContent>
            </div>
          </ScrollArea>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
}
