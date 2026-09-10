(function startControlRoom() {
  "use strict";

  const viewModel = globalThis.SPGViewModel;
  if (!viewModel) {
    return;
  }

  const POLL_INTERVAL_MS = 2000;
  const COMPOSER_EXPANDED_STORAGE_KEY = "spg.workComposer.expanded";
  const INTERACTION_STORAGE_KEY = "spg.currentInteraction.id";
  const OUTBOX_STORAGE_KEY = "spg.interaction.outbox.v1";
  const DRAFT_STORAGE_KEY = "spg.interaction.drafts.v1";
  const state = {
    goals: [],
    works: [],
    interactions: [],
    selectedInteractionId: "",
    sharedUnderstanding: null,
    selectedGoalId: "",
    selectedWorkId: "",
    selectedWork: null,
    attention: [],
    result: null,
    steering: null,
    statusFilter: "",
    busy: false,
    pollTimer: null,
    activeInteractionTurnId: "",
    interactionEventSource: null,
    streamingAssistantMessage: null,
    streamFrame: null,
    sendInFlight: false,
    finishingTurn: false,
    outbox: [],
    drafts: {},
    freshInteraction: false,
    storageAvailable: true,
  };

  const elements = {
    healthControl: document.getElementById("health-control"),
    healthDot: document.getElementById("health-dot"),
    healthLabel: document.getElementById("health-label"),
    showGoalForm: document.getElementById("show-goal-form"),
    goalForm: document.getElementById("goal-form"),
    goalTitle: document.getElementById("goal-title"),
    goalList: document.getElementById("goal-list"),
    statusFilter: document.getElementById("status-filter"),
    workList: document.getElementById("work-list"),
    workListEmpty: document.getElementById("work-list-empty"),
    refreshControl: document.getElementById("refresh-control"),
    workRefreshControl: document.getElementById("work-refresh-control"),
    retryControl: document.getElementById("retry-control"),
    loadingState: document.getElementById("loading-state"),
    globalError: document.getElementById("global-error"),
    globalErrorMessage: document.getElementById("global-error-message"),
    noSelection: document.getElementById("no-selection"),
    interactionHistory: document.getElementById("interaction-history"),
    interactionOutbox: document.getElementById("interaction-outbox"),
    composerStatus: document.getElementById("composer-status"),
    interactionProcessingStatus: document.getElementById("interaction-processing-status"),
    newInteractionControl: document.getElementById("new-interaction-control"),
    interactionReadiness: document.getElementById("interaction-readiness"),
    wattResponse: document.getElementById("watt-response"),
    interpretedMotive: document.getElementById("interpreted-motive"),
    interpretedOutcome: document.getElementById("interpreted-outcome"),
    interpretedContext: document.getElementById("interpreted-context"),
    interpretedRequests: document.getElementById("interpreted-requests"),
    interpretedConstraints: document.getElementById("interpreted-constraints"),
    interpretedQuestions: document.getElementById("interpreted-questions"),
    interactionResource: document.getElementById("interaction-resource"),
    interactionScope: document.getElementById("interaction-scope"),
    governedUnderstanding: document.getElementById("governed-understanding"),
    currentWorkFocus: document.getElementById("current-work-focus"),
    interactionFocusClassification: document.getElementById("interaction-focus-classification"),
    interactionImpactDisposition: document.getElementById("interaction-impact-disposition"),
    interactionCandidateChange: document.getElementById("interaction-candidate-change"),
    workRevisionAdmissionStatus: document.getElementById("work-revision-admission-status"),
    workSatisfactionState: document.getElementById("work-satisfaction-state"),
    interactionRelationshipState: document.getElementById("interaction-relationship-state"),
    workFocusHistory: document.getElementById("work-focus-history"),
    workTransitionSummary: document.getElementById("work-transition-summary"),
    interactionDesignSchema: document.getElementById("interaction-design-schema"),
    interactionDesignSchemaRationale: document.getElementById("interaction-design-schema-rationale"),
    interactionDesignStage: document.getElementById("interaction-design-stage"),
    interactionDesignNextFocus: document.getElementById("interaction-design-next-focus"),
    interactionDesignFocusRationale: document.getElementById("interaction-design-focus-rationale"),
    interactionDesignStrategy: document.getElementById("interaction-design-strategy"),
    interactionDesignProgress: document.getElementById("interaction-design-progress"),
    readinessAffordance: document.getElementById("readiness-affordance"),
    interactionAdmission: document.getElementById("interaction-admission"),
    interactionAuthorityIdentity: document.getElementById("interaction-authority-identity"),
    admitWorkControl: document.getElementById("admit-work-control"),
    workRevisionAdmission: document.getElementById("work-revision-admission"),
    workRevisionAuthorityIdentity: document.getElementById("work-revision-authority-identity"),
    approveWorkRevision: document.getElementById("approve-work-revision"),
    rejectWorkRevision: document.getElementById("reject-work-revision"),
    refineWorkRevision: document.getElementById("refine-work-revision"),
    workTransitionDecision: document.getElementById("work-transition-decision"),
    workTransitionAuthorityIdentity: document.getElementById("work-transition-authority-identity"),
    continueCurrentWork: document.getElementById("continue-current-work"),
    startNewWork: document.getElementById("start-new-work"),
    dismissWorkTransition: document.getElementById("dismiss-work-transition"),
    selectedWork: document.getElementById("selected-work"),
    workTitle: document.getElementById("work-title"),
    workStatus: document.getElementById("work-status"),
    executionProgress: document.getElementById("execution-progress"),
    executionPhase: document.getElementById("execution-phase"),
    executionActivity: document.getElementById("execution-activity"),
    executionCount: document.getElementById("execution-count"),
    executionElapsed: document.getElementById("execution-elapsed"),
    executionSignal: document.getElementById("execution-signal"),
    executionUpdated: document.getElementById("execution-updated"),
    executionBlocked: document.getElementById("execution-blocked"),
    attentionMarker: document.getElementById("attention-marker"),
    controlObjectiveMotive: document.getElementById("control-objective-motive"),
    controlObjectiveWork: document.getElementById("control-objective-work"),
    controlObjectiveOutcome: document.getElementById("control-objective-outcome"),
    controlObjectiveSatisfaction: document.getElementById("control-objective-satisfaction"),
    controlStatusWork: document.getElementById("control-status-work"),
    controlStatusPhase: document.getElementById("control-status-phase"),
    controlStatusActivity: document.getElementById("control-status-activity"),
    controlStatusCondition: document.getElementById("control-status-condition"),
    controlAttentionCard: document.getElementById("control-attention-card"),
    controlAttentionState: document.getElementById("control-attention-state"),
    controlAttentionSummary: document.getElementById("control-attention-summary"),
    controlEmergingDirection: document.getElementById("control-emerging-direction"),
    alignmentStatus: document.getElementById("alignment-status"),
    alignmentStatusBasis: document.getElementById("alignment-status-basis"),
    alignmentHumanSaid: document.getElementById("alignment-human-said"),
    alignmentInterpretationCurrency: document.getElementById("alignment-interpretation-currency"),
    alignmentInterpretedMotive: document.getElementById("alignment-interpreted-motive"),
    alignmentInterpretedOutcome: document.getElementById("alignment-interpreted-outcome"),
    alignmentGovernedRevision: document.getElementById("alignment-governed-revision"),
    alignmentGovernedMotive: document.getElementById("alignment-governed-motive"),
    alignmentGovernedOutcome: document.getElementById("alignment-governed-outcome"),
    alignmentUnderstoodObjective: document.getElementById("alignment-understood-objective"),
    alignmentConfirmedConstraints: document.getElementById("alignment-confirmed-constraints"),
    alignmentRelevantFacts: document.getElementById("alignment-relevant-facts"),
    alignmentUnresolvedQuestions: document.getElementById("alignment-unresolved-questions"),
    guidedDesignPanel: document.getElementById("guided-design-panel"),
    designReadiness: document.getElementById("design-readiness"),
    designObjective: document.getElementById("design-objective"),
    designProcess: document.getElementById("design-process"),
    designSchemaRationale: document.getElementById("design-schema-rationale"),
    designStage: document.getElementById("design-stage"),
    designCurrentFocus: document.getElementById("design-current-focus"),
    designFocusRationale: document.getElementById("design-focus-rationale"),
    designFacilitationStrategy: document.getElementById("design-facilitation-strategy"),
    designFacilitationGuidance: document.getElementById("design-facilitation-guidance"),
    designProgress: document.getElementById("design-progress"),
    designProgressNarrative: document.getElementById("design-progress-narrative"),
    designCompletedAreas: document.getElementById("design-completed-areas"),
    designUnresolvedAreas: document.getElementById("design-unresolved-areas"),
    designDependencyBlockers: document.getElementById("design-dependency-blockers"),
    designBlockers: document.getElementById("design-blockers"),
    designUpcoming: document.getElementById("design-upcoming"),
    designAgenda: document.getElementById("design-agenda"),
    directionState: document.getElementById("direction-state"),
    directionRevision: document.getElementById("direction-revision"),
    directionObjective: document.getElementById("direction-objective"),
    directionCurrentStep: document.getElementById("direction-current-step"),
    directionNextStep: document.getElementById("direction-next-step"),
    directionRationale: document.getElementById("direction-rationale"),
    directionRealityBasis: document.getElementById("direction-reality-basis"),
    directionCondition: document.getElementById("direction-condition"),
    trustSummaryState: document.getElementById("trust-summary-state"),
    trustCompletion: document.getElementById("trust-completion"),
    trustVerification: document.getElementById("trust-verification"),
    trustRuntimeCommit: document.getElementById("trust-runtime-commit"),
    trustBaseline: document.getElementById("trust-baseline"),
    trustActiveRuntime: document.getElementById("trust-active-runtime"),
    trustBasis: document.getElementById("trust-basis"),
    workRequest: document.getElementById("work-request"),
    desiredOutcome: document.getElementById("desired-outcome"),
    scopeSummary: document.getElementById("scope-summary"),
    artifactOperation: document.getElementById("artifact-operation"),
    artifactRationale: document.getElementById("artifact-rationale"),
    artifactTargetPanel: document.getElementById("artifact-target-panel"),
    artifactTargetPath: document.getElementById("artifact-target-path"),
    saveArtifactTarget: document.getElementById("save-artifact-target"),
    codeChangeContractPanel: document.getElementById("code-change-contract-panel"),
    codeAuthorityKind: document.getElementById("code-authority-kind"),
    codeTargetShape: document.getElementById("code-target-shape"),
    codeProposalConfidence: document.getElementById("code-proposal-confidence"),
    codeProposalRationale: document.getElementById("code-proposal-rationale"),
    codeProposalSource: document.getElementById("code-proposal-source"),
    codeConditionalTargets: document.getElementById("code-conditional-targets"),
    codeProposalUnresolved: document.getElementById("code-proposal-unresolved"),
    codeExactTargets: document.getElementById("code-exact-targets"),
    codeAllowedAreas: document.getElementById("code-allowed-areas"),
    codeForbiddenAreas: document.getElementById("code-forbidden-areas"),
    codeVerificationObligations: document.getElementById("code-verification-obligations"),
    saveCodeChangeContract: document.getElementById("save-code-change-contract"),
    productionPlanPanel: document.getElementById("production-plan-panel"),
    planFit: document.getElementById("plan-fit"),
    planObjective: document.getElementById("plan-objective"),
    planSteps: document.getElementById("plan-steps"),
    planVerification: document.getElementById("plan-verification"),
    planUnresolved: document.getElementById("plan-unresolved"),
    recentEvent: document.getElementById("recent-event"),
    nextAction: document.getElementById("next-action"),
    currentStep: document.getElementById("current-step"),
    constraintList: document.getElementById("constraint-list"),
    tagList: document.getElementById("tag-list"),
    technicalDetails: document.getElementById("technical-details"),
    resourceList: document.getElementById("resource-list"),
    manualAdvanceControl: document.getElementById("manual-advance-control"),
    authorityIdentity: document.getElementById("authority-identity"),
    workActions: document.getElementById("work-actions"),
    attentionSection: document.getElementById("attention-section"),
    attentionList: document.getElementById("attention-list"),
    trustedResult: document.getElementById("trusted-result"),
    artifactSummary: document.getElementById("artifact-summary"),
    verificationSummary: document.getElementById("verification-summary"),
    repositoryState: document.getElementById("repository-state"),
    remainingRisk: document.getElementById("remaining-risk"),
    workForm: document.getElementById("work-form"),
    composerToggle: document.getElementById("composer-toggle"),
    workRequirement: document.getElementById("work-requirement"),
    submitWork: document.getElementById("submit-work"),
    liveRegion: document.getElementById("live-region"),
    notice: document.getElementById("notice"),
    noticeMessage: document.getElementById("notice-message"),
    dismissNotice: document.getElementById("dismiss-notice"),
  };

  class ApiError extends Error {
    constructor(status, code, message) {
      super(message);
      this.status = status;
      this.code = code;
    }
  }

  async function apiRequest(path, options) {
    const request = options || {};
    const init = {
      method: request.method || "GET",
      headers: { Accept: "application/json" },
    };
    if (Object.prototype.hasOwnProperty.call(request, "body")) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(request.body);
    }
    const response = await fetch(path, init);
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : null;
    if (!response.ok) {
      throw new ApiError(
        response.status,
        payload && payload.code ? payload.code : "REQUEST_FAILED",
        payload && payload.message ? payload.message : "The request could not be completed.",
      );
    }
    return payload;
  }

  function createElement(tagName, className, text) {
    const node = document.createElement(tagName);
    if (className) {
      node.className = className;
    }
    if (text !== undefined && text !== null) {
      node.textContent = String(text);
    }
    return node;
  }

  function announce(message) {
    elements.liveRegion.textContent = "";
    globalThis.requestAnimationFrame(() => {
      elements.liveRegion.textContent = message;
    });
  }

  function showNotice(error) {
    const message = error instanceof ApiError
      ? `${error.code}: ${error.message}`
      : "The service is unavailable. Refresh and try again.";
    elements.noticeMessage.textContent = message;
    elements.notice.hidden = false;
    announce(message);
  }

  function hideNotice() {
    elements.notice.hidden = true;
    elements.noticeMessage.textContent = "";
  }

  function setBusy(value) {
    state.busy = value;
    const controls = document.querySelectorAll("button, input, select, textarea");
    controls.forEach((control) => {
      if (control !== elements.dismissNotice) {
        control.disabled = value;
      }
    });
    renderComposer();
    // A Turn can finish while another UI action is still refreshing. Retry
    // eligible browser intent when that action releases the busy guard.
    if (!value) void drainOutbox();
  }

  function setSurface(name) {
    elements.loadingState.hidden = name !== "loading";
    elements.globalError.hidden = name !== "error";
    elements.noSelection.hidden = name !== "empty";
    elements.selectedWork.hidden = name !== "selected";
  }

  function goalTitle(goalId) {
    const goal = state.goals.find((item) => item.goal_id === goalId);
    return goal ? goal.title : "No Goal";
  }

  function filteredWorks() {
    return state.works.filter((work) => {
      const goalMatches = !state.selectedGoalId || work.goal_id === state.selectedGoalId;
      const statusMatches = !state.statusFilter || work.status === state.statusFilter;
      return goalMatches && statusMatches;
    });
  }

  function renderGoalList() {
    elements.goalList.replaceChildren();
    const allButton = createElement("button", "goal-button", "All Works");
    allButton.type = "button";
    allButton.classList.toggle("selected", state.selectedGoalId === "");
    const allCount = createElement("span", "goal-count", state.works.length);
    allButton.append(allCount);
    allButton.addEventListener("click", () => selectGoal(""));
    elements.goalList.append(allButton);

    state.goals.forEach((goal) => {
      const button = createElement("button", "goal-button", goal.title);
      button.type = "button";
      button.classList.toggle("selected", state.selectedGoalId === goal.goal_id);
      const count = state.works.filter((work) => work.goal_id === goal.goal_id).length;
      button.append(createElement("span", "goal-count", count));
      button.addEventListener("click", () => selectGoal(goal.goal_id));
      elements.goalList.append(button);
    });
  }

  function renderWorkList() {
    elements.workList.replaceChildren();
    const works = filteredWorks();
    elements.workListEmpty.hidden = works.length !== 0;
    works.forEach((work) => {
      const button = createElement("button", "work-list-button");
      button.type = "button";
      button.classList.toggle("selected", state.selectedWorkId === work.work_id);
      button.setAttribute("aria-label", `Open Work: ${viewModel.workTitle(work)}`);

      button.append(createElement("span", "work-list-title", viewModel.workTitle(work)));
      const meta = createElement("span", "work-list-meta");
      const status = createElement("span", "", viewModel.statusLabel(work.status));
      if (work.human_attention_required) {
        status.prepend(createElement("span", "attention-pip"));
      }
      meta.append(status, createElement("span", "", goalTitle(work.goal_id)));
      button.append(meta);
      button.append(
        createElement(
          "span",
          "work-list-event",
          work.most_recent_meaningful_event || "No production event yet",
        ),
      );
      button.addEventListener("click", () => selectWork(work.work_id));
      elements.workList.append(button);
    });
  }

  function joined(values, emptyLabel) {
    return Array.isArray(values) && values.length ? values.join(" · ") : emptyLabel;
  }

  function messageKey(record, index) {
    return `${state.selectedInteractionId}:${record.actor}:${record.turn_id || record.interaction_record_id || index}`;
  }

  function renderConversation() {
    const history = viewModel.interactionConversationMessages(state.sharedUnderstanding, state.streamingAssistantMessage);
    const container = elements.interactionHistory;
    const existing = new Map(Array.from(container.children).map((node) => [node.dataset.messageKey, node]));
    const retained = new Set();
    history.forEach((record, index) => {
      const key = messageKey(record, index);
      let message = existing.get(key);
      if (!message) {
        message = createElement("article", `interaction-message actor-${record.actor.toLowerCase()}`);
        message.dataset.messageKey = key;
        message.append(createElement("p", "speaker-label", record.actor === "HUMAN" ? "You" : "Watt"));
        message.append(createElement("p", "message-content"));
        message.append(createElement("p", "message-meta"));
        message.append(createElement("p", "message-references"));
      }
      retained.add(message);
      updateMessageNode(message, record);
      if (container.children[index] !== message) container.insertBefore(message, container.children[index] || null);
    });
    Array.from(container.children).forEach((node) => { if (!retained.has(node)) node.remove(); });
    if (!history.length) container.append(createElement("p", "empty-copy", "No messages yet."));
  }

  function updateMessageNode(message, record) {
    message.classList.toggle("is-streaming", Boolean(record.streaming));
    message.setAttribute("aria-busy", String(Boolean(record.streaming)));
    const content = message.querySelector(".message-content");
    if (content.textContent !== record.content) content.textContent = record.content;
    const timestamp = record.created_at ? new Date(record.created_at).toLocaleTimeString() : "";
    const meta = `${timestamp}${record.processing_status ? ` · ${record.processing_status}` : ""}`;
    if (message.children[2].textContent !== meta) message.children[2].textContent = meta;
    const references = [...(record.supporting_references || []), ...(record.design_result_references || []), ...(record.governance_event_references || [])].join(" · ");
    if (message.children[3].textContent !== references) message.children[3].textContent = references;
    message.children[3].hidden = !references;
  }

  function renderInteractionStatus() {
    const turns = (state.sharedUnderstanding && state.sharedUnderstanding.turns) || [];
    const turnStatus = state.streamingAssistantMessage ? state.streamingAssistantMessage.status
      : turns.length ? turns[turns.length - 1].status : "IDLE";
    elements.interactionProcessingStatus.textContent = turnStatus;
    elements.interactionProcessingStatus.className = `status-badge ${turnStatus === "FAILED" ? "status-attention" : turnStatus === "COMPLETED" ? "status-completed" : "status-draft"}`;
  }

  function scheduleStreamRender() {
    if (state.streamFrame !== null) return;
    state.streamFrame = globalThis.requestAnimationFrame(() => {
      state.streamFrame = null;
      const streamed = state.streamingAssistantMessage;
      if (!streamed) return;
      const key = messageKey({ actor: "WATT", turn_id: streamed.turnId }, 0);
      const node = Array.from(elements.interactionHistory.children).find((item) => item.dataset.messageKey === key);
      if (node) {
        updateMessageNode(node, {
          content: streamed.content || "Watt is thinking...", streaming: true,
          processing_status: streamed.status, created_at: streamed.createdAt,
        });
      }
      renderInteractionStatus();
    });
  }

  function persistComposer() {
    try {
      // Tab-scoped storage prevents another open tab from draining this outbox.
      sessionStorage.setItem(OUTBOX_STORAGE_KEY, JSON.stringify(state.outbox));
      sessionStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(state.drafts));
      state.storageAvailable = true;
    } catch (_error) {
      state.storageAvailable = false;
    }
  }

  function restoreComposer() {
    try {
      state.outbox = viewModel.restoreInteractionOutbox(JSON.parse(sessionStorage.getItem(OUTBOX_STORAGE_KEY) || "[]"));
      const drafts = JSON.parse(sessionStorage.getItem(DRAFT_STORAGE_KEY) || "{}");
      state.drafts = drafts && typeof drafts === "object" && !Array.isArray(drafts) ? drafts : {};
      elements.workRequirement.value = state.drafts.new || "";
    } catch (_error) {
      state.storageAvailable = false;
    }
  }

  function saveDraft() {
    state.drafts[state.selectedInteractionId || "new"] = elements.workRequirement.value;
    persistComposer();
  }

  function renderComposer() {
    const waiting = Boolean(state.activeInteractionTurnId || state.finishingTurn || state.sendInFlight);
    elements.workRequirement.disabled = state.busy;
    elements.submitWork.disabled = state.busy;
    elements.newInteractionControl.disabled = state.busy || state.sendInFlight;
    elements.submitWork.textContent = waiting ? "Queue next message" : "Send";
    elements.composerStatus.textContent = !state.storageAvailable
      ? "Browser storage is unavailable. Keep this page open to retain drafts and waiting messages."
      : waiting ? "You can write ahead. Queued messages send after this reply is complete."
        : "Share a question, idea, or next step.";
    elements.interactionOutbox.hidden = state.outbox.length === 0;
    elements.interactionOutbox.replaceChildren();
    state.outbox.forEach((item) => {
      const row = createElement("article", "outbox-message");
      row.append(createElement("p", "outbox-content", item.content));
      const elsewhere = item.interactionId !== state.selectedInteractionId;
      const status = item.status === "sending" ? "Sending — receipt not confirmed yet."
        : item.status === "uncertain" ? "Delivery not confirmed. Check conversation history before sending again."
          : item.status === "paused" ? "Paused — not sent. Resume when you are ready."
            : "Waiting to send — Watt has not received this message.";
      row.append(createElement("p", "message-meta", `${elsewhere ? "Another conversation · " : ""}${status}`));
      const actions = createElement("div", "outbox-actions");
      if (elsewhere || item.status === "paused" || item.status === "uncertain") {
        const resume = createElement("button", "text-button", elsewhere || item.status === "uncertain" ? "View conversation" : "Resume");
        resume.type = "button";
        resume.disabled = state.busy || state.sendInFlight;
        resume.addEventListener("click", () => resumeOutbox(item.id));
        actions.append(resume);
      }
      if (item.status !== "sending") {
        const cancel = createElement("button", "text-button", item.status === "uncertain" ? "Remove local copy" : "Cancel");
        cancel.type = "button";
        cancel.addEventListener("click", () => {
          state.outbox = state.outbox.filter((entry) => entry.id !== item.id);
          persistComposer();
          renderComposer();
          void drainOutbox();
        });
        actions.append(cancel);
      }
      row.append(actions);
      elements.interactionOutbox.append(row);
    });
  }

  function renderInteraction() {
    const projection = state.sharedUnderstanding;
    renderConversation();
    renderComposer();
    if (!projection) {
      elements.interactionReadiness.textContent = "NOT_READY";
      elements.interactionReadiness.className = "status-badge status-draft";
      elements.interactionProcessingStatus.textContent = "IDLE";
      elements.interactionProcessingStatus.className = "status-badge status-draft";
      elements.wattResponse.hidden = false;
      elements.wattResponse.textContent = "Start anywhere. Watt will ask only for material clarification.";
      elements.interpretedMotive.textContent = "Not established yet";
      elements.interpretedOutcome.textContent = "Not established yet";
      elements.interpretedContext.textContent = "None yet";
      elements.interpretedRequests.textContent = "None yet";
      elements.interpretedConstraints.textContent = "None yet";
      elements.interpretedQuestions.textContent = "Tell Watt what you want to explore.";
      elements.interactionResource.textContent = "Not bound yet";
      elements.interactionScope.textContent = "Not bound yet";
      elements.governedUnderstanding.textContent = "None — no Work exists";
      elements.currentWorkFocus.textContent = "No governed Work focus";
      elements.interactionFocusClassification.textContent = "Not assessed";
      elements.interactionImpactDisposition.textContent = "No governed impact";
      elements.interactionCandidateChange.textContent = "None";
      elements.workRevisionAdmissionStatus.textContent = "Not applicable";
      elements.workSatisfactionState.textContent = "NO_FOCUSED_WORK";
      elements.interactionRelationshipState.textContent = "OPEN";
      elements.workFocusHistory.textContent = "None";
      elements.workTransitionSummary.textContent = "None";
      elements.interactionDesignSchema.textContent = "Not selected";
      elements.interactionDesignSchemaRationale.textContent = "Not assessed";
      elements.interactionDesignStage.textContent = "Not established";
      elements.interactionDesignNextFocus.textContent = "Not established";
      elements.interactionDesignFocusRationale.textContent = "Not established";
      elements.interactionDesignStrategy.textContent = "Not established";
      elements.interactionDesignProgress.textContent = "No design process selected.";
      elements.readinessAffordance.textContent = "Not ready to form Work.";
      elements.interactionAdmission.hidden = true;
      elements.workRevisionAdmission.hidden = true;
      elements.workTransitionDecision.hidden = true;
      return;
    }
    renderInteractionStatus();
    const assessment = projection.latest_assessment;
    const readiness = projection.readiness;
    const status = readiness ? readiness.status : "NOT_READY";
    elements.interactionReadiness.textContent = status;
    elements.interactionReadiness.className = `status-badge ${status === "READY" ? "status-completed" : "status-draft"}`;
    const latestWattMessage = [...(projection.conversation_messages || [])]
      .reverse()
      .find((message) => message.actor === "WATT");
    elements.wattResponse.hidden = Boolean(
      latestWattMessage || state.streamingAssistantMessage,
    );
    elements.wattResponse.textContent = latestWattMessage
      ? latestWattMessage.content
      : assessment
        ? assessment.natural_response
        : "Watt has not completed an assessment for the latest message yet.";
    elements.interpretedMotive.textContent = projection.interpreted_motive || "Not established yet";
    elements.interpretedOutcome.textContent = projection.desired_outcome || "Not established yet";
    elements.interpretedContext.textContent = joined(projection.candidate_context, "None yet");
    elements.interpretedRequests.textContent = joined(projection.current_requests, "None yet");
    elements.interpretedConstraints.textContent = joined(projection.candidate_constraints, "None yet");
    elements.interpretedQuestions.textContent = joined(
      projection.unresolved_material_questions,
      status === "READY" ? "None" : "Assessment pending",
    );
    const governed = projection.governed_revision;
    const repositoryIdentity = governed
      ? governed.repository_identity
      : projection.candidate_repository_identity;
    const repositoryRef = governed
      ? governed.repository_ref
      : projection.candidate_repository_ref;
    elements.interactionResource.textContent = repositoryIdentity
      ? `${repositoryIdentity} · ${repositoryRef}`
      : "Not bound yet";
    elements.interactionScope.textContent = governed
      ? `Admitted scope ${governed.engineering_scope_id} · basis ${governed.scope_basis_fingerprint}`
      : projection.candidate_scope_summary || "Not bound yet";
    elements.governedUnderstanding.textContent = governed
      ? `Work ${governed.work_id} · Reality revision ${governed.revision_number} · Motive: ${governed.motive} · Outcome: ${governed.desired_outcome} · Constraints: ${joined(governed.constraints, "none")}`
      : "None — no Work exists";
    elements.currentWorkFocus.textContent = projection.current_work_focus || "No governed Work focus";
    elements.interactionFocusClassification.textContent = projection.focus_classification || "Not assessed";
    elements.interactionImpactDisposition.textContent = projection.impact_disposition || "No governed impact";
    const candidate = projection.candidate_change;
    elements.interactionCandidateChange.textContent = candidate
      ? `${joined(candidate.changed_fields, "change")} · Outcome: ${candidate.desired_outcome}`
      : "None";
    elements.workRevisionAdmissionStatus.textContent = projection.work_revision_admission_status || "NOT_APPLICABLE";
    elements.workSatisfactionState.textContent = projection.work_satisfaction_state || "NO_FOCUSED_WORK";
    elements.interactionRelationshipState.textContent = projection.interaction_relationship_state || projection.condition;
    elements.workFocusHistory.textContent = joined(projection.work_focus_history, "None");
    const transition = projection.latest_work_transition;
    elements.workTransitionSummary.textContent = transition
      ? `${transition.focus_classification} · ${transition.choice} · ${transition.reason}`
      : "None";
    elements.interactionDesignSchema.textContent = projection.selected_design_schema_identity
      ? `${projection.selected_design_schema_identity} v${projection.selected_design_schema_version}`
      : "Not selected";
    elements.interactionDesignSchemaRationale.textContent = projection.design_schema_selection_rationale
      || "Not assessed";
    elements.interactionDesignStage.textContent = projection.design_stage || "Not established";
    elements.interactionDesignNextFocus.textContent = projection.design_next_focus || "Not established";
    elements.interactionDesignFocusRationale.textContent = projection.design_focus_rationale
      || "Not established";
    elements.interactionDesignStrategy.textContent = projection.design_facilitation_strategy
      || "Not established";
    elements.interactionDesignProgress.textContent = projection.design_progress_narrative
      || "No design process selected.";
    elements.readinessAffordance.textContent = projection.new_work_formation_pending
      ? "New Work formation context is open. Continue the Interaction; no Work exists until Human admission."
      : projection.work_satisfaction_state === "CURRENTLY_SATISFIED"
        ? "This Work achieved its current objective. The Interaction remains open."
      : governed
        ? "Governed Work admitted. This Interaction remains open and focused on that Work."
      : status === "READY"
        ? "Ready to form Work. Review the candidate understanding, Resource, scope, and constraints before admitting."
        : "Not ready to form Work.";
    elements.interactionAdmission.hidden = status !== "READY" || Boolean(governed);
    elements.workRevisionAdmission.hidden = !(
      governed && projection.work_revision_admission_status === "PENDING_HUMAN"
    );
    elements.workTransitionDecision.hidden = !(
      transition && transition.choice === "PENDING_HUMAN"
    );
  }

  function renderChips(container, values, emptyLabel) {
    container.replaceChildren();
    if (!values || values.length === 0) {
      container.append(createElement("span", "chip", emptyLabel));
      return;
    }
    values.forEach((value) => container.append(createElement("span", "chip", value)));
  }

  function renderResources(work) {
    elements.resourceList.replaceChildren();
    const scope = work.engineering_scope;
    elements.technicalDetails.hidden = !scope;
    if (!scope) {
      return;
    }
    scope.resources.forEach((binding) => {
      elements.resourceList.append(
        createElement(
          "div",
          "resource-item",
          `${binding.resource_id} · ${binding.condition}`,
        ),
      );
    });
  }

  function setComposerExpanded(expanded) {
    elements.workForm.hidden = !expanded;
    elements.composerToggle.setAttribute("aria-expanded", String(expanded));
    elements.composerToggle.textContent = expanded
      ? "Collapse composer"
      : "Expand composer";
  }

  function restoreComposerExpanded() {
    try {
      const stored = localStorage.getItem(COMPOSER_EXPANDED_STORAGE_KEY);
      if (stored === "true" || stored === "false") {
        setComposerExpanded(stored === "true");
      }
    } catch (_error) {
      // Keep the markup default when browser storage is unavailable.
    }
  }

  function renderProductionPlan(work) {
    const plan = work.production_plan;
    elements.productionPlanPanel.hidden = !plan;
    elements.planSteps.replaceChildren();
    if (!plan) {
      return;
    }
    elements.planFit.textContent = plan.fit_classification;
    elements.planObjective.textContent = plan.objective;
    plan.ordered_steps.forEach((step) => {
      elements.planSteps.append(createElement("li", "", step.instruction));
    });
    elements.planVerification.textContent = plan.verification_approach;
    elements.planUnresolved.textContent = plan.unresolved_questions.length
      ? plan.unresolved_questions.join(" · ")
      : "None";
  }

  function renderCodeChangeContract(work) {
    const editable = ["DRAFT", "NEEDS_REFINEMENT", "AWAITING_APPROVAL"].includes(work.status);
    const isCodeWork = work.target_kind === "CODE_WORK";
    const contract = work.change_contract;
    elements.codeChangeContractPanel.hidden = !isCodeWork || !editable;
    elements.codeTargetShape.textContent = contract ? contract.target_shape : "UNRESOLVED";
    elements.codeExactTargets.value = contract
      ? contract.exact_targets.map((target) => target.path).join("\n")
      : "";
    elements.codeAllowedAreas.value = contract ? contract.allowed_areas.join("\n") : "";
    elements.codeForbiddenAreas.value = contract ? contract.forbidden_areas.join("\n") : "";
    elements.codeVerificationObligations.value = contract
      ? contract.verification_obligations.map((item) => item.identity).join("\n")
      : "PATH_SCOPE\nGIT_DIFF_CHECK";
  }

  function renderRepositoryChangeProposal(work) {
    const proposal = work.change_proposal;
    const contract = work.change_contract;
    const newline = String.fromCharCode(10);
    elements.codeAuthorityKind.textContent = contract
      ? "Admitted Code Change Contract"
      : "Code Change Proposal · Not Production Authority";
    if (!proposal || contract) {
      elements.codeProposalConfidence.textContent = contract ? "HUMAN ADMITTED" : "UNRESOLVED";
      elements.codeProposalRationale.textContent = "No proposal evidence.";
      elements.codeProposalSource.textContent = "UNRESOLVED";
      elements.codeConditionalTargets.textContent = "None";
      elements.codeProposalUnresolved.textContent = "None";
      return;
    }
    elements.codeTargetShape.textContent = "PROPOSAL";
    elements.codeExactTargets.value = proposal.proposed_targets
      .filter((target) => target.disposition === "REQUIRED")
      .map((target) => target.path)
      .join(newline);
    elements.codeAllowedAreas.value = proposal.allowed_areas.join(newline);
    elements.codeForbiddenAreas.value = proposal.forbidden_areas.join(newline);
    elements.codeVerificationObligations.value = proposal.verification_obligations
      .map((item) => item.identity)
      .join(newline);
    elements.codeProposalConfidence.textContent = proposal.confidence;
    elements.codeProposalRationale.textContent = proposal.rationale;
    elements.codeProposalSource.textContent =
      proposal.source_revision.slice(0, 12) + " · " + proposal.provenance.provider_identity;
    elements.codeConditionalTargets.textContent =
      proposal.proposed_targets
        .filter((target) => target.disposition === "CONDITIONAL")
        .map((target) => target.path + " — " + target.rationale)
        .join(" · ") || "None";
    elements.codeProposalUnresolved.textContent =
      proposal.unresolved_scope_questions.join(" · ") || "None";
  }

  function actionLabel(action) {
    const labels = {
      REFINE: "Refine Draft",
      APPROVE: "Approve",
      REJECT: "Reject",
      REQUEST_REFINEMENT: "Request Refinement",
      ADVANCE: "Advance One Step",
      AUTHORIZE: "Authorize",
    };
    return labels[action] || action.replaceAll("_", " ");
  }

  function renderWorkActions(work) {
    elements.workActions.replaceChildren();
    viewModel.workActions(work.status).forEach((action) => {
      const classes = ["action-button"];
      if (action === "APPROVE") {
        classes.push("emphasis");
      }
      if (action === "REJECT") {
        classes.push("danger");
      }
      const button = createElement("button", classes.join(" "), actionLabel(action));
      button.type = "button";
      button.dataset.mutation = action;
      button.addEventListener("click", () => performWorkAction(action));
      elements.workActions.append(button);
    });
    if (elements.workActions.childElementCount === 0) {
      elements.workActions.append(
        createElement("span", "empty-copy", "No direct action is available in this state."),
      );
    }
    elements.manualAdvanceControl.hidden = !viewModel.shouldPoll(work.status);
  }

  function renderAttention() {
    elements.attentionList.replaceChildren();
    elements.attentionSection.hidden = state.attention.length === 0;
    state.attention.forEach((attention) => {
      const card = createElement("article", "attention-card");
      card.append(createElement("h4", "", attention.decision));
      card.append(createElement("p", "", attention.reason));
      card.append(
        createElement("p", "subject-ref", attention.governed_subject_ref),
      );
      const actions = createElement("div", "action-row");
      attention.available_actions.forEach((action) => {
        const recommended = attention.recommended_action === action;
        const label = recommended ? `${actionLabel(action)} · Recommended` : actionLabel(action);
        const button = createElement(
          "button",
          recommended ? "action-button emphasis" : "action-button",
          label,
        );
        button.type = "button";
        button.dataset.mutation = action;
        button.addEventListener("click", () => resolveAttention(attention.attention_id, action));
        actions.append(button);
      });
      card.append(actions);
      elements.attentionList.append(card);
    });
  }

  function renderControlRoomFoundation(work) {
    const projection = viewModel.controlRoomProjection(
      work,
      state.interactions,
      state.attention,
    );
    elements.controlObjectiveMotive.textContent = projection.objective.motive;
    elements.controlObjectiveWork.textContent = projection.objective.currentWork;
    elements.controlObjectiveOutcome.textContent = projection.objective.desiredOutcome;
    elements.controlObjectiveSatisfaction.textContent = projection.objective.satisfaction;
    elements.controlStatusWork.textContent = projection.status.workStatus;
    elements.controlStatusPhase.textContent = projection.status.lifecyclePhase;
    elements.controlStatusActivity.textContent = projection.status.activity;
    elements.controlStatusCondition.textContent = projection.status.condition;
    elements.controlAttentionCard.classList.toggle(
      "requires-attention",
      projection.attention.required,
    );
    elements.controlAttentionState.textContent = projection.attention.state;
    elements.controlAttentionSummary.textContent = projection.attention.summary;
    elements.controlEmergingDirection.textContent = projection.attention.emergingDirection;
  }

  function renderUnderstandingAlignment(work) {
    const projection = viewModel.understandingAlignmentProjection(
      work,
      state.interactions,
    );
    elements.alignmentStatus.textContent = projection.status.label;
    elements.alignmentStatus.className = `status-badge ${projection.status.tone}`;
    elements.alignmentStatusBasis.textContent = projection.status.basis;
    elements.alignmentHumanSaid.replaceChildren();
    if (projection.human.statements.length) {
      projection.human.statements.forEach((statement) => {
        elements.alignmentHumanSaid.append(createElement("li", "", statement));
      });
    } else {
      elements.alignmentHumanSaid.append(
        createElement("li", "empty-copy", "No Human expression is available for this Work."),
      );
    }
    elements.alignmentInterpretationCurrency.textContent = projection.interpreted.currency;
    elements.alignmentInterpretedMotive.textContent = projection.interpreted.motive;
    elements.alignmentInterpretedOutcome.textContent = projection.interpreted.desiredOutcome;
    elements.alignmentGovernedRevision.textContent = projection.governed.revision;
    elements.alignmentGovernedMotive.textContent = projection.governed.motive;
    elements.alignmentGovernedOutcome.textContent = projection.governed.desiredOutcome;
    elements.alignmentUnderstoodObjective.textContent = projection.shared.understoodObjective;
    elements.alignmentConfirmedConstraints.textContent = joined(
      projection.shared.confirmedConstraints,
      "No confirmed constraints.",
    );
    elements.alignmentRelevantFacts.textContent = joined(
      projection.shared.relevantFacts,
      "No governed context facts.",
    );
    elements.alignmentUnresolvedQuestions.textContent = joined(
      projection.shared.unresolvedQuestions,
      "No unresolved material questions.",
    );
  }

  function renderProductionIntelligence(work) {
    const direction = viewModel.currentDirectionProjection(
      work,
      state.steering,
      state.attention,
    );
    elements.directionState.textContent = direction.available
      ? "Plan Reality available"
      : "Plan Reality unavailable";
    elements.directionState.className = direction.available
      ? "status-badge status-ready"
      : "status-badge status-draft";
    elements.directionRevision.textContent = direction.revision;
    elements.directionObjective.textContent = direction.direction;
    elements.directionCurrentStep.textContent = direction.currentStep;
    elements.directionNextStep.textContent = direction.nextStep;
    elements.directionRationale.textContent = direction.rationale;
    elements.directionRealityBasis.textContent = joined(
      direction.realityBasis,
      "No Reality references are available for the current direction.",
    );
    elements.directionCondition.textContent = direction.condition;

    const trust = viewModel.trustSummaryProjection(work, state.result);
    elements.trustSummaryState.textContent = trust.state;
    elements.trustSummaryState.className = trust.trustedRepository
      ? "trust-label trusted"
      : "trust-label";
    elements.trustCompletion.textContent = trust.completion;
    elements.trustVerification.textContent = trust.verification;
    elements.trustRuntimeCommit.textContent = trust.runtimeCommit;
    elements.trustBaseline.textContent = trust.trustedBaseline;
    elements.trustActiveRuntime.textContent = trust.activeRuntime;
    elements.trustBasis.textContent = trust.basis;
  }

  function renderGuidedDesign(work) {
    const design = work && work.guided_design;
    elements.guidedDesignPanel.hidden = !design;
    if (!design) {
      return;
    }
    elements.designReadiness.textContent = `Design ${design.readiness}`;
    elements.designReadiness.className = design.readiness === "READY"
      ? "status-badge status-ready"
      : "status-badge status-attention";
    elements.designObjective.textContent = design.process_objective;
    elements.designProcess.textContent = `${design.schema_identity} v${design.schema_version} · agenda revision ${design.agenda_revision_number}`;
    elements.designSchemaRationale.textContent = design.schema_selection_rationale;
    elements.designStage.textContent = design.current_stage;
    elements.designCurrentFocus.textContent = design.current_focus
      ? `${design.current_focus.title}: ${design.current_focus.objective}`
      : "No design issue is currently selected.";
    elements.designFocusRationale.textContent = design.focus_rationale
      || "Plan Steering has not recorded a focus rationale yet.";
    elements.designFacilitationStrategy.textContent = design.facilitation_strategy;
    elements.designFacilitationGuidance.textContent = design.facilitation_guidance;
    elements.designProgress.textContent = `${design.resolved_count} of ${design.total_applicable_count} agenda issues resolved or intentionally skipped`;
    elements.designProgressNarrative.textContent = design.progress_narrative;
    elements.designCompletedAreas.textContent = joined(
      design.completed_areas,
      "No design areas completed yet.",
    );
    elements.designUnresolvedAreas.textContent = joined(
      design.unresolved_areas,
      "No unresolved design areas.",
    );
    elements.designDependencyBlockers.textContent = joined(
      design.dependency_blockers,
      "No unresolved dependencies for the current focus.",
    );
    elements.designBlockers.textContent = joined(
      design.readiness_blockers,
      "No unresolved critical design blockers.",
    );
    elements.designUpcoming.textContent = design.upcoming_transition
      || "No next governed transition is known.";
    elements.designAgenda.replaceChildren();
    design.issues.forEach((issue) => {
      const item = createElement("li", `design-issue design-issue-${String(issue.state).toLowerCase()}`);
      const heading = createElement("strong", "", issue.title);
      const stateLabel = createElement("span", "design-issue-state", issue.state);
      const objective = createElement("p", "", issue.objective);
      const reason = issue.skip_rationale || issue.reopen_rationale || issue.why_it_matters;
      const rationale = createElement("p", "empty-copy", reason);
      item.append(heading, stateLabel, objective, rationale);
      elements.designAgenda.append(item);
    });
  }

  function renderResult() {
    const result = state.result;
    if (!result) {
      elements.trustedResult.textContent = "Not trusted yet";
      elements.trustedResult.classList.remove("trusted");
      elements.artifactSummary.textContent = "No artifacts observed.";
      elements.verificationSummary.textContent = "No verification evidence available.";
      elements.repositoryState.textContent = "No repository result yet.";
      elements.remainingRisk.textContent = "This Work has not completed.";
      return;
    }
    const activation = result.runtime_activation;
    const activeAtTrusted = activation
      && activation.state === "ACTIVE_AT_TRUSTED_BASELINE";
    elements.trustedResult.textContent = result.trusted_result
      ? activeAtTrusted
        ? "Trusted result · Active at trusted baseline"
        : "Trusted repository result · Runtime activation required"
      : "Not trusted yet";
    elements.trustedResult.classList.toggle("trusted", result.trusted_result);
    elements.artifactSummary.textContent = viewModel.artifactSummary(result);
    elements.verificationSummary.textContent = viewModel.verificationSummary(result);
    elements.repositoryState.textContent = activation
      ? (result.repository_state || "No repository result yet.") + " · " + activation.state
      : result.repository_state || "No repository result yet.";
    elements.remainingRisk.textContent = (
      activation && activation.state !== "ACTIVE_AT_TRUSTED_BASELINE"
        ? activation.reason
        : result.remaining_blocker_or_risk
    ) || "No remaining blocker reported.";
  }

  function renderSelectedWork() {
    const work = state.selectedWork;
    if (!work) {
      setSurface("empty");
      return;
    }
    setSurface("selected");
    elements.workTitle.textContent = viewModel.workTitle(work);
    elements.workStatus.textContent = viewModel.statusLabel(work.status);
    elements.workStatus.className = `status-badge ${viewModel.statusTone(work.status)}`;
    const progress = viewModel.executionProgress(work);
    elements.executionProgress.hidden = !progress;
    if (progress) {
      elements.executionProgress.classList.toggle("is-active", progress.stillWorking);
      elements.executionProgress.classList.toggle("is-blocked", Boolean(progress.blockedReason));
      elements.executionPhase.textContent = progress.phase;
      elements.executionActivity.textContent = progress.activity;
      elements.executionCount.textContent = progress.progressText;
      elements.executionElapsed.textContent = progress.elapsedText;
      elements.executionSignal.textContent = progress.activitySignal;
      elements.executionUpdated.textContent = progress.updatedAt
        ? `Last activity ${new Date(progress.updatedAt).toLocaleTimeString()}`
        : "Last activity time unavailable";
      elements.executionBlocked.hidden = !progress.blockedReason;
      elements.executionBlocked.textContent = progress.blockedReason || "";
    }
    elements.attentionMarker.hidden = !work.human_attention_required;
    renderControlRoomFoundation(work);
    renderUnderstandingAlignment(work);
    renderGuidedDesign(work);
    renderProductionIntelligence(work);
    elements.workRequest.textContent = work.raw_user_requirement || "No request text available.";
    elements.desiredOutcome.textContent = work.desired_outcome || "Not defined yet";
    elements.scopeSummary.textContent = work.engineering_scope
      ? work.engineering_scope.summary
      : "Not bound yet";
    const target = work.artifact_target;
    const codeContract = work.change_contract;
    elements.artifactOperation.textContent = codeContract
      ? `${codeContract.target_kind} · ${codeContract.target_shape}`
      : target
      ? `${target.operation} · ${target.confidence} confidence`
      : "Not proposed yet";
    elements.artifactRationale.textContent = codeContract
      ? "Exact files and bounded areas shown in the admitted Change Contract."
      : target
      ? target.placement_rationale
      : "No placement proposal yet";
    elements.artifactTargetPath.value = target ? target.path : "";
    elements.artifactTargetPanel.hidden = work.target_kind === "CODE_WORK" || ![
      "DRAFT",
      "NEEDS_REFINEMENT",
      "AWAITING_APPROVAL",
    ].includes(work.status);
    elements.recentEvent.textContent = work.most_recent_meaningful_event || "No production event yet";
    elements.nextAction.textContent = work.what_happens_next || "No next action reported";
    elements.currentStep.textContent = work.current_production_step || "WORK_INTAKE";
    renderChips(elements.constraintList, work.constraints, "No explicit constraints");
    renderChips(elements.tagList, work.tags, "No tags");
    renderProductionPlan(work);
    renderCodeChangeContract(work);
    renderRepositoryChangeProposal(work);
    renderResources(work);
    renderWorkActions(work);
    renderAttention();
    renderResult();
    scheduleObservationPolling();
  }

  function authorityIdentity() {
    const identity = elements.authorityIdentity.value.trim();
    if (!identity) {
      throw new ApiError(422, "INVALID_REQUEST", "Human authority identity is required.");
    }
    return identity;
  }

  async function performWorkAction(action) {
    if (state.busy || !state.selectedWorkId) {
      return;
    }
    hideNotice();
    setBusy(true);
    try {
      const workPath = `/api/works/${state.selectedWorkId}`;
      let response;
      if (action === "REFINE") {
        response = await apiRequest(`${workPath}/refine`, { method: "POST", body: {} });
      } else if (action === "ADVANCE") {
        response = await apiRequest(`${workPath}/advance`, { method: "POST" });
      } else {
        const endpoint = {
          APPROVE: "approve",
          REJECT: "reject",
          REQUEST_REFINEMENT: "request-refinement",
        }[action];
        response = await apiRequest(`${workPath}/${endpoint}`, {
          method: "POST",
          body: { authority_identity: authorityIdentity() },
        });
      }
      state.selectedWork = response;
      announce(`${viewModel.workTitle(response)} is now ${viewModel.statusLabel(response.status)}.`);
      await refreshAfterMutation();
    } catch (error) {
      showNotice(error);
    } finally {
      setBusy(false);
      renderSelectedWork();
    }
  }

  async function updateArtifactTarget() {
    if (state.busy || !state.selectedWorkId) {
      return;
    }
    const path = elements.artifactTargetPath.value.trim();
    if (!path) {
      showNotice(new ApiError(422, "INVALID_REQUEST", "Artifact Target is required."));
      return;
    }
    hideNotice();
    setBusy(true);
    try {
      state.selectedWork = await apiRequest(
        `/api/works/${state.selectedWorkId}/refine`,
        { method: "POST", body: { expected_artifact_path: path } },
      );
      await refreshAfterMutation();
      announce(`Artifact Target updated to ${path}.`);
    } catch (error) {
      showNotice(error);
    } finally {
      setBusy(false);
      renderSelectedWork();
    }
  }

  function nonEmptyLines(value) {
    return value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
  }

  function typedVerificationObligations(value) {
    return nonEmptyLines(value).map((identity) => {
      const separator = identity.indexOf(":");
      return separator < 0
        ? { kind: identity, target: null }
        : { kind: identity.slice(0, separator), target: identity.slice(separator + 1) };
    });
  }

  async function updateCodeChangeContract() {
    if (state.busy || !state.selectedWorkId) {
      return;
    }
    const body = {
      code_exact_targets: nonEmptyLines(elements.codeExactTargets.value),
      code_allowed_areas: nonEmptyLines(elements.codeAllowedAreas.value),
      code_forbidden_areas: nonEmptyLines(elements.codeForbiddenAreas.value),
      code_verification_obligations: typedVerificationObligations(
        elements.codeVerificationObligations.value,
      ),
    };
    if (!body.code_exact_targets.length && !body.code_allowed_areas.length) {
      showNotice(new ApiError(422, "INVALID_REQUEST", "At least one exact target or bounded area is required."));
      return;
    }
    hideNotice();
    setBusy(true);
    try {
      state.selectedWork = await apiRequest(
        `/api/works/${state.selectedWorkId}/refine`,
        { method: "POST", body },
      );
      await refreshAfterMutation();
      announce("Code Change Proposal updated for Human review.");
    } catch (error) {
      showNotice(error);
    } finally {
      setBusy(false);
      renderSelectedWork();
    }
  }

  async function resolveAttention(attentionId, action) {
    if (state.busy) {
      return;
    }
    hideNotice();
    setBusy(true);
    try {
      state.selectedWork = await apiRequest(`/api/attention/${attentionId}/resolve`, {
        method: "POST",
        body: {
          action,
          authority_identity: authorityIdentity(),
        },
      });
      announce(`${actionLabel(action)} recorded through governed authority.`);
      await refreshAfterMutation();
    } catch (error) {
      showNotice(error);
    } finally {
      setBusy(false);
      renderSelectedWork();
    }
  }

  async function loadHealth() {
    elements.healthLabel.textContent = "Checking";
    elements.healthDot.className = "health-dot health-unknown";
    try {
      await apiRequest("/health");
      elements.healthLabel.textContent = "Ready";
      elements.healthDot.className = "health-dot health-ready";
    } catch (error) {
      elements.healthLabel.textContent = error instanceof ApiError && error.status === 503
        ? "Degraded"
        : "Unavailable";
      elements.healthDot.className = error instanceof ApiError && error.status === 503
        ? "health-dot health-degraded"
        : "health-dot health-unavailable";
    }
  }

  async function loadCollections() {
    const [goals, works, interactions] = await Promise.all([
      apiRequest("/api/goals"),
      apiRequest("/api/works"),
      apiRequest("/api/interactions"),
    ]);
    state.goals = goals;
    state.works = works;
    state.interactions = interactions;
    const previousInteractionId = state.selectedInteractionId;
    if (!state.selectedInteractionId && !state.freshInteraction && interactions.length) {
      let stored = "";
      try {
        stored = localStorage.getItem(INTERACTION_STORAGE_KEY) || "";
      } catch (_error) {
        stored = "";
      }
      const selected = interactions.find((item) => item.interaction_id === stored)
        || interactions[0];
      state.selectedInteractionId = selected.interaction_id;
      state.sharedUnderstanding = selected;
    } else if (state.selectedInteractionId) {
      state.sharedUnderstanding = interactions.find(
        (item) => item.interaction_id === state.selectedInteractionId,
      ) || null;
    }
    if (state.selectedInteractionId !== previousInteractionId) {
      elements.workRequirement.value = state.drafts[state.selectedInteractionId || "new"] || "";
    }
    const latestTurns = (state.sharedUnderstanding && state.sharedUnderstanding.turns) || [];
    const active = latestTurns.find((turn) => turn.status !== "COMPLETED" && turn.status !== "FAILED");
    if (active && !state.activeInteractionTurnId && !state.finishingTurn) observeInteractionTurn(state.selectedInteractionId, active.turn_id);
    renderGoalList();
    renderWorkList();
    renderInteraction();
  }

  async function loadSteeringProjection(workId) {
    try {
      return await apiRequest(`/api/works/${workId}/steering`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return null;
      }
      throw error;
    }
  }

  async function refreshSelected() {
    if (!state.selectedWorkId) {
      state.selectedWork = null;
      state.attention = [];
      state.result = null;
      state.steering = null;
      renderSelectedWork();
      return;
    }
    const workId = state.selectedWorkId;
    const interactionId = state.selectedInteractionId;
    const [work, attention, result, steering] = await Promise.all([
      apiRequest(`/api/works/${workId}`),
      apiRequest(`/api/attention?work_id=${encodeURIComponent(workId)}`),
      apiRequest(`/api/works/${workId}/result`),
      loadSteeringProjection(workId),
    ]);
    if (state.selectedWorkId !== workId || state.selectedInteractionId !== interactionId) return;
    state.selectedWork = work;
    state.works = state.works.map((item) => item.work_id === workId ? work : item);
    renderWorkList();
    state.attention = attention;
    state.result = result;
    state.steering = steering;
    renderSelectedWork();
  }

  function scheduleObservationPolling() {
    if (state.pollTimer !== null) {
      globalThis.clearTimeout(state.pollTimer);
      state.pollTimer = null;
    }
    if (!state.selectedWork || !viewModel.shouldPoll(state.selectedWork.status)) {
      return;
    }
    state.pollTimer = globalThis.setTimeout(async () => {
      state.pollTimer = null;
      if (state.busy) {
        scheduleObservationPolling();
        return;
      }
      try {
        await loadCollections();
        await refreshSelected();
      } catch (error) {
        showNotice(error);
      } finally {
        scheduleObservationPolling();
      }
    }, POLL_INTERVAL_MS);
  }

  async function refreshAfterMutation() {
    await loadCollections();
    await refreshSelected();
  }

  async function selectWork(workId) {
    if (state.busy) {
      return;
    }
    state.selectedWorkId = workId;
    renderWorkList();
    setSurface("loading");
    try {
      await refreshSelected();
    } catch (error) {
      showNotice(error);
      setSurface("error");
      elements.globalErrorMessage.textContent = "The selected Work could not be loaded.";
    }
  }

  function selectGoal(goalId) {
    state.selectedGoalId = goalId;
    renderGoalList();
    renderWorkList();
  }

  async function reloadWorkspace() {
    if (state.busy) {
      return;
    }
    setBusy(true);
    hideNotice();
    try {
      try {
        const assets = await apiRequest("/api/repository-assets");
        const select = document.getElementById("admission-resource");
        const previous = select.value;
        select.replaceChildren(new Option("尚无仓库，先开始 Work 与设计", ""));
        for (const asset of assets) {
          if (asset.resource_id) select.add(new Option(asset.title + " · " + asset.repository_identity, asset.resource_id));
        }
        select.value = previous;
      } catch (_error) { /* Existing interaction remains available if asset listing fails. */ }
      await Promise.all([loadHealth(), loadCollections()]);
      if (state.selectedWorkId) {
        await refreshSelected();
      } else {
        setSurface("empty");
        renderInteraction();
      }
    } catch (error) {
      elements.globalErrorMessage.textContent = error instanceof ApiError
        ? error.message
        : "The service may be temporarily unavailable.";
      setSurface("error");
      showNotice(error);
    } finally {
      setBusy(false);
    }
  }

  async function createGoal(event) {
    event.preventDefault();
    if (state.busy) {
      return;
    }
    setBusy(true);
    hideNotice();
    try {
      const goal = await apiRequest("/api/goals", {
        method: "POST",
        body: { title: elements.goalTitle.value.trim() },
      });
      state.selectedGoalId = goal.goal_id;
      elements.goalTitle.value = "";
      elements.goalForm.hidden = true;
      await loadCollections();
      announce(`Goal ${goal.title} created.`);
    } catch (error) {
      showNotice(error);
    } finally {
      setBusy(false);
    }
  }

  function observationIsCurrent(interactionId, turnId) {
    return state.selectedInteractionId === interactionId && state.activeInteractionTurnId === turnId;
  }

  function stopTurnObservation() {
    if (state.interactionEventSource) state.interactionEventSource.close();
    state.interactionEventSource = null;
    state.activeInteractionTurnId = "";
    state.streamingAssistantMessage = null;
    state.finishingTurn = false;
    if (state.streamFrame !== null) globalThis.cancelAnimationFrame(state.streamFrame);
    state.streamFrame = null;
  }

  function pauseOutbox(interactionId) {
    state.outbox.forEach((item) => {
      if (item.interactionId === interactionId && item.status === "queued") item.status = "paused";
    });
    persistComposer();
  }

  async function finishInteractionTurn(interactionId, turnId, failure) {
    if (!observationIsCurrent(interactionId, turnId) || state.finishingTurn) return;
    state.finishingTurn = true;
    if (state.interactionEventSource) state.interactionEventSource.close();
    state.interactionEventSource = null;
    try {
      const projection = await apiRequest(`/api/interactions/${interactionId}`);
      if (!observationIsCurrent(interactionId, turnId)) return;
      const savedTurn = (projection.turns || []).find((turn) => turn.turn_id === turnId);
      if (!savedTurn || (savedTurn.status !== "COMPLETED" && savedTurn.status !== "FAILED")) {
        throw new ApiError(409, "TURN_SYNC_PENDING", "The saved reply is not available yet. Refresh to check again; waiting messages remain paused.");
      }
      state.sharedUnderstanding = projection;
      state.interactions = state.interactions.map((item) => item.interaction_id === interactionId ? projection : item);
      stopTurnObservation();
      if (failure || savedTurn.status === "FAILED") {
        pauseOutbox(interactionId);
        showNotice(new ApiError(409, (failure && failure.code) || savedTurn.failure_code || "TURN_FAILED", (failure && failure.message) || savedTurn.failure_message || "Watt could not complete this reply. Waiting messages are paused."));
      } else {
        announce("Watt completed the reply. You can continue the conversation.");
      }
      renderInteraction();
      state.selectedWorkId = projection.governed_work_id || "";
      if (state.selectedWorkId) {
        setSurface("selected");
        void refreshSelected().catch(showNotice);
      } else {
        state.selectedWork = null;
        setSurface("empty");
      }
      if (!failure && savedTurn.status === "COMPLETED") void drainOutbox();
    } catch (error) {
      if (!observationIsCurrent(interactionId, turnId)) return;
      stopTurnObservation();
      pauseOutbox(interactionId);
      renderInteraction();
      showNotice(error);
    }
  }

  async function pollInteractionTurn(interactionId, turnId) {
    let failures = 0;
    while (observationIsCurrent(interactionId, turnId) && !state.finishingTurn) {
      try {
        const turn = await apiRequest(`/api/interactions/${interactionId}/turns/${turnId}`);
        if (!observationIsCurrent(interactionId, turnId)) return;
        failures = 0;
        if (state.streamingAssistantMessage) state.streamingAssistantMessage.status = turn.status;
        scheduleStreamRender();
        if (turn.status === "COMPLETED" || turn.status === "FAILED") {
          await finishInteractionTurn(interactionId, turnId, turn.status === "FAILED"
            ? { code: turn.failure_code, message: turn.failure_message } : null);
          return;
        }
      } catch (error) {
        if (!observationIsCurrent(interactionId, turnId)) return;
        failures += 1;
        if (failures >= 3) {
          stopTurnObservation();
          pauseOutbox(interactionId);
          renderInteraction();
          showNotice(new ApiError(0, "CONNECTION_LOST", "Connection lost. Refresh to recover the reply. Waiting messages are paused and will not be resent."));
          return;
        }
      }
      await new Promise((resolve) => globalThis.setTimeout(resolve, failures ? 2000 * failures : 600));
    }
  }

  function observeInteractionTurn(interactionId, turnId) {
    if (state.selectedInteractionId !== interactionId) return;
    if (state.interactionEventSource) state.interactionEventSource.close();
    state.activeInteractionTurnId = turnId;
    state.streamingAssistantMessage = {
      turnId, content: "", status: "PROCESSING", createdAt: new Date().toISOString(),
    };
    renderInteraction();
    if (typeof globalThis.EventSource !== "function") {
      void pollInteractionTurn(interactionId, turnId);
      return;
    }
    const source = new globalThis.EventSource(`/api/interactions/${interactionId}/turns/${turnId}/events`);
    state.interactionEventSource = source;
    let streamed = "";
    const current = () => observationIsCurrent(interactionId, turnId) && state.interactionEventSource === source;
    source.addEventListener("turn.status", (event) => {
      if (!current()) return;
      state.streamingAssistantMessage.status = JSON.parse(event.data).status;
      scheduleStreamRender();
    });
    source.addEventListener("message.delta", (event) => {
      if (!current()) return;
      streamed += JSON.parse(event.data).delta;
      state.streamingAssistantMessage.content = streamed;
      scheduleStreamRender();
    });
    source.addEventListener("message.reset", (event) => {
      if (!current()) return;
      streamed = JSON.parse(event.data).content;
      state.streamingAssistantMessage.content = streamed;
      scheduleStreamRender();
    });
    source.addEventListener("message.completed", () => {
      if (current()) void finishInteractionTurn(interactionId, turnId, null);
    });
    source.addEventListener("turn.failed", (event) => {
      if (current()) void finishInteractionTurn(interactionId, turnId, JSON.parse(event.data));
    });
    source.onerror = () => {
      if (!current()) return;
      source.close();
      state.interactionEventSource = null;
      void pollInteractionTurn(interactionId, turnId);
    };
  }

  async function resumeOutbox(id) {
    const item = state.outbox.find((entry) => entry.id === id);
    if (!item || state.busy || state.sendInFlight) return;
    saveDraft();
    const previousId = state.selectedInteractionId;
    setBusy(true);
    try {
      const projection = item.interactionId ? await apiRequest(`/api/interactions/${item.interactionId}`) : null;
      if (previousId !== item.interactionId) pauseOutbox(previousId);
      stopTurnObservation();
      state.selectedInteractionId = item.interactionId;
      state.freshInteraction = !item.interactionId;
      state.sharedUnderstanding = projection;
      elements.workRequirement.value = state.drafts[item.interactionId || "new"] || "";
      const active = ((projection && projection.turns) || []).find((turn) => turn.status !== "COMPLETED" && turn.status !== "FAILED");
      if (item.status === "paused" && previousId === item.interactionId) {
        item.status = "queued";
        // Resume is an explicit decision to proceed even after a failed prior Turn.
        item.waitForTurnId = active ? active.turn_id : "";
      }
      try { localStorage.setItem(INTERACTION_STORAGE_KEY, item.interactionId); } catch (_error) { /* optional preference */ }
      persistComposer();
      if (active) observeInteractionTurn(item.interactionId, active.turn_id);
      renderInteraction();
      state.selectedWorkId = (projection && projection.governed_work_id) || "";
      setSurface(state.selectedWorkId ? "selected" : "empty");
      if (state.selectedWorkId) void refreshSelected().catch(showNotice);
    } catch (error) {
      showNotice(error);
    } finally {
      setBusy(false);
      void drainOutbox();
    }
  }

  async function continueInteraction(event) {
    event.preventDefault();
    if (state.busy) return;
    const content = elements.workRequirement.value.trim();
    if (!content) return;
    if (state.outbox.filter((item) => item.interactionId === state.selectedInteractionId).length >= 3 || state.outbox.length >= 12) {
      showNotice(new ApiError(409, "OUTBOX_FULL", "Up to three messages can wait per conversation. Cancel or send a waiting message first. Your draft is kept."));
      return;
    }
    const id = globalThis.crypto.randomUUID();
    state.outbox.push({ id, interactionId: state.selectedInteractionId, content, status: "queued", waitForTurnId: state.activeInteractionTurnId });
    elements.workRequirement.value = "";
    saveDraft();
    hideNotice();
    renderComposer();
    if (state.activeInteractionTurnId || state.sendInFlight || state.finishingTurn) announce("Message queued in this browser. Watt has not received it yet.");
    void drainOutbox();
  }

  async function drainOutbox() {
    if (state.busy || state.sendInFlight || state.activeInteractionTurnId || state.finishingTurn) return;
    const item = viewModel.nextInteractionOutboxItem(state.outbox, state.selectedInteractionId, state.sharedUnderstanding);
    if (!item) return;
    state.sendInFlight = true;
    item.status = "sending";
    persistComposer();
    renderComposer();
    let postStarted = false;
    let accepted = false;
    try {
      if (!item.interactionId) {
        const created = await apiRequest("/api/interactions", { method: "POST", body: { human_identity: "human:local-operator" } });
        state.selectedInteractionId = created.interaction_id;
        state.freshInteraction = false;
        state.sharedUnderstanding = created;
        state.outbox.forEach((entry) => { if (!entry.interactionId) entry.interactionId = created.interaction_id; });
        state.drafts[created.interaction_id] = state.drafts.new || "";
        delete state.drafts.new;
        try { localStorage.setItem(INTERACTION_STORAGE_KEY, created.interaction_id); } catch (_error) { /* optional preference */ }
        persistComposer();
      }
      const interactionId = item.interactionId;
      postStarted = true;
      const turn = await apiRequest(`/api/interactions/${state.selectedInteractionId}/turns`, {
        method: "POST", body: { content: item.content, human_identity: "human:local-operator" },
      });
      accepted = true;
      // Only a successful receipt removes browser intent and adds persisted input.
      state.outbox = state.outbox.filter((entry) => entry.id !== item.id);
      state.outbox.forEach((entry) => {
        if (entry.interactionId === interactionId && entry.status === "queued") entry.waitForTurnId = turn.turn_id;
      });
      persistComposer();
      state.sharedUnderstanding = {
        ...state.sharedUnderstanding,
        conversation_messages: [
          ...viewModel.interactionConversationMessages(state.sharedUnderstanding, null),
          { actor: "HUMAN", turn_id: turn.turn_id, content: item.content, interaction_record_id: turn.request_record_id, processing_status: turn.status, created_at: turn.created_at },
        ],
      };
      observeInteractionTurn(interactionId, turn.turn_id);
      announce("Message received. No Work was created; Watt is preparing the reply.");
      const receivedProjection = await apiRequest(`/api/interactions/${interactionId}`);
      if (observationIsCurrent(interactionId, turn.turn_id) && !state.finishingTurn) state.sharedUnderstanding = receivedProjection;
    } catch (error) {
      if (!accepted) {
        item.status = postStarted && !(error instanceof ApiError && error.status >= 400 && error.status < 500) ? "uncertain" : "paused";
        pauseOutbox(item.interactionId);
      }
      showNotice(error);
    } finally {
      state.sendInFlight = false;
      persistComposer();
      renderInteraction();
      // A reply can finish before the acknowledgement's projection request does.
      if (accepted) void drainOutbox();
    }
  }

  async function admitInteractionWork() {
    const projection = state.sharedUnderstanding;
    const assessment = projection && projection.latest_assessment;
    if (state.busy || !projection || !assessment || !projection.readiness) {
      return;
    }
    const identity = elements.interactionAuthorityIdentity.value.trim();
    if (!identity) {
      showNotice(new ApiError(422, "INVALID_REQUEST", "Human authority identity is required."));
      return;
    }
    hideNotice();
    setBusy(true);
    try {
      state.sharedUnderstanding = await apiRequest(
        `/api/interactions/${projection.interaction_id}/admit-work`,
        {
          method: "POST",
          body: {
            engineering_resource_id: document.getElementById("admission-resource").value || null,
            assessment_id: assessment.assessment_id,
            basis_fingerprint: assessment.basis_fingerprint,
            authority_identity: identity,
          },
        },
      );
      state.selectedWorkId = state.sharedUnderstanding.governed_work_id;
      await loadCollections();
      await refreshSelected();
      setSurface("selected");
      renderInteraction();
      announce("Governed long-lived Work admitted. Automatic Steering activation started.");
    } catch (error) {
      showNotice(error);
    } finally {
      setBusy(false);
      renderInteraction();
      renderSelectedWork();
    }
  }

  async function decideWorkRevision(action) {
    const projection = state.sharedUnderstanding;
    const assessment = projection && projection.latest_assessment;
    const governed = projection && projection.governed_revision;
    if (state.busy || !projection || !assessment || !governed) {
      return;
    }
    const identity = elements.workRevisionAuthorityIdentity.value.trim();
    if (!identity) {
      showNotice(new ApiError(422, "INVALID_REQUEST", "Human authority identity is required."));
      return;
    }
    hideNotice();
    setBusy(true);
    try {
      state.sharedUnderstanding = await apiRequest(
        `/api/interactions/${projection.interaction_id}/work-revision-decisions`,
        {
          method: "POST",
          body: {
            assessment_id: assessment.assessment_id,
            basis_fingerprint: assessment.basis_fingerprint,
            expected_previous_revision_id: governed.revision_id,
            action,
            authority_identity: identity,
          },
        },
      );
      await loadCollections();
      await refreshSelected();
      renderInteraction();
      announce(action === "APPROVE"
        ? "Work Reality revision admitted. Existing Plan Steering reassessment scheduled."
        : "Human decision recorded. Governed Work remains unchanged.");
    } catch (error) {
      showNotice(error);
    } finally {
      setBusy(false);
      renderInteraction();
      renderSelectedWork();
    }
  }

  async function decideWorkTransition(choice) {
    const projection = state.sharedUnderstanding;
    const transition = projection && projection.latest_work_transition;
    if (state.busy || !projection || !transition) {
      return;
    }
    const identity = elements.workTransitionAuthorityIdentity.value.trim();
    if (!identity) {
      showNotice(new ApiError(422, "INVALID_REQUEST", "Human authority identity is required."));
      return;
    }
    hideNotice();
    setBusy(true);
    try {
      state.sharedUnderstanding = await apiRequest(
        "/api/interactions/" + projection.interaction_id + "/work-transition-decisions",
        {
          method: "POST",
          body: {
            transition_id: transition.transition_id,
            expected_originating_work_id: transition.originating_work_id,
            choice,
            authority_identity: identity,
          },
        },
      );
      state.selectedWorkId = state.sharedUnderstanding.governed_work_id || "";
      await loadCollections();
      if (state.selectedWorkId) {
        await refreshSelected();
        setSurface("selected");
      } else {
        state.selectedWork = null;
        setSurface("empty");
      }
      renderInteraction();
      announce(choice === "START_NEW_WORK"
        ? "New Work formation context started. No Work or production authority was created."
        : "Work transition choice recorded. Existing governed Work remains unchanged.");
    } catch (error) {
      showNotice(error);
    } finally {
      setBusy(false);
      renderInteraction();
      renderSelectedWork();
    }
  }

  function beginNewInteraction() {
    if (state.busy || state.sendInFlight) return;
    saveDraft();
    pauseOutbox(state.selectedInteractionId);
    stopTurnObservation();
    state.selectedInteractionId = "";
    state.freshInteraction = true;
    state.sharedUnderstanding = null;
    state.selectedWorkId = "";
    elements.workRequirement.value = state.drafts.new || "";
    try { localStorage.removeItem(INTERACTION_STORAGE_KEY); } catch (_error) { /* optional preference */ }
    setSurface("empty");
    renderInteraction();
    elements.workRequirement.focus();
  }

  function consumeNewWorkEntry() {
    const url = new URL(globalThis.location.href);
    if (url.searchParams.get("new") !== "1") return;
    state.selectedInteractionId = "";
    state.freshInteraction = true;
    state.sharedUnderstanding = null;
    state.selectedWorkId = "";
    try { localStorage.removeItem(INTERACTION_STORAGE_KEY); } catch (_error) { /* optional preference */ }
    url.searchParams.delete("new");
    globalThis.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  }

  elements.showGoalForm.addEventListener("click", () => {
    elements.goalForm.hidden = !elements.goalForm.hidden;
    if (!elements.goalForm.hidden) {
      elements.goalTitle.focus();
    }
  });
  elements.goalForm.addEventListener("submit", createGoal);
  elements.workForm.addEventListener("submit", continueInteraction);
  elements.workRequirement.addEventListener("input", saveDraft);
  globalThis.addEventListener("beforeunload", (event) => {
    if (!state.storageAvailable && (state.outbox.length || elements.workRequirement.value)) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
  elements.admitWorkControl.addEventListener("click", admitInteractionWork);
  elements.approveWorkRevision.addEventListener("click", () => decideWorkRevision("APPROVE"));
  elements.rejectWorkRevision.addEventListener("click", () => decideWorkRevision("REJECT"));
  elements.refineWorkRevision.addEventListener("click", () => decideWorkRevision("REQUEST_REFINEMENT"));
  elements.continueCurrentWork.addEventListener("click", () => decideWorkTransition("CONTINUE_CURRENT_WORK"));
  elements.startNewWork.addEventListener("click", () => decideWorkTransition("START_NEW_WORK"));
  elements.dismissWorkTransition.addEventListener("click", () => decideWorkTransition("DISMISSED"));
  elements.newInteractionControl.addEventListener("click", beginNewInteraction);
  elements.composerToggle.addEventListener("click", () => {
    const expanded = elements.composerToggle.getAttribute("aria-expanded") === "true";
    const nextExpanded = !expanded;
    setComposerExpanded(nextExpanded);
    try {
      localStorage.setItem(COMPOSER_EXPANDED_STORAGE_KEY, String(nextExpanded));
    } catch (_error) {
      // The in-page toggle still works when browser storage is unavailable.
    }
  });
  elements.statusFilter.addEventListener("change", () => {
    state.statusFilter = elements.statusFilter.value;
    renderWorkList();
  });
  elements.refreshControl.addEventListener("click", reloadWorkspace);
  elements.workRefreshControl.addEventListener("click", async () => {
    if (state.busy) {
      return;
    }
    setBusy(true);
    try {
      await refreshSelected();
      announce("Selected Work refreshed.");
    } catch (error) {
      showNotice(error);
    } finally {
      setBusy(false);
    }
  });
  elements.manualAdvanceControl.addEventListener(
    "click",
    () => performWorkAction("ADVANCE"),
  );
  elements.saveArtifactTarget.addEventListener("click", updateArtifactTarget);
  elements.saveCodeChangeContract.addEventListener("click", updateCodeChangeContract);
  elements.retryControl.addEventListener("click", reloadWorkspace);
  elements.healthControl.addEventListener("click", loadHealth);
  elements.dismissNotice.addEventListener("click", hideNotice);

  restoreComposer();
  restoreComposerExpanded();
  consumeNewWorkEntry();
  reloadWorkspace();
})();
