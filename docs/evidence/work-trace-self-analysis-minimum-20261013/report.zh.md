# Watt 真实 Work 自分析报告（中文）

- Work：`3ee622b5-b816-5679-afdc-e5de51cd2702`
- 分析请求：`1a9c6de8-8aea-4b80-aea9-e78331dcdd61`
- 报告摘要：`5e5247071cbfc808cfb3029e49b28958ddc247e019ffe4802a26a2e7afb3f3e5`
- 范围：本阶段仅详细分析一个事件；其他因果问题保持未分析或 UNKNOWN。
- 权限：仅咨询，不创建 Work、不修改源码、不部署。
- **来源：Watt Native 草稿经 Codex 辅助修订与来源校验；Watt 原执行为 FAILED / UNABLE_TO_COMPLETE。**
- 本报告不代表 Watt Native 自动分析通过，不用于部署准入。

## 原始目标

Human 首次输入要求新开一个独立有界 Work：只新增 services.html 服务介绍页与 news.html 公司新闻页，每页包含中文标题、简短说明和返回 index.html 的链接；两页分别原样使用各自指定文案；两页各自验证后整合并再次验证为同一事项的最终成果；不使用后端与外部资源；完成后形成候选成果，经真实 HTTP 预览与独立质量检查，等待 Human 明确验收，不自动接受。

引用：`fc3ffa57-bab3-5598-8c1e-300ce6b9d1d8`

## 预期结果

该 Work 的既定期望是产出 services.html 与 news.html 两个静态页面并各自满足内容与导航要求，随后整合验证；候选成果须经真实 HTTP 预览与独立质量检查后交 Human 明确验收，不自动接受。work 记录把该期望概括为「独立新增 services.html 与 news.html 两个静态页面; Provide an independently verified Preview of the exact produced Candidate for Human review.」。期望是规则性表述，不等于预览或验收事件已发生。

引用：`226cc9b7-9509-504f-961f-c16e4a420a88`/desired_outcome, `fc3ffa57-bab3-5598-8c1e-300ce6b9d1d8`

## 实际路径

冻结 Work 行记录 3 个 PWU、3 条 Self-Refine 事件。精确候选相对基线的最终净差异只列出 news.html 与 services.html；读取的候选两页包含各自指定文案和返回 index.html 的链接。这只说明两端提交的净变化，不能排除中间写入或外部副作用。本报告仅详细核对一次 process.run 拒绝；另外两条 Self-Refine 的根因、实际修复动作与重试次数未分析。

引用：`226cc9b7-9509-504f-961f-c16e4a420a88`/pwu_count, `226cc9b7-9509-504f-961f-c16e4a420a88`/self_refine_count, `1d01703c-5302-5e8e-ba51-180e75015661`/changed_paths, `b54db217-41fd-5200-9e59-ece37e2f9aa6`/content, `b3f83530-4019-5d81-8f8f-f54632655902`/content

## 当前状态

冻结导出中的 work 记录显示 state=COMPLETED、bucket=COMPLETED、queue_condition=COMPLETED、complete=true、completion_outcome=PRODUCED、acceptance_decision=ACCEPT、candidate_state=SEALED、repair_status=VERIFIED、steering_outcome=COMPLETE。这些是该行的冻结快照值；latest_activity_at 表示记录内的最近活动时间，不证明各状态在该时刻发生转换。

引用：`226cc9b7-9509-504f-961f-c16e4a420a88`

## 生产时间线

- 未赋予具体时间 / INTENT：Human 首次输入提出：新开一个独立有界 Work，新增 services.html 与 news.html，并规定中文标题与说明、返回 index.html 的链接、指定文案、整合验证、无后端与外部资源、真实 HTTP 预览与独立质量检查、最终由 Human 明确验收。该记录是纯文本原始输入，未观察到时间字段。
  - 引用：`fc3ffa57-bab3-5598-8c1e-300ce6b9d1d8`
- 2026-10-05T16:58:12.766041+00:00 / FAILURE：self-refine 事件（affected_component=semantic/scope）记录 signal=SCOPE_INFLATION、failure_family=CANDIDATE_INCONSISTENT，diagnostic_evidence 列出候选路径 services.html、news.html 与一份被拒绝行为清单（含「在 index.html 中添加指向新页面的导航链接」）。该清单是 Owner 诊断，不是已执行的文件写入证据。
  - 时间边界：此时间仅表示记录创建时间；同一行的其他字段是冻结快照值，不自动证明它们在该时刻已经成立。恢复完成须读取相应更新或结束记录。
  - 引用：`5175c590-1c90-5a47-acaf-b45601436cb0`/failure_family, `5175c590-1c90-5a47-acaf-b45601436cb0`/diagnostic_evidence, `5175c590-1c90-5a47-acaf-b45601436cb0`/created_at
