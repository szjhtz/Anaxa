import type { Message, Thread } from "@langchain/langgraph-sdk";

import type { Todo } from "../todos";

export type PlanStatus =
  | "draft"
  | "awaiting_approval"
  | "needs_revision"
  | "approved"
  | "executing"
  | "completed"
  | "blocked";

export interface PlanRevision extends Record<string, unknown> {
  revision_number?: number;
  source?: string;
  note?: string;
  status?: PlanStatus;
  updated_at?: string;
}

export interface PlanState extends Record<string, unknown> {
  summary?: string;
  phases?: string[];
  deliverables?: string[];
  open_questions?: string[];
  acceptance_criteria?: string[];
  risk_points?: string[];
  revision_count?: number;
  status?: PlanStatus;
  updated_at?: string;
  revisions?: PlanRevision[];
}

export interface AgentThreadState extends Record<string, unknown> {
  title: string;
  messages: Message[];
  plan?: PlanState | null;
  artifacts: string[];
  todos?: Todo[];
}

export interface AgentThread extends Thread<AgentThreadState> {}

export interface AgentThreadContext extends Record<string, unknown> {
  thread_id: string;
  model_name: string | undefined;
  thinking_enabled: boolean;
  is_plan_mode: boolean;
  subagent_enabled: boolean;
  visual_output_intent?: boolean;
  synthetic_data_mode?: boolean;
  reasoning_effort?: "low" | "medium" | "high" | "xhigh";
  agent_name?: string;
}
