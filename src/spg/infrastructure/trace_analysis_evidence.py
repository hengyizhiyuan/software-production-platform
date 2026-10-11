"""Read-only evidence adapters for the existing Native tool registry."""
from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from uuid import NAMESPACE_URL, UUID, uuid5
from copy import deepcopy

from spg.domain.native_execution import EffectCondition, ToolExecutionResult, canonical_digest
from spg.domain.trace_analysis import AnalysisReport
from spg.evaluation.work_diagnostic_export import Redactor
from spg.executor.tools import NativeToolRegistry, ToolDefinition
from spg.infrastructure.git_workspace import GitExactReality


def text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str)


def public_report_candidate(value):
    """Keep the declared public engineering rationale, suppress hidden reasoning."""
    redactor = Redactor(text_limit=40000)
    clean = redactor.clean(value)
    if isinstance(value, dict) and isinstance(value.get("findings"), list):
        for index, finding in enumerate(value["findings"]):
            if isinstance(finding, dict) and isinstance(finding.get("analysis"), str):
                clean["findings"][index]["analysis"] = redactor.clean(finding["analysis"])
    return clean


class CitationRejected(ValueError):
    def __init__(self, reason, location, evidence_id):
        super().__init__(reason)
        self.location, self.evidence_id = location, str(evidence_id)


