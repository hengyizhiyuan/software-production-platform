"""Qualify bounded recovery from actual acquisition owner rows, before Work."""


def observed_acquisition_recovery(rows, *, interaction_id, source_record_id):
    by_id = {row.get("id"): row for row in rows}
    for child in rows:
        request = child.get("request") or {}
        observed = child.get("observation") or {}
        parent = by_id.get(request.get("previous_attempt_id"))
        if parent is None:
            continue
        prior = parent.get("request") or {}
        failure = parent.get("observation") or {}
        evidence = observed.get("operation_evidence") or {}
        if (
            request.get("interaction_id") == prior.get("interaction_id") == interaction_id
            and request.get("source_record_id") == prior.get("source_record_id") == source_record_id
            and request.get("source") == prior.get("source")
            and request.get("authority_identity") == prior.get("authority_identity")
            and bool(request.get("authority_identity"))
            and request.get("operation_kind") == prior.get("operation_kind") == "ACQUIRE"
            and request.get("request_id") == observed.get("intake_request_id") == child.get("id")
            and prior.get("request_id") == failure.get("intake_request_id") == parent.get("id")
            and prior.get("attempt_number") in (1, 2)
            and request.get("attempt_number") == prior.get("attempt_number") + 1
            and request.get("attempt_number") <= 3
            and failure.get("condition") == "FAILED_RETRYABLE"
            and failure.get("failure_category") == "NETWORK_FAILURE"
            and observed.get("condition") == "READY"
            and observed.get("previous_attempt_id") == parent.get("id")
            and evidence.get("verified") is True
            and evidence.get("capability_id") == "git.repository.acquire"
            and evidence.get("resulting_revision") == observed.get("revision")
            and len(observed.get("revision") or "") == 40
            and len(observed.get("tree") or "") == 40
        ):
            return True
    return False