- 2026-10-05T16:58:13.408052+00:00 / PLANNING：冻结导出中的计划历史记录显示一次 STEP_TRANSITION：rationale 为「The current governed Step is ready to yield to the next admitted ordered Step」，其 reality_refs 中包含 kind=WORK 的 3ee622b5-b816-5679-afdc-e5de51cd2702 以及 GOVERNANCE_DECISION、SEMANTIC_RESULT、TRUSTED_BASELINE、WORK_REALITY_REVISION 引用。该记录是计划/步骤迁移事件，只记录迁移意图与引用。
  - 时间边界：此时间仅表示记录创建时间；同一行的其他字段是冻结快照值，不自动证明它们在该时刻已经成立。恢复完成须读取相应更新或结束记录。
  - 引用：`052d3c95-d143-5a93-886e-2ab3c620e8d3`, `052d3c95-d143-5a93-886e-2ab3c620e8d3`, `052d3c95-d143-5a93-886e-2ab3c620e8d3`/created_at
- 2026-10-05T16:59:24.631047+00:00 / FAILURE：一次 process.run 效果被拒绝：semantic_input 为 {argv: [ls, -la], cwd: .}，对应 receipt 的 output 为 effect_observed=false、error_type=ValueError、message='process executable is not allowlisted: ls'。
  - 时间边界：此时间仅表示记录创建时间；同一行的其他字段是冻结快照值，不自动证明它们在该时刻已经成立。恢复完成须读取相应更新或结束记录。
  - 引用：`7c97f43c-007e-57be-8740-97763f6b50b8`/semantic_input, `1a0c3cf3-4db9-5a68-8bc0-6bf201de1787`/output, `1a0c3cf3-4db9-5a68-8bc0-6bf201de1787`/created_at
- 2026-10-05T16:59:46.252619+00:00 / VERIFICATION：原始验证记录 obligation=PATH_SCOPE、result=PASS，source_ref=verification:54a6b0dd-7e72-55ab-956e-04cfd7059e1e。该条结果不证明其他验证、真实 HTTP 响应、浏览器渲染或交付下载成功。
  - 时间边界：此时间仅表示Owner 记录的事件时间；同一行的其他字段是冻结快照值，不自动证明它们在该时刻已经成立。恢复完成须读取相应更新或结束记录。
  - 引用：`de394107-6d51-5342-9688-eaf0f485936a`/obligation, `de394107-6d51-5342-9688-eaf0f485936a`/result, `de394107-6d51-5342-9688-eaf0f485936a`/source_ref, `de394107-6d51-5342-9688-eaf0f485936a`/timestamp
- 2026-10-05T17:00:20.983972+00:00 / RECOVERY_REFINEMENT：recovery 记录（affected_component=native-tool-host/process.run）以 budget_decision.classification_basis='rejected tool recipe had no effect' 说明该被拒配方无副作用，final_result=LOCAL_OBLIGATION_RECOVERED，observation_confidence=CONFIRMED_FAILURE。这些是 Owner 的判定与策略字段，不是实际重试次数的证明。
  - 时间边界：此时间仅表示记录最后更新时间；同一行的其他字段是冻结快照值，不自动证明它们在该时刻已经成立。恢复完成须读取相应更新或结束记录。
  - 引用：`4c4cdf32-d4b0-5d99-b3f8-374e25abe288`/budget_decision, `4c4cdf32-d4b0-5d99-b3f8-374e25abe288`/final_result, `4c4cdf32-d4b0-5d99-b3f8-374e25abe288`/observation_confidence, `4c4cdf32-d4b0-5d99-b3f8-374e25abe288`/updated_at
- 2026-10-05T17:00:55.824054+00:00 / EXECUTION：执行效果 Owner 记录一次 file.read，semantic_input.path=services.html、condition=SETTLED。这里只证明该效果行记录的工具、参数及状态，不据此断言文件内容、验证通过或后续恢复配方。
  - 时间边界：此时间仅表示记录创建时间；同一行的其他字段是冻结快照值，不自动证明它们在该时刻已经成立。恢复完成须读取相应更新或结束记录。
  - 引用：`1c3a6189-0a54-568a-8a97-c22279f38521`
