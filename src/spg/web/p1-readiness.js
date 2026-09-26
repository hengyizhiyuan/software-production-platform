(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const selected = $("selected-work");
  if (!selected || !$("p1-product-list")) return;
  const state = { products: [], productId: "", workId: "", observedKey: "" };
  async function api(path, method = "GET", body) {
    const response = await fetch(path, {
      method, credentials: "same-origin",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.message || payload.code || `HTTP ${response.status}`);
    return payload;
  }
  function node(tag, value, className = "") {
    const element = document.createElement(tag);
    element.textContent = value;
    if (className) element.className = className;
    return element;
  }
  function report(error, target = $("p1-platform-status")) {
    if (target) target.textContent = error.message || String(error);
  }
  function spendSummary(spend) {
    const observed = Object.entries(spend.by_currency || {}).map(([currency, amount]) => `${currency} ${amount}`);
    if (!observed.length && spend.amount !== null && spend.amount !== undefined) observed.push(String(spend.amount));
    if (!observed.length) return `${spend.status} (unknown)`;
    const missing = spend.unreported_attempt_count ? `; ${spend.unreported_attempt_count} attempts unreported` : "";
    return `${spend.status}: ${observed.join(", ")}${missing}`;
  }
  function currentProduct() { return state.products.find((item) => item.id === state.productId); }
  async function loadProducts() {
    state.products = await api("/api/products");
    if (selected.dataset.productId && state.products.some((item) => item.id === selected.dataset.productId)) {
      state.productId = selected.dataset.productId;
    }
    if (!state.productId && state.products.length) state.productId = state.products[0].id;
    renderProducts();
  }
  function renderProducts() {
    const list = $("p1-product-list");
    list.replaceChildren();
    if (!state.products.length) list.append(node("p", "No Product yet. Create one to retain source continuity.", "empty-copy"));
    for (const product of state.products) {
      const button = node("button", `${product.name} · ${product.works.length} Works`, "p1-product-button");
      button.type = "button";
      button.setAttribute("aria-pressed", String(product.id === state.productId));
      button.addEventListener("click", () => { state.productId = product.id; renderProducts(); });
      list.append(button);
    }
    const current = currentProduct();
    $("p1-product-detail").hidden = !current;
    $("p1-product-summary").textContent = current
      ? `${current.lifecycle} · ${current.assets.length} assets · ${current.works.length} Works · ${current.current_sources.length} repository sources`
      : "";
    const assets = $("p1-product-assets");
    assets.replaceChildren();
    if (current) {
      for (const source of current.current_sources) {
        const revision = source.metadata?.revision || "revision not yet observed";
        const branch = source.metadata?.repository_ref || "branch not yet observed";
        assets.append(node("p", `Source · ${source.reference} · ${branch} · ${revision}`));
      }
      for (const asset of current.assets.filter((item) => item.asset_kind !== "REPOSITORY")) {
        assets.append(node("p", `${asset.asset_kind} · ${asset.reference}`));
      }
    }
    const select = $("p1-work-product");
    select.replaceChildren();
    select.append(new Option("Select Product", ""));
    for (const product of state.products) select.append(new Option(product.name, product.id));
    select.value = selected.dataset.productId || state.productId || "";
    const bound = Boolean(selected.dataset.productId);
    $("p1-bind-work").disabled = !state.workId || bound;
    $("p1-work-product-summary").textContent = bound
      ? `This Work changes ${state.products.find((item) => item.id === selected.dataset.productId)?.name || selected.dataset.productId}.`
      : "This Work is not yet assigned to a long-lived Product.";
  }
  async function refreshWorkContext(force = false) {
    const id = selected.dataset.workId || "";
    const key = `${id}:${selected.dataset.productId || ""}`;
    if (!force && key === state.observedKey) return;
    state.observedKey = key;
    state.workId = id;
    if (!id) { renderProducts(); return; }
    if (selected.dataset.productId && state.products.some((item) => item.id === selected.dataset.productId)) {
      state.productId = selected.dataset.productId;
    }
    renderProducts();
    try {
      const diagnosis = await api(`/api/works/${id}/operations`);
      if (selected.dataset.workId !== id) return;
      const summary = $("p1-diagnosis");
      summary.replaceChildren(node("h4", `Production: ${diagnosis.state}`),
        node("p", diagnosis.root_cause || "No blocker observed."),
        node("p", `${diagnosis.pwu.length} PWUs · ${diagnosis.queue.length} queue entries · ${diagnosis.verification.count} verifications`));
      if (diagnosis.candidate_ids.length) summary.append(node("p", `Candidates: ${diagnosis.candidate_ids.join(", ")}`));
      if (diagnosis.evidence_refs.length) summary.append(node("p", `Evidence: ${diagnosis.evidence_refs.join(", ")}`));
      const economics = diagnosis.economics;
      const cost = $("p1-economics");
      cost.replaceChildren(node("h4", "Production economics"),
        node("p", `Wall ${economics.wall_elapsed_seconds ?? "unknown"}s · accumulated execution ${economics.execution_seconds}s · queue wait ${economics.queue_wait_seconds}s · critical path ${economics.critical_path_seconds ?? "unknown"}s`),
        node("p", `Tokens ${economics.token_usage.status}: ${economics.token_usage.total_tokens ?? "unknown"} · provider spend ${spendSummary(economics.observed_provider_spend)}`),
        node("p", `${economics.pwu_count} PWUs · ${economics.join_count} Joins · ${economics.self_refine_event_count || 0} Self-Refine events`));
      const productId = selected.dataset.productId;
      const history = $("p1-history");
      history.replaceChildren();
      if (productId) {
        const facts = await api(`/api/products/${productId}/history`);
        if (selected.dataset.workId !== id || selected.dataset.productId !== productId) return;
        history.append(node("h4", `${facts.name} · governed history`));
        for (const event of facts.timeline.slice(-20)) {
          const detail = event.requirement || event.desired_outcome || event.objective || event.diagnosis || event.result || event.revision || "";
          history.append(node("p", `${event.at.slice(0, 16)} · ${event.kind} · ${String(detail).slice(0, 180)}`));
        }
      }
    } catch (error) {
      if (selected.dataset.workId === id) {
        state.observedKey = "";
        report(error, $("p1-diagnosis"));
      }
    }
  }
  const observer = new MutationObserver(() => void refreshWorkContext());
  observer.observe(selected, { attributes: true, attributeFilter: ["data-work-id", "data-product-id"] });
  for (const id of ["refresh-control", "work-refresh-control"]) {
    $(id)?.addEventListener("click", () => {
      void loadProducts().catch((error) => report(error, $("p1-product-list")));
      void refreshWorkContext(true);
    });
  }
  $("p1-product-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const product = await api("/api/products", "POST", { name: $("p1-product-name").value.trim() });
      state.productId = product.id;
      $("p1-product-name").value = "";
      await loadProducts();
    } catch (error) { report(error, $("p1-product-summary")); }
  });
  $("p1-repository-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const current = currentProduct();
    if (!current) return;
    const source = $("p1-repository-url").value.trim();
    try {
      const result = await api(`/api/products/${current.id}/repository-intake`, "POST", {
        request_id: crypto.randomUUID(), source, title: `${current.name} repository`,
        description: "Existing Product source", authority_identity: "human:owner",
      });
      $("p1-product-summary").textContent = `${result.observation.condition} · ${result.observation.repository_ref || "no branch"} · ${result.observation.revision || result.observation.human_message}`;
      await loadProducts();
    } catch (error) { report(error, $("p1-product-summary")); }
  });
  $("p1-bind-work").addEventListener("click", async () => {
    const productId = $("p1-work-product").value;
    if (!state.workId || !productId) return;
    try {
      await api(`/api/products/${productId}/works/${state.workId}`, "POST");
      state.productId = productId;
      selected.dataset.productId = productId;
      await loadProducts();
      $("work-refresh-control")?.click();
    } catch (error) { report(error, $("p1-work-product-summary")); }
  });
  async function loadOperations() {
    try {
      const [operations, evaluations, platform] = await Promise.all([
        api("/api/operations/connectors"), api("/api/operations/evaluations?limit=8"),
        api("/api/operations/summary"),
      ]);
      const unhealthy = platform.leases.unhealthy_count;
      const waiting = platform.queue.by_condition.WAITING_RESOURCE || 0;
      $("p1-platform-status").textContent = `${platform.workers.healthy}/${platform.workers.registered} workers healthy · ${platform.queue.active_count} queued/active (${waiting} waiting for resources) · ${unhealthy} unhealthy leases · ${platform.recent_self_refine_failures} recent failed/escalated refinements · provider spend ${spendSummary(platform.recent_work_provider_spend)} across ${platform.recent_work_provider_spend.sample_size} recent Works · ${operations.connectors.length} Connectors · ${operations.credentials.length} GitHub grants · ${evaluations.length} evaluations`;
      const connectors = $("p1-connector-list");
      connectors.replaceChildren(node("h4", "Connectors"));
      for (const item of operations.connectors) {
        const row = document.createElement("details");
        row.append(node("summary", `${item.capability_id} · ${item.scope} · ${item.health} · ${item.enabled ? "enabled" : "disabled"}`));
        row.append(node("p", `${item.provider} · ${item.capability_family} · owner ${item.owner_id} · v${item.version} · ${item.maturity} · ${item.qualification}${item.provisional ? " · provisional" : ""}${item.deprecated ? " · deprecated" : ""}`));
        row.append(node("p", `Credential: ${(item.credential_requirements || []).join(", ") || "none"} · permissions: ${(item.permissions_required || []).join(", ") || "none"}`));
        row.append(node("p", `Usage: ${item.usage_count_status || item.usage_count} · last execution success: ${item.last_success_at || item.last_success_status || "unknown"} · health failures: ${item.failure_count} · last failure: ${item.last_failure_at || "none"}`));
        const button = node("button", item.enabled ? "Disable" : "Enable", "text-button");
        button.type = "button";
        button.addEventListener("click", async () => {
          try { await api(`/api/operations/connectors/${item.id}`, "PUT", { enabled: !item.enabled }); await loadOperations(); }
          catch (error) { report(error); }
        });
        const history = node("pre", "");
        const audit = node("button", "Audit history", "text-button");
        audit.type = "button";
        audit.addEventListener("click", async () => {
          try {
            const events = await api(`/api/operations/connectors/${item.id}/history`);
            history.textContent = events.map((event) => `${event.created_at} · ${event.action} · ${event.actor_id} · ${JSON.stringify(event.detail)}`).join("\n") || "No control changes recorded.";
          } catch (error) { report(error, history); }
        });
        row.append(button, audit, history);
        connectors.append(row);
      }
      const credentials = $("p1-credential-list");
      credentials.replaceChildren(node("h4", "Credential references"));
      for (const item of operations.credentials) {
        const row = document.createElement("details");
        row.append(node("summary", `${item.repository_url} · ${item.permission} · ${item.credential_status}`));
        row.append(node("p", `${item.provider || "GitHub"} · owner ${item.owner_id} · ${item.scope} · ${item.credential_ref} · expires ${item.expires_at || "unreported"} · verified ${item.last_verified_at || "never"} · use ${item.usage_count} · failures ${item.failure_count}`));
        if (item.condition === "ACTIVE") {
          const revoke = node("button", "Revoke", "text-button");
          revoke.type = "button";
          revoke.addEventListener("click", async () => {
            try { await api(`/api/github/grants/${item.grant_id}`, "DELETE"); await loadOperations(); }
            catch (error) { report(error); }
          });
          row.append(revoke);
        }
        const history = node("pre", "");
        const audit = node("button", "Audit history", "text-button");
        audit.type = "button";
        audit.addEventListener("click", async () => {
          try {
            const events = await api(`/api/github/grants/${item.grant_id}/history`);
            history.textContent = events.map((event) => `${event.created_at} · ${event.action} · ${event.actor_id} · ${JSON.stringify(event.detail)}`).join("\n") || "No grant changes recorded.";
          } catch (error) { report(error, history); }
        });
        row.append(audit, history);
        credentials.append(row);
      }
      const evaluation = $("p1-evaluation-list");
      evaluation.replaceChildren(node("h4", "Release evaluation"));
      for (const item of evaluations) evaluation.append(node("p", `${item.version} · ${item.purpose} · ${item.qualification} · ${item.trend.status}`));
    } catch (error) { report(error); }
  }
  $("p1-operator-panel").addEventListener("toggle", () => {
    if ($("p1-operator-panel").open) void loadOperations();
  });
  $("p1-github-grant-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api("/api/github/grants", "POST", {
        repository_url: $("p1-github-repository").value.trim(),
        capability: $("p1-github-permission").value,
      });
      await loadOperations();
    } catch (error) { report(error); }
  });
  void loadProducts().catch((error) => report(error, $("p1-product-list")));
  void refreshWorkContext();
})();
