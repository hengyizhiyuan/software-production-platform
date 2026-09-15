export type Surface = "home" | "work" | "history" | "deliveries";

export type PrototypePhase =
  | "PRE_WORK"
  | "REFINING"
  | "READY_FOR_WORK"
  | "DESIGNING"
  | "PLANNING"
  | "QUEUED"
  | "WAITING_FOR_CAPACITY"
  | "RUNNING"
  | "CHECKPOINTED"
  | "PAUSED"
  | "RECOVERING"
  | "WAITING_FOR_HUMAN"
  | "VERIFYING"
  | "RESULT_READY"
  | "READY_FOR_AUTHORIZATION"
  | "AUTHORIZED"
  | "DELIVERED"
  | "COMPLETED"
  | "REOPENED";

export type Tone = "neutral" | "active" | "success" | "attention" | "warning";

export interface Message {
  actor: "human" | "watt";
  text: string;
  pending?: boolean;
}

export interface Milestone {
  label: string;
  detail: string;
  state: "done" | "current" | "next" | "blocked";
}

export interface AttentionFact {
  contract: "handling" | "awareness" | "decision";
  title: string;
  body: string;
  action?: string;
  consequence?: string;
}

export interface ResultFact {
  kind: "application" | "change" | "multi";
  title: string;
  summary: string;
  highlights: string[];
  checks: string[];
  limitations?: string[];
  assets?: string[];
  previewVariant?: "dashboard" | "mobile" | "diff";
}

export interface DeliveryFact {
  title: string;
  form: string;
  detail: string;
  action: string;
  trust: string;
  runtimeState?: "aligned" | "different";
}

export interface OwnerFacts {
  wic?: string;
  work?: string;
  guidedDesign?: string;
  steering?: string;
  queue?: string;
  executor?: string;
  verification?: string;
  authority?: string;
  delivery?: string;
  assets?: string;
}

export interface Transition {
  label: string;
  to: string;
  kind?: "primary" | "secondary" | "danger";
  hint?: string;
}

export interface Scene {
  id: string;
  label: string;
  phase: PrototypePhase;
  surface: Surface;
  tone: Tone;
  eyebrow: string;
  title: string;
  summary: string;
  workName?: string;
  workOutcome?: string;
  changedSince?: string[];
  messages?: Message[];
  understanding?: {
    objective: string;
    scope: string[];
    constraints: string[];
    deliverable: string;
    boundary: string;
  };
  recommendation?: {
    title: string;
    body: string;
    rationale: string;
    alternatives?: string[];
  };
  milestones?: Milestone[];
  production?: {
    label: string;
    activity: string;
    reason?: string;
    elapsed?: string;
    queueDetail?: string[];
  };
  attention?: AttentionFact;
  result?: ResultFact;
  deliveries?: DeliveryFact[];
  assets?: { name: string; role: string; state: string }[];
  ownerFacts: OwnerFacts;
  scenarioIds: string[];
  tensionIds: string[];
  acceptanceFocus: string;
  transitions: Transition[];
}

export interface ScenarioPack {
  id: string;
  title: string;
  shortTitle: string;
  description: string;
  reviewReason: string;
  seed: string;
  scenes: Scene[];
}
