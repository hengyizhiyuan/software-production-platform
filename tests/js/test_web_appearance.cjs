"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const repositoryRoot = path.resolve(__dirname, "..", "..");
const appearanceSource = fs.readFileSync(
  path.join(repositoryRoot, "src", "spg", "web", "appearance.js"),
  "utf8",
);

function loadAppearance() {
  const context = {};
  context.globalThis = context;
  vm.runInNewContext(appearanceSource, context, { filename: "appearance.js" });
  return context.WattAppearance;
}

function memoryStorage(initial) {
  const values = new Map(Object.entries(initial || {}));
  return {
    getItem(key) { return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { values.set(key, String(value)); },
    value(key) { return values.get(key); },
  };
}

function classList(initial) {
  const values = new Set(initial || []);
  return {
    toggle(value, force) {
      if (force === undefined ? !values.has(value) : force) values.add(value);
      else values.delete(value);
    },
    contains(value) { return values.has(value); },
  };
}

function surface(id) {
  const controls = {
    collapse: { attributes: {}, textContent: "Collapse", setAttribute(key, value) { this.attributes[key] = value; } },
    focus: { attributes: {}, textContent: "Focus", setAttribute(key, value) { this.attributes[key] = value; } },
  };
  return {
    id,
    classList: classList(["workspace-surface"]),
    querySelector(selector) {
      if (selector === "[data-collapse-surface]") return controls.collapse;
      if (selector === "[data-focus-surface]") return controls.focus;
      return null;
    },
    controls,
  };
}

test("formal UI registry exposes Industrial Cyan and preserves five future asset dogfood references", () => {
  const appearance = loadAppearance();
  assert.equal(appearance.WORKSPACE_SKINS.length, 6);
  assert.deepEqual(
    Array.from(appearance.WORKSPACE_SKINS.filter((skin) => skin.enabled), (skin) => skin.skinId),
    ["INDUSTRIAL_CYAN"],
  );
  assert.deepEqual(
    Array.from(appearance.WORKSPACE_SKINS.filter((skin) => !skin.enabled), (skin) => skin.skinId),
    ["EXECUTIVE_AMBER", "TECHNICAL_GRAPHITE", "PRECISION_SILVER", "WARM_PROFESSIONAL", "FUTURISTIC_STUDIO"],
  );
  assert.ok(
    appearance.WORKSPACE_SKINS.filter((skin) => !skin.enabled)
      .every((skin) => skin.status === "FUTURE_EXTERNAL_ASSET_DOGFOOD"),
  );
  assert.equal(appearance.GLOBAL_THEMES.LIGHT.id, "LIGHT");
  assert.equal(appearance.GLOBAL_THEMES.DARK.id, "DARK");
});

test("appearance preferences persist locally without mutating product Reality", () => {
  const appearance = loadAppearance();
  const storage = memoryStorage();
  const root = { dataset: {}, style: {} };
  const workspace = { dataset: {} };
  const productReality = Object.freeze({ workId: "work-7", revision: 3, status: "RUNNING" });
  const before = JSON.stringify(productReality);

  appearance.selectGlobalTheme("DARK", { storage, root });
  appearance.selectWorkspaceSkin("INDUSTRIAL_CYAN", { storage, workspace });

  assert.equal(root.dataset.globalTheme, "DARK");
  assert.equal(root.style.colorScheme, "dark");
  assert.equal(workspace.dataset.workspaceSkin, "INDUSTRIAL_CYAN");
  assert.equal(workspace.dataset.workspacePresentation, "industrial-control");
  assert.equal(storage.value(appearance.GLOBAL_THEME_STORAGE_KEY), "DARK");
  assert.equal(storage.value(appearance.WORKSPACE_SKIN_STORAGE_KEY), "INDUSTRIAL_CYAN");
  assert.equal(JSON.stringify(productReality), before);
});

test("planned skins cannot be selected and corrupted preferences recover safely", () => {
  const appearance = loadAppearance();
  const storage = memoryStorage({
    [appearance.GLOBAL_THEME_STORAGE_KEY]: "NOT_A_THEME",
    [appearance.WORKSPACE_SKIN_STORAGE_KEY]: "FUTURISTIC_STUDIO",
  });
  const root = { dataset: {}, style: {} };
  const workspace = { dataset: {} };

  const selected = appearance.initialize({ storage, root, workspace });

  assert.equal(selected.globalTheme.id, "LIGHT");
  assert.equal(selected.workspaceSkin.skinId, "INDUSTRIAL_CYAN");
  assert.equal(root.dataset.globalTheme, "LIGHT");
  assert.equal(workspace.dataset.workspaceSkin, "INDUSTRIAL_CYAN");
});

test("stable workspace preserves the four semantic surface slots across collapse cycles", () => {
  const appearance = loadAppearance();
  assert.deepEqual(Array.from(appearance.WORKSPACE_SURFACE_ORDER), [
    "reality-surface", "agenda-surface", "production-surface", "actions-surface",
  ]);
  const target = surface("agenda-surface");

  assert.equal(appearance.setSurfaceCollapsed(target, true), true);
  assert.equal(target.classList.contains("is-collapsed"), true);
  assert.equal(target.controls.collapse.attributes["aria-expanded"], "false");
  assert.equal(target.controls.collapse.textContent, "Expand");
  assert.equal(appearance.setSurfaceCollapsed(target, false), false);
  assert.equal(target.classList.contains("is-collapsed"), false);
  assert.equal(target.controls.collapse.attributes["aria-expanded"], "true");
});

test("focus is temporary emphasis and returns to the unchanged four-surface order", () => {
  const appearance = loadAppearance();
  const surfaces = appearance.WORKSPACE_SURFACE_ORDER.map(surface);
  const grid = {
    classList: classList(),
    querySelectorAll() { return surfaces; },
  };

  assert.equal(appearance.setFocusedSurface(grid, "production-surface"), "production-surface");
  assert.equal(grid.classList.contains("has-focus"), true);
  assert.equal(surfaces[2].classList.contains("is-focused"), true);
  assert.equal(surfaces[2].controls.focus.textContent, "Overview");
  assert.equal(appearance.setFocusedSurface(grid, null), null);
  assert.equal(grid.classList.contains("has-focus"), false);
  assert.ok(surfaces.every((item) => !item.classList.contains("is-focused")));
  assert.equal(
    JSON.stringify(surfaces.map((item) => item.id)),
    JSON.stringify(Array.from(appearance.WORKSPACE_SURFACE_ORDER)),
  );
});
