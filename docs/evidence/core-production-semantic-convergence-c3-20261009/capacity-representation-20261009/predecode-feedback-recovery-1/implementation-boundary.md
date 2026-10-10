# C3 Predecode Feedback Recovery — Approved Implementation Boundary

Human 已批准最小修复，并要求诊断严格绑定原始 Wire fingerprint、库存 fingerprint、Attempt 和持久收据。
基线 application `a91442c21ed487b10d8dc38023b0807787a29648`，证据 HEAD `6ef1cff94f4a8cbab7b16eb861b338627ab56824`。
Guardian `76c1e87a1b29d151f4ed949748e3298f2169c5b1` / ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c` 保持不变。

## 修改范围

- 现有 Provider decoder：有界、脱敏的独立 wire 谓词集合。原始 bytes SHA256 与 raw route fingerprint；不构造部分 Candidate 或 component ID。
- 现有 Work formation/feedback Owner：绑定原始请求与响应 receipt IDs、Attempt、Work Reality、Source、库存、Wire request/table/schema fingerprints；诊断 fingerprint；下一请求引用实际反馈收据。
- 恢复、终态重放和下一候选前重算诊断/反馈，核对原始 bytes / 收据 / 来源 / 血缘；漂移即 UNRESOLVED truthful stop，不再调用模型。
- 复用既有 source index、`fulfillment-compact-v1` 和反馈 v2；两候选、一反馈、最多四逻辑调用及原模型预算不变。
- 不自动修改 f/u、丢弃引用、扩展跨度、补造事实或授予权限；需要 locator 的原文覆盖保持 NOT_EVALUABLE，后续由现有 locator/validators/Review 负责。

## 资格边界

受控正向、负向、持久化恢复和 exact image 回归；旧 raw outputs 可只读重检，不修改历史收据或冒称新模型成功。
本轮无真实模型请求、G0、Holdout、生产修改或 Guardian/ECF 契约变化；不自动关闭 C3。
公开报告仅含身份、稳定谓词、数字及脱敏日志。完整历史私有输入保持原 ECS 恢复位置。
