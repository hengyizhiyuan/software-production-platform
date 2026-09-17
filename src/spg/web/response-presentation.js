(function () {
  "use strict";

  const IMPLEMENTED_BLOCK_KINDS = Object.freeze(["PROSE", "LIST"]);
  const RESERVED_BLOCK_KINDS = Object.freeze([
    "TABLE",
    "COMPARISON",
    "OPTION_CARDS",
    "CHECKLIST",
    "STATUS",
    "DIAGRAM",
  ]);

  function parsePlainResponse(value) {
    const text = String(value || "").trim();
    if (!text) return [];
    return text.split(/\n\s*\n/).map((section) => {
      const lines = section.split("\n").map((line) => line.trim()).filter(Boolean);
      const list = lines.length > 0 && lines.every((line) => /^[-*]\s+/.test(line));
      return list
        ? { kind: "LIST", items: lines.map((line) => line.replace(/^[-*]\s+/, "")) }
        : { kind: "PROSE", text: lines.join("\n") };
    });
  }

  function render(container, value) {
    if (!container || !container.ownerDocument || typeof container.replaceChildren !== "function") {
      if (container) container.textContent = String(value || "");
      return;
    }
    const document = container.ownerDocument;
    const nodes = parsePlainResponse(value).map((block) => {
      if (block.kind === "LIST") {
        const list = document.createElement("ul");
        list.className = "rich-response-list";
        block.items.forEach((item) => {
          const row = document.createElement("li");
          row.textContent = item;
          list.append(row);
        });
        return list;
      }
      const paragraph = document.createElement("p");
      paragraph.className = "rich-response-block";
      paragraph.textContent = block.text;
      return paragraph;
    });
    container.replaceChildren(...nodes);
  }

  globalThis.WattResponsePresentation = Object.freeze({
    IMPLEMENTED_BLOCK_KINDS,
    RESERVED_BLOCK_KINDS,
    parsePlainResponse,
    render,
  });
})();