- 2026-10-05T17:01:33.482220+00:00 / FAILURE：执行步骤 b4d11a60（kind=INFERENCE，condition=FAILED）的 result_payload 为 error_type=InferenceAdapterDecisionRejected、failure_code=INVALID_MODEL_RESPONSE、reason_code=NATIVE_DECISION_SCHEMA_REJECTED、validation_issues=[{location: [], type: json_invalid}]。被拒模型响应的具体内容未在该载荷中给出。
  - 时间边界：此时间仅表示记录的结束时间；同一行的其他字段是冻结快照值，不自动证明它们在该时刻已经成立。恢复完成须读取相应更新或结束记录。
  - 引用：`6fc93cee-5308-5608-907d-d9b0ed5890db`/kind, `6fc93cee-5308-5608-907d-d9b0ed5890db`/result_payload, `6fc93cee-5308-5608-907d-d9b0ed5890db`/finished_at
- 2026-10-05T17:02:01.871500+00:00 / RECOVERY_REFINEMENT：推理失败对应的 Recovery 投影记录 expected_reality.outcome=VALID_GOVERNED_DECISION、final_result=LOCAL_OBLIGATION_RECOVERED。期望与结果字段不证明实际执行了何种修复或重试了几次；投影不是新增事件。
  - 时间边界：此时间仅表示记录最后更新时间；同一行的其他字段是冻结快照值，不自动证明它们在该时刻已经成立。恢复完成须读取相应更新或结束记录。
  - 引用：`d7e7df09-3bbe-5d72-a9b7-6c8169cc5881`/expected_reality, `d7e7df09-3bbe-5d72-a9b7-6c8169cc5881`/final_result, `d7e7df09-3bbe-5d72-a9b7-6c8169cc5881`/updated_at
- 2026-10-05T17:34:47.061884+00:00 / FINAL_STATE：验收 Owner 记录 Human 的 ACCEPT 决定，并绑定 manifest_id=a783ea78-c02d-52c6-a094-8e7f9018f9e1。Human 的决定不替代本报告对每项验证或 HTTP 响应的独立核对。
  - 时间边界：此时间仅表示记录创建时间；同一行的其他字段是冻结快照值，不自动证明它们在该时刻已经成立。恢复完成须读取相应更新或结束记录。
  - 引用：`e00219b7-497d-5912-b021-1053d01a830b`/payload, `e00219b7-497d-5912-b021-1053d01a830b`/created_at
- 未赋予具体时间 / VERIFICATION：交付审计记录未含可观察的交付动作：actions 为空数组，client_received 与 client_saved 均为 UNAVAILABLE，completion_basis 为 'ASGI_SEND_COMPLETED proves server send only'，historical_action_identity=NOT_RECORDED。因此本次观察未取得客户端送达或历史点击证据，也未据此否定此前的服务端发送。
  - 引用：`479142b6-7991-5409-9882-0c5979c82020`/actions, `479142b6-7991-5409-9882-0c5979c82020`/client_received, `479142b6-7991-5409-9882-0c5979c82020`/client_saved, `479142b6-7991-5409-9882-0c5979c82020`/completion_basis, `479142b6-7991-5409-9882-0c5979c82020`/historical_action_identity
- 未赋予具体时间 / FINAL_STATE：work-output-1 相对基线 d4ad65db95fa1bb3ad7ec951ea844fd4939c2a3d 的最终净差异只包含两个新增文件 news.html 与 services.html，index.html 不在 changed_paths 中。这是两个提交之间的净变化观察，不证明中间过程没有其他写入或外部副作用，也不建立各状态的转换时刻。
  - 引用：`1d01703c-5302-5e8e-ba51-180e75015661`/changed_paths, `1d01703c-5302-5e8e-ba51-180e75015661`/baseline

## F1-process-run-allowlist-rejection

分类：UNKNOWN；认知状态：UNKNOWN

### OBSERVED FACT

Work 3ee622b5 执行期间的一次 process.run 效果 condition=FAILED：semantic_input 为 {argv: [ls, -la], cwd: .}，对应 receipt 的 output 为 {effect_observed: false, error_type: 'ValueError', message: 'process executable is not allowlisted: ls'}，同一效果的 execution_evidence 记录 evidence_type=TOOL_REJECTION。即该命令被宿主拒绝，未观察到任何执行效果。

### ANALYSIS

已验证的源码对照：本次捕获的当前 runtime 实现包含可执行文件允许列表检查，在不允许的可执行文件进入子进程前拒绝；runtime_ports 的相应分支把这一拒绝消息归入可自主修复的无效果配方拒绝。历史回执的 ValueError 消息与这个分支相符。若历史 Worker 使用同构实现，这能解释观察，但历史加载版本和选择该参数的原始决策未核对，无法确认实际走了哪条实现路径，也无法把模型方差与平台缺陷作排他分类。Owner 的诊断标签及最终 ACCEPT 都不能补足上述因果证据，故分类与历史根因保持 UNKNOWN。

### UNKNOWN / 边界

