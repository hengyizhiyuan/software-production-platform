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
        self.tags: list[str] = []
        self._heading: list[str] | None = None
        self._paragraph: list[str] | None = None
        self._list_stack: list[int] = []
        self._item_stack: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        del attrs
        self.tags.append(tag)
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
    page_aliases = {path: Path(path).stem.replace("-", "_") + "_page"
                    for path in html_targets}
    file_aliases = {path: Path(path).name.replace(".", "_")
                    for path in html_targets}
    supported = tuple(fact for fact in facts if fact.subject.startswith("page.")
                      or fact.subject.startswith("artifact.file.")
                      or any(fact.subject.startswith(f"{path}.") for path in html_targets)
                      or any(fact.subject.startswith(f"{alias}.")
                             for alias in (*page_aliases.values(), *file_aliases.values()))
                      or fact.subject in {"index.h1_text", "index.ordered_list_items",
                                          "repository.change_scope", "change.file_scope",
                                          "work.modifiable_files", "work.change_scope",
                                          "work.new_file_count", "deliverable.page",
                                          "artifact.target_file", "change.allowed_paths",
                                          "acceptance.verification",
                                          "repository.change_scope_file_count",
                                          "artifact.change_scope",
                                          "acceptance.artifact_content"}
                      or fact.subject.startswith("acceptance.ordered_list")
                      or fact.subject == "repository.changed_files")
    if not supported:
        return ()
    observed: dict[str, _HTMLFacts | None] = {}
    checks: list[dict[str, object]] = []
    ordered_subjects = {"page.ordered_list.items", "page.ordered_list.item_texts",
                        "page.list.item_text"}
    ordered_scopes = set()
    for fact in supported:
        if fact.subject in ordered_subjects and fact.relation is SemanticRelation.ORDERED_COMPONENT:
            if fact.scope is not None:
                ordered_scopes.add(fact.scope)
            elif len(html_targets) == 1:
                ordered_scopes.update(html_targets)
    for fact in supported:
        path = fact.scope or (next(iter(html_targets)) if len(html_targets) == 1 else "")
        if (fact.subject == "index.ordered_list_items"
                and fact.scope == "index.html ordered list"):
            path = "index.html"
        if len(html_targets) == 1 and path not in html_targets:
            only_path = next(iter(html_targets))
            if (fact.subject in {"page.count", "acceptance.artifact_content"}
                    and fact.scope in {"managed Product repository",
                                       "N1 qualification work"}):
                path = only_path
            if (fact.subject.startswith(file_aliases[only_path] + ".")
                    and fact.scope in {f"{only_path} semantic HTML page",
                                       f"the single ordered list in {only_path}"}):
                path = only_path
            elif fact.subject.startswith("artifact.file.") and fact.scope == "work":
                path = only_path
        if fact.subject in {"repository.changed_files", "repository.change_scope",
                            "change.file_scope", "work.modifiable_files",
                            "work.change_scope", "artifact.target_file",
                            "change.allowed_paths", "artifact.file.change_scope",
                            "repository.change_scope_file_count",
                            "index_html.file_scope", "artifact.change_scope"}:
            result = subprocess.run(
                ["git", "-C", str(repository), "diff", "--name-only",
                 contract.source_revision, proposed_revision, "--"],
                check=False, capture_output=True, timeout=15, text=True,
            )
            expected = (tuple(fact.value) if isinstance(fact.value, tuple) else
                        (fact.value,) if fact.subject in {"change.file_scope",
                                                           "artifact.file.change_scope"}
                        and isinstance(fact.value, str) and fact.value in html_targets else
                        (fact.value[:-5],) if fact.subject == "work.change_scope"
                        and isinstance(fact.value, str)
                        and fact.value.endswith(" only")
                        and fact.value[:-5] in html_targets else
                        (fact.value,) if fact.subject == "work.change_scope"
                        and isinstance(fact.value, str)
                        and fact.value in html_targets else
                        (fact.value,) if fact.subject == "artifact.change_scope"
                        and isinstance(fact.value, str)
                        and fact.value in html_targets else
                        (fact.value,) if fact.subject == "artifact.target_file"
                        and isinstance(fact.value, str)
                        and fact.value in html_targets else
                        (fact.value,) if fact.subject == "change.allowed_paths"
                        and isinstance(fact.value, str)
                        and fact.value in html_targets else
                        ("index.html",) if fact.subject == "repository.change_scope"
                        and fact.value == "index.html only" else
                        ("index.html",) if fact.subject == "repository.change_scope_file_count"
                        and fact.value == "only index.html is created or changed" else
                        ("index.html",) if fact.subject == "index_html.file_scope"
                        and fact.value == "index.html only" else ())
            actual = tuple(result.stdout.splitlines()) if result.returncode == 0 else ()
            passed = (fact.relation is (SemanticRelation.EQUALITY
                       if fact.subject == "artifact.target_file" else SemanticRelation.SCOPE)
                      and (fact.qualifiers.get("exclusive") == "true"
                           or fact.qualifiers.get("only") is True
                           or fact.subject in {"repository.change_scope",
                                               "work.modifiable_files",
                                               "change.file_scope",
                                               "artifact.file.change_scope",
                                               "repository.change_scope_file_count",
                                               "index_html.file_scope",
                                               "artifact.change_scope",
                                               "work.change_scope",
                                               "artifact.target_file",
                                               "change.allowed_paths"})
                      and bool(expected) and actual == expected)
            reason = "EXACT_CHANGED_FILES" if passed else "CHANGED_FILE_SCOPE_MISMATCH"
        elif fact.subject == "deliverable.page":
            tree = subprocess.run(
                ["git", "-C", str(repository), "ls-tree", "-r", "--name-only",
                 proposed_revision], check=False, capture_output=True,
                timeout=15, text=True)
            pages = tuple(name for name in tree.stdout.splitlines()
                          if name.endswith(".html")) if tree.returncode == 0 else ()
            passed = (fact.relation is SemanticRelation.CARDINALITY
                      and fact.value == 1 and len(html_targets) == 1
                      and pages == (fact.qualifiers.get("path"),)
                      and pages[0] in html_targets)
            reason = "EXACT_DELIVERABLE_PAGE" if passed else "DELIVERABLE_PAGE_MISMATCH"
        elif fact.subject in {"acceptance.verification",
                                   "acceptance.artifact_content"}:
            bound = tuple(check for check in checks if check["scope"] == path
                          and check["reason"] in {"EXACT_H1", "EXACT_PARAGRAPH"})
            passed = (fact.relation is SemanticRelation.ACCEPTANCE_ASSERTION
                      and fact.value in {
                          "exact heading and paragraph verified",
                          "exact heading and paragraph verified and reviewable Candidate left"}
                      and {check["reason"] for check in bound}
                      == {"EXACT_H1", "EXACT_PARAGRAPH"}
                      and all(check["passed"] for check in bound))
            reason = "BOUND_EXACT_TEXT_VERIFICATION" if passed else "EXACT_TEXT_VERIFICATION_MISSING"
        elif fact.subject in {"work.new_file_count", "artifact.file.count"}:
            result = subprocess.run(
                ["git", "-C", str(repository), "diff", "--name-status",
                 contract.source_revision, proposed_revision, "--"],
                check=False, capture_output=True, timeout=15, text=True)
            added = tuple(line.split("\t", 1)[1] for line in result.stdout.splitlines()
                          if line.startswith("A\t")) if result.returncode == 0 else ()
            passed = (fact.relation is SemanticRelation.CARDINALITY
                      and len(added) == fact.value
                      and all(path in html_targets for path in added))
            reason = "EXACT_NEW_FILE_COUNT" if passed else "NEW_FILE_COUNT_MISMATCH"
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
            elif (fact.subject in {"page.heading.text", "page.heading_text",
                                   "page.h1.text", "page.h1_text",
                                   "artifact.file.h1_text",
                                   "index_html.h1_text", "index_html.h1.text",
                                   "page.index_html.h1.text",
                                   f"{path}.h1.text", "index.h1_text",
                                   f"{path}.h1_text",
                                   f"{page_aliases[path]}.h1_text",
                                   f"{file_aliases[path]}.heading_text"}
                    and fact.relation in {SemanticRelation.EQUALITY,
                                          SemanticRelation.ACCEPTANCE_ASSERTION}
                    and isinstance(fact.value, str)
                    and (fact.subject in {"page.h1.text", "page.h1_text",
                                         "page.heading_text",
                                         "page.heading.text", "artifact.file.h1_text",
                                         "index_html.h1_text", "index_html.h1.text",
                                         "page.index_html.h1.text",
                                         f"{path}.h1.text",
                                         "index.h1_text", f"{path}.h1_text",
                                         f"{page_aliases[path]}.h1_text",
                                         f"{file_aliases[path]}.heading_text"}
                         or fact.qualifiers.get("heading_level") == 1
                         or fact.qualifiers.get("exact") is True)):
                passed = (parser.headings == [fact.value]
                          and not any(tag in parser.tags for tag in
                                      ("h2", "h3", "h4", "h5", "h6")))
                reason = "EXACT_H1" if passed else "H1_TEXT_OR_COUNT_MISMATCH"
            elif (fact.subject in {"page.paragraph.text", "page.paragraph_text",
                                   "artifact.file.paragraph_text",
                                   "index_html.paragraph.text",
                                   "page.index_html.paragraph.text",
                                   f"{path}.paragraph.text",
                                   f"{path}.paragraph_text",
                                   f"{page_aliases[path]}.paragraph_text"}
                    and fact.relation in {SemanticRelation.EQUALITY,
                                          SemanticRelation.ACCEPTANCE_ASSERTION}
                    and isinstance(fact.value, str)):
                passed = parser.paragraphs == [fact.value]
                reason = "EXACT_PARAGRAPH" if passed else "PARAGRAPH_TEXT_OR_COUNT_MISMATCH"
            elif (fact.subject in {f"{path}.h1.count", "page.h1.count",
                                   "page.h1_count", "page.heading.count"}
                    and fact.relation is SemanticRelation.CARDINALITY):
                passed = (len(parser.headings) == fact.value
                          and not any(tag in parser.tags for tag in
                                      ("h2", "h3", "h4", "h5", "h6")))
                reason = "EXACT_H1_COUNT" if passed else "H1_COUNT_MISMATCH"
            elif (fact.subject in {f"{path}.paragraph.count", "page.paragraph.count",
                                   "page.paragraph_count"}
                    and fact.relation is SemanticRelation.CARDINALITY):
                passed = len(parser.paragraphs) == fact.value
                reason = "EXACT_PARAGRAPH_COUNT" if passed else "PARAGRAPH_COUNT_MISMATCH"
            elif (fact.subject in {"page.count", "index_html.page_count"}
                    and fact.relation is SemanticRelation.CARDINALITY):
                tree = subprocess.run(
                    ["git", "-C", str(repository), "ls-tree", "-r", "--name-only",
                     proposed_revision], check=False, capture_output=True,
                    timeout=15, text=True)
                pages = tuple(name for name in tree.stdout.splitlines()
                              if name.endswith(".html")) if tree.returncode == 0 else ()
                passed = pages == (path,) and fact.value == 1
                reason = "EXACT_PAGE_COUNT" if passed else "PAGE_COUNT_MISMATCH"
            elif (fact.subject in {"page.markup", "index_html.markup.semantics"}
                    and fact.relation is SemanticRelation.BEHAVIOR
                    and fact.value == "semantic HTML"):
                passed = all(tag in parser.tags for tag in ("html", "body", "h1", "p"))
                reason = "SEMANTIC_HTML_STRUCTURE" if passed else "SEMANTIC_HTML_STRUCTURE_MISSING"
            elif (fact.subject in {"page.entry_file", "page.path"}
                    and fact.relation is SemanticRelation.EQUALITY):
                passed = fact.value == path
                reason = "EXACT_ENTRY_FILE" if passed else "ENTRY_FILE_MISMATCH"
            elif (fact.subject in {"index.ordered_list_items", "page.list.item_count",
                                   "index_html.ordered_list_count",
                                   "index_html.list_item_acceptance_count"}
                    and fact.relation is SemanticRelation.CARDINALITY):
                passed = (path in ordered_scopes
                          and len(parser.ordered_lists) == 1
                          and (len(parser.ordered_lists[0]) == fact.value
                               if fact.subject != "index_html.ordered_list_count"
                               else fact.value == 1))
                reason = "BOUND_EXACT_LIST_COUNT" if passed else "ORDERED_VALUES_OR_COUNT_MISMATCH"
            elif (fact.subject == f"{file_aliases[path]}.ordered_list.item_count"
                    and fact.relation is SemanticRelation.CARDINALITY):
                passed = (path in ordered_scopes
                          and len(parser.ordered_lists) == 1
                          and len(parser.ordered_lists[0]) == fact.value)
                reason = "BOUND_EXACT_LIST_COUNT" if passed else "ORDERED_VALUES_OR_COUNT_MISMATCH"
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
            elif (fact.subject == "index_html.list_item_occurrence"
                    and fact.relation is SemanticRelation.ACCEPTANCE_ASSERTION):
                passed = (path in ordered_scopes
                          and fact.value ==
                          "each of the fourteen texts appears exactly once, in order"
                          and len(parser.ordered_lists) == 1
                          and len(parser.ordered_lists[0]) == 14)
                reason = "BOUND_TO_ORDERED_FACT" if passed else "ORDERED_FACT_MISSING"
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
                                  "acceptance.ordered_list_texts",
                                  "page.list.item_count",
                                  "index.ordered_list_items",
                                  "index_html.ordered_list_count",
                                  "index_html.list_item_acceptance_count",
                                  "index_html.list_item_occurrence",
                                  *(f"{alias}.ordered_list.item_count"
                                    for alias in file_aliases.values())}
                or (check["subject"] == "page.ordered_list.items"
                    and check["reason"] == "BOUND_TO_ORDERED_FACT")) \
                and check["scope"] in failed_ordered_scopes:
            check["passed"] = False
    return tuple(checks)
