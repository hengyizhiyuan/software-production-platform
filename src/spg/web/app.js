(function startControlRoom() {
  "use strict";

  const viewModel = globalThis.SPGViewModel;
  if (!viewModel) {
    return;
  }

  const POLL_INTERVAL_MS = 2000;
  const state = {
    goals: [],
    works: [],
    selectedGoalId: "",
    selectedWorkId: "",
    selectedWork: null,
    attention: [],
    result: null,
    statusFilter: "",
    busy: false,
    pollTimer: null,
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
    selectedWork: document.getElementById("selected-work"),
    workTitle: document.getElementById("work-title"),
    workStatus: document.getElementById("work-status"),
    attentionMarker: document.getElementById("attention-marker"),
    workRequest: document.getElementById("work-request"),
    desiredOutcome: document.getElementById("desired-outcome"),
    scopeSummary: document.getElementById("scope-summary"),
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
    workRequirement: document.getElementById("work-requirement"),
    composerGoal: document.getElementById("composer-goal"),
    workTags: document.getElementById("work-tags"),
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

  function renderGoalOptions() {
    const selected = elements.composerGoal.value || state.selectedGoalId;
    elements.composerGoal.replaceChildren();
    const noGoal = createElement("option", "", "No Goal");
    noGoal.value = "";
    elements.composerGoal.append(noGoal);
    state.goals.forEach((goal) => {
      const option = createElement("option", "", goal.title);
      option.value = goal.goal_id;
      elements.composerGoal.append(option);
    });
    elements.composerGoal.value = state.goals.some((goal) => goal.goal_id === selected)
      ? selected
      : "";
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
    elements.trustedResult.textContent = result.trusted_result
      ? "Trusted result"
      : "Not trusted yet";
    elements.trustedResult.classList.toggle("trusted", result.trusted_result);
    elements.artifactSummary.textContent = viewModel.artifactSummary(result);
    elements.verificationSummary.textContent = viewModel.verificationSummary(result);
    elements.repositoryState.textContent = result.repository_state || "No repository result yet.";
    elements.remainingRisk.textContent = result.remaining_blocker_or_risk || "No remaining blocker reported.";
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
    elements.attentionMarker.hidden = !work.human_attention_required;
    elements.workRequest.textContent = work.raw_user_requirement || "No request text available.";
    elements.desiredOutcome.textContent = work.desired_outcome || "Not defined yet";
    elements.scopeSummary.textContent = work.engineering_scope
      ? work.engineering_scope.summary
      : "Not bound yet";
    elements.recentEvent.textContent = work.most_recent_meaningful_event || "No production event yet";
    elements.nextAction.textContent = work.what_happens_next || "No next action reported";
    elements.currentStep.textContent = work.current_production_step || "WORK_INTAKE";
    renderChips(elements.constraintList, work.constraints, "No explicit constraints");
    renderChips(elements.tagList, work.tags, "No tags");
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
    const [goals, works] = await Promise.all([
      apiRequest("/api/goals"),
      apiRequest("/api/works"),
    ]);
    state.goals = goals;
    state.works = works;
    renderGoalList();
    renderGoalOptions();
    renderWorkList();
  }

  async function refreshSelected() {
    if (!state.selectedWorkId) {
      state.selectedWork = null;
      state.attention = [];
      state.result = null;
      renderSelectedWork();
      return;
    }
    const workId = state.selectedWorkId;
    const [work, attention, result] = await Promise.all([
      apiRequest(`/api/works/${workId}`),
      apiRequest(`/api/attention?work_id=${encodeURIComponent(workId)}`),
      apiRequest(`/api/works/${workId}/result`),
    ]);
    state.selectedWork = work;
    state.attention = attention;
    state.result = result;
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
    elements.composerGoal.value = goalId;
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
      await Promise.all([loadHealth(), loadCollections()]);
      if (state.selectedWorkId) {
        await refreshSelected();
      } else if (filteredWorks().length > 0) {
        state.selectedWorkId = filteredWorks()[0].work_id;
        await refreshSelected();
      } else {
        setSurface("empty");
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
      elements.composerGoal.value = goal.goal_id;
      announce(`Goal ${goal.title} created.`);
    } catch (error) {
      showNotice(error);
    } finally {
      setBusy(false);
    }
  }

  async function createWork(event) {
    event.preventDefault();
    if (state.busy) {
      return;
    }
    const requirement = elements.workRequirement.value;
    setBusy(true);
    hideNotice();
    try {
      const body = {
        requirement,
        goal_id: elements.composerGoal.value || null,
        tags: viewModel.splitTags(elements.workTags.value),
      };
      let work = await apiRequest("/api/works", { method: "POST", body });
      state.selectedWorkId = work.work_id;
      state.statusFilter = "";
      elements.statusFilter.value = "";
      elements.workRequirement.value = "";
      elements.workTags.value = "";
      try {
        work = await apiRequest(`/api/works/${work.work_id}/refine`, {
          method: "POST",
          body: {},
        });
      } catch (refinementError) {
        showNotice(refinementError);
      }
      state.selectedWork = work;
      await refreshAfterMutation();
      announce(`${viewModel.workTitle(work)} created as a governed Work.`);
    } catch (error) {
      showNotice(error);
    } finally {
      setBusy(false);
      renderSelectedWork();
    }
  }

  elements.showGoalForm.addEventListener("click", () => {
    elements.goalForm.hidden = !elements.goalForm.hidden;
    if (!elements.goalForm.hidden) {
      elements.goalTitle.focus();
    }
  });
  elements.goalForm.addEventListener("submit", createGoal);
  elements.workForm.addEventListener("submit", createWork);
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
  elements.retryControl.addEventListener("click", reloadWorkspace);
  elements.healthControl.addEventListener("click", loadHealth);
  elements.dismissNotice.addEventListener("click", hideNotice);

  reloadWorkspace();
})();
