(function () {
  "use strict";

  const STEP_NAMES = {
    DESIGN: "Design", PRODUCTION: "Produce", PRODUCE: "Produce",
    VERIFICATION: "Verify", VERIFY: "Verify", DELIVERY: "Deliver", DELIVER: "Deliver",
    UNDERSTANDING: "Understand", WORK_ADMISSION: "Understand",
  };
  function stepName(step) {
    if (!step) return "";
    return step.objective || STEP_NAMES[step.type] || String(step.type || "Step").replaceAll("_", " ");
  }
  function agendaSteps(steering) {
    if (!steering) return [];
    return [
      ...(steering.completed_steps || []).map((step) => ({ label: stepName(step), state: "DONE", key: step.step_id })),
      ...(steering.current_step ? [{ label: stepName(steering.current_step), state: "CURRENT", key: steering.current_step.step_id }] : []),
      ...(steering.known_next_steps || []).map((step) => ({ label: stepName(step), state: "NEXT", key: step.step_id })),
    ];
  }
  const MILESTONE_TYPES = {
    REFINE: ["Understand", "understand"],
    HUMAN_DECISION: ["Shape direction", "direction"],
    DESIGN: ["Shape solution", "design"],
    PRODUCE: ["Produce", "production"],
    VERIFY_ACCEPT: ["Verify", "verification"],
    COMPLETE: ["Deliver", "delivery"],
  };
  function agendaMilestones(steering) {
    if (!steering) return [];
    const source = [
      ...(steering.completed_steps || []).map((step) => ({ step, state: "DONE" })),
      ...(steering.current_step ? [{ step: steering.current_step, state: "CURRENT" }] : []),
      ...(steering.known_next_steps || []).map((step) => ({ step, state: "NEXT" })),
    ];
    const milestones = [];
    source.forEach(({ step, state }) => {
      const type = String(step.type || "").toUpperCase();
      const [label, category] = MILESTONE_TYPES[type] || [stepName(step), `step:${step.step_id || type}`];
      let current = milestones[milestones.length - 1];
      if (!current || current.category !== category) {
        current = { label, category, state: "NEXT", steps: [] };
        milestones.push(current);
      }
      current.steps.push({ label: stepName(step), state, key: step.step_id });
      const states = current.steps.map((item) => item.state);
      current.state = states.every((item) => item === "DONE") ? "DONE"
        : states.every((item) => item === "NEXT") ? "NEXT" : "CURRENT";
    });
    return milestones;
  }
  function currentProductionQueue(work, queue) {
    const entries = Array.isArray(queue) ? queue : [];
    const revisionId = work?.current_work_reality_revision_id;
    if (!revisionId || !entries.some((entry) => entry.work_reality_revision_id)) {
      return entries;
    }
    return entries.filter(
      (entry) => entry.work_reality_revision_id === revisionId,
    );
  }
  function productionState(work, queue, attempt, attentionItems = []) {
    const currentQueue = currentProductionQueue(work, queue);
    const entry = currentQueue.length ? currentQueue[currentQueue.length - 1] : null;
    const revisionScopedQueue = Array.isArray(queue)
      && queue.some((item) => item.work_reality_revision_id);
    const attemptIsCurrent = Boolean(entry) || !revisionScopedQueue;
    const mode = attemptIsCurrent ? attempt?.state?.runtime_mode : null;
    const terminalOutcome = attemptIsCurrent ? attempt?.state?.terminal_outcome : null;
    const candidateReady = Array.isArray(attentionItems) && attentionItems.some(
      (item) => (!item.work_id || item.work_id === work?.work_id)
        && item.kind === "CANDIDATE_AUTHORIZATION"
        && Array.isArray(item.available_actions)
        && item.available_actions.includes("AUTHORIZE"),
    );
    // Completion owns whether production yielded a reviewable Candidate.  Keep
    // the Executor's terminal outcome in evidence, but do not let it overwrite
    // the later, authoritative completion/attention state shown to the Human.
    if (candidateReady) {
      return { state: "FINISHED", detail: "Candidate ready for preview and authorization." };
    }
    if (mode === "RECOVERING" || mode === "RESUME_REQUESTED") return { state: "RECOVERING", detail: "Restoring execution from retained state." };
    if (mode === "FAILED") return { state: "FAILED", detail: "Execution stopped with a failure." };
    if (mode === "FINISHED" && terminalOutcome === "UNABLE_TO_COMPLETE") {
      const transportFailures = (attempt?.steps || []).filter(
        (step) => step?.result_payload?.error_type === "InferenceTransportUnknown",
      ).length;
      const providerDecision = [...(attempt?.steps || [])].reverse().find(
        (step) => step?.result_payload?.action === "UNABLE_TO_COMPLETE",
      );
      return {
        state: "FAILED",
        detail: transportFailures > 1
          ? `Provider response failed after ${transportFailures - 1} automatic retries.`
          : providerDecision
            ? "Execution finished with unresolved obligations. Review the recorded evidence before retrying."
            : "Provider did not return a usable completion decision.",
      };
    }
    if (mode === "PAUSED") return { state: "BLOCKED", detail: "Execution is paused." };
    if (entry) {
      if (entry.progression_state === "INFRASTRUCTURE_UNAVAILABLE") {
        return {
          state: "RECOVERING",
          detail: entry.progression_reason || "Execution infrastructure is unavailable. Watt will recover automatically.",
        };
      }
      if (entry.progression_state === "SCHEDULING" && ["QUEUED", "RETURNED_TO_QUEUE"].includes(entry.condition)) {
        return {
          state: "PREPARING",
          detail: entry.progression_reason || "Watt is assigning available execution capacity.",
        };
      }
      if (entry.progression_state === "CAPACITY_WAIT") {
        return {
          state: "QUEUED",
          detail: "Waiting for execution capacity.",
        };
      }
      if (
        entry.condition === "WAITING_RESOURCE"
        && /provider_transport|transport failed|incompleteread|remotedisconnected|timed? ?out/i.test(entry.wait_reason || "")
      ) {
        const retry = Math.min(Number(entry.resume_count || 1), 3);
        return {
          state: "RETRYING PROVIDER",
          detail: `Provider response was interrupted. Retrying automatically from the last checkpoint (${retry}/3).`,
        };
      }
      const map = {
        QUEUED: ["QUEUED", "Waiting for execution capacity."],
        WAITING_RESOURCE: ["WAITING FOR CAPACITY", entry.wait_reason || "Waiting for a suitable worker."],
        WAITING_HUMAN: ["WAITING FOR HUMAN", entry.wait_reason || "A Human decision is needed."],
        ALLOCATED: ["PREPARING", "Capacity allocated; execution is starting."],
        EXECUTING: ["RUNNING", "The executor is working on the current task."],
        CHECKPOINTED: ["RUNNING", "Progress was saved at a checkpoint."],
        RETURNED_TO_QUEUE: ["QUEUED", "Execution will continue in a later slice."],
        COMPLETED: ["FINISHED", "The execution attempt completed."],
        CANCELLED: ["BLOCKED", "The execution attempt was cancelled."],
      };
      if (map[entry.condition]) return { state: map[entry.condition][0], detail: map[entry.condition][1] };
    }
    if (["ACTIVE", "WAITING_PRODUCTION"].includes(work?.automatic_progression_state)) {
      return {
        state: "PREPARING",
        detail: work.what_happens_next || "Watt is preparing the next production cycle.",
      };
    }
    if (work?.automatic_progression_state === "STOPPED" && work?.last_stop_reason === "BLOCKED") {
      return {
        state: "STOPPED",
        detail: work.what_happens_next || "The current production cycle could not be prepared.",
      };
    }
    if (work?.execution_progress?.blocked_reason) return { state: "BLOCKED", detail: work.execution_progress.blocked_reason };
    if (work?.execution_progress?.still_working) return { state: "RUNNING", detail: work.execution_progress.activity || "Production is active." };
    if (work?.work_complete || work?.status === "COMPLETED") return { state: "FINISHED", detail: "Current production is complete." };
    if (work?.status === "NEEDS_ATTENTION") {
      const actionable = humanActionProjection(work, attentionItems).required;
      return actionable
        ? { state: "WAITING FOR HUMAN", detail: work.what_happens_next || "A Human decision is needed before production can continue." }
        : { state: "BLOCKED", detail: work.what_happens_next || "Production cannot progress; no Human action is available in this Work." };
    }
    if (work?.status === "BLOCKED" || work?.status === "FAILED") return { state: work.status, detail: work.most_recent_meaningful_event || "Production needs attention." };
    return { state: "IDLE", detail: "No execution is active." };
  }

  function createViewer({ document, loadFile }) {
    const root = document.getElementById("inspection-window");
    const tabs = document.getElementById("inspection-tabs");
    const content = document.getElementById("inspection-content");
    const pathLabel = document.getElementById("inspection-path");
    const search = document.getElementById("inspection-search");
    const viewButton = document.getElementById("inspection-view");
    const files = new Map();
    let active = null;
    let sourceMode = false;
    function node(tag, text, className) {
      const item = document.createElement(tag);
      if (text != null) item.textContent = text;
      if (className) item.className = className;
      return item;
    }
    function appendCodeLine(parent, line, number) {
      const row = node("div", null, "inspection-code-line");
      row.append(node("span", String(number), "inspection-line-number"));
      const code = node("span", null, "inspection-line-text");
      const pattern = /\b(class|def|return|const|let|function|if|else|for|while|import|from|async|await|SELECT|CREATE|TABLE)\b/g;
      let cursor = 0;
      for (const match of line.matchAll(pattern)) {
        code.append(document.createTextNode(line.slice(cursor, match.index)));
        code.append(node("span", match[0], "inspection-token"));
        cursor = match.index + match[0].length;
      }
      code.append(document.createTextNode(line.slice(cursor)));
      row.append(code);
      parent.append(row);
    }
    function renderSource(text, lineNumbers) {
      const block = node("div", null, "inspection-code");
      text.split("\n").forEach((line, index) => {
        if (lineNumbers) appendCodeLine(block, line, index + 1);
        else block.append(node("div", line || "\u00a0", "inspection-source-line"));
      });
      content.append(block);
    }
    function appendInline(parent, text) {
      const token = /(\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\))/g;
      let cursor = 0;
      for (const match of text.matchAll(token)) {
        parent.append(document.createTextNode(text.slice(cursor, match.index)));
        if (match[2]) parent.append(node("strong", match[2]));
        else if (match[3]) parent.append(node("em", match[3]));
        else if (match[4]) parent.append(node("code", match[4]));
        else {
          const label = match[5];
          const target = match[6];
          if (/^https?:\/\//i.test(target)) {
            const link = node("a", label);
            link.href = target;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            parent.append(link);
          } else parent.append(node("span", label, "inspection-relative-link"));
        }
        cursor = match.index + match[0].length;
      }
      parent.append(document.createTextNode(text.slice(cursor)));
    }
    function renderMarkdown(text) {
      const lines = text.split("\n");
      let index = 0;
      while (index < lines.length) {
        const line = lines[index];
        if (!line.trim()) { index += 1; continue; }
        if (/^```/.test(line)) {
          const block = node("pre", null, "inspection-markdown-code");
          index += 1;
          const code = [];
          while (index < lines.length && !/^```/.test(lines[index])) code.push(lines[index++]);
          block.append(node("code", code.join("\n")));
          content.append(block);
          index += 1;
          continue;
        }
        const heading = /^(#{1,6})\s+(.+)$/.exec(line);
        if (heading) { const title = node(`h${heading[1].length}`); appendInline(title, heading[2]); content.append(title); index += 1; continue; }
        if (/^\s*[-*+]\s+/.test(line) || /^\s*\d+\.\s+/.test(line)) {
          const ordered = /^\s*\d+\./.test(line);
          const list = node(ordered ? "ol" : "ul");
          while (index < lines.length && (ordered ? /^\s*\d+\.\s+/.test(lines[index]) : /^\s*[-*+]\s+/.test(lines[index]))) {
            const item = node("li");
            appendInline(item, lines[index++].replace(/^\s*(?:[-*+]|\d+\.)\s+/, ""));
            list.append(item);
          }
          content.append(list);
          continue;
        }
        if (/^\|.+\|\s*$/.test(line) && /^\|?[\s:|-]+\|\s*$/.test(lines[index + 1] || "")) {
          const table = node("table");
          const header = node("tr");
          line.split("|").slice(1, -1).forEach((cell) => { const item = node("th"); appendInline(item, cell.trim()); header.append(item); });
          table.append(header); index += 2;
          while (index < lines.length && /^\|.+\|\s*$/.test(lines[index])) {
            const row = node("tr");
            lines[index++].split("|").slice(1, -1).forEach((cell) => { const item = node("td"); appendInline(item, cell.trim()); row.append(item); });
            table.append(row);
          }
          content.append(table);
          continue;
        }
        const paragraph = [];
        while (index < lines.length && lines[index].trim() && !/^(#{1,6}\s|```|\s*[-*+]\s|\s*\d+\.\s)/.test(lines[index])) paragraph.push(lines[index++]);
        if (paragraph.length) { const item = node("p"); appendInline(item, paragraph.join(" ")); content.append(item); }
        else index += 1;
      }
    }
    function render() {
      tabs.replaceChildren(); content.replaceChildren();
      for (const [key, file] of files) {
        const tab = node("div", null, "inspection-tab");
        tab.setAttribute("role", "tab");
        tab.setAttribute("aria-selected", String(key === active));
        const select = node("button", file.path.split("/").pop());
        select.type = "button"; select.addEventListener("click", () => { active = key; search.value = ""; render(); });
        const close = node("button", "×");
        close.type = "button"; close.setAttribute("aria-label", `Close ${file.path}`);
        close.addEventListener("click", () => {
          files.delete(key);
          if (active === key) active = files.size ? [...files.keys()].at(-1) : null;
          if (!files.size) root.hidden = true;
          render();
        });
        tab.append(select, close); tabs.append(tab);
      }
      const file = files.get(active);
      if (!file) return;
      pathLabel.textContent = `${file.path} · ${file.revision.slice(0, 12)} · read only`;
      const renderableDocument = file.kind === "DOCUMENTATION" && /\.(?:md|markdown|rst|txt|adoc)$/i.test(file.path);
      viewButton.hidden = !renderableDocument;
      viewButton.textContent = sourceMode ? "Rendered view" : "Source view";
      if (renderableDocument && !sourceMode) renderMarkdown(file.content);
      else renderSource(file.content, file.kind === "CODE" || !renderableDocument);
      const query = search.value.trim().toLowerCase();
      if (query) {
        for (const element of content.querySelectorAll(".inspection-code-line, .inspection-source-line, p, li, td")) {
          if (element.textContent.toLowerCase().includes(query)) element.classList.add("inspection-search-hit");
        }
        content.querySelector(".inspection-search-hit")?.scrollIntoView({ block: "center" });
      }
    }
    async function open(workId, path, revision) {
      const key = `${workId}:${revision}:${path}`;
      if (!files.has(key)) files.set(key, await loadFile(workId, path, revision));
      active = key; sourceMode = false; search.value = ""; root.hidden = false; render();
    }
    document.getElementById("inspection-close").addEventListener("click", () => { root.hidden = true; });
    document.getElementById("inspection-expand").addEventListener("click", (event) => {
      root.classList.toggle("is-expanded");
      event.currentTarget.textContent = root.classList.contains("is-expanded") ? "Restore" : "Enlarge";
    });
    document.getElementById("inspection-opacity").addEventListener("click", (event) => {
      root.classList.toggle("is-translucent");
      event.currentTarget.textContent = root.classList.contains("is-translucent") ? "Opaque" : "Semi-transparent";
    });
    viewButton.addEventListener("click", () => { sourceMode = !sourceMode; render(); });
    search.addEventListener("input", render);
    document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !root.hidden) root.hidden = true; });
    return { open, count: () => files.size };
  }

  function conversationOwnership(messages, handedOffTurnId = "") {
    const records = Array.isArray(messages) ? messages : [];
    const latest = records.at(-1)?.turn_id;
    if (!latest || latest === handedOffTurnId) return { history: records, current: [] };
    return {
      history: records.filter((record) => record.turn_id !== latest),
      current: records.filter((record) => record.turn_id === latest),
    };
  }

  const COMPOSER_MODES = Object.freeze({
    COMPACT_IDLE: "COMPACT_IDLE",
    EXPANDED_COMPOSING: "EXPANDED_COMPOSING",
    SUBMITTING: "SUBMITTING",
    WAITING_RESPONSE: "WAITING_RESPONSE",
    RESPONSE_SETTLED: "RESPONSE_SETTLED",
  });

  function nextComposerMode(current, event, hasDraft = false) {
    if (event === "FOCUS" || event === "EXPAND") return COMPOSER_MODES.EXPANDED_COMPOSING;
    if (event === "SEND") return COMPOSER_MODES.SUBMITTING;
    if (event === "ACCEPTED") return COMPOSER_MODES.WAITING_RESPONSE;
    if (event === "SETTLED") return COMPOSER_MODES.RESPONSE_SETTLED;
    if (event === "OUTSIDE" || event === "COLLAPSE") {
      return hasDraft ? COMPOSER_MODES.EXPANDED_COMPOSING : COMPOSER_MODES.COMPACT_IDLE;
    }
    return current;
  }

  function humanActionProjection(work, attentionItems, selectedAgreementId = null) {
    const workStatus = work?.status;
    const workActions = workStatus === "DRAFT" || workStatus === "NEEDS_REFINEMENT"
      ? ["REFINE"]
      : workStatus === "AWAITING_APPROVAL"
        ? ["APPROVE", "REQUEST_REFINEMENT", "REJECT"] : [];
    const items = Array.isArray(attentionItems) ? attentionItems : [];
    const attention = items.filter((item) => !item.work_id || item.work_id === work?.work_id);
    const explicit = attention.filter((item) => Array.isArray(item.available_actions)
      && item.available_actions.length
      && !(workActions.length && item.kind === "WORK_DRAFT_APPROVAL"));
    const conversationalDecision = attention.find((item) => item.kind === "STEERING_DECISION_REQUIRED"
      && (!item.available_actions || item.available_actions.length === 0));
    const required = Boolean(workActions.length || explicit.length || selectedAgreementId || conversationalDecision);
    return {
      required,
      count: (workActions.length ? 1 : 0) + explicit.length
        + (selectedAgreementId ? 1 : 0) + (conversationalDecision ? 1 : 0),
      workActions,
      actionableAttention: explicit,
      conversationalDecision: conversationalDecision || null,
      summary: selectedAgreementId ? "Decide whether to keep this agreement."
        : explicit.length || workActions.length ? "Your decision is needed."
          : conversationalDecision ? "Respond to the material decision in conversation."
            : "No action required.",
    };
  }

  function prospectiveWorkspaceProjection(projection, selectedWorkId = "") {
    const assessment = projection?.latest_assessment;
    const semantics = assessment?.progressive_semantics;
    const intent = semantics?.turn_intent;
    const productionIntent = ["BUILD", "ACTION_REQUEST", "MODIFY", "DEPLOY"].includes(intent);
    const durablePreWork = Boolean(
      projection?.current_work_id && !projection?.governed_work_id,
    );
    const semanticWorkCandidate = Boolean(
      assessment
      && (assessment.interpreted_motive || projection?.interpreted_motive)
      && intent !== "DIRECT_QUESTION"
      && (productionIntent || projection?.selected_design_schema_identity)
      && semantics?.governance_candidate !== "CONVERSATION_ONLY",
    );
    const visible = !selectedWorkId && !projection?.governed_work_id
      && (durablePreWork || semanticWorkCandidate);
    const readiness = projection?.readiness;
    return {
      visible,
      canStart: visible && readiness?.status === "READY",
      blocker: visible ? readiness?.unresolved_material_questions?.[0]
        || readiness?.missing_information?.[0] || null : null,
    };
  }

  globalThis.WattControlRoom = Object.freeze({ agendaSteps, agendaMilestones, currentProductionQueue, productionState, conversationOwnership, nextComposerMode, humanActionProjection, prospectiveWorkspaceProjection, createViewer });
})();