class EvidenceCatalog:
    """Exact snapshot references; model text never acquires instruction authority."""

    def __init__(self, snapshot: dict):
        self.snapshot = snapshot
        self.digest = canonical_digest(snapshot)
        self.records: dict[str, dict] = {}
        self.values: dict[str, object] = {}
        self.observed: set[str] = set()
        self.observed_excerpts: dict[str, list[str]] = {}
        self.add("capture", "/capture", snapshot.get("capture", {}))
        self.add("work", "/lifecycle/work", snapshot["lifecycle"].get("work", {}))
        self.add("intent", "/lifecycle/first_human_input",
                 snapshot["lifecycle"].get("first_human_input"))
        self.add("limits", "/capture_warnings", {
            "warnings": snapshot.get("capture_warnings", []),
            "missing": snapshot.get("missing_evidence", []),
            "truncation": snapshot["lifecycle"].get("capture_truncation", {}),
        })
        lifecycle = snapshot["lifecycle"]
        for group in ("timeline", "semantic", "contexts", "plan_history", "steering",
                      "units", "verification", "recovery", "candidate", "guardian",
                      "manifests", "acceptance", "governance", "conversation", "served_delivery"):
            values = lifecycle.get(group)
            if isinstance(values, list):
                for index, value in enumerate(values):
                    self.add(group, f"/lifecycle/{group}/{index}", value)
            elif values:
                self.add(group, f"/lifecycle/{group}", values)
        for table, rows in (lifecycle.get("advanced", {}).get("owners", {}) or {}).items():
            for index, row in enumerate(rows):
                self.add(table, f"/lifecycle/advanced/owners/{table}/{index}", row)

    def add(self, group: str, pointer: str, value, *, repository=False):
        evidence_id = str(uuid5(NAMESPACE_URL, f"watt-trace:{self.digest}:{pointer}"))
        body = value if isinstance(value, str) else text(value)
        if repository and isinstance(value, dict):
            field = next((key for key in ("content", "matches", "patch") if key in value), None)
            if field:
                body = text({key: child for key, child in value.items() if key != field}) + "\nSOURCE_EXCERPT\n" + value[field]
        self.records[evidence_id] = {
            "evidence_id": evidence_id, "group": group, "pointer": pointer,
            "source_ref": value.get("source_ref") if isinstance(value, dict) else None,
            "content_digest": canonical_digest({"value": value}),
            "repository": repository, "body": body,
            "condition": value.get("condition") if isinstance(value, dict) else None,
        }
        self.values[evidence_id] = value
        return evidence_id

    def index(self, group=None, query=None, offset=0, limit=30):
        if offset < 0 or limit < 1 or limit > 40:
            raise ValueError("index requires offset >= 0 and 1 <= limit <= 40")
        rows = [row for row in self.records.values()
                if (not group or group == row["group"])
                and (not query or query.lower() in row["body"].lower())]
        return {"total": len(rows), "offset": offset, "next_offset":
                offset + limit if offset + limit < len(rows) else None,
                "items": [{k: v for k, v in row.items() if k != "body"}
                          | {"excerpt": row["body"][:300]} for row in rows[offset:offset + limit]]}

    def read(self, evidence_id: str, offset=0, limit=16000):
        if offset < 0 or limit < 1 or limit > 24000:
            raise ValueError("read requires offset >= 0 and 1 <= limit <= 24000")
        row = self.records[evidence_id]
        self.observed.add(evidence_id)
        body = row["body"]
        self.observed_excerpts.setdefault(evidence_id, []).append(body[offset:offset + limit])
        return {k: v for k, v in row.items() if k != "body"} | {
            "content": body[offset:offset + limit], "offset": offset,
            "total_characters": len(body), "next_offset":
            offset + limit if offset + limit < len(body) else None,
            "trust": "MODEL_PROPOSAL_NOT_OWNER_EVIDENCE" if row["group"] == "analysis_draft" else "UNTRUSTED_EVIDENCE_ONLY",
        }

    def seed(self):
        groups = {}
        for row in self.records.values():
            groups[row["group"]] = groups.get(row["group"], 0) + 1
        initial = [self.read(row["evidence_id"], limit=6000)
                   for row in self.records.values()
                   if row["group"] in {"capture", "work", "intent", "limits"}]
        used = len(text(initial))
        counts = {}
        for row in self.records.values():
            group = row["group"]
            important = (group in {"self_refine_events", "baseline_candidates", "work_delivery_acceptances", "runtime_commits"}
                         or (group in {"execution_steps", "effect_receipts"} and row["condition"] == "FAILED"))
            if not important or counts.get(group, 0) >= 3 or used > 28000:
                continue
            counts[group] = counts.get(group, 0) + 1
            if len(row["body"]) <= 4000:
                parts = [self.read(row["evidence_id"], limit=4000)]
            else:
                parts = [self.read(row["evidence_id"], limit=2000),
                         self.read(row["evidence_id"], offset=len(row["body"]) - 2000, limit=2000)]
            initial.extend(parts)
            used += len(text(parts))
        return {"snapshot_digest": self.digest, "groups": groups,
                "initial_evidence": initial,
                "selection_policy": "Identity/limits plus bounded failure, refinement and final-owner excerpts. Omitted records remain pageable; excerpts are not a completeness claim.",
                "rule": "Use evidence.index/read to investigate owners, failed steps, receipts, contracts, context and recovery. Counts are projections, not deduplicated execution totals."}

    def validate(self, report: AnalysisReport):
        if str(report.work_id) != str(self.snapshot["work_id"]):
            raise ValueError("REPORT_WORK_ID_MISMATCH")
        errors = []
        def strings(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for child in value.values():
                    yield from strings(child)
            elif isinstance(value, list):
                for child in value:
                    yield from strings(child)
        def citation(c, location, *, repository=False):
            row = self.records.get(str(c.evidence_id))
            if not row or str(c.evidence_id) not in self.observed:
                raise CitationRejected("CITATION_NOT_OBSERVED", location, c.evidence_id)
            if row["group"] == "analysis_draft":
                raise CitationRejected("MODEL_PROPOSAL_NOT_OWNER_EVIDENCE", location, c.evidence_id)
            excerpts = self.observed_excerpts.get(str(c.evidence_id), [])
            literal = any(c.quote in excerpt for excerpt in excerpts)
            # Exact decoded JSON string quotes are legitimate only when their
            # exact encoded substring was returned. No fuzzy normalization and
            # no access to an unread tail of the original record are permitted.
            encoded = json.dumps(c.quote, ensure_ascii=False)[1:-1]
            decoded = (any(c.quote in value for value in strings(self.values[str(c.evidence_id)]))
                       and any(encoded in excerpt for excerpt in excerpts))
            if not literal and not decoded:
                raise CitationRejected("CITATION_QUOTE_MISMATCH", location, c.evidence_id)
            if repository and not row["repository"]:
                raise CitationRejected("REPOSITORY_CITATION_REQUIRED", location, c.evidence_id)
        facts = [(name, getattr(report, name)) for name in (
            "original_objective", "expected_outcome", "actual_execution_path", "current_state")]
        facts += [(("timeline", i), fact) for i, fact in enumerate(report.timeline)]
        facts += [(("findings", i, "fact"), finding.fact) for i, finding in enumerate(report.findings)]
        for name, fact in facts:
            prefix = list(name) if isinstance(name, tuple) else [name]
            for i, c in enumerate(fact.citations):
                try:
                    citation(c, prefix + ["citations", i])
                except CitationRejected as error:
                    errors.append(error)
        for index, finding in enumerate(report.findings):
            for i, c in enumerate(finding.repository_citations):
                try:
                    citation(c, ["findings", index, "repository_citations", i], repository=True)
                except CitationRejected as error:
                    errors.append(error)
        if errors:
            error = errors[0]
            error.issues = [{"type": "CitationRejected", "reason": str(item),
                             "location": item.location, "evidence_id": item.evidence_id}
                            for item in errors[:12]]
            raise error
        failure_ids = {eid for eid, row in self.records.items()
                       if (row["group"] in {"execution_steps", "effect_receipts"}
                           and row["condition"] == "FAILED") or row["group"] == "self_refine_events"}
        cited = {str(c.evidence_id) for finding in report.findings for c in finding.fact.citations}
        if failure_ids and not (failure_ids & cited):
            raise ValueError("OBSERVED_INCIDENT_REQUIRES_FINDING_WITH_ORIGINAL_OWNER_CITATION")
        # This is citation/structure verification. It cannot prove that prose
        # follows logically from the quotes or promote hypotheses to findings.


class RepositorySnapshot:
    """No checkout, fetch, shell, arbitrary revision or runtime source mutation."""

    def __init__(self, *, key: str, path: Path, revision: str, roots: tuple[str, ...]):
        if not re.fullmatch(r"[0-9a-f]{40,64}", revision):
            raise ValueError("repository snapshot requires an exact commit oid")
        self.key, self.path, self.revision, self.roots = key, path.resolve(), revision, roots
        self.tree = self.git("rev-parse", f"{revision}^{{tree}}").strip()

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.path), *args],
                                capture_output=True, timeout=20, check=False)
        if result.returncode:
            raise ValueError("EXACT_REPOSITORY_EVIDENCE_UNAVAILABLE")
        if len(result.stdout) > 2_000_000:
            raise ValueError("REPOSITORY_QUERY_CAPACITY_EXCEEDED")
        return result.stdout.decode("utf-8", errors="replace")

    def safe_path(self, value):
        path = PurePosixPath(value)
        if (path.is_absolute() or ".." in path.parts or "\\" in value
                or not any(root == "." or value == root or value.startswith(root.rstrip("/") + "/")
                           for root in self.roots)
                or any(part.startswith(".") for part in path.parts)
                or any(word in value.lower() for word in ("holdout", "credential", "secret", ".env"))):
            raise ValueError("REPOSITORY_PATH_NOT_ADMITTED")
        return str(path)

    def native_read_scope(self):
        if "." not in self.roots:
            return self.roots
        paths = self.git("ls-tree", "--name-only", self.revision).splitlines()
        admitted = []
        for path in paths:
            try:
                admitted.append(self.safe_path(path))
            except ValueError:
                continue
        if len(admitted) > 100:
            raise ValueError("SOURCE_SCOPE_CAPACITY_EXCEEDED")
        return tuple(admitted)

    def read(self, path, start_line=1, lines=120):
        path = self.safe_path(path)
        if start_line < 1 or lines < 1 or lines > 200:
            raise ValueError("repository read requires start_line >= 1 and 1 <= lines <= 200")
        mode = self.git("ls-tree", self.revision, "--", path).split()[0]
        if mode not in {"100644", "100755"}:
            raise ValueError("REPOSITORY_ENTRY_NOT_REGULAR_FILE")
        size = int(self.git("cat-file", "-s", f"{self.revision}:{path}"))
        if size > 1_000_000:
            raise ValueError("REPOSITORY_BLOB_CAPACITY_EXCEEDED")
        data, blob = GitExactReality().read_blob(self.path, self.revision, path)
        rows = data.decode("utf-8").splitlines()
        excerpt = "\n".join(f"{i + 1}: {line}" for i, line in
                            enumerate(rows) if start_line - 1 <= i < start_line - 1 + lines)
        return {"repository": self.key, "revision": self.revision, "tree": self.tree,
                "path": path, "blob": blob, "start_line": start_line,
                "total_lines": len(rows), "next_line": start_line + lines
                if start_line + lines <= len(rows) else None,
                "content": Redactor(text_limit=24000).clean(excerpt)}

    def search(self, query, path):
        path = self.safe_path(path)
        if not query or len(query) > 200:
            raise ValueError("repository query must contain 1..200 characters")
        # grep exit 1 means no matches; all other failures remain unavailable.
        result = subprocess.run(["git", "-C", str(self.path), "grep", "-n", "-F",
                                 "-e", query, self.revision, "--", path],
                                capture_output=True, timeout=20, check=False)
        if result.returncode not in {0, 1}:
            raise ValueError("REPOSITORY_QUERY_FAILED")
        output = result.stdout.decode("utf-8", errors="replace")
        permitted = []
        for line in output.splitlines():
            matched_path = line.removeprefix(self.revision + ":").split(":", 1)[0]
            try:
                self.safe_path(matched_path)
            except ValueError:
                continue
            permitted.append(line)
        output = "\n".join(permitted)
        return {"repository": self.key, "revision": self.revision, "tree": self.tree,
                "matches": Redactor(text_limit=16000).clean(output[:16000]),
                "truncated": len(output) > 16000}

    def diff(self, baseline: "RepositorySnapshot"):
        if baseline.path != self.path:
            raise ValueError("DIFF_REPOSITORY_IDENTITY_MISMATCH")
        paths = self.git("diff", "--name-only", baseline.revision, self.revision, "--").splitlines()
        allowed = []
        for path in paths:
            try:
                allowed.append(self.safe_path(path))
            except ValueError:
                continue
        if len(allowed) > 100:
            raise ValueError("DIFF_PATH_CAPACITY_EXCEEDED")
        patch = self.git("diff", "--no-ext-diff", "--no-textconv", baseline.revision,
                         self.revision, "--", *allowed) if allowed else ""
        return {"repository": self.key, "baseline": baseline.revision,
                "revision": self.revision, "tree": self.tree,
                "changed_paths": allowed, "excluded_paths": len(paths) - len(allowed),
                "patch": Redactor(text_limit=24000).clean(patch[:24000]),
                "truncated": len(patch) > 24000}


