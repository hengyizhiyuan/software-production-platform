import type { Message } from "./types";

export type InteractionPhase = "idle" | "received" | "streaming" | "complete" | "archived";

export interface CurrentInteraction {
  id: number;
  phase: InteractionPhase;
  humanTurn?: string;
  wattReply?: string;
  visibleReply: string;
  history: Message[];
  readingProtected: boolean;
  expanded: boolean;
  realityEffect?: string;
}

export type InteractionAction =
  | { type: "submit"; text: string; reply: string; realityEffect?: string }
  | { type: "start" }
  | { type: "reveal"; length: number }
  | { type: "complete" }
  | { type: "protect-reading"; value: boolean }
  | { type: "toggle-expanded" }
  | { type: "archive" }
  | { type: "reset"; history: Message[]; seed?: Partial<CurrentInteraction> };

export function initialInteraction(history: Message[] = []): CurrentInteraction {
  return { id: 0, phase: "idle", visibleReply: "", history, readingProtected: false, expanded: false };
}

function settleCurrent(state: CurrentInteraction): Message[] {
  if (!state.humanTurn) return state.history;
  const settled: Message[] = [{ actor: "human", text: state.humanTurn }];
  if (state.wattReply) settled.push({ actor: "watt", text: state.wattReply });
  return [...state.history, ...settled];
}

export function interactionReducer(state: CurrentInteraction, action: InteractionAction): CurrentInteraction {
  switch (action.type) {
    case "submit":
      return {
        id: state.id + 1,
        phase: "received",
        humanTurn: action.text,
        wattReply: action.reply,
        visibleReply: "",
        history: state.phase === "idle" || state.phase === "archived" ? state.history : settleCurrent(state),
        readingProtected: false,
        expanded: false,
        realityEffect: action.realityEffect,
      };
    case "start": return state.phase === "received" ? { ...state, phase: "streaming" } : state;
    case "reveal": return state.phase === "streaming" ? { ...state, visibleReply: state.wattReply?.slice(0, action.length) ?? "" } : state;
    case "complete": return state.wattReply ? { ...state, phase: "complete", visibleReply: state.wattReply } : state;
    case "protect-reading": return { ...state, readingProtected: action.value };
    case "toggle-expanded": return { ...state, expanded: !state.expanded, readingProtected: !state.expanded };
    case "archive":
      if (state.phase !== "complete" || state.readingProtected) return state;
      return { ...state, phase: "archived", history: settleCurrent(state), humanTurn: undefined, wattReply: undefined, visibleReply: "", realityEffect: undefined, expanded: false };
    case "reset": return { ...initialInteraction(action.history), ...action.seed, history: action.history };
  }
}

export function transitionMotion(prefersReducedMotion: boolean): "crossfade" | "instant" {
  return prefersReducedMotion ? "instant" : "crossfade";
}
