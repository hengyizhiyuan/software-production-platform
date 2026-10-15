"""Golden Journey driver over Watt's public HTTP API (runs on the ECS host).

Drives one natural-language requirement through the same endpoints as the
experience frontend, applies controlled authorization automatically (Human
Governor decision 2026-10-15), and records a timestamped stage timeline until
a downloadable artifact exists, a stage stalls, or the deadline passes.

    python3 journey.py --name G1 --text "..." --token-file /data/watt/runtime/.env --out DIR
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--base", default="http://127.0.0.1:8080")
parser.add_argument("--name", required=True)
parser.add_argument("--text", required=True)
parser.add_argument("--token-file", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--deadline", type=float, default=3600)
parser.add_argument("--stall", type=float, default=900)
parser.add_argument("--answer", default="按你的建议来")
args = parser.parse_args()
token = next(l.split("=", 1)[1].strip() for l in open(args.token_file) if l.startswith("SPG_OPERATOR_TOKEN="))
os.makedirs(args.out, exist_ok=True)
start = time.time()
timeline, last_change = [], time.time()
state = {}


def api(method, path, body=None, raw=False):
    request = urllib.request.Request(args.base + path, method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    begin = time.time()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
            elapsed = time.time() - begin
            return (payload if raw else json.loads(payload or b"null")), elapsed, response.status
    except urllib.error.HTTPError as error:
        return {"http_error": error.code, "body": error.read().decode()[:2000]}, time.time() - begin, error.code
    except (urllib.error.URLError, ConnectionError, TimeoutError) as error:
        # A restarting API is an observation, not the end of the journey.
        return {"http_error": 0, "body": repr(error)[:300]}, time.time() - begin, 0


def mark(event, **detail):
    global last_change
    last_change = time.time()
    row = {"t": round(time.time() - start, 2), "event": event, **detail}
    timeline.append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)
    save()


def save():
    with open(os.path.join(args.out, "timeline.json"), "w") as handle:
        json.dump({"name": args.name, "text": args.text, "timeline": timeline, "state": state}, handle, ensure_ascii=False, indent=1)


def signature(ws):
    r = ws.get("reality") or {}
    work = ws.get("work") or {}
    cand = r.get("candidate") or {}
    return {"work_status": work.get("status"), "step": (ws.get("focus") or {}).get("status"),
        "execution": (r.get("execution") or {}).get("state") if isinstance(r.get("execution"), dict) else r.get("execution"),
        "candidate": bool(cand.get("candidate_fingerprint")), "authorization_pending": cand.get("authorization_pending"),
        "guardian": (r.get("guardian") or {}).get("status"), "gate": (r.get("guardian") or {}).get("gate"),
        "deliveries": len(r.get("deliveries") or []),
        "accepted": any((d.get("acceptance") or {}).get("decision") == "ACCEPT" for d in r.get("deliveries") or []),
        "actions": sorted({a.get("kind") for a in ws.get("actions") or []}),
        "admission": (r.get("admission_context") or {}).get("status")}


result, elapsed, status = api("POST", "/api/experience/intent", {"text": args.text})
mark("intent_submitted", http=status, request_s=round(elapsed, 2), kind=result.get("kind"))
if result.get("kind") == "CLARIFY":
    mark("clarify", question=result.get("question"), options=result.get("options"))
    state["terminal"] = "CLARIFY_AT_INTENT"
    save()
    raise SystemExit(0)
product = (result.get("product") or {}).get("id")
interaction = result.get("interaction_id")
state.update(product=product, interaction=interaction)
seen_turns, answered, previewed, authorized, published, accepted = set(), set(), False, set(), set(), set()
previous = None
while time.time() - start < args.deadline:
    conversation, _, _ = api("GET", f"/api/experience/interactions/{interaction}")
    if "http_error" in conversation:
        time.sleep(3)
        continue
    for turn in conversation.get("turns", []):
        key = (turn.get("id"), turn.get("status"))
        if key not in seen_turns:
            seen_turns.add(key)
            mark("turn", turn=turn.get("id"), status=turn.get("status"))
    replies = [m for m in conversation.get("messages", []) if m.get("actor") == "WATT"]
    if replies and state.get("last_reply") != replies[-1].get("content"):
        state["last_reply"] = replies[-1].get("content")
        mark("watt_reply", chars=len(state["last_reply"]), text=state["last_reply"][:600])
    work_id = conversation.get("current_work_id")
    if work_id and state.get("work") != work_id:
        state["work"] = work_id
        mark("work_admitted", work=work_id)
    query = f"?work={work_id}" if work_id else f"?interaction={interaction}"
    ws, ws_s, _ = api("GET", f"/api/experience/products/{product}/workspace{query}")
    if isinstance(ws, dict) and "http_error" not in ws:
        sig = signature(ws)
        if sig != previous:
            mark("workspace", workspace_ms=round(ws_s * 1000), **sig)
            previous = sig
        for action in ws.get("actions") or []:
            kind, aid = action.get("kind"), action.get("id")
            options = action.get("actions") or []
            if aid in answered:
                continue
            if "AUTHORIZE" in options or "APPROVE" in options:
                if "AUTHORIZE" in options and not previewed and work_id:
                    preview, _, code = api("POST", f"/api/works/{work_id}/candidate-preview", {})
                    previewed = True
                    mark("preview_requested", http=code)
                    continue
                choice = "AUTHORIZE" if "AUTHORIZE" in options else "APPROVE"
                out, _, code = api("POST", f"/api/attention/{aid}/resolve", {"action": choice,
                    "authority_identity": "human:owner", "rationale": "Controlled authorization (Golden Journey)."})
                if code < 300:
                    answered.add(aid)
                mark("controlled_" + choice.lower(), attention=aid, kind=kind, http=code, detail=str(out)[:300])
            elif action.get("interaction_id") or kind in {"QUESTION", "HUMAN_QUESTION", "CLARIFICATION", "DECISION"}:
                out, _, code = api("POST", f"/api/experience/products/{product}/turns",
                    {"text": args.answer, "interaction_id": action.get("interaction_id") or interaction, "attention_id": aid})
                answered.add(aid)
                mark("answered_question", attention=aid, kind=kind, http=code)
        r = ws.get("reality") or {}
        cand = r.get("candidate") or {}
        if work_id and cand.get("candidate_fingerprint") and (r.get("guardian") or {}).get("gate") == "PASS" \
                and not r.get("deliveries") and cand["candidate_fingerprint"] not in published and not cand.get("authorization_pending"):
            out, _, code = api("POST", f"/api/works/{work_id}/deliveries", {"candidate_fingerprint": cand["candidate_fingerprint"],
                "repository_revision": cand.get("repository_revision")})
            published.add(cand["candidate_fingerprint"])
            mark("delivery_published", http=code, detail=str(out)[:300])
        for delivery in r.get("deliveries") or []:
            manifest = delivery.get("manifest") or {}
            if manifest.get("id") and manifest["id"] not in accepted and not delivery.get("acceptance"):
                data, dl_s, code = api("GET", f"/api/works/{work_id}/deliveries/{manifest['id']}/download", raw=True)
                if code == 200:
                    with open(os.path.join(args.out, "delivery.zip"), "wb") as handle:
                        handle.write(data)
                mark("downloaded", http=code, bytes=len(data) if isinstance(data, bytes) else 0, download_s=round(dl_s, 2))
                out, _, code = api("POST", f"/api/works/{work_id}/deliveries/{manifest['id']}/acceptance",
                    {"manifest_fingerprint": manifest.get("fingerprint"), "decision": "ACCEPT",
                     "authority_identity": "human:owner", "rationale": "Controlled acceptance (Golden Journey)."})
                accepted.add(manifest["id"])
                mark("accepted", http=code, detail=str(out)[:300])
                state["terminal"] = "DELIVERED_AND_ACCEPTED" if code < 300 else "DOWNLOADED"
                save()
                raise SystemExit(0)
        if (ws.get("work") or {}).get("status") in {"BLOCKED", "FAILED", "DISCARDED"} and time.time() - last_change > 120:
            state["terminal"] = "WORK_" + ws["work"]["status"]
            work, _, _ = api("GET", f"/api/works/{work_id}") if work_id else ({}, 0, 0)
            state["work_detail"] = work
            mark("terminal", reason=state["terminal"])
            break
    if time.time() - last_change > args.stall:
        state["terminal"] = "STALLED"
        mark("terminal", reason="STALLED", idle_s=round(time.time() - last_change))
        break
    time.sleep(3)
else:
    state["terminal"] = "DEADLINE"
    mark("terminal", reason="DEADLINE")
if state.get("work"):
    for name, path in (("work", ""), ("steering", "/steering"), ("operations", "/operations"), ("self_refine", "/self-refine")):
        data, _, _ = api("GET", f"/api/works/{state['work']}{path}")
        with open(os.path.join(args.out, f"{name}.json"), "w") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=1)
save()
