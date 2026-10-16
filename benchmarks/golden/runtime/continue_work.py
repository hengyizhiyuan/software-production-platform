"""Continue an already-admitted Work to delivery: controlled authorization, publish, download, accept.

Same public-API steps as golden_journey.py, for a Work that is already running.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

base, work_id, product_id, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
token = next(l.split("=", 1)[1].strip() for l in open("/run/watt.env") if l.startswith("SPG_OPERATOR_TOKEN="))
start = time.time()


def api(method, path, body=None, raw=False):
    request = urllib.request.Request(base + path, method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
            return (payload if raw else json.loads(payload or b"null")), response.status
    except urllib.error.HTTPError as error:
        return {"http_error": error.code, "body": error.read().decode()[:500]}, error.code
    except (urllib.error.URLError, ConnectionError, TimeoutError) as error:
        return {"http_error": 0, "body": repr(error)[:200]}, 0


def say(*parts):
    print(f"{time.time() - start:7.1f}s", *parts, flush=True)


previewed, authorized, published, last = False, set(), set(), None
while time.time() - start < 3000:
    ws, code = api("GET", f"/api/experience/products/{product_id}/workspace?work={work_id}")
    if code != 200:
        time.sleep(5); continue
    r = ws.get("reality") or {}
    cand, guardian = r.get("candidate") or {}, r.get("guardian") or {}
    state = ((ws.get("work") or {}).get("status"), guardian.get("gate"), bool(cand.get("candidate_fingerprint")),
             len(r.get("deliveries") or []), sorted({a.get("kind") for a in ws.get("actions") or []}))
    if state != last:
        say("STATE", state); last = state
    for action in ws.get("actions") or []:
        options = action.get("actions") or []
        if action["id"] in authorized or "AUTHORIZE" not in options:
            continue
        if not previewed:
            _, code = api("POST", f"/api/works/{work_id}/candidate-preview", {}); previewed = True
            say("PREVIEW", code); break
        out_, code = api("POST", f"/api/attention/{action['id']}/resolve", {"action": "AUTHORIZE",
            "authority_identity": "human:owner", "rationale": "Controlled authorization (Golden G2)."})
        if code < 300:
            authorized.add(action["id"])
        say("AUTHORIZE", code, str(out_)[:160])
    if (cand.get("candidate_fingerprint") and guardian.get("gate") == "PASS" and not r.get("deliveries")
            and not cand.get("authorization_pending") and cand["candidate_fingerprint"] not in published):
        out_, code = api("POST", f"/api/works/{work_id}/deliveries", {"candidate_fingerprint": cand["candidate_fingerprint"],
            "repository_revision": cand.get("repository_revision")})
        published.add(cand["candidate_fingerprint"]); say("PUBLISH", code)
    for delivery in r.get("deliveries") or []:
        manifest = delivery.get("manifest") or {}
        if manifest.get("id") and not delivery.get("acceptance"):
            data, code = api("GET", f"/api/works/{work_id}/deliveries/{manifest['id']}/download", raw=True)
            if code == 200:
                open(os.path.join(out, "delivery.zip"), "wb").write(data)
            say("DOWNLOAD", code, len(data) if isinstance(data, bytes) else 0)
            out_, code = api("POST", f"/api/works/{work_id}/deliveries/{manifest['id']}/acceptance",
                {"manifest_fingerprint": manifest.get("fingerprint"), "decision": "ACCEPT",
                 "authority_identity": "human:owner", "rationale": "Controlled acceptance (Golden G2)."})
            say("ACCEPT", code)
            raise SystemExit(0)
    if (ws.get("work") or {}).get("status") in {"BLOCKED", "FAILED", "DISCARDED", "NEEDS_ATTENTION"} and not any(
            "AUTHORIZE" in (a.get("actions") or []) for a in ws.get("actions") or []):
        say("STOPPED", state)
        if time.time() - start > 60:
            raise SystemExit(1)
    time.sleep(4)
say("DEADLINE")
