"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const repositoryRoot = path.resolve(__dirname, "..", "..");
const source = fs.readFileSync(
  path.join(repositoryRoot, "src", "spg", "web", "response-presentation.js"),
  "utf8",
);
const context = {};
context.globalThis = context;
vm.runInNewContext(source, context, { filename: "response-presentation.js" });

test("response presentation keeps a bounded composable extension seam", () => {
  const presentation = context.WattResponsePresentation;
  assert.deepEqual(Array.from(presentation.IMPLEMENTED_BLOCK_KINDS), ["PROSE", "LIST"]);
  assert.deepEqual(Array.from(presentation.RESERVED_BLOCK_KINDS), [
    "TABLE", "COMPARISON", "OPTION_CARDS", "CHECKLIST", "STATUS", "DIAGRAM",
  ]);
});

test("plain response parsing separates prose and simple lists without HTML interpretation", () => {
  const blocks = context.WattResponsePresentation.parsePlainResponse(
    "Current Reality is stable.\n\n- Verify the candidate\n- Ask for Human authority",
  );
  assert.equal(blocks.length, 2);
  assert.equal(blocks[0].kind, "PROSE");
  assert.equal(blocks[0].text, "Current Reality is stable.");
  assert.equal(blocks[1].kind, "LIST");
  assert.deepEqual(Array.from(blocks[1].items), ["Verify the candidate", "Ask for Human authority"]);
});
