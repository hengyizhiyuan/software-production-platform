"""Golden case 8: a multi-turn product-design discussion (runs on the ECS host).

Sends a fixed sequence of Human turns to one interaction, waits for each Turn to
settle, and records every Watt reply verbatim with the Work it was attached to.
The transcript is then judged by an independent model call against three
questions: does the conversation keep moving toward a buildable plan, does
Watt's understanding drift across turns, and does it contradict or forget
decisions already confirmed.

    python3 discussion.py --name G8 --script script.json --token-file ENV --out DIR \\
        [--judge-key-file ENV]
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
parser.add_argument("--script", required=True)
parser.add_argument("--token-file", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--turn-timeout", type=float, default=600)
parser.add_argument("--judge-key-file")
args = parser.parse_args()
env = dict(l.strip().split("=", 1) for l in open(args.token_file) if "=" in l and not l.startswith("#"))
token = env["SPG_OPERATOR_TOKEN"]
script = json.load(open(args.script, encoding="utf-8"))
os.makedirs(args.out, exist_ok=True)
start = time.time()
log = []


def api(method, path, body=None):
    request = urllib.request.Request(args.base + path, method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read() or b"null"), response.status
    except urllib.error.HTTPError as error:
        return {"http_error": error.code, "body": error.read().decode()[:1000]}, error.code
    except (urllib.error.URLError, ConnectionError, TimeoutError) as error:
        return {"http_error": 0, "body": repr(error)[:300]}, 0


def save():
    with open(os.path.join(args.out, "discussion.json"), "w", encoding="utf-8") as handle:
        json.dump({"name": args.name, "script": script, "log": log}, handle, ensure_ascii=False, indent=1)


def settle(interaction):
    """Wait until no Turn of the interaction is RECEIVED or PROCESSING."""
    deadline = time.time() + args.turn_timeout
    while time.time() < deadline:
        conversation, _ = api("GET", f"/api/experience/interactions/{interaction}")
        if "http_error" not in conversation and conversation.get("turns") and all(
                t["status"] not in ("RECEIVED", "PROCESSING") for t in conversation["turns"]):
            return conversation
        time.sleep(2)
    return None


first, status = api("POST", "/api/experience/intent", {"text": script["turns"][0]})
routing = [{"kind": first.get("kind"), "question": first.get("question")}]
if first.get("kind") == "CLARIFY" and script.get("product_name"):
    # The router is stochastic: the same opening is routed NEW or CLARIFY run to run.
    # Answer its question the way the Human would by naming the Product explicitly.
    first, status = api("POST", "/api/experience/intent",
                        {"text": f"新建一个产品「{script['product_name']}」：" + script["turns"][0]})
    routing.append({"kind": first.get("kind"), "question": first.get("question")})
if first.get("kind") == "CLARIFY":
    log.append({"turn": 0, "human": script["turns"][0], "clarify": first, "routing": routing})
    save()
    raise SystemExit("intent asked to clarify the Product twice")
product, interaction = (first.get("product") or {}).get("id"), first.get("interaction_id")
log.append({"opening_kind": first.get("kind"), "product": product, "routing": routing})
for index, text in enumerate(script["turns"]):
    sent = time.time()
    if index:
        # An ADVISORY opening has no Product; the home page cannot continue it,
        # so the driver uses the generic Interaction turn endpoint instead.
        result, status = (api("POST", f"/api/experience/products/{product}/turns",
                              {"text": text, "interaction_id": interaction}) if product else
                          api("POST", f"/api/interactions/{interaction}/turns",
                              {"content": text, "human_identity": "human:owner"}))
        if "http_error" in result:
            log.append({"turn": index, "human": text, "error": result})
            break
    conversation = settle(interaction)
    if conversation is None:
        log.append({"turn": index, "human": text, "error": "TURN_TIMEOUT"})
        break
    replies = [m["content"] for m in conversation["messages"] if m["actor"] == "WATT"]
    log.append({"turn": index, "human": text, "watt": replies[-1] if replies else None,
                "seconds": round(time.time() - sent, 1), "work": conversation.get("current_work_id"),
                "readiness": conversation.get("readiness"),
                "turn_status": conversation["turns"][-1]["status"]})
    print(json.dumps(log[-1], ensure_ascii=False)[:400], flush=True)
    save()

if args.judge_key_file:
    keys = dict(l.strip().split("=", 1) for l in open(args.judge_key_file) if "=" in l and not l.startswith("#"))
    transcript = "\n\n".join(f"[第 {e['turn'] + 1} 轮] 用户：{e['human']}\nWatt：{e.get('watt') or e.get('error')}"
                             for e in log if "turn" in e)
    rubric = (
        "你是独立评审，只评价下面这段产品方案讨论中 Watt 的表现，不评价用户。按以下三项分别给 1-5 分并说明依据，"
        "必须引用具体轮次：\n"
        "1. 推进：Watt 是否把讨论持续推向一个可以开工的方案（主动收敛、提出下一步、在合适时询问是否开工），还是原地打转。\n"
        "2. 不漂移：随着轮次增加，Watt 对产品目标、范围和约束的理解是否保持一致，是否被后续话题带偏。\n"
        "3. 不矛盾：Watt 是否与自己前面的回复矛盾，是否遗忘或推翻用户已经确认的决定。\n"
        "另外列出所有具体问题（轮次 + 问题），并给出总体结论 PASS/FAIL（任一项低于 3 分即 FAIL）。"
        "只输出 JSON：{\"progress\":{\"score\":n,\"reason\":\"\"},\"drift\":{\"score\":n,\"reason\":\"\"},"
        "\"consistency\":{\"score\":n,\"reason\":\"\"},\"issues\":[{\"turn\":n,\"problem\":\"\"}],\"verdict\":\"PASS|FAIL\"}")
    body = {"model": keys.get("SPG_JUDGE_MODEL", "deepseek-v4-pro"), "input": rubric + "\n\n" + transcript,
            "max_output_tokens": 16000, "reasoning": {"effort": "low"}}
    request = urllib.request.Request(keys.get("SPG_DEEPSEEK_BASE_URL", "https://api.deepseek.com") + "/responses",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + keys["SPG_DEEPSEEK_API_KEY"], "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        payload = json.loads(response.read())
    text = "".join(part.get("text", "") for item in payload.get("output", []) if item.get("type") == "message"
                   for part in item.get("content", []))
    try:
        verdict = json.loads(text[text.index("{"):text.rindex("}") + 1])
    except ValueError:
        verdict = {"raw": text}
    with open(os.path.join(args.out, "judgement.json"), "w", encoding="utf-8") as handle:
        json.dump(verdict, handle, ensure_ascii=False, indent=1)
    print("JUDGEMENT", json.dumps(verdict, ensure_ascii=False)[:1500], flush=True)
print("DONE", round(time.time() - start), "s", flush=True)
