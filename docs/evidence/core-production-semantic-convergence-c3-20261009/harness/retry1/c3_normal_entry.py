#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
"""C3 normal Product/Experience entry. No fixture, retry, or Human gate writes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, parse, request

SCHEMA = "c3-normal-entry-state-v1"
MAX_RESPONSE = 8 * 1024 * 1024
ID_KEYS = frozenset("id product_id work_id turn_id interaction_id request_record_id assessment_id revision_id previous_revision_id source_interaction_id source_assessment_id engineering_scope_id engineering_resource_id source_baseline_id governance_record_id current_work_id governed_work_id current_work_reality_revision_id current_steering_step_id current_production_run_id latest_trusted_runtime_commit_id steering_plan_id active_revision_id step_id decision_id change_id from_revision_id to_revision_id event_id obligation_id fact_id pwu_id task_id attempt_id candidate_id verification_id manifest_id preview_id production_run_id completion_id native_attempt_id result_id".split())
ID_LIST_KEYS = frozenset("candidate_ids verification_ids source_record_ids affected_step_ids completed_pwu_ids".split())
HASH_KEYS = frozenset("basis_fingerprint revision_fingerprint candidate_fingerprint repository_revision source_revision repository_tree tree scope_basis_fingerprint fingerprint content_sha256 sha256 qualified_output_revision qualified_output_tree".split())
ENUM_KEYS = frozenset("status state condition mode wic_mode source_kind target_kind type outcome gate result owner next_owner failure_code failure_attribution blocker_code source_owner protected_context_status context_status context_class decision_kind requested_effect work_status automatic_progression_state last_stop_reason current_steering_step_type current_production_step steering_outcome production_admission_state repository_acquisition_state production_next_step profile schema_version binding_phase verification_component effect_class".split())
BOOL_KEYS = frozenset("steering_enabled human_attention_required work_complete latest_assessment_current production_request_detected new_work_formation_pending current_production_cycle_trusted control_state_valid authorization_pending required healthy acceptance_required".split())
NUMBER_KEYS = frozenset("count failed finding_count revision_number active_revision_number current_production_cycle_number position sequence attempt_number repair_attempt_count retries_consumed retry_budget max_attempts generation".split())
STRUCTURE_KEYS = frozenset("latest_assessment readiness governed_revision current_step completed_steps known_next_steps plan_changes latest_decision execution_progress production_plan_runtime pwus tasks production_work_units current_cycle cycles pwu queue worker self_refine metrics work_convergence events refinements obligations semantic_ir ir protected_obligations protected_context_checks obligation_fulfillment_checks checks validation candidate verification deliveries manifest acceptance runtime reality execution guardian managed_source current_work recent_works plan production source_baseline source_vector production_context lineage binding input output".split())


class DriverStop(Exception):
    """Only fixed, non-sensitive codes may be surfaced."""


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        if os.name == "posix":
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temp.exists():
            temp.unlink()


def load_json(path, code):
    try:
        data = path.read_bytes()
        value = json.loads(data.decode("utf-8-sig"))
    except (OSError, UnicodeError, ValueError):
        raise DriverStop(code) from None
    if not isinstance(value, dict):
        raise DriverStop(code)
    return value, digest(data)


def uuid_value(value):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def projection(value, token, depth=0):
    """Allowlist structural identifiers; never retain narratives/error bodies/URLs."""
    if depth > 14:
        return None
    if isinstance(value, list):
        return [projected for item in value[:1000]
                if (projected := projection(item, token, depth + 1)) not in (None, {})]
    if not isinstance(value, dict):
        return None
    result = {}
    for key, item in value.items():
        if key in ID_KEYS:
            if item is None:
                result[key] = None
            elif (uid := uuid_value(item)):
                result[key] = uid
        elif key in ID_LIST_KEYS and isinstance(item, list):
            result[key] = [uid for raw in item if (uid := uuid_value(raw))]
        elif key in HASH_KEYS and isinstance(item, str) and re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", item):
            if token not in item:
                result[key] = item
        elif key in ENUM_KEYS:
            if item is None:
                result[key] = None
            elif isinstance(item, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,95}", item) and token not in item:
                result[key] = item
        elif key in BOOL_KEYS and isinstance(item, bool):
            result[key] = item
        elif key in NUMBER_KEYS and isinstance(item, (int, float)) and not isinstance(item, bool):
            result[key] = item
        elif (key.endswith("_at") or key in {"lease_deadline", "deadline"}) and isinstance(item, str):
            try:
                datetime.fromisoformat(item.replace("Z", "+00:00"))
                result[key] = item
            except ValueError:
                pass
        elif key in STRUCTURE_KEYS and isinstance(item, (dict, list)):
            result[key] = projection(item, token, depth + 1)
    return result


@contextmanager
def exclusive_state_lock(path):
    """OS process lock releases after crashes; the retained lock file is harmless."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise DriverStop("STATE_ALREADY_IN_USE") from None
        try:
            yield
        finally:
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, base, token, timeout):
        self.base, self.token, self.timeout = base, token, timeout
        self.opener = request.build_opener(request.ProxyHandler({}), NoRedirect())

    def call(self, method, path, body=None):
        started = now()
        payload = None if body is None else canonical(body)
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        req = request.Request(self.base + path, data=payload, headers=headers, method=method)
        receipt = {"method": method, "path": path, "started_at_utc": started,
                   "request_body_sha256": None if payload is None else digest(payload)}
        raw = b""
        value = None
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                receipt["http_status"] = response.status
                raw = response.read(MAX_RESPONSE + 1)
        except error.HTTPError as failure:
            receipt["http_status"] = failure.code
            try:
                raw = failure.read(MAX_RESPONSE + 1)
            except Exception:
                receipt["transport_error_type"] = "HTTP_BODY_UNAVAILABLE"
            finally:
                failure.close()
        except Exception as failure:
            receipt["transport_error_type"] = type(failure).__name__
        receipt["completed_at_utc"] = now()
        receipt["response_bytes_observed"] = len(raw)
        receipt["response_body_sha256"] = digest(raw)
        if len(raw) > MAX_RESPONSE:
            receipt["response_truncated"] = True
        else:
            try:
                value = json.loads(raw)
            except (ValueError, UnicodeError):
                receipt["response_json_valid"] = False
            else:
                receipt["response_json_valid"] = True
                receipt["projection"] = projection(value, self.token)
        # HTTP bodies, exception strings, headers, URLs and credentials never persist.
        successful = bool(200 <= receipt.get("http_status", 0) < 300
                          and not receipt.get("response_truncated")
                          and isinstance(value, (dict, list)))
        return successful, value, receipt


