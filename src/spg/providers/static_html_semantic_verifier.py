"""Read-only checks for exact, Human-admitted static HTML semantic facts."""

from html.parser import HTMLParser
from pathlib import Path
import subprocess

from spg.domain.change import CodeChangeContract
from spg.domain.engineering_semantics import SemanticFactReference, SemanticRelation


class _HTMLFacts(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[str] = []
        self.ordered_lists: list[list[str]] = []
        self.outside_list_text: list[str] = []
        self._heading: list[str] | None = None
        self._list_stack: list[int] = []
        self._item_stack: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        del attrs
        if tag == "h1":
            self._heading = []
        elif tag == "ol":
            self._list_stack.append(len(self.ordered_lists))
            self.ordered_lists.append([])
        elif tag == "li" and self._list_stack:
            self._item_stack.append([])

    def handle_data(self, data: str) -> None:
        if self._heading is not None:
            self._heading.append(data)
        if self._item_stack:
            self._item_stack[-1].append(data)
        else:
            self.outside_list_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self._heading is not None:
            self.headings.append("".join(self._heading).strip())
            self._heading = None
        elif tag == "li" and self._item_stack and self._list_stack:
            self.ordered_lists[self._list_stack[-1]].append(
                "".join(self._item_stack.pop()).strip()
            )
        elif tag == "ol" and self._list_stack:
            self._list_stack.pop()


def verify_static_html_semantic_facts(
    repository: Path,
    proposed_revision: str,
    contract: CodeChangeContract,
    facts: tuple[SemanticFactReference, ...],
) -> tuple[dict[str, object], ...]:
    """Check supported facts against the immutable proposed Git blob.

    A fact outside the admitted exact HTML targets fails closed. Other semantic
    domains keep their existing owner and are not marked verified here.
    """
    supported = tuple(fact for fact in facts if fact.subject in {
        "page.heading.text", "page.ordered_list.items",
    })
    if not supported:
        return ()
    html_targets = {target.path for target in contract.exact_targets
                    if target.path.endswith(".html")}
    observed: dict[str, _HTMLFacts | None] = {}
    checks: list[dict[str, object]] = []
    ordered = {fact.scope for fact in supported
               if fact.subject == "page.ordered_list.items"
               and fact.relation is SemanticRelation.ORDERED_COMPONENT}
    for fact in supported:
        path = fact.scope or ""
        if path not in html_targets:
            passed = False
            reason = "FACT_SCOPE_OUTSIDE_EXACT_HTML_TARGET"
        else:
            if path not in observed:
                result = subprocess.run(
                    ["git", "-C", str(repository), "show", f"{proposed_revision}:{path}"],
                    check=False, capture_output=True, timeout=15,
                )
                parser = None
                if result.returncode == 0:
                    try:
                        parser = _HTMLFacts()
                        parser.feed(result.stdout.decode("utf-8", errors="strict"))
                        parser.close()
                    except (UnicodeDecodeError, ValueError):
                        parser = None
                observed[path] = parser
            parser = observed[path]
            if parser is None:
                passed, reason = False, "EXACT_HTML_BLOB_UNREADABLE"
            elif (fact.subject == "page.heading.text"
                    and fact.relation is SemanticRelation.EQUALITY
                    and isinstance(fact.value, str)
                    and fact.qualifiers.get("heading_level") == 1):
                passed = parser.headings == [fact.value]
                reason = "EXACT_H1" if passed else "H1_TEXT_OR_COUNT_MISMATCH"
            elif (fact.subject == "page.ordered_list.items"
                    and fact.relation is SemanticRelation.ORDERED_COMPONENT
                    and isinstance(fact.value, tuple)
                    and all(isinstance(value, str) for value in fact.value)):
                expected = list(fact.value)
                passed = (len(parser.ordered_lists) == 1
                          and parser.ordered_lists[0] == expected
                          and len(expected) == len(set(expected))
                          and fact.qualifiers.get("count", len(expected)) == len(expected)
                          and not any(value in " ".join(parser.outside_list_text)
                                      for value in expected))
                reason = "EXACT_ORDERED_LIST" if passed else "ORDERED_LIST_CONTENT_OR_COUNT_MISMATCH"
            elif (fact.subject == "page.ordered_list.items"
                    and fact.relation is SemanticRelation.ACCEPTANCE_ASSERTION):
                # The admitted assertion is checked by the exact ordered fact;
                # without that fact, a prose promise cannot receive PASS.
                passed = path in ordered and len(parser.ordered_lists) == 1
                reason = "BOUND_TO_ORDERED_FACT" if passed else "ORDERED_FACT_MISSING"
            else:
                passed, reason = False, "SEMANTIC_FACT_PROFILE_UNSUPPORTED"
        checks.append({"fact_id": str(fact.fact_id), "subject": fact.subject,
                       "scope": path, "passed": passed, "reason": reason})
    # An assertion and its ordered value must share the outcome.
    failed_ordered_scopes = {check["scope"] for check in checks
                             if check["subject"] == "page.ordered_list.items"
                             and not check["passed"]}
    for check in checks:
        if check["subject"] == "page.ordered_list.items" and check["scope"] in failed_ordered_scopes:
            check["passed"] = False
    return tuple(checks)
