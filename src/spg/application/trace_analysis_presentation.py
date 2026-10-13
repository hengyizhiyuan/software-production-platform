"""Small, read-only projections of saved analysis receipts; no new inference."""
from html import escape


def analysis_summary(record):
    """Exclude candidates, snapshots and execution payloads from the user view."""
    result = {key: record.get(key) for key in (
        "work_id", "request_id", "status", "phase", "started_at", "finished_at",
        "verification", "semantic_qualification", "authority", "report",
        "native_self_review", "liveness")}
    kernel = record.get("kernel_result") or {}
    result["kernel_result"] = {key: kernel.get(key) for key in (
        "terminal_outcome", "inference_submissions", "tool_effects",
        "summary", "residual_obligations")}
    result["failure"] = {key: value for key, value in (record.get("failure") or {}).items()
                         if key in {"error_type", "reason_code", "failure_code", "phase", "validation_issues"}}
    receipts = record.get("verification_receipts") or []
    result["verification_receipts"] = [{
        "verification": item.get("verification"),
        "draft_id": item.get("draft_id"),
        "omitted_issues": item.get("omitted_issues", 0),
        "issues": [{key: issue[key] for key in (
            "type", "reason", "location", "evidence_id", "check_observation") if key in issue}
            for issue in item.get("issues", [])[:12]],
    } for item in receipts[-6:]]
    result["omitted_verification_receipts"] = max(0, len(receipts) - 6)
    result["boundary"] = "保存记录的展示摘要；失败草稿未作为生产诊断结论，UNKNOWN 不代表没有问题。"
    return result


def concise_analysis_html(record):
    """Human-readable download, with provenance and bounded excerpts, not raw JSON."""
    value = analysis_summary(record)
    report = value.get("report")
    def text(raw, limit=1200):
        raw = str(raw or "UNKNOWN")
        return escape(raw[:limit] + ("（摘录；完整内容见页面对应 Tab）" if len(raw) > limit else ""))
    def paragraph(raw, limit=1200):
        return "<p>" + text(raw, limit) + "</p>"
    def refs(fact):
        return "<small>引用：" + text("；".join(
            str(c.get("evidence_id")) + (" " + str(c["field"]) if c.get("field") is not None else "")
            for c in fact.get("citations", [])), 1600) + "</small>"
    sections = ["<h1>Watt Trace 简明分析报告</h1>", paragraph(
        f"Work：{value['work_id']} / 分析请求：{value['request_id']}", 500),
        paragraph(f"分析状态：{value['status']} / 引用校验：{value['verification']}", 500),
        paragraph("报告供人工审查；根因假设不等于已证实根因。本文件摘录重点，不包含执行证据整包。", 500)]
    if report:
        sections += ["<h2>目标与当前状态</h2>"]
        for key in ("original_objective", "current_state"):
            fact = report.get(key) or {}
            sections += [paragraph(fact.get("statement")), refs(fact)]
        for finding in report.get("findings", [])[:3]:
            fact = finding.get("fact") or {}
            sections += ["<h2>失败现象 / 偏离</h2>", paragraph(fact.get("statement")), refs(fact),
                "<h2>原因总结</h2>", paragraph(f"{finding.get('epistemic_status', 'UNKNOWN')} · {finding.get('classification', 'UNKNOWN')}", 200),
                paragraph(finding.get("analysis")), paragraph("边界：" + str(finding.get("uncertainty", "UNKNOWN"))),
                "<small>源码引用：" + text("；".join(str(c.get("evidence_id")) for c in finding.get("repository_citations", [])), 1200) + "</small>",
                "<h2>改进方案</h2>", paragraph(finding.get("recommendation")),
                paragraph("回归资格：" + str(finding.get("regression_qualification", "UNKNOWN")))]
        if not report.get("findings"):
            sections += [paragraph("未形成具体偏离的 Finding，原因保持 UNKNOWN。")]
        for title, key in (("立即恢复", "immediate_recovery"), ("Self-Refine", "self_refine_opportunities"),
                           ("平台改进", "platform_improvements"), ("延期事项", "deferred_items")):
            sections += ["<h3>" + title + "</h3>"]
            for item in report.get(key, [])[:3]:
                sections += [paragraph(item.get("statement"), 900),
                             "<small>依据：" + text("、".join(item.get("finding_ids", [])), 300) + "</small>"]
        sections += ["<h2>生产过程摘录</h2>"]
        for event in report.get("timeline", [])[:12]:
            sections += [paragraph(f"{event.get('stage')} · {event.get('timestamp') or '未记录单一事件时间'}", 200),
                         paragraph(event.get("statement"), 350), refs(event)]
        sections += ["<h2>缺失证据 / UNKNOWN</h2>"]
        for gap in report.get("missing_evidence", [])[:6]:
            sections += [paragraph(gap if isinstance(gap, str) else gap.get("statement"), 500)]
    else:
        kernel = value["kernel_result"]
        sections += ["<h2>失败现象</h2>", paragraph("本次分析未形成合格报告；原 Work 的根因保持 UNKNOWN。"),
            "<h2>原因总结（分析流程自身）</h2>", paragraph(kernel.get("summary"), 3000),
            paragraph("终态：" + str(kernel.get("terminal_outcome") or "UNKNOWN"), 200),
            paragraph("错误类型：" + str(value["failure"].get("error_type") or "未记录额外异常"), 200),
            "<h3>保存的校验反馈</h3>"]
        for receipt in value["verification_receipts"][-3:]:
            for issue in receipt["issues"][:4]:
                sections += [paragraph(f"{issue.get('location', '')}：{issue.get('reason') or issue.get('type')}", 700)]
        sections += ["<h2>改进方案</h2>", paragraph(
            "依据保存的校验反馈修订引用与证据范围，在原权限和预算内完成自审；未验证的生产原因保持 UNKNOWN。若仍无法形成报告，保留失败记录供人工审查。", 500)]
    sections += [paragraph(f"推理：{value['kernel_result'].get('inference_submissions')} / 工具：{value['kernel_result'].get('tool_effects')}", 200)]
    return ("<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
            "<title>Watt Trace 简明分析报告</title><style>body{max-width:900px;margin:32px auto;padding:0 20px;"
            "font:16px/1.7 sans-serif;color:#18333c}h2{border-bottom:1px solid #ddd;padding-bottom:6px}"
            "p,small{white-space:pre-wrap;overflow-wrap:anywhere}small{color:#5c6b70}@media print{body{margin:0}}</style>"
            "<body>" + "".join(sections) + "</body></html>").encode("utf-8")