def validate_identity(value, base):
    required = {"qualification": "C3", "qualification_run": "retry-1", "isolated": True, "provider_ready": True}
    if any(value.get(key) != expected for key, expected in required.items()):
        raise DriverStop("IDENTITY_ISOLATION_OR_PROVIDER_NOT_CONFIRMED")
    if value.get("model_credential_scope") not in {"ISOLATED_C3", "HUMAN_AUTHORIZED_SHARED_TEST"}:
        raise DriverStop("IDENTITY_PROVIDER_SCOPE_NOT_AUTHORIZED")
    if not re.fullmatch(r"[0-9a-f]{40}", str(value.get("source_revision", ""))):
        raise DriverStop("IDENTITY_EXACT_REVISION_REQUIRED")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(value.get("image_id", ""))):
        raise DriverStop("IDENTITY_EXACT_IMAGE_REQUIRED")
    database = value.get("database_name", "")
    service = value.get("api_service", "")
    if database != "spg_c3_retry1_qualification_20261009":
        raise DriverStop("IDENTITY_C3_DATABASE_REQUIRED")
    if service != "watt-c3-retry1-api-20261009":
        raise DriverStop("IDENTITY_C3_API_SERVICE_REQUIRED")
    parsed = parse.urlsplit(base)
    if (parsed.scheme not in {"http", "https"} or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in {"", "/"}):
        raise DriverStop("BASE_URL_UNSAFE")
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1", service}:
        raise DriverStop("BASE_URL_NOT_ISOLATED_ENDPOINT")
    try:
        if parsed.port is None:
            raise DriverStop("BASE_URL_EXPLICIT_PORT_REQUIRED")
        datetime.fromisoformat(str(value["captured_at_utc"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        raise DriverStop("IDENTITY_TIMESTAMP_OR_PORT_INVALID") from None
    if str(value.get("api_base_url", "")).rstrip("/") != base:
        raise DriverStop("IDENTITY_BASE_URL_MISMATCH")
    # No unfiltered deployment receipts/settings are copied into state.
    return {key: value[key] for key in (
        "qualification", "qualification_run", "isolated", "provider_ready", "model_credential_scope",
        "source_revision", "image_id", "database_name", "api_service", "api_base_url",
        "captured_at_utc")}


def save_state(path, state):
    state["updated_at_utc"] = now()
    atomic_json(path, state)


def record_call(args, state, label, receipt):
    state["receipt_sequence"] += 1
    number = state["receipt_sequence"]
    save_state(args.state_file, state)  # Reserve the receipt number before writing it.
    atomic_json(args.evidence_dir / (state["run_id"] + f"-{number:06d}-" + label + ".json"), {
        "schema": "c3-normal-entry-api-observation-v1", "run_id": state["run_id"],
        "runtime_identity": state["runtime_identity"], "input_sha256": state["input_sha256"],
        "qualification_claim": "OBSERVATION_ONLY_NOT_WORK_PASS", **receipt})
    save_state(args.state_file, state)


def post_once(args, state, client, operation, path, body, id_fields):
    if state["operations"][operation]["state"] != "NOT_ATTEMPTED":
        raise DriverStop("CREATE_ALREADY_ATTEMPTED_NO_REPEAT")
    state["operations"][operation] = {
        "state": "IN_FLIGHT", "started_at_utc": now(), "path": path,
        "request_body_sha256": digest(canonical(body))}
    save_state(args.state_file, state)  # Must precede the side effect.
    ok, data, receipt = client.call("POST", path, body)
    record_call(args, state, operation, receipt)
    ids = {target: uuid_value(data.get(source)) for target, source in id_fields.items()} if isinstance(data, dict) else {}
    if not ok or not ids or not all(ids.values()):
        state["operations"][operation]["state"] = "UNKNOWN_OUTCOME"
        save_state(args.state_file, state)
        raise DriverStop("POST_OUTCOME_REQUIRES_READ_ONLY_RECONCILIATION")
    state.update(ids)
    state["operations"][operation]["state"] = "CONFIRMED"
    state["operations"][operation]["confirmed_at_utc"] = now()
    save_state(args.state_file, state)


def reconcile(args, state, client, text):
    if any(getattr(args, name) is not None and not uuid_value(getattr(args, name))
           for name in ("adopt_product_id", "adopt_interaction_id", "adopt_turn_id")):
        raise DriverStop("RECONCILIATION_INVALID_UUID")
    product_id = uuid_value(args.adopt_product_id) or state.get("product_id")
    interaction_id = uuid_value(args.adopt_interaction_id)
    turn_id = uuid_value(args.adopt_turn_id)
    if not product_id or bool(interaction_id) != bool(turn_id):
        raise DriverStop("RECONCILIATION_REQUIRES_EXACT_IDS")
    if interaction_id is None:
        ok, product, receipt = client.call("GET", f"/api/products/{product_id}")
        record_call(args, state, "reconcile-product", receipt)
        if (not ok or not isinstance(product, dict)
                or uuid_value(product.get("id")) != product_id
                or product.get("name") != state["product_name"]
                or product.get("managed_source") is None
                or state.get("product_id") not in (None, product_id)
                or state["operations"]["create_product"]["state"] == "NOT_ATTEMPTED"):
            raise DriverStop("RECONCILIATION_PRODUCT_MISMATCH")
        state["product_id"] = product_id
        state["operations"]["create_product"].update(
            state="CONFIRMED_BY_READ_ONLY_RECONCILIATION", reconciled_at_utc=now())
        save_state(args.state_file, state)
        return
    ids = [product_id, interaction_id, turn_id]
    paths = [("reconcile-product", f"/api/products/{product_id}"),
             ("reconcile-turn", f"/api/interactions/{interaction_id}/turns/{turn_id}"),
             ("reconcile-interaction", f"/api/interactions/{interaction_id}"),
             ("reconcile-workspace", f"/api/experience/products/{product_id}/workspace?interaction={interaction_id}")]
    values = []
    for label, path in paths:
        ok, data, receipt = client.call("GET", path)
        record_call(args, state, label, receipt)
        if not ok or not isinstance(data, dict):
            raise DriverStop("READ_ONLY_RECONCILIATION_INCOMPLETE")
        values.append(data)
    product, turn, interaction, workspace = values
    if (uuid_value(product.get("id")) != product_id or product.get("name") != state["product_name"]
            or product.get("managed_source") is None
            or uuid_value(turn.get("interaction_id")) != interaction_id
            or uuid_value(turn.get("turn_id")) != turn_id
            or uuid_value(workspace.get("interaction_id")) != interaction_id):
        raise DriverStop("RECONCILIATION_IDENTITY_MISMATCH")
    record_id = uuid_value(turn.get("request_record_id"))
    matches = [item for item in interaction.get("records", []) if isinstance(item, dict)
               and uuid_value(item.get("record_id")) == record_id]
    if len(matches) != 1 or matches[0].get("content") != text:
        raise DriverStop("RECONCILIATION_INPUT_MISMATCH")
    # Existing confirmed identities are immutable even during recovery.
    for key, supplied in zip(("product_id", "interaction_id", "turn_id"), ids):
        if state.get(key) not in (None, supplied):
            raise DriverStop("RECONCILIATION_PREVIOUS_ID_CONFLICT")
    if any(state["operations"][operation]["state"] == "NOT_ATTEMPTED"
           for operation in ("create_product", "submit_turn")):
        raise DriverStop("RECONCILIATION_OPERATION_WAS_NOT_ATTEMPTED")
    state.update(dict(zip(("product_id", "interaction_id", "turn_id"), ids)))
    for operation in ("create_product", "submit_turn"):
        state["operations"][operation].update(state="CONFIRMED_BY_READ_ONLY_RECONCILIATION", reconciled_at_utc=now())
    save_state(args.state_file, state)


def poll(args, state, client):
    interaction_id, turn_id = state["interaction_id"], state["turn_id"]
    for iteration in range(args.poll_limit):
        observations = {}
        for label, path in (
            ("turn", f"/api/interactions/{interaction_id}/turns/{turn_id}"),
            ("interaction", f"/api/interactions/{interaction_id}"),
            ("realization", f"/api/interactions/{interaction_id}/turns/{turn_id}/realization")):
            ok, data, receipt = client.call("GET", path)
            record_call(args, state, label, receipt)
            observations[label] = data if ok and isinstance(data, dict) else {}
        turn = observations["turn"]
        interaction = observations["interaction"]
        work_id = uuid_value(interaction.get("governed_work_id")) or uuid_value(interaction.get("current_work_id"))
        if work_id:
            if state.get("work_id") not in (None, work_id):
                raise DriverStop("OBSERVED_WORK_ID_CHANGED_REQUIRES_REVIEW")
            state["work_id"] = work_id
            for label, suffix in (("work", ""), ("operations", "/operations"),
                                  ("steering", "/steering"), ("self-refine", "/self-refine"),
                                  ("guardian", "/guardian-assurance"), ("delivery", "/delivery")):
                ok, data, receipt = client.call("GET", f"/api/works/{work_id}" + suffix)
                record_call(args, state, label, receipt)
                observations[label] = data if ok and isinstance(data, dict) else {}
        work = observations.get("work", {})
        state["latest_observation"] = projection({
            "turn_id": turn_id, "interaction_id": interaction_id, "work_id": work_id,
            "status": turn.get("status"), "work_status": work.get("status"),
            "human_attention_required": work.get("human_attention_required"),
            "work_complete": work.get("work_complete"),
            "current_work_reality_revision_id": work.get("current_work_reality_revision_id"),
            "current_production_run_id": work.get("current_production_run_id"),
            "automatic_progression_state": work.get("automatic_progression_state")}, client.token)
        state["polls_completed"] += 1
        save_state(args.state_file, state)
        # A turn completing is only admission/interaction completion, never Work PASS.
        if turn.get("status") in {"FAILED", "CANCELLED"}:
            state["driver_status"] = "TURN_STOP_OBSERVED"
            break
        if work.get("work_complete") or work.get("status") in {"COMPLETED", "CANCELLED", "TERMINATED", "NON_CONVERGING"}:
            state["driver_status"] = "WORK_BOUNDARY_OBSERVED_REVIEW_REQUIRED"
            break
        if work.get("human_attention_required"):
            state["driver_status"] = "HUMAN_ATTENTION_PENDING_NO_AUTHORIZATION_WRITTEN"
            break
        if iteration + 1 < args.poll_limit:
            time.sleep(args.poll_seconds)
    else:
        state["driver_status"] = "BOUNDED_OBSERVATION_WINDOW_ENDED"
    save_state(args.state_file, state)
    print(json.dumps({"run_id": state["run_id"], "product_id": state.get("product_id"),
        "interaction_id": interaction_id, "turn_id": turn_id, "work_id": state.get("work_id"),
        "driver_status": state["driver_status"], "latest_observation": state.get("latest_observation"),
        "qualification_claim": "OBSERVATION_ONLY_NOT_WORK_PASS"}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--identity-path", required=True, type=Path)
    parser.add_argument("--credentials-file", required=True, type=Path)
    parser.add_argument("--input-file", type=Path, default=Path(__file__).parent / "evidence/original-g0-input.json")
    parser.add_argument("--state-file", type=Path, default=Path(__file__).parent / "evidence/normal-entry-state.json")
    parser.add_argument("--evidence-dir", type=Path, default=Path(__file__).parent / "evidence/normal-entry")
    parser.add_argument("--execute", action="store_true", help="Otherwise validate prerequisites only; no HTTP/state writes.")
    parser.add_argument("--submit-unattempted-turn", action="store_true", help="Resume only a confirmed Product whose Turn was never attempted.")
    parser.add_argument("--adopt-product-id")
    parser.add_argument("--adopt-interaction-id")
    parser.add_argument("--adopt-turn-id")
    parser.add_argument("--poll-limit", type=int, default=20)
    parser.add_argument("--poll-seconds", type=float, default=5)
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args()
    if not (1 <= args.poll_limit <= 1000 and 0 <= args.poll_seconds <= 30 and 1 <= args.timeout <= 60):
        raise DriverStop("POLL_OR_TIMEOUT_OUTSIDE_BOUNDS")
    args.base_url = args.base_url.rstrip("/")
    original, original_sha = load_json(args.input_file, "ORIGINAL_INPUT_UNAVAILABLE")
    text = original.get("prompt")
    if (original.get("schema") != "c2-original-g0-input-v1" or not isinstance(text, str)
            or not text or text != text.strip()
            or not uuid_value(original.get("source_record_id"))
            or original.get("human_governor_content_acceptance") is not False):
        raise DriverStop("ORIGINAL_INPUT_PROVENANCE_INVALID")
    identity_raw, identity_sha = load_json(args.identity_path, "RUNTIME_IDENTITY_UNAVAILABLE")
    identity = validate_identity(identity_raw, args.base_url)
    credentials, _ = load_json(args.credentials_file, "ISOLATED_CREDENTIALS_UNAVAILABLE")
    token = credentials.get("operator_token")
    if not isinstance(token, str) or len(token) < 32 or "\n" in token or "\r" in token:
        raise DriverStop("ISOLATED_OPERATOR_TOKEN_INVALID")
    client = Client(args.base_url, token, args.timeout)
    if not args.execute:
        print(json.dumps({"driver_status": "PREREQUISITES_VALIDATED_NO_HTTP", "input_sha256": digest(text.encode()),
                          "source_record_id": original["source_record_id"], "runtime_identity": identity}))
        return
    with exclusive_state_lock(args.state_file.with_suffix(args.state_file.suffix + ".lock")):
        existing = args.state_file.exists()
        if existing:
            state, _ = load_json(args.state_file, "STATE_UNREADABLE_NO_CREATE")
            if (state.get("schema") != SCHEMA or state.get("original_input_file_sha256") != original_sha
                    or state.get("runtime_identity_file_sha256") != identity_sha
                    or state.get("input_sha256") != digest(text.encode())):
                raise DriverStop("STATE_INPUT_OR_RUNTIME_IDENTITY_DRIFT_NO_CREATE")
        else:
            if args.evidence_dir.exists() and any(args.evidence_dir.glob("*-*.json")):
                raise DriverStop("EVIDENCE_EXISTS_WITHOUT_STATE_NO_CREATE")
            if args.submit_unattempted_turn or any((args.adopt_product_id, args.adopt_interaction_id, args.adopt_turn_id)):
                raise DriverStop("RECOVERY_REQUIRES_EXISTING_STATE")
            run_id = str(uuid.uuid4())
            state = {"schema": SCHEMA, "run_id": run_id, "created_at_utc": now(),
                "product_name": "C3 G0 normal entry " + run_id,
                "source_record_id": original["source_record_id"],
                "original_input_file_sha256": original_sha, "input_sha256": digest(text.encode()),
                "runtime_identity_file_sha256": identity_sha, "runtime_identity": identity,
                "receipt_sequence": 0, "polls_completed": 0,
                "human_integration_authorization_written": False,
                "human_acceptance_written": False, "human_delivery_authorization_written": False,
                "operations": {name: {"state": "NOT_ATTEMPTED"} for name in ("create_product", "submit_turn")}}
            save_state(args.state_file, state)
            post_once(args, state, client, "create_product", "/api/products", {
                "name": state["product_name"], "description": "C3 retry-1 isolated normal-entry qualification; no Human Integration, Acceptance or Delivery authorization.",
                "source_mode": "managed"}, {"product_id": "id"})
        if any((args.adopt_product_id, args.adopt_interaction_id, args.adopt_turn_id)):
            reconcile(args, state, client, text)
        if not state.get("product_id"):
            raise DriverStop("PRODUCT_OUTCOME_UNRESOLVED_NO_REPEAT")
        if not state.get("turn_id"):
            if existing and not args.submit_unattempted_turn:
                raise DriverStop("EXISTING_STATE_IS_READ_ONLY_USE_EXPLICIT_UNATTEMPTED_TURN_RESUME")
            if state["operations"]["create_product"]["state"] not in {"CONFIRMED", "CONFIRMED_BY_READ_ONLY_RECONCILIATION"}:
                raise DriverStop("PRODUCT_NOT_CONFIRMED_NO_TURN")
            post_once(args, state, client, "submit_turn", f"/api/experience/products/{state['product_id']}/turns",
                      {"text": text}, {"interaction_id": "interaction_id", "turn_id": "turn_id"})
        if not state.get("interaction_id"):
            raise DriverStop("INTERACTION_OUTCOME_UNRESOLVED_NO_REPEAT")
        poll(args, state, client)


if __name__ == "__main__":
    try:
        main()
    except DriverStop as failure:
        print(json.dumps({"driver_status": "STOPPED", "code": str(failure),
                          "qualification_claim": "NO_PASS_CLAIM"}), file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print('{"driver_status":"INTERRUPTED_RESUME_READ_ONLY","qualification_claim":"NO_PASS_CLAIM"}', file=sys.stderr)
        sys.exit(130)
    except Exception as failure:
        print(json.dumps({"driver_status": "STOPPED", "code": "UNEXPECTED_DRIVER_ERROR",
                          "error_type": type(failure).__name__, "qualification_claim": "NO_PASS_CLAIM"}), file=sys.stderr)
        sys.exit(3)
