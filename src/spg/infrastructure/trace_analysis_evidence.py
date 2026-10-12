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
from spg.domain.trace_analysis import AnalysisReport, EvidenceFamily
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


# Producer contracts, not inferred from words in an untrusted log. The transfer
# surface is DeliveryObservationService's download audit; Guardian owns its HTTP
# preview observations. Identity aliases follow existing Native Owner fields.

RELATION_FIELDS = {"pwu_id": "PWU", "work_unit_id": "PWU", "session_id": "SESSION",
                   "attempt_id": "ATTEMPT", "work_id": "WORK", "candidate_id": "CANDIDATE"}

# Only producer-declared references establish incident association. A shared
# attempt/Work, error text or timestamp cannot distinguish incidents in that scope.
RECORD_NAMESPACES = {"effect_receipts": "native-receipt", "execution_steps": "native-inference-step",
                     "execution_effects": "native-effect", "tool_effects": "native-effect", "execution_sessions": "native-session",
                     "execution_attempts": "native-attempt"}
# production_trace exports these same Owner rows in both surfaces.
OWNER_GROUP_PROJECTIONS = {"recovery": "self_refine_events"}

DIRECT_REFERENCE_FIELDS = {"receipt_ref": "native-receipt", "receipt_id": "native-receipt",
                          "inference_step_ref": "native-inference-step", "inference_step_id": "native-inference-step",
                          "effect_ref": "native-effect", "effect_id": "native-effect"}


def time_boundary(field):
    meaning = {"created_at": "记录创建", "updated_at": "记录最后更新",
               "started_at": "记录的开始", "finished_at": "记录的结束",
               "sealed_at": "候选封存", "assessed_at": "保证评估", "committed_at": "运行时提交", "timestamp": "Owner 记录的事件"}[field]
    return f"此时间仅表示{meaning}时间；同一行的其他字段是冻结快照值，不自动证明它们在该时刻已经成立。恢复完成须读取相应更新或结束记录。"


def source_semantics(group, value, repository):
    group = OWNER_GROUP_PROJECTIONS.get(group, group)
    families = ["OWNER_RECORD"]
    if group in {"evidence_check", "evidence_inspection", "analysis_draft"}:
        return {"surface": "DERIVED_SCOPE_LOOKUP" if group == "evidence_check" else
                "DERIVED_OWNER_INSPECTION" if group == "evidence_inspection" else "MODEL_PROPOSAL",
                "families": [], "boundary": "Not an original Owner fact; never cite as historical proof."}
    if group == "served_delivery":
        return {"surface": "DELIVERY_TRANSFER_AUDIT", "families": families + ["DELIVERY_TRANSFER"],
                "boundary": "Download/server-transfer audit. completion_basis is a rule description, not an observed event. An audit object with empty actions does not prove any send completed. Does not prove or disprove preview GET status, browser rendering or client persistence."}
    if group == "guardian":
        if isinstance(value, dict) and any(isinstance(item, dict) and isinstance(item.get("status_code"), int)
                                          for item in (value.get("evidence") or [])):
            families.append("PREVIEW_HTTP")
        return {"surface": "GUARDIAN_ASSURANCE", "families": families,
                "boundary": "Only actual HTTP evidence entries prove preview status/digest. Gate PASS alone does not prove browser rendering or client persistence."}
    if group == "self_refine_events":
        if isinstance(value, dict) and any(key in value for key in RELATION_FIELDS):
            families.append("EXECUTION_RELATIONSHIP")
        return {"surface": "OWNER_REFINEMENT_DIAGNOSIS", "families": families,
                "field_roles": {"diagnostic_evidence": "DIAGNOSIS_NOT_EXECUTION_RECEIPT",
                                "expected_reality": "EXPECTED_NOT_OBSERVED",
                                "observed_reality": "OWNER_RECORDED_OBSERVATION",
                                "repair_hypothesis": "UNVERIFIED_HYPOTHESIS",
                                "known_failure_match": "OWNER_CLASSIFIER_LABEL_NOT_RECURRENCE_PROOF",
                                "refinement_class": "OWNER_CLASSIFIER_LABEL_NOT_CAPABILITY_DEFECT_PROOF",
                                "platform_improvement_candidate_ref": "PROPOSAL_REFERENCE_NOT_VERIFIED_DEFECT"},
                "boundary": "Signals and recovery are recorded Owner diagnoses. Required/rejected/expected behavior lists do not establish executed file changes or the contents of an unavailable rejected candidate. Budget attempt_count and convergence fields do not independently prove model call counts or successful regeneration; inspect original steps/calls and producer source. Execution receipts and exact candidate source/diff are separate observations; causal interpretation remains hypothetical. Known-match/recurring labels and proposal references alone do not establish repeated executions, a reproducible failure or an implementation defect."}
    if repository:
        source_kind = ("EXACT_IMPLEMENTATION_READ" if isinstance(value, dict) and
            all(k in value for k in ("repository", "revision", "path", "blob", "content")) else
            "SOURCE_SEARCH_LOCATOR" if isinstance(value, dict) and
            all(k in value for k in ("repository", "revision", "matches")) else
            "FINAL_NET_DIFF" if isinstance(value, dict) and "changed_paths" in value else
            "UNCLASSIFIED_COMPARISON")
        return {"surface": "COMMITTED_REPOSITORY", "families": families,
                "source_kind": source_kind,
                "boundary": "Exact source at the declared revision is comparison evidence, not historical Worker identity. A final diff proves net changes between the two commits, not the absence of intermediate mutations or external effects; it alone cannot justify rollback decisions or a regeneration history."}
    if not repository and isinstance(value, dict) and any(key in value for key in RELATION_FIELDS):
        families.append("EXECUTION_RELATIONSHIP")
    return {"surface": "ORIGINAL_OWNER_OR_PROJECTION",
            "families": families, "boundary": "A projection is not an independent event. Identifiers prove recorded links, not lifecycle completion."}


def json_field_range(body, pointer):
    """Locate a JSON Pointer in original serialization without recomposing it."""
    if pointer == "":
        return 0, len(body)
    if not isinstance(pointer, str) or not pointer.startswith("/") or len(pointer) > 500:
        raise ValueError("READ_FIELD_REQUIRES_JSON_POINTER")
    decoder = json.JSONDecoder()
    start, end = 0, len(body)
    for token in pointer[1:].split("/"):
        if re.search(r"~(?![01])", token):
            raise ValueError("READ_FIELD_INVALID_ESCAPE")
        key = token.replace("~1", "/").replace("~0", "~")
        while start < end and body[start].isspace():
            start += 1
        kind, cursor, found, index = body[start:start + 1], start + 1, None, 0
        if kind not in {"{", "["}:
            raise ValueError("READ_FIELD_NOT_FOUND")
        while cursor < end:
            while cursor < end and (body[cursor].isspace() or body[cursor] == ","):
                cursor += 1
            if body[cursor:cursor + 1] in {"}", "]", ""}:
                break
            if kind == "{":
                name, cursor = decoder.raw_decode(body, cursor)
                while body[cursor].isspace():
                    cursor += 1
                if body[cursor] != ":":
                    raise ValueError("READ_FIELD_INVALID_JSON")
                cursor += 1
            else:
                name = str(index)
                index += 1
            while body[cursor].isspace():
                cursor += 1
            value_start = cursor
            _, cursor = decoder.raw_decode(body, cursor)
            if name == key:
                found = value_start, cursor
                break
        if found is None:
            raise ValueError("READ_FIELD_NOT_FOUND")
        start, end = found
    return start, end