class AnalysisTools:
    def __init__(self, catalog: EvidenceCatalog, repositories: dict[str, RepositorySnapshot]):
        self.catalog, self.repositories = catalog, repositories
        self.accepted_report = None
        self.accepted_digest = None
        self.verification_receipts = []
        self.drafts = {}

    def registry(self):
        definitions = (
            ("evidence.index", "List exact Trace/Owner evidence references; page with next_offset.",
             {"group": {"type": "string"}, "query": {"type": "string"},
              "offset": {"type": "integer"}, "limit": {"type": "integer"}}, []),
            ("evidence.read", "Read an evidence UUID, retaining exact source and digest; page long content.",
             {"evidence_id": {"type": "string"}, "offset": {"type": "integer"},
              "limit": {"type": "integer"}}, ["evidence_id"]),
            ("repository.read", "Read exact committed source lines; repository key and scope are fixed by the service.",
             {"repository": {"type": "string"}, "path": {"type": "string"},
              "start_line": {"type": "integer"}, "lines": {"type": "integer"}}, ["repository", "path"]),
            ("repository.search", "Search fixed committed source. No shell or workspace reads.",
             {"repository": {"type": "string"}, "path": {"type": "string"},
              "query": {"type": "string"}}, ["repository", "path", "query"]),
            ("repository.diff", "Read related changes between two service-admitted snapshots in the same repository.",
             {"repository": {"type": "string"}, "baseline_repository": {"type": "string"}},
             ["repository", "baseline_repository"]),
            ("analysis.submit", "Verify a structured advisory report. Failures return bounded feedback for same-contract Self-Refine. Use the supplied JSON schema.",
             {"report": {"type": "object"}}, ["report"]),
            ("analysis.revise", "Explicitly correct a retained rejected report using bounded remove/replace JSON Pointer edits. Revalidate the entire report without regenerating it. This changes advisory artifacts only.",
             {"draft_id": {"type": "string"}, "edits": {"type": "array", "minItems": 1, "maxItems": 24,
              "items": {"type": "object", "properties": {"op": {"enum": ["remove", "replace"]},
                        "path": {"type": "string"}, "value": {}},
                        "required": ["op", "path"], "additionalProperties": False}}}, ["draft_id", "edits"]),
        )
        def schema(identity, props, required):
            props = deepcopy(props)
            result = {"type": "object", "properties": props, "required": required,
                      "additionalProperties": False}
            if identity == "evidence.index":
                props["offset"]["minimum"] = 0
                props["limit"].update(minimum=1, maximum=40)
            if identity == "evidence.read":
                props["offset"]["minimum"] = 0
                props["limit"].update(minimum=1, maximum=24000)
            if identity == "repository.read":
                props["start_line"]["minimum"] = 1
                props["lines"].update(minimum=1, maximum=200)
            if identity == "repository.search":
                props["query"].update(minLength=1, maxLength=200)
            if identity == "analysis.submit":
                report_schema = AnalysisReport.model_json_schema()
                result["$defs"] = report_schema.pop("$defs")
                props["report"] = report_schema
            return result
        return NativeToolRegistry(tuple(ToolDefinition(
            identity=identity, version="1", description=description,
            input_schema=schema(identity, props, required),
            effect_classification="LOCAL_EVIDENCE" if identity.startswith("analysis.") else "READ",
            handler=self.execute,
        ) for identity, description, props, required in definitions))

    async def execute(self, request):
        identity, args = request.proposal.tool_identity, request.proposal.arguments
        draft_id, candidate = None, None
        try:
            if identity == "evidence.index":
                output = self.catalog.index(**args)
            elif identity == "evidence.read":
                output = self.catalog.read(**args)
            elif identity.startswith("repository."):
                args = dict(args)
                repo = self.repositories[args.pop("repository")]
                import asyncio
                if identity == "repository.diff":
                    value = await asyncio.to_thread(repo.diff, self.repositories[args.pop("baseline_repository")])
                else:
                    value = await asyncio.to_thread(repo.read if identity == "repository.read" else repo.search, **args)
                eid = self.catalog.add("repository", f"repository/{repo.key}/{canonical_digest(value)}",
                                       value, repository=True)
                output = self.catalog.read(eid, limit=24000)
            elif identity in {"analysis.submit", "analysis.revise"}:
                if identity == "analysis.submit":
                    candidate = args["report"]
                else:
                    candidate = deepcopy(self.drafts[args["draft_id"]])
                    edits = args["edits"]
                    if not 1 <= len(edits) <= 24:
                        raise ValueError("REPORT_EDIT_CAPACITY_EXCEEDED")
                    for edit in edits:
                        if set(edit) - {"op", "path", "value"} or edit["op"] not in {"remove", "replace"}:
                            raise ValueError("REPORT_EDIT_NOT_ADMITTED")
                        path = edit["path"]
                        if not isinstance(path, str) or not path.startswith("/") or len(path) > 300:
                            raise ValueError("REPORT_EDIT_POINTER_INVALID")
                        parts = [p.replace("~1", "/").replace("~0", "~") for p in path[1:].split("/")]
                        parent = candidate
                        for part in parts[:-1]:
                            parent = parent[int(part)] if isinstance(parent, list) and part.isdigit() else parent[part]
                        last = int(parts[-1]) if isinstance(parent, list) and parts[-1].isdigit() else parts[-1]
                        if edit["op"] == "remove":
                            del parent[last]
                        else:
                            # Replace must reference an existing field; it never
                            # inserts a new path or changes source repositories.
                            parent[last]
                            parent[last] = edit["value"]
                if not isinstance(candidate, dict):
                    raise ValueError("REPORT_DRAFT_NOT_OBJECT")
                if len(text(candidate).encode()) > 128000:
                    raise ValueError("REPORT_DRAFT_CAPACITY_EXCEEDED")
                draft_id = self.catalog.add("analysis_draft", f"analysis-drafts/{canonical_digest(candidate)}",
                                            public_report_candidate(candidate))
                self.drafts[draft_id] = deepcopy(candidate)
                report = AnalysisReport.model_validate(candidate)
                self.catalog.validate(report)
                self.accepted_report = report.model_dump(mode="json")
                self.accepted_digest = canonical_digest(self.accepted_report)
                output = {"verification": "CITATIONS_AND_STRUCTURE_PASS",
                          "report_digest": self.accepted_digest,
                          "semantic_correctness": "HUMAN_REVIEW_REQUIRED",
                          "production_authority": "NONE"}
                self.verification_receipts.append(output)
            else:
                raise ValueError("TOOL_NOT_ADMITTED")
            condition = EffectCondition.SETTLED
        except (ValueError, KeyError, TypeError, UnicodeError, IndexError) as error:
            self.accepted_report = None if identity.startswith("analysis.") else self.accepted_report
            if hasattr(error, "errors"):
                issues = [{"location": list(item["loc"]), "type": item["type"],
                           "reason": Redactor(text_limit=300).clean(item["msg"])}
                          for item in error.errors(include_input=False, include_context=False)[:12]]
            else:
                issues = [{"type": type(error).__name__, "reason": Redactor(text_limit=300).clean(str(error))}]
                if isinstance(error, CitationRejected):
                    issues = getattr(error, "issues", [{"type": "CitationRejected", "reason": str(error),
                             "location": error.location, "evidence_id": error.evidence_id}])
            output = {"verification": "FAIL", "issues": issues,
                      "effect_observed": False, "repair": "Same contract only; preserve UNKNOWN and permissions."}
            if draft_id:
                output["draft_id"] = draft_id
                output["draft_read_tool"] = "evidence.read"
                # Give exact same-candidate lineage feedback without inventing,
                # normalizing, or automatically repairing finding identifiers.
                findings = candidate.get("findings")
                known = [f.get("finding_id") for f in findings if isinstance(f, dict)] if isinstance(findings, list) else []
                output["valid_finding_ids"] = known[:30]
                for section in ("immediate_recovery", "self_refine_opportunities", "platform_improvements", "deferred_items"):
                    items = candidate.get(section)
                    for index, item in enumerate(items if isinstance(items, list) else []):
                        refs = item.get("finding_ids") if isinstance(item, dict) else None
                        if isinstance(refs, list) and any(ref not in known for ref in refs):
                            issues.append({"location": [section, index, "finding_ids"],
                                           "type": "UNKNOWN_FINDING_REFERENCE"})
            condition = EffectCondition.FAILED
            if identity.startswith("analysis."):
                self.verification_receipts.append(output)
        return ToolExecutionResult(delivery_id=request.delivery_id, tool_identity=identity,
                                   condition=condition, output=output,
                                   output_digest=canonical_digest(output))
