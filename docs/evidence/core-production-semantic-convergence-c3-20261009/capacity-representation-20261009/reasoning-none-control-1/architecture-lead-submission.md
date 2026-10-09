# C3 — 推理模式对照验证结果提交

**结果：Provider COMPLETED；Candidate 被既有确定性校验拒绝；C3 保持 PARTIAL。执行已停止。**

Human 于 2026-10-10 批准一次隔离对照：Formation 仅将 `reasoning.effort=low` 改为 `none`，Review 保持 `low`；仍为 `deepseek-flash / 16384 / 120 秒`，不允许任何重试。此次结果不替换 [原 low 验证](../live-model-verification-1/architecture-lead-submission.md)，不修改运行时模型配置或已冻结应用。

## 1. 精确身份与请求差异

- Watt：`e0df8196cb51480f542af13b40cfa77fca6b6a6e`；Tree：`d479d61f5fcac075a5af3a274f60cbe3f6e9f53f`。
- 实际镜像：`sha256:7a4ac00e3599bda2dbcebe46b15dd0b45f3be86552021023ebd288eb732f7b35`。
- Guardian：`d01bac1ad153e1eadefafe87d2ea4f5d65896ab6`；ECF：`5aa4f8833c359c15bd059eda5972aa3915bcc18c`。
- 原 Work 库存：`048189aa-0613-5307-b6f4-c430e7977f93`；Reality：`332a3a38-8719-580c-a1a2-c331ae14a5ae`；同一 26 项来源和 12 个已有 Capability。
- Inventory：`7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf`；原快照 SHA256：`9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c`。
- 本次执行：**2026-10-10 01:15:13.947 → 01:15:25.857 Asia/Shanghai**；原始收据为 UTC 2026-10-09 17:15:13.947 → 17:15:25.857。

离线预检确认实际镜像、288 个已安装 Owner 源码文件哈希、库存、wire request/table/schema 身份匹配。Formation 的完整请求对象与原请求比较，**只有 `reasoning.effort` 不同**；其他 Instructions、Inventory、Capabilities、Schema、模型及预算一致。实际请求体 54,366 字节，SHA256 `c0f6c531dcc4878afba390edbdeeb1f0c1ef08845ed749546142f543ebd90acc`；原 low 请求为 54,365 字节。这不是减少库存或 Prompt 的试验。

调整只发生在独立探针的请求内存 Profile，原始配置仍为 `low`。冻结应用和生产环境配置没有改变。独立 Review 的原有 `low` 配置完成了离线核对，但未被调用。

## 2. 实际 Provider 对照

| 指标 | 先前 low 验证 | 本次 none 对照 |
|---|---:|---:|
| HTTP | 200 | 200 |
| Provider 终态 | incomplete / max_output_tokens | **completed** |
| input_tokens | 17,466 | **17,441** |
| output_tokens | 16,384 | **3,722** |
| reasoning_tokens | 16,384 | **0** |
| cached_tokens | 0 | **0** |
| total_tokens | 33,850 | **21,163** |
| 独立可见 JSON Token 数 | UNKNOWN | **UNKNOWN** |
| 观察耗时，秒 | 60.591191162 | **11.909806004** |

本次请求 ID：`cbf1ecf5-2224-46e0-934a-e2e192560407`；requested/effective model 均为 `deepseek-flash`。观察到首个响应事件和 `provider_first_token`。完整模型 JSON 为 10,903 UTF8 字节，SHA256 `f83c20fd050555b1983cc1cc00f9feccc10751a1fa95ff14f087d52ec98c24d5`。

**仅一次 Formation、一次 HTTP；零传输重发、零 Self-Refine、零 Review。** 用户禁止重试由探针在任何恢复重发前终止的守卫执行；本次并未触发该守卫。Usage 表为 Provider 实际报告字段，不把 reasoning 重复加到 output。独立可见 JSON Token 计数、计费金额、CPU、峰值内存未测量。

## 3. Candidate 完整性与拒绝证据

冻结 Provider 成功通过安全观察、wire JSON/schema 解码与精确 Owner metadata 恢复，形成一个**未接纳的 Fulfillment Candidate**。它不是软件产物的 sealed Candidate。

