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
        self.paragraphs: list[str] = []
        self.ordered_lists: list[list[str]] = []
        self.outside_list_text: list[str] = []
        self._heading: list[str] | None = None
        self._paragraph: list[str] | None = None
        self._list_stack: list[int] = []
        self._item_stack: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        del attrs
        if tag == "h1":
            self._heading = []
        elif tag == "p":
            self._paragraph = []
        elif tag == "ol":
            self._list_stack.append(len(self.ordered_lists))
            self.ordered_lists.append([])
        elif tag == "li" and self._list_stack:
            self._item_stack.append([])

    def handle_data(self, data: str) -> None:
        if self._heading is not None:
            self._heading.append(data)
        if self._paragraph is not None:
            self._paragraph.append(data)
        if self._item_stack:
            self._item_stack[-1].append(data)
        else:
            self.outside_list_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self._heading is not None:
            self.headings.append("".join(self._heading).strip())
            self._heading = None
        elif tag == "p" and self._paragraph is not None:
            self.paragraphs.append("".join(self._paragraph).strip())
            self._paragraph = None
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
    html_targets = {target.path for target in contract.exact_targets
                    if target.path.endswith(".html")}
    supported = tuple(fact for fact in facts if fact.subject.startswith("page.")
                      or any(fact.subject.startswith(f"{path}.") for path in html_targets)
                      or fact.subject.startswith("acceptance.ordered_list")
                      or fact.subject == "repository.changed_files")
    if not supported:
        return ()
    observed: dict[str, _HTMLFacts | None] = {}
    checks: list[dict[str, object]] = []
    ordered_subjects = {"page.ordered_list.items", "page.ordered_list.item_texts"}
    ordered_scopes = set()
    for fact in supported:
        if fact.subject in ordered_subjects and fact.relation is SemanticRelation.ORDERED_COMPONENT:
            if fact.scope is not None:
                ordered_scopes.add(fact.scope)
            elif len(html_targets) == 1:
                ordered_scopes.update(html_targets)
    for fact in supported:
        path = fact.scope or (next(iter(html_targets)) if len(html_targets) == 1 else "")
        if fact.subject == "repository.changed_files":
            result = subprocess.run(
                ["git", "-C", str(repository), "diff", "--name-only",
                 contract.source_revision, proposed_revision, "--"],
                check=False, capture_output=True, timeout=15, text=True,
            )
            expected = tuple(fact.value) if isinstance(fact.value, tuple) else ()
            actual = tuple(result.stdout.splitlines()) if result.returncode == 0 else ()
            passed = (fact.relation is SemanticRelation.SCOPE
                      and fact.qualifiers.get("exclusive") == "true"
                      and bool(expected) and actual == expected)
            reason = "EXACT_CHANGED_FILES" if passed else "CHANGED_FILE_SCOPE_MISMATCH"
        elif path not in html_targets:
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
            elif (fact.subject in {"page.heading.text", "page.h1.text",
                                   f"{path}.h1.text"}
                    and fact.relation is SemanticRelation.EQUALITY
                    and isinstance(fact.value, str)
                    and (fact.subject in {"page.h1.text", f"{path}.h1.text"}
                         or fact.qualifiers.get("heading_level") == 1)):
                passed = parser.headings == [fact.value]
                reason = "EXACT_H1" if passed else "H1_TEXT_OR_COUNT_MISMATCH"
            elif (fact.subject in {"page.paragraph.text", f"{path}.paragraph.text"}
                    and fact.relation is SemanticRelation.EQUALITY
                    and isinstance(fact.value, str)):
                passed = parser.paragraphs == [fact.value]
                reason = "EXACT_PARAGRAPH" if passed else "PARAGRAPH_TEXT_OR_COUNT_MISMATCH"
            elif (fact.subject == f"{path}.h1.count"
                    and fact.relation is SemanticRelation.CARDINALITY):
                passed = len(parser.headings) == fact.value
                reason = "EXACT_H1_COUNT" if passed else "H1_COUNT_MISMATCH"
            elif (fact.subject == f"{path}.paragraph.count"
                    and fact.relation is SemanticRelation.CARDINALITY):
                passed = len(parser.paragraphs) == fact.value
                reason = "EXACT_PARAGRAPH_COUNT" if passed else "PARAGRAPH_COUNT_MISMATCH"
            elif (fact.subject in ordered_subjects
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
            elif (fact.subject == "page.ordered_list.item_occurrence"
                    and fact.relation is SemanticRelation.CARDINALITY):
                passed = (path in ordered_scopes and fact.value == 1
                          and len(parser.ordered_lists) == 1)
                reason = "BOUND_TO_ORDERED_FACT" if passed else "ORDERED_FACT_MISSING_OR_OCCURRENCE_MISMATCH"
            elif (fact.subject in {"page.ordered_list.items",
                                   "acceptance.ordered_list_texts"}
                    and fact.relation is SemanticRelation.ACCEPTANCE_ASSERTION):
                # Assertions inherit the exact ordered-value check. A free-text
                # assertion or a list without the admitted values cannot PASS.
                expected_count = fact.qualifiers.get("count")
                passed = (path in ordered_scopes and len(parser.ordered_lists) == 1
                          and (fact.subject != "acceptance.ordered_list_texts"
                               or (fact.value is True
                                   and expected_count == len(parser.ordered_lists[0])
                                   and fact.qualifiers.get("order") == "fixed"
                                   and fact.qualifiers.get("occurrence") == "once")))
                reason = "BOUND_TO_ORDERED_FACT" if passed else "ORDERED_FACT_MISSING"
            else:
                passed, reason = False, "SEMANTIC_FACT_PROFILE_UNSUPPORTED"
        checks.append({"fact_id": str(fact.fact_id), "subject": fact.subject,
                       "scope": path, "passed": passed, "reason": reason})
    # An assertion and its ordered value must share the outcome.
    failed_ordered_scopes = {check["scope"] for check in checks
                             if check["subject"] in ordered_subjects
                             and not check["passed"]}
    for check in checks:
        if (check["subject"] in {"page.ordered_list.item_occurrence",
                                  "acceptance.ordered_list_texts"}
                or (check["subject"] == "page.ordered_list.items"
                    and check["reason"] == "BOUND_TO_ORDERED_FACT")) \
                and check["scope"] in failed_ordered_scopes:
            check["passed"] = False
    return tuple(checks)
