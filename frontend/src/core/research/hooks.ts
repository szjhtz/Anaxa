import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  advanceResearchQuest,
  createResearchQuest,
  decideResearchGate,
  getResearchQuest,
  listResearchQuests,
} from "./api";
import type {
  AdvanceResearchQuestRequest,
  CreateResearchQuestRequest,
  GateStatus,
  ResearchStage,
} from "./types";

const RESEARCH_QUESTS_KEY = ["research", "quests"] as const;

export function useResearchQuests(threadId?: string) {
  return useQuery({
    queryKey: [...RESEARCH_QUESTS_KEY, threadId ?? "all"],
    queryFn: () => listResearchQuests(threadId),
    staleTime: 15_000,
  });
}

export function useResearchQuest(questId: string | null | undefined) {
  return useQuery({
    queryKey: ["research", "quest", questId],
    queryFn: () => getResearchQuest(questId!),
    enabled: !!questId,
    staleTime: 10_000,
  });
}

export function useCreateResearchQuest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: CreateResearchQuestRequest) => createResearchQuest(request),
    onSuccess: (quest) => {
      void queryClient.invalidateQueries({ queryKey: RESEARCH_QUESTS_KEY });
      void queryClient.invalidateQueries({ queryKey: ["research", "quest", quest.quest_id] });
    },
  });
}

export function useAdvanceResearchQuest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      questId,
      request,
    }: {
      questId: string;
      request?: AdvanceResearchQuestRequest;
    }) => advanceResearchQuest(questId, request),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: RESEARCH_QUESTS_KEY });
      void queryClient.invalidateQueries({ queryKey: ["research", "quest", result.quest.quest_id] });
    },
  });
}

export function useDecideResearchGate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: {
      questId: string;
      stage: ResearchStage;
      gateType: string;
      status: GateStatus;
      reason?: string;
    }) => decideResearchGate(request),
    onSuccess: (gate) => {
      void queryClient.invalidateQueries({ queryKey: RESEARCH_QUESTS_KEY });
      void queryClient.invalidateQueries({ queryKey: ["research", "quest", gate.quest_id] });
    },
  });
}
