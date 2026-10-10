# 当前独立 Review 容量与语义边界

## 已证实

- 最终源码 `8c2b3d224e898b3dc8e8220f78f6a6723c158941`，镜像 `sha256:97a8db7f77c2898a65bdc975bb0f49f0f3350fe3e20c6e3650f4aeb3e54c01fa`。
- 第二次 Formation：45 Route，完整结构/Owner 必要前提 PASS；42 BOUND_PENDING_EVIDENCE，3 RETAINED_CONTEXT。原三项路径参数、两项来源证明机械失败不再出现，一次反馈有效修复本次四项来源证明错误。
- Candidate fingerprint：`cac68104396cc5bb5e313a9069508b80e24db028e6ec70414ea902f96bd2827f`；components fingerprint：`648e1a31a8f8a8924c59d5e306a11080d8bf3e6d604c1cc0973c483b62a546b5`；原库存 fingerprint：`7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf`。
- 独立 Review：请求体 65,745 字节、实际输入 20,758 tokens；HTTP 200 后 `incomplete/max_output_tokens`，实际 output=16,384、reasoning=16,384，output_text delta=0。没有 Review JSON，语义完整性结论 UNKNOWN。
- 原 canonical Review 请求实际输入 33,148 tokens、请求体 104,657 字节，也以全部 16,384 reasoning tokens 停止。新 existing-wire 输入减少了冗余，但没有取得独立审查结果。
- 本地 ModelProfile 仅有 reasoning_effort/max_output_tokens，Adapter 将其传给 `/responses`；没有现有的可见输出预留或 reasoning 硬预算字段。

## Provider 契约核对（2026-10-10，只读，无额外模型调用）

Responses 的 max_output_tokens 同时包括 reasoning 和可见输出；effort 控制思考模式。见 [官方 API](https://api-docs.deepseek.com/api/create-response/)。

[官方兼容性说明](https://api-docs.deepseek.com/guides/responses_api/)仅支持 reasoning.effort 等列出的能力，未支持的参数会被忽略；不能发明一个输出预留参数并宣称已生效。[Anthropic 兼容说明](https://api-docs.deepseek.com/guides/anthropic_api/)明确 budget_tokens 被忽略，也不是可用的规避方案。

这些文档没有证明 low 在当前完整审查上一定可以于 16,384 内完成。未公开的控制能力、完成该审查所需的实际 reasoning 数量及货币费用 UNKNOWN。

## 尚未关闭的真实语义问题

当前实际提案 Route 41/source 23 将文件新增排除关联 DENY_PREVIEW，Route 21/source 13 同样提议该 Gate。既有消费器实际会据此禁止 preview.inspect；该限制的语义来源仍未被独立 Review 证明。

同源正确的 Git Diff Route 42 不能证明额外 Preview 禁止也合法。结构/来源身份 PASS 只能说明引用和必要参数合法，不能自动证明这种语义映射。没有为此建立关键词 Alias、改写 Fact、虚构 typed effect 或跳过 Review。

所以本轮没有合格的 Fulfillment Plan、Work/Candidate/Assurance PASS。最终 Owner 保持 STOPPED/UNRESOLVED，原历史 Candidate、Work 和 Human Decisions 不变。

## 下一项必要决策与最小后续验证建议

现有固定 Review low/16,384 下，两个不同大小输入的真实调用均耗尽 reasoning 而无审查输出。没有新的 Provider 条件或有效配置变化前，继续相同调用没有修复依据。停止原因是这一已证实的独立 Review 能力/预算契约边界，不是 Formation 两次候选限制。

建议先在现有独立 Semantic Review Owner 内校准推理模式：对上述未改动、精确 fingerprint 的 45 Route 提案做一次隔离 `reasoning=none` 审查，保持模型、16,384 上限、120 秒、库存、输出 Schema、全部确定性与语义完整性门禁；不修改生产默认 Profile。目的先是取得完整、可核验的审查反馈，不能预设 PASS。

该模式改变不属于此前明确固定的 Review low 验证配置，因此本轮未执行。若随后采用此方案，必须另外证明该 Reviewer 会拒绝机械合法而语义错误的候选；未证明前不能把 none 的单一 PASS 当成同等生产资格。

拿到真实审查失败后，才在既有 Formation/一次反馈机制内修复对应语义候选或反馈消费缺陷，按新的精确源码资格继续；不修改历史提案后冒称成功，不扩张为分阶段 Formation，不解封 Holdout或启动 G0/C4。

保留 low 并改变总预算、增加新的分阶段能力或更换模型都是不同的资源/架构选择；本轮没有实施。没有提出把 Review 改成确定性关键词判断的方案。