class EvidenceCatalog:
    """Exact snapshot references; model text never acquires instruction authority."""

    def __init__(self, snapshot: dict):
        self.snapshot = snapshot
        self.digest = canonical_digest(snapshot)
        self.records: dict[str, dict] = {}
        self.values: dict[str, object] = {}
        self.observed: set[str] = set()
        self.observed_excerpts: dict[str, list[str]] = {}
        self.observed_ranges: dict[str, list[tuple[int, int]]] = {}
        self.checks: dict[str, dict] = {}
        self.inspections: dict[str, dict] = {}
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
                      "manifests", "acceptance", "governance", "conversation", "served_delivery", "preview"):
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
            "semantics": source_semantics(group, value, repository),
        }
        self.values[evidence_id] = value
        return evidence_id

    def _range_read(self, evidence_id, start, end):
        frontier = start
        for left, right in sorted(self.observed_ranges.get(evidence_id, [])):
            if left > frontier:
                break
            frontier = max(frontier, right)
            if frontier >= end:
                return True
        return False

    def index(self, group=None, query=None, offset=0, limit=30):
        if offset < 0 or limit < 1 or limit > 40:
            raise ValueError("index requires offset >= 0 and 1 <= limit <= 40")
        rows = [row for row in self.records.values()
                if (not group or group == row["group"])
                and (not query or query.lower() in row["body"].lower())]
        selected = rows[offset:offset + limit]
        # Index snippets are also evidence actually returned to the model.
        # Only that bounded snippet becomes observed, never the unread body.
        for row in selected:
            eid = row["evidence_id"]
            self.observed.add(eid)
            self.observed_excerpts.setdefault(eid, []).append(row["body"][:300])
            self.observed_ranges.setdefault(eid, []).append((0, min(300, len(row["body"]))))
        return {"total": len(rows), "offset": offset, "next_offset":
                offset + limit if offset + limit < len(rows) else None,
                "items": [{k: v for k, v in row.items() if k != "body"}
                          | {"excerpt": row["body"][:300]} for row in selected]}

    def read(self, evidence_id: str, offset=0, limit=16000, *, field=None, _observe=True):
        if offset < 0 or limit < 1 or limit > 24000:
            raise ValueError("read requires offset >= 0 and 1 <= limit <= 24000")
        row = self.records[evidence_id]
        body = row["body"]
        left, right = json_field_range(body, field) if field is not None else (0, len(body))
        start, end = min(right, left + offset), min(right, left + offset + limit)
        if _observe:
            self.observed.add(evidence_id)
            self.observed_excerpts.setdefault(evidence_id, []).append(body[start:end])
            self.observed_ranges.setdefault(evidence_id, []).append((start, end))
        return {k: v for k, v in row.items() if k != "body"} | {
            "content": body[start:end], "offset": offset, "field": field,
            "original_body_range": [start, end],
            "total_characters": right - left, "next_offset":
            offset + limit if offset + limit < right - left else None,
            "trust": "MODEL_PROPOSAL_NOT_OWNER_EVIDENCE" if row["group"] == "analysis_draft" else
                     "DERIVED_SCOPE_LOOKUP_NOT_OWNER_FACT" if row["group"] in {"evidence_check", "evidence_inspection"} else "UNTRUSTED_EVIDENCE_ONLY",
            "related_records": self.related(evidence_id),
            "time_boundaries": {k: time_boundary(k) for k in
                ("created_at", "updated_at", "started_at", "finished_at", "sealed_at", "assessed_at", "committed_at", "timestamp")
                if isinstance(self.values[evidence_id], dict) and isinstance(self.values[evidence_id].get(k), str)},
        }

    def _references(self, evidence_id):
        value = self.values[evidence_id]
        if not isinstance(value, dict):
            return []
        references = []
        for key in ("evidence_references",):
            for i, token in enumerate(value.get(key, []) if isinstance(value.get(key), list) else []):
                if isinstance(token, str):
                    references.append(("/" + key + "/" + str(i), token))
        for prefix, body in (("", value), ("/diagnostic_evidence", value.get("diagnostic_evidence")),
                             ("/observed_reality", value.get("observed_reality"))):
            if isinstance(body, dict):
                for key, namespace in DIRECT_REFERENCE_FIELDS.items():
                    token = body.get(key)
                    if isinstance(token, str):
                        references.append((prefix + "/" + key, token if token.startswith(namespace + ":") else namespace + ":" + token))
        return references

    def association(self, subject_evidence_id, evidence_id):
        subject_evidence_id, evidence_id = str(subject_evidence_id), str(evidence_id)
        subject, other = self.records.get(subject_evidence_id), self.records.get(evidence_id)
        excluded = {"repository", "analysis_draft", "evidence_check", "evidence_inspection"}
        if not subject or not other or subject["group"] in excluded or other["group"] in excluded:
            return {"status": "NOT_ESTABLISHED", "basis": "ORIGINAL_OWNER_RECORDS_REQUIRED"}
        if subject_evidence_id == evidence_id:
            return {"status": "RELATED", "basis": "SAME_ORIGINAL_RECORD"}
        a, b = self.values[subject_evidence_id], self.values[evidence_id]
        same_owner = (OWNER_GROUP_PROJECTIONS.get(subject["group"], subject["group"]) ==
                      OWNER_GROUP_PROJECTIONS.get(other["group"], other["group"]) or
                      RECORD_NAMESPACES.get(subject["group"]) is not None and
                      RECORD_NAMESPACES.get(subject["group"]) == RECORD_NAMESPACES.get(other["group"]))
        if same_owner and isinstance(a, dict) and isinstance(b, dict) and a.get("id") and a.get("id") == b.get("id"):
            return {"status": "RELATED", "basis": "SAME_OWNER_IDENTITY_PROJECTION"}
        if {subject["group"], other["group"]} <= {"capture", "limits"}:
            return {"status": "RELATED", "basis": "SAME_CAPTURE_METADATA"}
        for source_id, target_id in ((subject_evidence_id, evidence_id), (evidence_id, subject_evidence_id)):
            target = self.records[target_id]
            value = self.values[target_id]
            namespace = RECORD_NAMESPACES.get(target["group"])
            if namespace and isinstance(value, dict) and value.get("id"):
                identity = namespace + ":" + str(value["id"])
                for pointer, token in self._references(source_id):
                    if token == identity:
                        return {"status": "RELATED", "basis": "EXPLICIT_OWNER_REFERENCE",
                                "source_evidence_id": source_id, "reference_pointer": pointer,
                                "target_evidence_id": target_id, "reference": token}
        return {"status": "NOT_ESTABLISHED", "basis": "NO_EXPLICIT_OWNER_REFERENCE",
                "limitation": "Shared Work/attempt/component/error/timestamp is not incident identity."}

    def related(self, evidence_id):
        # This lookup is metadata, never an observation of an unread record body.
        if OWNER_GROUP_PROJECTIONS.get(self.records[evidence_id]["group"], self.records[evidence_id]["group"]) not in {"self_refine_events", *RECORD_NAMESPACES}:
            return {"items": [], "truncated": False}
        items = [{"evidence_id": eid, "group": row["group"], "association": relation}
                 for eid, row in self.records.items() if eid != evidence_id
                 and (relation := self.association(evidence_id, eid))["status"] == "RELATED"]
        return {"items": items[:8], "truncated": len(items) > 8,
                "rule": "Read original linked records before quoting. These are recorded links, not causal proof."}

    def inspect(self, subject_evidence_id):
        """Read bounded original fields along explicit incident references.

        Two-hop traversal is retrieval coverage, not transitive fact association.
        Every fact citation still needs its own direct Owner relation. No shared
        Work/attempt match, database lookup, historical absence or authority grant.
        """
        subject_evidence_id = str(subject_evidence_id)
        subject = self.records[subject_evidence_id]
        excluded = {"repository", "analysis_draft", "evidence_check", "evidence_inspection", "timeline", "units"}
        if subject["group"] in excluded:
            raise ValueError("INSPECTION_REQUIRES_ORIGINAL_OWNER")
        selected, frontier, edges = [subject_evidence_id], [subject_evidence_id], []
        omitted = set()
        projections = {}
        for _depth in range(2):
            following = []
            for source_id in frontier:
                for eid, row in list(self.records.items()):
                    if eid in selected or row["group"] in excluded:
                        continue
                    relation = self.association(source_id, eid)
                    if relation["status"] != "RELATED":
                        continue
                    equivalent = next((prior for prior in selected
                        if self.association(prior, eid).get("basis") == "SAME_OWNER_IDENTITY_PROJECTION"
                        and self.records[prior]["body"] == row["body"]), None)
                    if equivalent:
                        projections[eid] = equivalent
                        continue
                    if len(selected) >= 12:
                        omitted.add(eid)
                        continue
                    selected.append(eid)
                    following.append(eid)
                    edges.append({"from": source_id, "to": eid, "association": relation})
            frontier = following
        rows, remaining = [], 18000
        # Use exact fragments of the original serialized body. Field metadata
        # never marks a body or a tail as read; returned fragments alone do.
        for eid in selected:
            row, value = self.records[eid], self.values[eid]
            fields = []
            body = row["body"]
            starts = list(re.finditer(r'^  "(?:[^"\\]|\\.)*": ', body, re.M)) if isinstance(value, dict) else []
            for i, start in enumerate(starts):
                key = json.loads(start.group(0)[2:-2])
                end = starts[i + 1].start() if i + 1 < len(starts) else len(body)
                fragment = body[start.start():end]
                child = value[key]
                state = ("REDACTED" if isinstance(child, str) and child.startswith("[REDACTED") else
                         "EMPTY" if child is None or child == "" or child == [] or child == {} else "PRESENT")
                already_read = self._range_read(eid, start.start(), end)
                if (len(fragment) > 3000 or len(fragment) > remaining) and not already_read:
                    fields.append({"field": "/" + key.replace("~", "~0").replace("/", "~1"),
                                   "availability": state, "read_status": "NOT_READ_CAPACITY", "characters": len(fragment)})
                    continue
                if already_read:
                    fields.append({"field": "/" + key.replace("~", "~0").replace("/", "~1"),
                                   "availability": state, "read_status": "READ", "previous_original_read": True})
                    continue
                remaining -= len(fragment)
                self.observed.add(eid)
                self.observed_excerpts.setdefault(eid, []).append(fragment)
                self.observed_ranges.setdefault(eid, []).append((start.start(), end))
                fields.append({"field": "/" + key.replace("~", "~0").replace("/", "~1"),
                               "availability": state, "read_status": "READ", "original_excerpt": fragment})
            if not isinstance(value, dict):
                part = body[:min(3000, remaining)]
                remaining -= len(part)
                self.observed.add(eid)
                self.observed_excerpts.setdefault(eid, []).append(part)
                self.observed_ranges.setdefault(eid, []).append((0, len(part)))
                fields.append({"field": "", "read_status": "READ" if part == body else "PARTIAL_READ", "original_excerpt": part})
            payload = value.get("request_payload") if isinstance(value, dict) else None
            if isinstance(payload, dict):
                for i, tool in enumerate(payload.get("available_tools", []) if isinstance(payload.get("available_tools"), list) else []):
                    if not isinstance(tool, dict) or not isinstance(tool.get("identity"), str):
                        continue
                    pointer = f"/request_payload/available_tools/{i}/identity"
                    left, right = json_field_range(body, pointer)
                    if right - left > 3000 or right - left > remaining:
                        fields.append({"field": pointer, "availability": "PRESENT", "read_status": "NOT_READ_CAPACITY"})
                        continue
                    remaining -= right - left
                    fragment = self.read(eid, field=pointer, limit=3000)["content"]
                    fields.append({"field": pointer, "availability": "PRESENT", "read_status": "READ",
                        "original_excerpt": fragment, "authority_boundary": "ORIGINAL_OFFERED_TOOL_DEFINITION; not an executed effect or an automatic permission grant"})
            rows.append({"evidence_id": eid, "group": row["group"], "pointer": row["pointer"],
                         "fields": fields, "semantics": row["semantics"]})
        result = {"subject_evidence_id": subject_evidence_id, "records": rows, "edges": edges,
                  "identical_owner_projections": projections,
                  "omitted_records": sorted(omitted), "scope": "EXPLICIT_EXPORTED_OWNER_REFERENCES_UP_TO_TWO_HOPS",
                  "boundary": "Retrieval links are not causal proof or transitive incident identity; absence in one record does not establish absence in another."}
        unread = [(r["evidence_id"], f["field"]) for r in rows for f in r["fields"] if f["read_status"] != "READ"]
        result["bounded_conclusion"] = (
            f"本次关联读取仅限冻结导出 {self.digest} 中主体 {subject_evidence_id} 的显式 Owner 引用（最多两跳）。"
            f"返回 {len(rows)} 条记录，容量未读字段 {len(unread)} 项，省略关联记录 {len(omitted)} 条。"
            "PRESENT 表示该字段已导出；READ 才表示原始片段已返回。REDACTED 表示值被脱敏，EMPTY 表示已导出的空值；二者均不表示历史未保存。"
            "字段未导出、未读取或关联范围外的信息保持 UNKNOWN；单一记录不能证明其他 Owner 或平台历史不存在。"
            "仓库比较不自动证明历史 Worker 版本；创建时间不自动证明后来的恢复状态。")
        iid = self.add("evidence_inspection", "inspections/" + canonical_digest(result), result)
        result["inspection_id"] = iid
        self.inspections[iid] = result
        self.observed.add(iid)
        return result

    def check(self, family, group=None, field=None):
        """Bounded original-snapshot search, before any assertion of absence.

        A full scan is distinguished from its bounded returned examples. Nothing
        here assesses natural-language entailment or writes original Owner state.
        """
        family = EvidenceFamily(family).value
        if field is not None and (len(field) > 200 or not field.startswith("/")):
            raise ValueError("CHECK_FIELD_REQUIRES_JSON_POINTER; use /* to enumerate record fields or /field/* for nested children; bare * is invalid")
        if family in {"PREVIEW_HTTP", "DELIVERY_TRANSFER"} and (group or field):
            raise ValueError("CHECK_SOURCE_SURFACE_FIXED_BY_FAMILY")
        if family == "OWNER_RECORD" and (not group or field is None):
            raise ValueError("OWNER_CHECK_REQUIRES_GROUP_AND_FIELD")
        original = [r for r in self.records.values() if r["group"] not in {"repository", "analysis_draft", "evidence_check", "evidence_inspection"}]
        if group and group not in {r["group"] for r in original}:
            # An unexported group is not proof that its Owner has no records.
            raise ValueError("CHECK_GROUP_NOT_CAPTURED")
        selected = [r for r in original if (not group or group == r["group"])
                    and (family == "OWNER_RECORD" or family in r["semantics"]["families"]
                         or family == "PREVIEW_HTTP" and r["group"] == "guardian")]
        if family == "EXECUTION_RELATIONSHIP":
            selected.sort(key=lambda r: (r["group"] not in {"execution_sessions", "execution_attempts"}, r["group"], r["pointer"]))
        if field and selected:
            root_field = field[1:].split("/", 1)[0].replace("~1", "/").replace("~0", "~")
            roots = sorted({key for row in selected for key in
                            (self.values[row["evidence_id"]].keys()
                             if isinstance(self.values[row["evidence_id"]], dict) else ())})
            if roots and root_field not in roots and root_field != "*":
                raise ValueError("CHECK_SELECTOR_ROOT_NOT_IN_RECORD_SCHEMA; field is relative to each record, "
                                 "not the group array. Available root fields: " + ", ".join(roots[:60]))
        def walk(value, parts, pointer=""):
            if not parts:
                yield pointer, value
                return
            key, *rest = parts
            if key == "*":
                items = enumerate(value) if isinstance(value, list) else value.items() if isinstance(value, dict) else ()
                for name, child in items:
                    yield from walk(child, rest, pointer + "/" + str(name))
            elif isinstance(value, dict) and key in value:
                yield from walk(value[key], rest, pointer + "/" + key)
            elif isinstance(value, list) and key.isdigit() and int(key) < len(value):
                yield from walk(value[int(key)], rest, pointer + "/" + key)
        matches, redacted = [], False
        field_states = {"AVAILABLE": 0, "REDACTED": 0, "EMPTY": 0, "NOT_EXPORTED": 0}
        for row in selected:
            value = self.values[row["evidence_id"]]
            if isinstance(value, str) and value.startswith("[REDACTED"):
                redacted = True
                field_states["REDACTED"] += 1
                continue
            if family == "PREVIEW_HTTP":
                entries = [(f"/evidence/{i}", child) for i, child in enumerate((value.get("evidence") or []) if isinstance(value, dict) else [])
                           if isinstance(child, dict) and isinstance(child.get("status_code"), int)]
            elif family == "DELIVERY_TRANSFER":
                entries = [("", value)]
            elif field:
                entries = list(walk(value, [part.replace("~1", "/").replace("~0", "~") for part in field[1:].split("/")]))
                if not entries:
                    field_states["NOT_EXPORTED"] += 1
            else:
                entries = [("/" + key, child) for key, child in value.items() if key in RELATION_FIELDS]
            for pointer, child in entries:
                if isinstance(child, str) and child.startswith("[REDACTED"):
                    redacted = True
                    field_states["REDACTED"] += 1
                    continue
                if child is None or child == "" or child == [] or child == {}:
                    field_states["EMPTY"] += 1
                    continue
                field_states["AVAILABLE"] += 1
                matches.append({"evidence_id": row["evidence_id"], "group": row["group"],
                    "pointer": row["pointer"] + pointer, "record_id": value.get("id") if isinstance(value, dict) else None,
                    "identity_kind": RELATION_FIELDS.get(pointer.lstrip("/")),
                    "value": child if family != "DELIVERY_TRANSFER" else {
                        "actions": value.get("actions"),
                        "action_count": len(value["actions"]) if isinstance(value.get("actions"), list) else None,
                        "client_received": value.get("client_received"), "client_saved": value.get("client_saved"),
                        "completion_rule_description": value.get("completion_basis"),
                        "interpretation": "PRESENT means an audit object exists, not a completed transfer. Inspect individual actions and their observed states; a rule description alone proves no event."}})
        lifecycle = self.snapshot["lifecycle"]
        partial = bool(lifecycle.get("capture_truncation") or self.snapshot.get("capture_warnings")
                       or lifecycle.get("advanced", {}).get("excluded_due_to_capacity") or redacted)
        result = {"family": family, "group": group, "field": field,
                  "availability": "PRESENT" if matches else "INCOMPLETE_CAPTURE" if partial or not selected else "NOT_OBSERVED_IN_CAPTURE",
                  "scope": "FROZEN_EXPORTED_OWNER_RECORDS_ONLY", "scope_complete": not partial,
                  "searched_records": len(selected), "total_matches": len(matches),
                  "field_states": field_states,
                  "examples": matches[:12], "examples_truncated": len(matches) > 12,
                  "limitation": "No match is limited to this export and selector. Unread or uncaptured evidence cannot prove historical/system absence. HTTP preview, download transfer and browser/client observations are distinct."}
        # Limit the entire field value, not each nested string separately.
        # A request/contract contains many individually small strings; applying
        # only Redactor.text_limit can still return hundreds of KiB in a lookup.
        for example in result["examples"]:
            value = example["value"]
            size = len(text(value).encode("utf-8"))
            if size > 1500:
                example["value"] = {"visibility": "NOT_RETURNED_CAPACITY", "serialized_bytes": size,
                    "value_digest": canonical_digest({"value": value}),
                    "read_required": {"tool": "evidence.read", "evidence_id": example["evidence_id"]},
                    "boundary": "Field is PRESENT; lookup metadata is not an original field read or absence."}
        # Return only bounded examples, even if a field references a large body.
        result = Redactor(text_limit=1500).clean(result)
        result["bounded_conclusion"] = (
            f"仅在冻结导出 {self.digest} 中检查 family={family}, group={group or '(producer scope)'}, "
            f"field={field or '(family observations)'}：availability={result['availability']}，"
            f"匹配 {result['total_matches']} 项，扫描 {result['searched_records']} 条记录。"
            f"字段状态：可用 {field_states['AVAILABLE']}，脱敏 {field_states['REDACTED']}，空值 {field_states['EMPTY']}，未导出 {field_states['NOT_EXPORTED']}。"
            "脱敏表示值不可见，空值表示已导出的空值，均不能推断历史未保存。"
            "这不证明其他字段、其他 Owner、完整响应体或平台历史不存在；未读取、脱敏和未采集须保留 UNKNOWN。")
        eid = self.add("evidence_check", f"checks/{canonical_digest(result)}", result)
        result = dict(result, check_id=eid)
        self.checks[eid] = result
        # Derived checks can substantiate scope/availability, never replace Owner citations.
        self.observed.add(eid)
        return result

    def reality(self):
        return {"families": [self.check(family) for family in (
            "PREVIEW_HTTP", "DELIVERY_TRANSFER", "EXECUTION_RELATIONSHIP")],
            "rule": "Read original examples through evidence.read before causal claims. Reconcile all families in evidence_assessments. Call evidence.check before missing_evidence; never infer missing preview or lineage from another Owner surface."}

    def seed(self):
        groups = {}
        for row in self.records.values():
            groups[row["group"]] = groups.get(row["group"], 0) + 1
        work_id = next(eid for eid, row in self.records.items() if row["group"] == "work")
        # The Work inspection already returns its original fields. Avoid copying
        # the same body twice, and reserve room inside the existing ECF budget
        # for repository provenance and Human focus. Omitted evidence is pageable.
        initial = [self.read(row["evidence_id"], limit=2000)
                   for row in self.records.values()
                   if row["group"] in {"capture", "intent", "limits"}]
        seed = {"snapshot_digest": self.digest, "groups": groups,
                "planning_stage_targets": [eid for eid, row in self.records.items()
                    if row["group"] in {"plan_history", "production_work_units"}][:3],
                "execution_stage_targets": [eid for eid, row in self.records.items()
                    if row["group"] in {"execution_effects", "effect_receipts", "execution_steps"}
                    and isinstance(self.values[eid], dict) and self.values[eid].get("condition") in {"SETTLED", "COMPLETED"}][:3],
                "initial_inspections": [self.inspect(work_id)],
                "evidence_reality": self.reality(),
                "initial_evidence": initial,
                "incident_targets": [{"evidence_id": eid, "group": row["group"], "pointer": row["pointer"]}
                    for eid, row in self.records.items() if row["group"] == "self_refine_events"
                    or row["group"] in {"execution_steps", "effect_receipts"} and row["condition"] == "FAILED"][:12],
                "selection_policy": "Identity/limits plus bounded failure, refinement and final-owner excerpts. Omitted records remain pageable; excerpts are not a completeness claim.",
                "rule": "Use evidence.index/read to investigate owners, failed steps, receipts, contracts, context and recovery. Counts are projections, not deduplicated execution totals."}
        counts = {}
        for row in list(self.records.values()):
            group = row["group"]
            important = (group in {"self_refine_events", "baseline_candidates", "work_delivery_acceptances", "runtime_commits"}
                         or (group in {"execution_steps", "effect_receipts"} and row["condition"] == "FAILED"))
            if not important or counts.get(group, 0) >= 3:
                continue
            reads = [(0, 4000)] if len(row["body"]) <= 4000 else [(0, 2000), (len(row["body"]) - 2000, 2000)]
            # A prospective excerpt must not count as read if it cannot be
            # included in the context actually returned to the model.
            parts = [self.read(row["evidence_id"], offset=offset, limit=limit, _observe=False)
                     for offset, limit in reads]
            if len(text(dict(seed, initial_evidence=initial + parts))) > 44000:
                continue
            counts[group] = counts.get(group, 0) + 1
            initial.extend(self.read(row["evidence_id"], offset=offset, limit=limit)
                           for offset, limit in reads)
        return seed

    def original_field_excerpt(self, evidence_id, field):
        eid = str(evidence_id)
        row = self.records.get(eid)
        if not row or eid not in self.observed:
            raise CitationRejected("CITATION_NOT_OBSERVED", ["field"], eid)
        if row["repository"] or row["group"] in {"analysis_draft", "evidence_check", "evidence_inspection"}:
            raise CitationRejected("FIELD_REFERENCE_REQUIRES_ORIGINAL_JSON_OWNER", ["field"], eid)
        try:
            left, right = json_field_range(row["body"], field)
        except ValueError as error:
            raise CitationRejected("ORIGINAL_FIELD_REFERENCE_NOT_CAPTURED: " + str(error), ["field"], eid) from None
        if not self._range_read(eid, left, right):
            raise CitationRejected("ORIGINAL_FIELD_REFERENCE_NOT_FULLY_READ; use evidence.read with this field first", ["field"], eid)
        return row["body"][left:right]

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
            if row["group"] in {"analysis_draft", "evidence_check", "evidence_inspection"}:
                raise CitationRejected("MODEL_PROPOSAL_NOT_OWNER_EVIDENCE", location, c.evidence_id)
            excerpts = [self.original_field_excerpt(c.evidence_id, c.field)] if c.field is not None else self.observed_excerpts.get(str(c.evidence_id), [])
            if c.quote is not None:
                literal = any(c.quote in excerpt for excerpt in excerpts)
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
        known_owner_ids = {str(value["id"]) for eid, value in self.values.items()
            if isinstance(value, dict) and value.get("id") and not self.records[eid]["repository"]
            and self.records[eid]["group"] not in {"analysis_draft", "evidence_check", "evidence_inspection"}}
        uuid_pattern = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")
        for name, fact in facts:
            prefix = list(name) if isinstance(name, tuple) else [name]
            supported_ids = {str(report.work_id)}
            for c in fact.citations:
                for value in strings(self.values.get(str(c.evidence_id), {})):
                    supported_ids.update(uuid_pattern.findall(value))
            for owner_id in set(uuid_pattern.findall(fact.statement)) & known_owner_ids - supported_ids:
                errors.append(CitationRejected("FACT_NAMES_UNCITED_OWNER_RECORD; removing a citation also requires correcting claims about that record", prefix + ["statement"], report.work_id))
            for i, c in enumerate(fact.citations):
                try:
                    citation(c, prefix + ["citations", i])
                    row = self.records[str(c.evidence_id)]
                    if fact.evidence_family.value not in row["semantics"]["families"]:
                        raise CitationRejected("CITATION_SOURCE_SURFACE_MISMATCH: " + fact.evidence_family.value,
                                               prefix + ["citations", i], c.evidence_id)
                except CitationRejected as error:
                    errors.append(error)
        if (any(row["group"] in {"execution_effects", "effect_receipts", "execution_steps"}
                and isinstance(self.values[eid], dict) and self.values[eid].get("condition") in {"SETTLED", "COMPLETED"}
                for eid, row in self.records.items()) and not any(t.stage == "EXECUTION" for t in report.timeline)):
            errors.append(CitationRejected("OBSERVED_EXECUTION_STAGE_MUST_BE_RECONSTRUCTED; inspect settled/completed original records", ["timeline"], report.work_id))
        if (any(row["group"] in {"plan_history", "production_work_units"} for row in self.records.values())
                and not any(t.stage == "PLANNING" for t in report.timeline)):
            errors.append(CitationRejected("OBSERVED_PLANNING_STAGE_MUST_BE_RECONSTRUCTED; inspect original plan/PWU records", ["timeline"], report.work_id))
        previous_time = None
        for index, item in enumerate(report.timeline):
            if item.timestamp is None and item.timestamp_evidence_id is None:
                continue
            subject_id = str(item.timestamp_evidence_id)
            row = self.records.get(subject_id)
            value = self.values.get(subject_id)
            prefix = ["timeline", index]
            if (subject_id not in self.observed or not row or row["repository"]
                    or row["group"] in {"analysis_draft", "evidence_check", "evidence_inspection"}
                    or not isinstance(value, dict)):
                errors.append(CitationRejected("TIMELINE_TIME_REQUIRES_ORIGINAL_OWNER", prefix + ["timestamp_evidence_id"], subject_id))
                continue
            recorded = value.get(item.timestamp_field)
            try:
                if item.timestamp is None:
                    self.original_field_excerpt(subject_id, "/" + item.timestamp_field)
                actual = datetime.fromisoformat((item.timestamp if item.timestamp is not None else recorded).replace("Z", "+00:00"))
                expected = datetime.fromisoformat(recorded.replace("Z", "+00:00"))
                if actual.utcoffset() is None or expected.utcoffset() is None or actual != expected:
                    raise ValueError("timestamp mismatch")
            except (ValueError, TypeError, AttributeError):
                errors.append(CitationRejected("TIMELINE_TIME_DOES_NOT_MATCH_OWNER_FIELD", prefix + ["timestamp"], subject_id))
                continue
            # A timestamp also needs to have been returned to the model. Index
            # metadata or an unread tail cannot establish an event time.
            if not any(recorded in excerpt for excerpt in self.observed_excerpts.get(subject_id, [])):
                errors.append(CitationRejected("TIMELINE_TIME_NOT_OBSERVED", prefix + ["timestamp"], subject_id))
            if subject_id not in {str(c.evidence_id) for c in item.citations}:
                errors.append(CitationRejected("TIMELINE_TIME_SOURCE_MUST_BE_CITED", prefix + ["citations"], subject_id))
            for i, c in enumerate(item.citations):
                if self.association(subject_id, c.evidence_id)["status"] != "RELATED":
                    errors.append(CitationRejected("TIMELINE_DISTINCT_EVENTS_REQUIRE_SEPARATE_ENTRIES_OR_UNDATED_SUMMARY", prefix + ["citations", i], c.evidence_id))
            if previous_time is not None and actual < previous_time:
                errors.append(CitationRejected("TIMELINE_EVENTS_MUST_BE_CHRONOLOGICAL", prefix + ["timestamp"], subject_id))
            previous_time = actual
        for index, finding in enumerate(report.findings):
            subject_id = str(finding.subject_evidence_id)
            inspection = self.inspections.get(str(finding.inspection_id))
            if not inspection or inspection["subject_evidence_id"] != subject_id:
                errors.append(CitationRejected("FINDING_REQUIRES_SUBJECT_OWNER_INSPECTION; call evidence.inspect", ["findings", index, "inspection_id"], subject_id))
            else:
                checks = [self.checks.get(str(cid)) for cid in finding.uncertainty_check_ids]
                if any(c is None for c in checks):
                    errors.append(CitationRejected("UNCERTAINTY_CHECK_NOT_PERFORMED", ["findings", index, "uncertainty_check_ids"], subject_id))
                inspected_groups = {OWNER_GROUP_PROJECTIONS.get(r["group"], r["group"]) for r in inspection["records"]}
                for field in ("scope_check_ids", "uncertainty_check_ids"):
                    for cid in getattr(finding, field):
                        check = self.checks.get(str(cid))
                        if check and check["group"] and OWNER_GROUP_PROJECTIONS.get(check["group"], check["group"]) not in inspected_groups:
                            errors.append(CitationRejected("CHECK_OWNER_SCOPE_NOT_ASSOCIATED_WITH_FINDING; split unrelated Owner gaps", ["findings", index, field], subject_id))
            if subject_id not in self.observed:
                errors.append(CitationRejected("FINDING_SUBJECT_NOT_OBSERVED", ["findings", index, "subject_evidence_id"], subject_id))
            if subject_id not in {str(c.evidence_id) for c in finding.fact.citations}:
                errors.append(CitationRejected("FINDING_REQUIRES_SUBJECT_CITATION", ["findings", index, "fact", "citations"], subject_id))
            for i, c in enumerate(finding.fact.citations):
                if self.association(subject_id, c.evidence_id)["status"] != "RELATED":
                    errors.append(CitationRejected("CITATION_OWNER_ASSOCIATION_NOT_ESTABLISHED: choose same subject or explicit Owner reference", ["findings", index, "fact", "citations", i], c.evidence_id))
            if finding.scope_check_ids:
                checks = [self.checks.get(str(cid)) for cid in finding.scope_check_ids]
                if any(not c or c["availability"] == "PRESENT" for c in checks):
                    errors.append(CitationRejected("PRESENT_CHECK_CANNOT_SUPPORT_MISSING_FIELD_FINDING; use uncertainty_check_ids for present evidence, or check its precise unavailable field with OWNER_RECORD", ["findings", index, "scope_check_ids"], subject_id))
            for i, c in enumerate(finding.repository_citations):
                try:
                    citation(c, ["findings", index, "repository_citations", i], repository=True)
                except CitationRejected as error:
                    errors.append(error)
            if (finding.epistemic_status == "ROOT_CAUSE_HYPOTHESIS" and
                    not any(self.records.get(str(c.evidence_id), {}).get("semantics", {}).get("source_kind") ==
                            "EXACT_IMPLEMENTATION_READ" for c in finding.repository_citations)):
                errors.append(CitationRejected("ROOT_CAUSE_REQUIRES_IMPLEMENTATION_EXCERPT; use repository.read for surrounding producer control flow or retain UNKNOWN; search only locates code and a final diff cannot establish its mechanism", ["findings", index, "repository_citations"], subject_id))
        findings = {f.finding_id: f for f in report.findings}
        for section in ("immediate_recovery", "self_refine_opportunities", "platform_improvements", "deferred_items"):
            for index, item in enumerate(getattr(report, section)):
                for fid in item.finding_ids:
                    subject = self.records.get(str(findings[fid].subject_evidence_id))
                    if not subject or item.evidence_family.value not in subject["semantics"]["families"]:
                        errors.append(CitationRejected("RECOMMENDATION_FAMILY_REQUIRES_FINDING_SUBJECT_SURFACE; split unrelated topics", [section, index, "finding_ids"], findings[fid].subject_evidence_id))
        if errors:
            error = errors[0]
            error.issues = [{"type": "CitationRejected", "reason": str(item),
                             "location": item.location, "evidence_id": item.evidence_id}
                            for item in errors[:12]]
            raise error
        reviewed, reviewed_checks = set(), set()
        for assessment in report.evidence_assessments:
            check = self.checks.get(str(assessment.check_id))
            if (not check or check["family"] != assessment.family.value
                    or check["availability"] != assessment.availability
                    or (assessment.family.value != "OWNER_RECORD" and (check["group"] or check["field"]))):
                raise ValueError("EVIDENCE_ASSESSMENT_MUST_MATCH_SEEDED_FAMILY_LOOKUP")
            if str(assessment.check_id) in reviewed_checks or (assessment.family.value != "OWNER_RECORD" and assessment.family.value in reviewed):
                raise ValueError("DUPLICATE_EVIDENCE_ASSESSMENT")
            reviewed.add(assessment.family.value)
            reviewed_checks.add(str(assessment.check_id))
        if not {"PREVIEW_HTTP", "DELIVERY_TRANSFER", "EXECUTION_RELATIONSHIP"}.issubset(reviewed):
            raise ValueError("EVIDENCE_FAMILY_RECONCILIATION_REQUIRED")
        for gap in report.missing_evidence:
            check = self.checks.get(str(gap.check_id))
            if (not check or check["family"] != gap.family.value or check["availability"] != gap.availability):
                raise ValueError("MISSING_EVIDENCE_CONTRADICTS_LOOKUP_OR_UNCHECKED; PRESENT cannot be missing")
            if str(gap.check_id) not in {str(cid) for finding in report.findings for cid in finding.scope_check_ids}:
                raise ValueError("MISSING_EVIDENCE_REQUIRES_SCOPED_FINDING")
        failure_ids = {eid for eid, row in self.records.items()
                       if (row["group"] in {"execution_steps", "effect_receipts"}
                           and row["condition"] == "FAILED") or row["group"] == "self_refine_events"}
        cited = {str(c.evidence_id) for finding in report.findings for c in finding.fact.citations}
        if failure_ids and not (failure_ids & cited):
            raise ValueError("OBSERVED_INCIDENT_REQUIRES_FINDING_WITH_ORIGINAL_OWNER_CITATION")
        # This is citation/structure verification. It cannot prove that prose
        # follows logically from the quotes or promote hypotheses to findings.


    def materialize_boundaries(self, report):
        """Presentation from already-validated receipts, never repair prose/IDs.

        Preserve the original model draft. Factual claims, classifications,
        references, recommendations and causal hypotheses are never rewritten.
        """
        self.validate(report)
        def cite(c):
            raw = self.original_field_excerpt(c.evidence_id, c.field) if c.field is not None else None
            return c.model_copy(update={"observed_value": raw[:1200] if raw is not None else None,
                "observed_value_truncated": raw is not None and len(raw) > 1200})
        def fact(f):
            return f.model_copy(update={"citations": tuple(cite(c) for c in f.citations)})
        times = []
        for t in report.timeline:
            t = fact(t)
            if t.timestamp_evidence_id is not None:
                observed = self.values[str(t.timestamp_evidence_id)][t.timestamp_field]
                t = t.model_copy(update={"timestamp": t.timestamp if t.timestamp is not None else observed,
                    "owner_time_boundary": time_boundary(t.timestamp_field)})
            times.append(t)
        findings = []
        for f in report.findings:
            inspection = self.inspections[str(f.inspection_id)]
            boundaries = [inspection["bounded_conclusion"]] + [self.checks[str(cid)]["bounded_conclusion"]
                for cid in (*f.uncertainty_check_ids, *f.scope_check_ids)]
            findings.append(f.model_copy(update={"checked_boundaries": tuple(boundaries), "fact": fact(f.fact),
                "repository_citations": tuple(cite(c) for c in f.repository_citations)}))
        result = report.model_copy(update={"findings": tuple(findings),
            **{name: fact(getattr(report, name)) for name in ("original_objective", "expected_outcome", "actual_execution_path", "current_state")},
            "timeline": tuple(times),
            "evidence_assessments": tuple(a.model_copy(update={"checked_boundary": self.checks[str(a.check_id)]["bounded_conclusion"]}) for a in report.evidence_assessments),
            "missing_evidence": tuple(g.model_copy(update={"checked_boundary": self.checks[str(g.check_id)]["bounded_conclusion"]}) for g in report.missing_evidence)})
        self.validate(result)
        return result


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
        rows = data.decode("utf-8").splitlines(keepends=True)
        # Keep source bytes (after declared redaction) directly quotable. Line
        # numbers are metadata; inserting them into every line changes multiline
        # excerpts and causes exact quotations of genuinely read code to fail.
        excerpt = "".join(rows[start_line - 1:start_line - 1 + lines])
        return {"repository": self.key, "revision": self.revision, "tree": self.tree,
                "path": path, "blob": blob, "start_line": start_line,
                "end_line": min(len(rows), start_line - 1 + lines),
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
        self.pending_reports = {}
        self.accepted_review = None
        self.verification_receipts = []
        self.drafts = {}
        self.audit_budget = None

    def registry(self):
        definitions = (
            ("evidence.index", "List exact Trace/Owner evidence references; page with next_offset.",
             {"group": {"type": "string"}, "query": {"type": "string"},
              "offset": {"type": "integer"}, "limit": {"type": "integer"}}, []),
            ("evidence.read", "Read an evidence UUID, retaining exact source and digest; page long content.",
             {"evidence_id": {"type": "string"}, "offset": {"type": "integer"},
              "limit": {"type": "integer"}, "field": {"type": "string", "description": "Optional JSON Pointer relative to this original record; page its exact value without reading an unrelated large parent"}}, ["evidence_id"]),
            ("evidence.inspect", "Read original linked Owner fields along explicit references (up to two hops). Returns inspection_id and checked scope metadata for finding uncertainty. READ, PRESENT, REDACTED, EMPTY and NOT_READ_CAPACITY are distinct. It does not infer historical absence or transitive fact association. Page unread originals with evidence.read, then inspect again; keep UNKNOWN if required fields cannot be read.",
             {"subject_evidence_id": {"type": "string"}}, ["subject_evidence_id"]),
            ("evidence.check", "Check original snapshot evidence before absence claims. PREVIEW_HTTP and DELIVERY_TRANSFER fix their producer scope; EXECUTION_RELATIONSHIP enumerates actual identifier links. OWNER_RECORD requires a captured group and JSON Pointer field (/* enumerates record fields). No-match never proves global/historical absence.",
             {"family": {"enum": [f.value for f in EvidenceFamily]}, "group": {"type": "string"},
              "field": {"type": "string", "maxLength": 200,
                        "description": "JSON Pointer relative to EACH RECORD, e.g. /pwu_id or /result_payload/raw_response. Do not prefix /0 for the group array. Use /* for record fields or /field/* for nested children, never bare *. PRESENT container existence does not prove that all children contain usable observations."}}, ["family"]),
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
            ("analysis.review", "Review the entire pending report against observed sources within this same Native investigation. Return evidence-based judgments in any wording. REVISE yields feedback for existing analysis.revise; a recorded self-review is not independent assurance. No permissions or execution effects are granted.",
             {"draft_id": {"type": "string"}, "items": {"type": "array", "minItems": 1, "maxItems": 50,
              "items": {"type": "object", "properties": {
                  "target_path": {"type": "string"}, "judgment": {"enum": ["SUPPORTED", "QUALIFIED", "UNKNOWN", "REVISE"]},
                  "evidence_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 100},
                  "rationale": {"type": "string", "minLength": 1, "maxLength": 1600}},
                  "required": ["target_path", "judgment", "evidence_ids", "rationale"], "additionalProperties": False}}}, ["draft_id", "items"]),
            ("analysis.revise", "Explicitly correct a retained rejected report using bounded add/remove/replace JSON Pointer edits. Revalidate the entire report without regenerating it. This changes advisory artifacts only.",
             {"draft_id": {"type": "string"}, "edits": {"type": "array", "minItems": 1, "maxItems": 24,
              "items": {"type": "object", "properties": {"op": {"enum": ["add", "remove", "replace"]},
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
            if identity.startswith("repository.") and self.repositories:
                props["repository"]["enum"] = sorted(self.repositories)
                if identity == "repository.diff":
                    props["baseline_repository"]["enum"] = sorted(self.repositories)
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

    def review_targets(self, report):
        targets = []
        def add(path, references):
            targets.append({"target_path": path, "evidence_ids": sorted({str(eid) for eid in references})})
        for name in ("original_objective", "expected_outcome", "actual_execution_path", "current_state"):
            add("/" + name, (c["evidence_id"] for c in report[name]["citations"]))
        add("/timeline", (c["evidence_id"] for t in report["timeline"] for c in t["citations"]))
        by_id = {f["finding_id"]: f for f in report["findings"]}
        for i, f in enumerate(report["findings"]):
            add(f"/findings/{i}", [c["evidence_id"] for c in f["fact"]["citations"] + f["repository_citations"]]
                + f["scope_check_ids"] + f["uncertainty_check_ids"] + [f["inspection_id"]])
        for section in ("immediate_recovery", "self_refine_opportunities", "platform_improvements", "deferred_items"):
            if report[section]:
                add("/" + section, [c["evidence_id"] for item in report[section] for fid in item["finding_ids"]
                    for c in by_id[fid]["fact"]["citations"] + by_id[fid]["repository_citations"]])
        for section in ("evidence_assessments", "missing_evidence"):
            if report[section]:
                add("/" + section, (item["check_id"] for item in report[section]))
        return targets

    def resolved_observations(self, report):
        """Return bounded deterministic values for this report's explicit references."""
        values, used, omitted = [], 0, 0
        def add(entry):
            nonlocal used, omitted
            size = len(text(entry))
            if used + size > 24000:
                omitted += 1
            else:
                values.append(entry)
                used += size
        def fact(path, value):
            for i, c in enumerate(value["citations"]):
                if c.get("field") is not None:
                    add({"report_path": path + f"/citations/{i}", "evidence_id": c["evidence_id"],
                        "field": c["field"], "observed_value": c["observed_value"], "truncated": c["observed_value_truncated"]})
        for name in ("original_objective", "expected_outcome", "actual_execution_path", "current_state"):
            fact("/" + name, report[name])
        for i, item in enumerate(report["timeline"]):
            fact(f"/timeline/{i}", item)
            if item["timestamp_evidence_id"] is not None:
                add({"report_path": f"/timeline/{i}/timestamp", "evidence_id": item["timestamp_evidence_id"],
                    "field": "/" + item["timestamp_field"], "observed_value": item["timestamp"], "boundary": item["owner_time_boundary"]})
        for i, f in enumerate(report["findings"]):
            fact(f"/findings/{i}/fact", f["fact"])
        return {"values": values, "omitted_values": omitted,
            "scope": "FULLY_READ_ORIGINAL_REFERENCES; VALUES_ARE_NOT_SEMANTIC_ENTAILMENT; OMITTED_VALUES_REMAIN_RETRIEVABLE"}

    async def execute(self, request):
        identity, args = request.proposal.tool_identity, request.proposal.arguments
        draft_id, candidate, edit_context = None, None, None
        try:
            if identity == "evidence.index":
                output = self.catalog.index(**args)
            elif identity == "evidence.read":
                output = self.catalog.read(**args)
            elif identity == "evidence.check":
                output = self.catalog.check(**args)
            elif identity == "evidence.inspect":
                output = self.catalog.inspect(**args)
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
            elif identity == "analysis.review":
                report = self.pending_reports[args["draft_id"]]
                targets = {t["target_path"]: set(t["evidence_ids"]) for t in self.review_targets(report)}
                items = args["items"]
                if len(items) != len(targets) or {i["target_path"] for i in items} != set(targets):
                    raise ValueError("SELF_REVIEW_REQUIRES_COMPLETE_REPORT_COVERAGE")
                for item in items:
                    refs = set(item["evidence_ids"])
                    if refs != targets[item["target_path"]] or not refs.issubset(self.catalog.observed):
                        raise ValueError("SELF_REVIEW_SOURCE_SCOPE_MISMATCH")
                    if item["judgment"] not in {"SUPPORTED", "QUALIFIED", "UNKNOWN", "REVISE"} or not item["rationale"].strip():
                        raise ValueError("SELF_REVIEW_JUDGMENT_REQUIRED")
                needs_revision = [i for i in items if i["judgment"] == "REVISE"]
                review = {"draft_id": args["draft_id"], "report_digest": canonical_digest(report),
                    "items": public_report_candidate(items), "authority": "MODEL_SELF_REVIEW_PROPOSAL_NOT_INDEPENDENT_ASSURANCE"}
                if needs_revision:
                    self.accepted_report, self.accepted_digest, self.accepted_review = None, None, None
                    output = {"verification": "NATIVE_SELF_REVIEW_REQUIRES_REVISION", "draft_id": args["draft_id"],
                        "feedback": needs_revision, "effect_observed": False, "failure_class": "RUNTIME_MODEL_VARIANCE", "issues": [{"type": "NATIVE_SELF_REVIEW_FEEDBACK", "location": i["target_path"], "reason": i["rationale"]} for i in needs_revision], "repair": "Use existing analysis.revise under the same contract and budget; review the changed report again."}
                else:
                    self.accepted_report, self.accepted_digest, self.accepted_review = report, canonical_digest(report), review
                    output = {"verification": "CITATIONS_AND_STRUCTURE_PASS", "native_self_review": "RECORDED_NOT_INDEPENDENT_ASSURANCE",
                        "report_digest": self.accepted_digest, "semantic_correctness": "HUMAN_REVIEW_REQUIRED", "production_authority": "NONE"}
                self.verification_receipts.append(output | {"review": review})
            elif identity in {"analysis.submit", "analysis.revise"}:
                if identity == "analysis.submit":
                    candidate = args["report"]
                else:
                    candidate = deepcopy(self.drafts[args["draft_id"]])
                    edits = args["edits"]
                    if not 1 <= len(edits) <= 24:
                        raise ValueError("REPORT_EDIT_CAPACITY_EXCEEDED")
                    for edit in edits:
                        if set(edit) - {"op", "path", "value"} or edit["op"] not in {"add", "remove", "replace"}:
                            raise ValueError("REPORT_EDIT_NOT_ADMITTED")
                        path = edit["path"]
                        if not isinstance(path, str) or not path.startswith("/") or len(path) > 300:
                            raise ValueError("REPORT_EDIT_POINTER_INVALID")
                        parts = [p.replace("~1", "/").replace("~0", "~") for p in path[1:].split("/")]
                        parent = candidate
                        for part in parts[:-1]:
                            parent = parent[int(part)] if isinstance(parent, list) and part.isdigit() else parent[part]
                        last = int(parts[-1]) if isinstance(parent, list) and parts[-1].isdigit() else parts[-1]
                        edit_context = {"path": path, "operation": edit["op"],
                            "available_parent_fields": list(parent)[:60] if isinstance(parent, dict) else [],
                            "target_present": last in parent if isinstance(parent, dict) else isinstance(last, int) and 0 <= last < len(parent)}
                        if edit["op"] == "add":
                            if isinstance(parent, list):
                                index = len(parent) if last == "-" else last
                                if not isinstance(index, int) or not 0 <= index <= len(parent):
                                    raise ValueError("REPORT_ADD_ARRAY_INDEX_INVALID")
                                parent.insert(index, edit["value"])
                            else:
                                parent[last] = edit["value"]
                        elif edit["op"] == "remove":
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
                edit_context = None
                report = AnalysisReport.model_validate(candidate)
                report = self.catalog.materialize_boundaries(report)
                self.pending_reports[draft_id] = report.model_dump(mode="json")
                self.accepted_report, self.accepted_digest, self.accepted_review = None, None, None
                output = {"verification": "CITATIONS_AND_STRUCTURE_PASS",
                          "draft_id": draft_id, "candidate_digest": canonical_digest(self.pending_reports[draft_id]),
                          "review_targets": self.review_targets(self.pending_reports[draft_id]),
                          "resolved_observations": self.resolved_observations(self.pending_reports[draft_id]),
                          "next_action": "analysis.review", "semantic_correctness": "NATIVE_SELF_REVIEW_REQUIRED_THEN_HUMAN_REVIEW",
                          "production_authority": "NONE"}
                self.verification_receipts.append(output)
            else:
                raise ValueError("TOOL_NOT_ADMITTED")
            condition = EffectCondition.FAILED if identity == "analysis.review" and needs_revision else EffectCondition.SETTLED
        except (ValueError, KeyError, TypeError, UnicodeError, IndexError) as error:
            if identity.startswith("analysis."):
                self.accepted_report, self.accepted_digest, self.accepted_review = None, None, None
            if hasattr(error, "errors"):
                issues = [{"location": list(item["loc"]), "type": item["type"],
                           "reason": Redactor(text_limit=300).clean(item["msg"])}
                          for item in error.errors(include_input=False, include_context=False)[:12]]
            else:
                issues = [{"type": type(error).__name__, "reason": Redactor(text_limit=300).clean(str(error))}]
                if isinstance(error, CitationRejected):
                    issues = getattr(error, "issues", [{"type": "CitationRejected", "reason": str(error),
                             "location": error.location, "evidence_id": error.evidence_id}])
            if identity == "evidence.read" and str(error) == "READ_FIELD_NOT_FOUND":
                eid = str(args.get("evidence_id"))
                value = self.catalog.values.get(eid)
                issues[0].update(evidence_id=eid, requested_field=args.get("field"),
                    captured_root_fields=sorted(value)[:50] if isinstance(value, dict) else [],
                    boundary="Requested pointer not found in this captured record. Field names are navigation metadata, not observed values or evidence of historical absence.",
                    repair="Inspect this record's original fields, then read the exact admitted JSON Pointer; preserve UNKNOWN where its value is unavailable.")
            if identity == "analysis.revise" and draft_id is None and args.get("draft_id") in self.drafts:
                draft_id = args["draft_id"]
                candidate = deepcopy(self.drafts[draft_id])
                if edit_context is not None:
                    issues.append({"type": "REPORT_EDIT_INPUT_FEEDBACK", "location": edit_context["path"],
                        **edit_context, "admitted_operations": ["add", "remove", "replace"],
                        "repair": "For an omitted property, explicitly add the proposed value or replace its existing parent. The original draft is unchanged; all evidence and schema gates are rechecked."})
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
                # Return the exact rejected value at each reported location so
                # same-draft correction does not require rereading the entire
                # report. This supplies no edits or invented Owner quotations.
                feedback_bytes = 0
                for issue in issues:
                    value = candidate
                    try:
                        for part in issue.get("location", []):
                            value = value[part]
                    except (KeyError, TypeError, IndexError):
                        continue
                    encoded = text(public_report_candidate(value)).encode()
                    if len(encoded) <= 2000 and feedback_bytes + len(encoded) <= 8000:
                        issue["rejected_value"] = public_report_candidate(value)
                        feedback_bytes += len(encoded)
                    location = issue.get("location", [])
                    if len(location) >= 3 and location[0] == "timeline" and isinstance(location[1], int):
                        # Return the exact retained entry so a model can replace
                        # coupled time fields together, without another full-draft
                        # read. This is proposal context, never an Owner fact or edit.
                        context = public_report_candidate(candidate["timeline"][location[1]])
                        encoded = text(context).encode()
                        if len(encoded) <= 2000 and feedback_bytes + len(encoded) <= 8000:
                            issue["rejected_context"] = {"path": "/timeline/" + str(location[1]), "value": context}
                            feedback_bytes += len(encoded)
            condition = EffectCondition.FAILED
            if identity.startswith("analysis."):
                self.verification_receipts.append(output)
        if self.audit_budget is not None:
            output = dict(output, audit_budget=self.audit_budget())
        return ToolExecutionResult(delivery_id=request.delivery_id, tool_identity=identity,
                                   condition=condition, output=output,
                                   output_digest=canonical_digest(output))
