(function () {
  "use strict";

  const GLOBAL_THEME_STORAGE_KEY = "watt.appearance.globalTheme.v1";
  const WORKSPACE_SKIN_STORAGE_KEY = "watt.appearance.workspaceSkin.v1";

  const GLOBAL_THEMES = Object.freeze({
    LIGHT: Object.freeze({ id: "LIGHT", displayName: "Light" }),
    DARK: Object.freeze({ id: "DARK", displayName: "Dark" }),
  });

  const WORKSPACE_SKINS = Object.freeze([
    Object.freeze({
      skinId: "INDUSTRIAL_CYAN",
      displayName: "Industrial Cyan",
      status: "IMPLEMENTED",
      baseAppearance: "DARK",
      tokenProfile: "industrial-cyan-v1",
      presentationProfile: "industrial-control",
      enabled: true,
      version: 1,
      referenceAsset: "/docs/assets/ui-skins/01-industrial-cyan.png",
    }),
    Object.freeze({
      skinId: "EXECUTIVE_AMBER",
      displayName: "Executive Amber",
      status: "FUTURE_EXTERNAL_ASSET_DOGFOOD",
      baseAppearance: "DARK",
      tokenProfile: "executive-amber-v1",
      presentationProfile: "operational-command",
      enabled: false,
      version: 1,
      referenceAsset: "/docs/assets/ui-skins/02-executive-amber.png",
    }),
    Object.freeze({
      skinId: "TECHNICAL_GRAPHITE",
      displayName: "Technical Graphite",
      status: "FUTURE_EXTERNAL_ASSET_DOGFOOD",
      baseAppearance: "DARK",
      tokenProfile: "technical-graphite-v1",
      presentationProfile: "engineering-console",
      enabled: false,
      version: 1,
      referenceAsset: "/docs/assets/ui-skins/03-technical-graphite.png",
    }),
    Object.freeze({
      skinId: "PRECISION_SILVER",
      displayName: "Precision Silver",
      status: "FUTURE_EXTERNAL_ASSET_DOGFOOD",
      baseAppearance: "LIGHT",
      tokenProfile: "precision-silver-v1",
      presentationProfile: "precision-instrument",
      enabled: false,
      version: 1,
      referenceAsset: "/docs/assets/ui-skins/04-precision-silver.png",
    }),
    Object.freeze({
      skinId: "WARM_PROFESSIONAL",
      displayName: "Warm Professional",
      status: "FUTURE_EXTERNAL_ASSET_DOGFOOD",
      baseAppearance: "LIGHT",
      tokenProfile: "warm-professional-v1",
      presentationProfile: "calm-professional",
      enabled: false,
      version: 1,
      referenceAsset: "/docs/assets/ui-skins/05-warm-professional.png",
    }),
    Object.freeze({
      skinId: "FUTURISTIC_STUDIO",
      displayName: "Futuristic Studio",
      status: "FUTURE_EXTERNAL_ASSET_DOGFOOD",
      baseAppearance: "DARK",
      tokenProfile: "futuristic-studio-v1",
      presentationProfile: "future-engineering",
      enabled: false,
      version: 1,
      referenceAsset: "/docs/assets/ui-skins/06-futuristic-studio.png",
    }),
  ]);

  const DEFAULT_GLOBAL_THEME = "LIGHT";
  const DEFAULT_WORKSPACE_SKIN = "INDUSTRIAL_CYAN";
  const WORKSPACE_SURFACE_ORDER = Object.freeze([
    "reality-surface",
    "agenda-surface",
    "production-surface",
    "actions-surface",
  ]);

  function globalTheme(themeId) {
    return GLOBAL_THEMES[themeId] || GLOBAL_THEMES[DEFAULT_GLOBAL_THEME];
  }

  function workspaceSkin(skinId, requireEnabled) {
    const skin = WORKSPACE_SKINS.find((item) => item.skinId === skinId);
    if (!skin || (requireEnabled && !skin.enabled)) {
      return WORKSPACE_SKINS.find((item) => item.skinId === DEFAULT_WORKSPACE_SKIN);
    }
    return skin;
  }

  function readPreference(storage, key, fallback) {
    try {
      return storage && storage.getItem(key) || fallback;
    } catch (_error) {
      return fallback;
    }
  }

  function persistPreference(storage, key, value) {
    try {
      if (storage) storage.setItem(key, value);
    } catch (_error) {
      // Appearance remains usable when browser preference storage is unavailable.
    }
  }

  function applyGlobalTheme(themeId, root) {
    const selected = globalTheme(themeId);
    if (root) {
      root.dataset.globalTheme = selected.id;
      root.style.colorScheme = selected.id === "DARK" ? "dark" : "light";
    }
    return selected;
  }

  function applyWorkspaceSkin(skinId, workspace) {
    const selected = workspaceSkin(skinId, true);
    if (workspace) {
      workspace.dataset.workspaceSkin = selected.skinId;
      workspace.dataset.workspaceAppearance = selected.baseAppearance;
      workspace.dataset.workspacePresentation = selected.presentationProfile;
    }
    return selected;
  }

  function initialize(options) {
    const settings = options || {};
    const storage = settings.storage || (typeof globalThis.localStorage === "undefined" ? null : globalThis.localStorage);
    const root = settings.root || (typeof document === "undefined" ? null : document.documentElement);
    const workspace = settings.workspace || (typeof document === "undefined" ? null : document.querySelector("[data-workspace-skin]"));
    const requestedTheme = readPreference(storage, GLOBAL_THEME_STORAGE_KEY, DEFAULT_GLOBAL_THEME);
    const requestedSkin = readPreference(storage, WORKSPACE_SKIN_STORAGE_KEY, DEFAULT_WORKSPACE_SKIN);
    return {
      globalTheme: applyGlobalTheme(requestedTheme, root),
      workspaceSkin: applyWorkspaceSkin(requestedSkin, workspace),
    };
  }

  function selectGlobalTheme(themeId, options) {
    const settings = options || {};
    const storage = settings.storage || (typeof globalThis.localStorage === "undefined" ? null : globalThis.localStorage);
    const root = settings.root || (typeof document === "undefined" ? null : document.documentElement);
    const selected = applyGlobalTheme(themeId, root);
    persistPreference(storage, GLOBAL_THEME_STORAGE_KEY, selected.id);
    return selected;
  }

  function selectWorkspaceSkin(skinId, options) {
    const settings = options || {};
    const storage = settings.storage || (typeof globalThis.localStorage === "undefined" ? null : globalThis.localStorage);
    const workspace = settings.workspace || (typeof document === "undefined" ? null : document.querySelector("[data-workspace-skin]"));
    const selected = applyWorkspaceSkin(skinId, workspace);
    persistPreference(storage, WORKSPACE_SKIN_STORAGE_KEY, selected.skinId);
    return selected;
  }

  function setSurfaceCollapsed(surface, collapsed) {
    if (!surface) return false;
    const next = Boolean(collapsed);
    surface.classList.toggle("is-collapsed", next);
    const control = surface.querySelector("[data-collapse-surface]");
    if (control) {
      control.setAttribute("aria-expanded", String(!next));
      control.textContent = next ? "Expand" : "Collapse";
    }
    return next;
  }

  function setFocusedSurface(grid, surfaceId) {
    if (!grid) return null;
    const target = WORKSPACE_SURFACE_ORDER.includes(surfaceId) ? surfaceId : null;
    grid.querySelectorAll(".workspace-surface").forEach((surface) => {
      const active = surface.id === target;
      surface.classList.toggle("is-focused", active);
      const control = surface.querySelector("[data-focus-surface]");
      if (control) {
        control.setAttribute("aria-expanded", String(active));
        control.textContent = active ? "Overview" : "Focus";
      }
    });
    grid.classList.toggle("has-focus", Boolean(target));
    return target;
  }

  globalThis.WattAppearance = Object.freeze({
    GLOBAL_THEME_STORAGE_KEY,
    WORKSPACE_SKIN_STORAGE_KEY,
    GLOBAL_THEMES,
    WORKSPACE_SKINS,
    DEFAULT_GLOBAL_THEME,
    DEFAULT_WORKSPACE_SKIN,
    WORKSPACE_SURFACE_ORDER,
    globalTheme,
    workspaceSkin,
    readPreference,
    applyGlobalTheme,
    applyWorkspaceSkin,
    initialize,
    selectGlobalTheme,
    selectWorkspaceSkin,
    setSurfaceCollapsed,
    setFocusedSurface,
  });

  if (typeof document !== "undefined") initialize();
})();
