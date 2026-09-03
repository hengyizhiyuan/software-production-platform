(function exposeViewModel(root) {
  "use strict";

  const STATUS_LABELS = Object.freeze({
    DRAFT: "Draft",
    NEEDS_REFINEMENT: "Needs refinement",
    AWAITING_APPROVAL: "Awaiting approval",
    READY: "Watt is preparing",
    RUNNING: "Watt is working",
    NEEDS_ATTENTION: "Needs your attention",
    BLOCKED: "Blocked",
    COMPLETED: "Completed",
  });

  const STATUS_TONES = Object.freeze({
    DRAFT: "status-draft",
    NEEDS_REFINEMENT: "status-refinement",
    AWAITING_APPROVAL: "status-approval",
    READY: "status-ready",
    RUNNING: "status-running",
    NEEDS_ATTENTION: "status-attention",
    BLOCKED: "status-blocked",
    COMPLETED: "status-completed",
  });

  function statusLabel(status) {
    return STATUS_LABELS[status] || String(status || "Unknown");
  }

  function statusTone(status) {
    return STATUS_TONES[status] || "status-draft";
  }

  function workActions(status) {
    if (status === "DRAFT" || status === "NEEDS_REFINEMENT") {
      return ["REFINE"];
    }
    if (status === "AWAITING_APPROVAL") {
      return ["APPROVE", "REQUEST_REFINEMENT", "REJECT"];
    }
    return [];
  }

  function shouldPoll(status) {
    return status === "READY" || status === "RUNNING";
  }

  function splitTags(value) {
    const unique = new Set(
      String(value || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    );
    return Array.from(unique).sort();
  }

  function conciseRequirement(value, limit) {
    const normalized = String(value || "").trim().replace(/\s+/g, " ");
    const maximum = limit || 72;
    if (normalized.length <= maximum) {
      return normalized || "Untitled Work";
    }
    return `${normalized.slice(0, maximum - 1)}…`;
  }

  function workTitle(work) {
    return work && work.title
      ? work.title
      : conciseRequirement(work && work.raw_user_requirement, 72);
  }

  function artifactSummary(result) {
    if (!result || !Array.isArray(result.produced_artifacts) || result.produced_artifacts.length === 0) {
      return "No artifacts observed.";
    }
    return result.produced_artifacts.join(", ");
  }

  function verificationSummary(result) {
    if (!result || !Array.isArray(result.verification_summary) || result.verification_summary.length === 0) {
      return "No verification evidence available.";
    }
    return result.verification_summary.join(" · ");
  }

  root.SPGViewModel = Object.freeze({
    STATUS_LABELS,
    statusLabel,
    statusTone,
    workActions,
    shouldPoll,
    splitTags,
    conciseRequirement,
    workTitle,
    artifactSummary,
    verificationSummary,
  });
})(globalThis);
