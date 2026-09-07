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

  function executionProgress(work) {
    const progress = work && work.execution_progress;
    if (!progress) {
      return null;
    }
    const completed = Number.isInteger(progress.transitions_completed)
      ? Math.max(0, progress.transitions_completed)
      : 0;
    const knownTotal = Number.isInteger(progress.transitions_total)
      && progress.transitions_total > 0;
    const apiPercent = Number.isFinite(progress.percent_complete)
      ? Math.max(0, Math.min(100, Math.round(progress.percent_complete)))
      : null;
    const percentComplete = knownTotal
      ? (apiPercent === null
        ? Math.min(100, Math.round((completed / progress.transitions_total) * 100))
        : apiPercent)
      : null;
    return {
      phase: progress.phase || "Production",
      activity: progress.activity || "Observing current production reality",
      progressText: knownTotal
        ? `${completed} of ${progress.transitions_total} transitions · ${percentComplete}%`
        : `${completed} transitions completed · total unknown`,
      percentComplete,
      elapsedText: `${Math.max(0, Math.floor(progress.elapsed_seconds || 0))}s elapsed`,
      stillWorking: progress.still_working === true,
      activitySignal: progress.still_working === true ? "Still working" : "Not running",
      updatedAt: progress.updated_at || null,
      blockedReason: progress.blocked_reason || null,
    };
  }

  function sameIdentity(left, right) {
    return Boolean(left) && Boolean(right) && String(left) === String(right);
  }

  function understandingForWork(work, understandings) {
    if (!work || !Array.isArray(understandings)) {
      return null;
    }
    return understandings.find(
      (item) => sameIdentity(item && item.current_work_id, work.work_id),
    ) || understandings.find((item) => (
      sameIdentity(
        item && item.governed_revision && item.governed_revision.work_id,
        work.work_id,
      )
    )) || null;
  }

  function controlRoomProjection(work, understandings, attentionItems) {
    if (!work) {
      return null;
    }
    const understanding = understandingForWork(work, understandings);
    const governed = understanding
      && understanding.governed_revision
      && sameIdentity(understanding.governed_revision.work_id, work.work_id)
      ? understanding.governed_revision
      : null;
    const attention = Array.isArray(attentionItems)
      ? attentionItems.filter((item) => sameIdentity(item && item.work_id, work.work_id))
      : [];
    const progress = executionProgress(work);
    const attentionRequired = work.human_attention_required === true || attention.length > 0;
    const attentionCount = attention.length || (attentionRequired ? 1 : 0);
    const attentionSummary = attention.length
      ? attention.map((item) => `${item.decision}: ${item.reason}`).join(" | ")
      : attentionRequired
        ? "Work Reality reports that Human attention is required."
        : "No blockers, reviews, or transitions require Human action.";
    const emergingDirection = attention.find((item) => item.recommendation)
      || attention.find((item) => item.expected_impact);

    return {
      objective: {
        motive: governed && governed.motive
          ? governed.motive
          : "Not available from governed Work Reality.",
        currentWork: workTitle(work),
        desiredOutcome: work.desired_outcome || "Not established in Work Reality.",
        satisfaction: understanding
          && sameIdentity(understanding.current_work_id, work.work_id)
          && understanding.work_satisfaction_state
          ? understanding.work_satisfaction_state
          : "Not available for this Work.",
      },
      status: {
        workStatus: statusLabel(work.status),
        lifecyclePhase: work.current_production_step || "Not reported by Work Reality.",
        activity: progress
          ? progress.activity
          : "No active production activity reported.",
        condition: progress && progress.blockedReason
          ? progress.blockedReason
          : attention.length
            ? attention.map((item) => item.reason).join(" | ")
            : attentionRequired
              ? "Work Reality reports that Human attention is required."
              : "No blocking or waiting condition reported.",
      },
      attention: {
        required: attentionRequired,
        state: attentionRequired
          ? `${attentionCount} Human attention requirement${attentionCount === 1 ? "" : "s"}`
          : "No Human attention required",
        summary: attentionSummary,
        emergingDirection: emergingDirection
          ? emergingDirection.recommendation || emergingDirection.expected_impact
          : "No emerging direction reported.",
      },
    };
  }

  function stringValues(values) {
    return Array.isArray(values) ? values.filter((item) => String(item || "").trim()) : [];
  }

  function understandingAlignmentProjection(work, understandings) {
    if (!work) {
      return null;
    }
    const understanding = understandingForWork(work, understandings);
    const assessment = understanding && understanding.latest_assessment;
    const assessmentCurrent = Boolean(
      assessment && understanding.latest_assessment_current === true,
    );
    const governed = understanding
      && understanding.governed_revision
      && sameIdentity(understanding.governed_revision.work_id, work.work_id)
      ? understanding.governed_revision
      : null;
    const unresolved = stringValues(
      understanding && understanding.unresolved_material_questions,
    );
    const waitingForHuman = Boolean(
      understanding
      && (
        understanding.work_revision_admission_status === "PENDING_HUMAN"
        || (
          understanding.latest_work_transition
          && understanding.latest_work_transition.choice === "PENDING_HUMAN"
        )
      ),
    );

    let statusLabelText = "Needs clarification";
    let statusToneText = "status-refinement";
    let statusBasis = "No WIC Shared Understanding is available for this Work.";
    if (waitingForHuman) {
      statusLabelText = "Waiting for Human decision";
      statusToneText = "status-approval";
      statusBasis = "Existing WIC Reality reports a pending Human decision.";
    } else if (!understanding || !assessment) {
      statusBasis = "No WIC assessment is available for this Work.";
    } else if (!assessmentCurrent) {
      statusBasis = "The latest WIC assessment is no longer current.";
    } else if (
      understanding.readiness
      && understanding.readiness.status === "READY"
      && unresolved.length === 0
    ) {
      statusLabelText = "Understood";
      statusToneText = "status-completed";
      statusBasis = "The current WIC assessment is READY with no unresolved material questions.";
    } else if (unresolved.length) {
      statusBasis = unresolved.length === 1
        ? "1 unresolved material question remains."
        : `${unresolved.length} unresolved material questions remain.`;
    } else {
      statusBasis = "The current WIC assessment has not reached READY.";
    }

    const interpretedMotive = understanding && understanding.interpreted_motive;
    const interpretedOutcome = understanding && understanding.desired_outcome;
    const governedMotive = governed && governed.motive;
    const governedOutcome = governed && governed.desired_outcome;

    return {
      available: Boolean(understanding),
      interactionId: understanding ? understanding.interaction_id : null,
      status: {
        label: statusLabelText,
        tone: statusToneText,
        basis: statusBasis,
      },
      human: {
        statements: stringValues(understanding && understanding.human_said),
      },
      interpreted: {
        current: assessmentCurrent,
        currency: assessment
          ? assessmentCurrent ? "Current advisory interpretation" : "Stale advisory interpretation"
          : "No advisory interpretation",
        motive: interpretedMotive || "Not interpreted.",
        desiredOutcome: interpretedOutcome || "Not interpreted.",
        constraints: stringValues(understanding && understanding.candidate_constraints),
        relevantFacts: stringValues(understanding && understanding.candidate_context),
      },
      governed: {
        available: Boolean(governed),
        revision: governed
          ? `Work Reality revision ${governed.revision_number}`
          : "No governed Work Reality revision",
        motive: governedMotive || "Not governed.",
        desiredOutcome: governedOutcome || "Not governed.",
        constraints: stringValues(governed && governed.constraints),
        relevantFacts: stringValues(governed && governed.context_facts),
      },
      shared: {
        understoodObjective: interpretedMotive || interpretedOutcome
          ? [interpretedMotive, interpretedOutcome].filter(Boolean).join(" -> ")
          : "No understood objective is available.",
        confirmedConstraints: stringValues(governed && governed.constraints),
        relevantFacts: stringValues(governed && governed.context_facts),
        unresolvedQuestions: unresolved,
      },
    };
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
    executionProgress,
    controlRoomProjection,
    understandingAlignmentProjection,
    splitTags,
    conciseRequirement,
    workTitle,
    artifactSummary,
    verificationSummary,
  });
})(globalThis);