历史 Worker 的实际加载源码、选择 ls -la 的决策依据、真实替代动作与实际重试次数均未核对。effect_observed=false 是这条回执的记录，不证明整次 Work 没有其他副作用。另两条 Self-Refine 未作根因分析。PREVIEW_HTTP 检查提供的是定位和存在状态，本报告未逐条核对其响应内容，不把它写成客户端下载或保存证据。

### 建议与回归

若后续再次遇到同类拒绝，先核对该次实际授予的权限、工具能力和回执，再在同一契约内选择确能满足需要的合法方案。不能仅凭工具名称认定它可列目录，也不扩大允许列表、增加重试上限或重放效果不确定的操作；证据或权限不足时受治理地终止。历史记录本身不构成重开该 Work 的授权。

在允许列表限制下提交不获准的可执行文件，检查拒绝回执与显式效果关联；存在合法且足够的授权方案时，在原预算内恢复，否则有界终止。加入拒绝但未运行、效果不确定、历史实现无法定位等变体，不能据最终成功或分类标签排除其他原因。

保留权限、预算、原始记录和验证门禁；检查有证据的恢复或真实终止，不以零偏差、更多权限或无限重试作为通过条件。

事实引用：`1a0c3cf3-4db9-5a68-8bc0-6bf201de1787`/condition, `1a0c3cf3-4db9-5a68-8bc0-6bf201de1787`/output, `7c97f43c-007e-57be-8740-97763f6b50b8`/semantic_input, `50be8eb9-0f8e-5283-9fbf-ed5e4c3395e2`/evidence_type
源码引用：`85341df8-a381-5be7-9dc8-54610c1ec7a2`/content, `7dca429a-664e-50f6-9ba9-3f3aa23303ae`/content

## 即时处置建议

- 若后续再次遇到同类拒绝，先核对该次实际授予的权限、工具能力和回执，再在同一契约内选择确能满足需要的合法方案。不能仅凭工具名称认定它可列目录，也不扩大允许列表、增加重试上限或重放效果不确定的操作；证据或权限不足时受治理地终止。历史记录本身不构成重开该 Work 的授权。

## Self-Refine 建议

- 已有 Owner 诊断与回执可支撑有界恢复的候选建议，但未读实际修复配方，不能宣称具体工具替代已经执行或一定足够。后续仅在原契约和预算内核对合法替代方案；不足则终止。

## 平台演进建议

未提出条目。空列表不代表历史证据完整或平台没有问题。

## 本阶段未覆盖

- 本次仅详细分析一起异常：semantic/scope 的 SCOPE_INFLATION 诊断（self_refine_events/0）与 native-executor/inference-decision 的 NATIVE_DECISION_SCHEMA_REJECTED（self_refine_events/2）只作背景记录；被提议步骤 c875e823 的请求载荷、被拒推理步骤的原始响应内容以及冻结导出中的 PREVIEW_HTTP 原始记录均未读取，保持 UNKNOWN，需在后续阶段或由 Human 决定是否继续。

## 证据面核对

- 对冻结导出中 group=self_refine_events 的 /* 字段检查返回 PRESENT：扫描 3 条记录、79 个匹配，其中 79 可用、3 脱敏、5 空值、0 未导出。三起 self-refine 事件因此有可读的原始诊断字段；脱敏字段内容不可见，且该检查不证明其他 group、其他 Owner 或平台历史。
- 冻结导出中 family=PREVIEW_HTTP 匹配 6 项、扫描 4 条记录，字段状态为可用 6、脱敏 0、空值 0、未导出 0。本次调查只取得该检查返回的定位示例，未逐条读取这些预览原始记录，故预览请求的状态、摘要与响应体在本次观察中保持 UNKNOWN；该结果也不证明其他 Owner 或完整响应体不存在。
- 冻结导出中 family=DELIVERY_TRANSFER 匹配 1 项、扫描 1 条记录，字段可用 1。读取该唯一记录（479142b6-7991-5409-9882-0c5979c82020）显示 actions 为空、client_received/client_saved 均为 UNAVAILABLE、completion_basis='ASGI_SEND_COMPLETED proves server send only'、historical_action_identity=NOT_RECORDED，因此没有客户端送达或历史点击的观察；这不证明或否定预览 GET 状态与浏览器渲染。
- 冻结导出中 family=EXECUTION_RELATIONSHIP 匹配 356 项、扫描 469 条记录（356 可用、218 空值、0 未导出、0 脱敏）。本次调查只沿主体 1a0c3cf3 与 6fc93cee 的显式引用读取了少量关联记录，未枚举全部匹配项，因此不能声称覆盖全部执行关联。

## 受检范围内缺失证据

未提出条目。空列表不代表历史证据完整或平台没有问题。
