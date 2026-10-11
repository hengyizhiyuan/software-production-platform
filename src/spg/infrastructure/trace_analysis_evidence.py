"""Read-only evidence adapters for the existing Native tool registry."""
from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from uuid import NAMESPACE_URL, UUID, uuid5

from spg.domain.native_execution import EffectCondition, ToolExecutionResult, canonical_digest
from spg.domain.trace_analysis import AnalysisReport
from spg.evaluation.work_diagnostic_export import Redactor
from spg.executor.tools import NativeToolRegistry, ToolDefinition
from spg.infrastructure.git_workspace import GitExactReality


def text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str)


class EvidenceCatalog:
    """Exact snapshot references; model text never acquires instruction authority."""

    def __init__(self, snapshot: dict):
        self.snapshot = snapshot
        self.digest = canonical_digest(snapshot)
        self.records: dict[str, dict] = {}
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
        body = text(value)
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
            "trust": "UNTRUSTED_EVIDENCE_ONLY",
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
        def citation(c, *, repository=False):
            row = self.records.get(str(c.evidence_id))
            if not row or str(c.evidence_id) not in self.observed:
                raise ValueError("CITATION_NOT_OBSERVED")
            if not any(c.quote in excerpt for excerpt in self.observed_excerpts.get(str(c.evidence_id), [])):
                raise ValueError("CITATION_QUOTE_MISMATCH")
            if repository and not row["repository"]:
                raise ValueError("REPOSITORY_CITATION_REQUIRED")
        facts = [report.original_objective, report.expected_outcome,
                 report.actual_execution_path, report.current_state, *report.timeline,
                 *(finding.fact for finding in report.findings)]
        for fact in facts:
            for c in fact.citations:
                citation(c)
        for finding in report.findings:
            for c in finding.repository_citations:
                citation(c, repository=True)
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
        )
        return NativeToolRegistry(tuple(ToolDefinition(
            identity=identity, version="1", description=description,
            input_schema={"type": "object", "properties": props, "required": required,
                          "additionalProperties": False},
            effect_classification="READ" if identity != "analysis.submit" else "LOCAL_EVIDENCE",
            handler=self.execute,
        ) for identity, description, props, required in definitions))

    async def execute(self, request):
        identity, args = request.proposal.tool_identity, request.proposal.arguments
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
            elif identity == "analysis.submit":
                report = AnalysisReport.model_validate(args["report"])
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
            self.accepted_report = None if identity == "analysis.submit" else self.accepted_report
            if hasattr(error, "errors"):
                issues = [{"location": list(item["loc"]), "type": item["type"]}
                          for item in error.errors(include_input=False, include_context=False)[:12]]
            else:
                issues = [{"type": type(error).__name__, "reason": str(error)[:160]}]
            output = {"verification": "FAIL", "issues": issues,
                      "effect_observed": False, "repair": "Same contract only; preserve UNKNOWN and permissions."}
            condition = EffectCondition.FAILED
            if identity == "analysis.submit":
                self.verification_receipts.append(output)
        return ToolExecutionResult(delivery_id=request.delivery_id, tool_identity=identity,
                                   condition=condition, output=output,
                                   output_digest=canonical_digest(output))