- 57 条候选 Route，包含全部 26 个来源 ordinal `0–25`；提案中覆盖全部 11 个 Work Constraint indices `0–10`。
- 现有精确引文定位未作任何调整；本次不进行模型反馈、去重、临时修补或追加请求。
- Candidate fingerprint：`98e38e96d66751327a6eb44519cf980db471aae99664b324c3e36a043a049444`。
- Components fingerprint：`74d621203266a170e163f420e9899ac989cd611d1c80c0d2a30af594ca74ff94`。
- **真实第一失败谓词：`OBLIGATION_PROJECTION_DUPLICATE_ROUTE`**，位于既有 `validate_projection_candidate` 的 `(source_ref, capability)` 唯一性检查。

具体重复是 source ordinal **5（FACT）** 的 **两条 `ARTIFACT_CONTENT`**：两者目标均为 `index.html`，component span 均为 `[0,71)`，引用／支持／范围一致，quote SHA256 均为 `6d705ee2c308e80fe8caf6db21f4ba5b0e004098a0bf81bd13fbb7ea98be57e1`，只有 rationale 不同。这是本次观察到的重复提案，**没有证据证明是合法不同组件被错误合并或误拒**。不为通过而删除一条 Route。

此外，实际提案包含 **11 条 `UNRESOLVED` Route**。这只是候选表达观察，不是已生成的权威 Binding 状态；不得将其改写为本次实际下游停止谓词。唯一性失败发生在其他完整验证之前，因此来源集合、约束索引“存在”不证明原值、顺序、Scope、权限、完整语义或最终 Owner/Phase/Gate 全部已验证。

完整确定性校验：**FAIL**。独立 Semantic Review：**NOT_EXECUTED**。其完整性与语义结论不得报告 PASS；无合格候选，未消耗第二次模型调用。后续运行时 Admission、Verification、Guardian、Integration、Acceptance、Delivery 均未执行或授权。

## 4. 结论与 Architecture Lead 决策边界

**E1 / PROVEN_SCOPED：** 在该精确库存和冻结应用上，仅改变 Formation reasoning 为 `none` 的此次请求完成了模型输出，未触发原来的输出容量终态；但产出的候选不满足现有契约，专项真实计划资格未通过。

单次随机输出不能证明 `none` 是通用的正确默认值、容量问题已永久消除、输入 Token 计数为何相差 25、或为何出现重复与未决。没有对原事故 Work、隐藏推理或 Provider 统计语义作历史倒推。也不能把这次 JSON 完成当作语义完整性或 C3 Closure。

按 Human 指令，**转交 Architecture Lead 判断是否需要有界分阶段语义形成设计**。评审输入包括本次重复、11 个未决提案及原 low 容量终态。当前证据不足以自行认定必须建立分阶段机制；如批准后续设计，仍应明确多组件闭合、完整库存／原始 Fact／权限、现有独立 Review、累计预算和 Owner 边界如何连续保持。本次不扩大实现、不更改门禁、不去重后重验、不改生产 Profile、不请求新的 Work/G0。

## 5. 持久化与退出

- [实际运行结果](reasoning-mode-result.json)：完整阶段、实际 Usage、请求差异、Candidate 元数据与失败谓词。
- [Candidate 结构审查](candidate-integrity-review.json)：可复核的来源存在性、重复与未决统计，不宣称语义 PASS。
- [授权](authorization.json)；[预检](preflight-container.json)；[调用前](live-container-before.json)／[调用后](live-container.json)实际容器身份。
- [恢复与交付](delivery-and-recovery.md)；[公开文件哈希](public-file-manifest.json)。

ECS 本次恢复目录：`/data/watt/c3-semantic-convergence-20261009/capacity-representation-20261009/reasoning-none-control-1/`。原始结果在 `evidence/`；安全 Candidate 原文、展开候选、原有 Provider-only 凭据和执行日志在受保护的 `private/`，不进入 Git。公开证据只保存身份、数值、ordinal、稳定失败码和内容哈希，不保存隐藏推理、密钥、敏感 Prompt 或原始 Provider 私有响应体。

容器已退出并保留，执行标记防止自动重复。应用、测试框架、生产配置、原 Work／Owner／Candidate／Human Decision／Quality Ledger／Holdout 均保持不变。本次新增证据推送原 C3 分支，完成后停止。
