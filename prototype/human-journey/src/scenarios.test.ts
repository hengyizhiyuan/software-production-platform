import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { cloneSeed, getScene, scenarioPacks, VALID_SCENARIO_IDS, VALID_TENSION_IDS } from "./scenarios";

describe("scenario fixture integrity", () => {
  it("contains the complete P01-P16 pack set with unique seeds", () => {
    expect(scenarioPacks.map((pack) => pack.id)).toEqual(
      Array.from({ length: 16 }, (_, index) => `P${String(index + 1).padStart(2, "0")}`),
    );
    for (const pack of scenarioPacks) {
      expect(pack.scenes.length).toBeGreaterThanOrEqual(3);
      expect(pack.scenes.some((scene) => scene.id === pack.seed)).toBe(true);
      expect(new Set(pack.scenes.map((scene) => scene.id)).size).toBe(pack.scenes.length);
    }
  });

  it("keeps every scene reachable and every transition local and valid", () => {
    for (const pack of scenarioPacks) {
      const valid = new Set(pack.scenes.map((scene) => scene.id));
      const seen = new Set<string>();
      const pending = [pack.seed];
      while (pending.length) {
        const id = pending.shift()!;
        if (seen.has(id)) continue;
        seen.add(id);
        for (const transition of getScene(pack, id).transitions) {
          expect(valid.has(transition.to), `${pack.id}/${id} -> ${transition.to}`).toBe(true);
          pending.push(transition.to);
        }
      }
      expect(seen, `${pack.id} contains unreachable scenes`).toEqual(valid);
    }
  });

  it("references only frozen scenario and tension identities", () => {
    for (const pack of scenarioPacks) {
      for (const scene of pack.scenes) {
        for (const id of scene.scenarioIds) expect(VALID_SCENARIO_IDS.has(id), `${scene.id}: ${id}`).toBe(true);
        for (const id of scene.tensionIds) expect(VALID_TENSION_IDS.has(id), `${scene.id}: ${id}`).toBe(true);
      }
    }
  });

  it("resets to an independent deterministic copy of the exact seed", () => {
    for (const pack of scenarioPacks) {
      const first = cloneSeed(pack);
      const second = cloneSeed(pack);
      expect(first).toEqual(second);
      expect(first).not.toBe(second);
      expect(first.id).toBe(pack.seed);
    }
  });

  it("contains no production API, provider, or remote URL in prototype source", () => {
    const sourceDir = dirname(fileURLToPath(import.meta.url));
    const files = readdirSync(sourceDir).filter(
      (name) => /\.(ts|tsx|css)$/.test(name) && !name.endsWith(".test.ts"),
    );
    const source = files.map((name) => readFileSync(join(sourceDir, name), "utf8")).join("\n");
    expect(source).not.toMatch(/https?:\/\//i);
    expect(source).not.toMatch(/["'`]\/api\//i);
    expect(source).not.toMatch(/deepseek|openai\.com|postgres(?:ql)?:\/\//i);
  });

  it("keeps the Human review ledger complete and unaccepted", () => {
    const sourceDir = dirname(fileURLToPath(import.meta.url));
    const ledger = readFileSync(join(sourceDir, "../acceptance/scenes.md"), "utf8");
    const ledgerSceneIds = [...ledger.matchAll(/^\| P\d{2} \| ([a-z0-9-]+) \|/gm)].map((match) => match[1]);
    const fixtureSceneIds = scenarioPacks.flatMap((pack) => pack.scenes.map((scene) => scene.id));
    expect(ledgerSceneIds).toEqual(fixtureSceneIds);
    expect(ledger).not.toContain("| HUMAN_EXPERIENCE_ACCEPTED |");
  });
});
