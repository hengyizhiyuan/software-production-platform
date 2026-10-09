# Phase C3 — Open Semantic Obligation & Evidence Convergence

## 结论

**C3 PARTIAL — Exact Engineering Blocker**

记录时间：2026-10-09T13:40:11.098026+00:00。这是新 qualification report，保留 C1/C2/N1 历史事实。

已完成有界开放式义务形成、按 Owner/阶段取证、候选/反馈连续性，以及真实 G0 暴露的来源、失败诊断和未决停止修正。受控回归证明其明确范围；本次 C3 **没有真实 G0 的 Worker → Candidate → Verification → Guardian 完整成功，也没有独立 Holdout 资格**。

最终代码和真实失败运行分开记录。没有 Human Integration、Acceptance、Delivery 授权；没有可申请授权的新 Candidate。N1/C4 均未关闭。

## A. 实际根因与最小实现

C2 base f2dda0549efe35e7855f26f73a5770ac4159f97a；最后实测应用 88f1d9805d3ed1aa779ed3c78902b193fae240f8。独立 Watt/Guardian 分支均为 codex/c3-open-semantic-obligation-convergence。Program ADR-0002 引用版本1e2c1fdf37d9252c0a9bd480fc2ff15c88d0fee1。ECF 未修改。

1. 旧构造主要消费 typed CONSTRAINT/requested_effects。真实 WIC/IRK 保存的 Intent、Clause、Exclusion、NEGATED 和 Work Constraints 未形成完整库存；缺少 typed item 不能表示没有义务。
2. Protected Context 将治理要求统一索取 implementation-source witness，混淆内容、Git、Source、Permit、Seal 与未来 Human Gate。
3. 原失败收据不足以定位来源、检查、反馈、请求和预算；复用 Work Governance、Model Runtime 和 Native Execution Evidence 修正。
4. 第一条真实 G0 暴露 CURRENT REFERENCE 错作 retained context，以及错误要求每个 Clause 引文与同一 Item 引文重叠。正式 IRK 契约分别验证原始记录跨度；修正没有删除原始 Facts、Scope、值、来源或权限。
5. 第二条真实 G0 的 formation Provider 失败，原代码只保留异常类名。上游全库存 UNRESOLVED 仍创建 Runtime/PWU/Attempt/Dispatch，直到正确的 Native 门禁拒绝，又被 Orchestrator 错分为 infrastructure failure。
6. 最终修订仅保存 typed safe Provider failure 字段，并在 Runtime 前通过现有 Steering/Work Governance 明确 BLOCKED，避免错误晋升及不适用的执行恢复分类。

库存包括 FACT、IR_CONSTRAINT、IR_CLAUSE、WORK_CONSTRAINT、IR_ITEM、WORK_CONTEXT。允许模型提出带原始来源的履行候选；确定性检查原始身份、跨度、版本、Scope、Authority、Capability 和完整覆盖，并独立审查候选语义。不是每句话都强制建 Fact，也不是每项 Fact 都成为当前执行义务。合法但不能映射的要求显式 UNRESOLVED，不丢弃。

没有增加 Subject/Scope Alias、业务关键词路由、原 G0 文件名/Case ID 特例、schema、全局 Refine/Trace/治理 Owner。

详见 [来源契约审查](source-contract-repair-review.md)、[Provider 诊断](provider-failure-diagnostic-review.md)、[停止接线](fulfillment-stop-admission-review.md)、[真实终止链](retry-1/real-g0-terminal-review.json)。

过去 Provider 的具体 HTTP 原因仍 UNKNOWN；最终诊断不表示 transport 恢复。约59秒不能证明 timeout、quota 或 schema 错误。

## B. Owner / Phase / Evidence

| 贡献类型 | 确定性绑定要求 | 证据及实际门禁 |
| --- | --- | --- |
| 内容、数量、顺序、值 | 原 Fact/Clause/Constraint、Scope、Value、Qualifiers 和受审查检查候选 | 确切 Candidate/Git Blob，内容/行为 Verification |
| 文件与变更范围 | Source、Target、Task/Change Contract | 精确 Git Diff 和版本 |
| Product Source | 对应 Product 当前真实版本及来源，不以 bootstrap/historical ref 推断 Human 接受 | Product/Source Owner 持久记录 |
| 持续禁止副作用 | typed Effect/Capability、Task 权限、restricted Native grant | 当前 Native/Effect Gate 与适用执行记录；日志缺失不是完整审计 |
| Candidate 条件 | 原义务保留在现有 Seal/Completion Gate | Candidate Owner 真实状态；不提前伪造 Seal |
| 未来 Human 授权 | 引用原义务，证明真实后续 Gate 承接 | Human Gate PENDING；不能由模型创造决定 |
| 非执行权威上下文 | source-linked component、独立审查、原权限与 Facts 保护 | CONTEXT_RETAINED，不是 SATISFIED/Assurance |
| 未合法映射或缺证据 | 完整保留原要求与来源，明确 UNRESOLVED | Runtime 前 BLOCKED；Native 独立严格拒绝不变 |

Guardian 的必要兼容扩展在独立权威仓库完成，与 Watt adapter 匹配。它独立解析原 source records、版本、scope、阶段和真实 Owner evidence，不能凭 Watt COVERED 标签通过。旧 v1/Gate/Finding 保留。ECF 仍用原版本，无内部重构。证据见 [实际 C1 Owner records](retry-1/final-image-regression/c1-chain-guardian-owner-records.json) 及原回归。

## C. 候选 / 反馈 / 有界终止

Formation 最多两个候选、一次反馈、每候选一次独立 semantic review，最多四次逻辑 Model Runtime 调用，仍服从既有 purpose/resource/transport 预算。这不是实际 HTTP 次数；缺失的 transport replay/usage 为 UNKNOWN。

原 append-only Work Governance 收据保存 pending、response、候选定位、review、validation、库存、原来源、目标、失败谓词、反馈、请求及 usage。同一依据的 terminal/pending 未知结果不能重开调用，清空临时 plan 不能重置预算。

最终 typed Provider failure 白名单仅含规范化 kind/request_sent/usage_unknown/retryable/provider_status/termination_reason/request_id/occurred_at，不取异常正文、HTTP bodies、headers 或任意上下文。无 numeric usage/HTTP retry count 时为 null/UNKNOWN。Review 失败前的原候选在前序 response 与 fingerprint 中仍可追溯。

WORK_FULFILLMENT_STOP_OBSERVATION 复用 Governance 通道、exact scope fingerprint 和幂等 ID。它不是 Human Decision、实际 Self-Refine attempt、LOCAL_OBLIGATION_RECOVERED 或许可；不触发 Provider retry timer。

实际 Design scope Self-Refine b2cce513-53da-4962-b161-1491e4730bc2 和8259d87d-7d0a-4fd4-b074-ea7bdbc55fc3 均为 VERIFIED / LOCAL_OBLIGATION_RECOVERED / RESUMED；各自后续 Work 未完成，不能折算整条 PASS。可观察两个事件共38148 tokens，不是整个 Work 模型账单。

## D. 回归与成本

| 修订与范围 | 实际结果 | 资格边界 |
| --- | --- | --- |
| 首个 C3 image54355780… | Watt159 / Guardian108 / Carrier2 / C2 PG2 PASS；原 C1 48 PASS、2 FAIL | 原错误 fixture 取了 FACT 而非 IR_CONSTRAINT，保留失败 |
| 相同旧 image、测试文件补充 | 对应2个修正负向节点 PASS | 测试文件覆盖；不改写原 trial |
| 来源/背景消费 development snapshot | 169 PASS | 显式只读 source overlay，无真实 Provider/正常 Work |
| source91f5dbc / image6f8d9b3a… | 397 PASS，0 FAIL/ERROR/SKIP | 安装态 Watt203、Guardian140、全 C1 50、Carrier2、C2 PG2；受控 fixture |
| 最终停止/诊断 development | 15 PASS | network none，无凭据/业务DB/真实 Provider/Work |
| 最终 sourced8ea064 / image51c0b8be… | 216 PASS，0 FAIL/ERROR/SKIP | 安装态相关单元，network none，无 source overlay/Provider/业务 Work/DB |

受控负向包括错误内容、缺证据、错版本、Scope 漂移、Native 扩权、缺失/错误 Guardian evidence、有序约束、相同依据重复调用及未决 stop。正向只证明各 receipt 范围，不是实际模型泛化。

早期 FAIL/ERROR/SKIP、Windows fcntl collection error、错误 fixture 和 HTTP 前 compile failure 均保留，不折算 PASS。未重复全 N1 G0–G6。累计重复执行、真实 build/test wall time、观测 tokens 与 UNKNOWN 成本见 [账本](cumulative-regression-ledger.md)。单项计数不是唯一覆盖或质量等级。

## E. Exact revision 与真实 G0

最终应用：d8ea0642f0c360794e69c366e8f15fa369eeed0b；Tree：390f00dce94089af2de1b750954ddabb42451f44。
Guardian：d01bac1ad153e1eadefafe87d2ea4f5d65896ab6；Tree：4f75d9137bebc7bf956fe4466cbae93f88c5c03b。
ECF：5aa4f8833c359c15bd059eda5972aa3915bcc18c；Tree：878d39d9c259272bb05f2e02bdf9d60c22fad460。
实际新 image：sha256:51c0b8be88969720cb3a3cfc4e047edc7f229aa22348a95a89cbb4bf83a18e39。

[新 build](terminal-fix-qualification/build.json)、[安装态回归](terminal-fix-qualification/watt-terminal-receipt.json) 与实际 imports/container ID 保存 exact source 和 image。没有用旧 image 覆盖 Python 文件伪装新构建。独立比对596文件：2项byte-identical，594项只有Git archive的LF→CRLF导出差异，无其他变更；实际安装源码按build输入SHA核对，不冒称所有原Blob字节完全相同。见 [冻结审查](frozen-terminal-fix-review.json)。

| 真实运行 | Source / Owner / image | Work 与结果 |
| --- | --- | --- |
| 第一条正常入口 G0 | Watt390fa22 / Guardian657ee84 / ECF5aa4f88 / image54355780… | 24d9cc2d-52a8-5d27-b38a-e49c3f73394c；来源构造失败，生产前 BLOCKED，无 Candidate |
| 来源修复后新 G0 | Watt91f5dbc / Guardiand01bac1 / ECF5aa4f88 / image6f8d9b3a… | 048189aa-0613-5307-b6f4-c430e7977f93；ProviderError → 全库存 UNRESOLVED → Native 正确拒绝，未进入 Queue/Worker |
| 最终小修订 | 上述完整 source / image51c0b8be… | 只有受控回归，没有新真实 G0 PASS；未继续随机创建 Work |

第二条 G0：
Product b2f46852-a9cd-4d0f-bcb4-ec2a3b0d7587；
Reality332a3a38-8719-580c-a1a2-c331ae14a5ae；
PWU395f75c3-6bbb-4028-8565-7a227f4adf04；
Attemptf5026ead-1f51-4795-935a-85d4045547d4。

Formation pending receipt2f5111b7-c478-42bb-b670-31d624d61568，
terminal804b22c0-dcff-4a98-a870-0b7bd6905b29；
inventory7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf；
reason OBLIGATION_FORMATION_TRANSPORT_ModelProviderError；
actual Native predicate OBLIGATION_PROJECTION_UNRESOLVED。

Managed Git 仅有 bootstrap README，revision465038ded6cf4ba335a11577de76acb1dea55b76。不是 Worker 新产物，也不是 Human 接受的 Product V1。
当前 Work PE container 未创建，actual image qualification 是 NOT_REACHED；已消失 C2 PE 的历史 identity 仍 UNKNOWN。App role image 不能替代 PE/Attempt 资格。

没有 Verification/Candidate/Guardian。Driver/API 最后观察为 NEEDS_ATTENTION/STOPPED；之后的只读 PostgreSQL snapshot 中原始 product_works.condition 为 READY。这是不同来源/观察边界，不能据前者宣称原始 Work condition 已持久化为 NEEDS_ATTENTION；二者都不是完成，也不是 Candidate-ready Human Integration review。无 scoped identities 的授权查询记 NO_SCOPED_IDENTITIES_NOT_QUERIED，不能以空数组证明完整审计。

取证时间、来源、事件、查询等级和原始 Owner 链见 [只读取证](retry-1/g0-owner-2/export-execution.json)、[终止审查](retry-1/real-g0-terminal-review.json)、同目录 canonical/log。两个失败 Work 未修改、重置、恢复或自动重试。

## F. Independent Holdout

审查者在实现冻结前封存24项/8类；spec SHA256770828adeabec942548218c17bc6e9dbb9222ce19df19bc89c260f28ed8f4cf0。

**NOT EXECUTED — Explicit Human Unseal Authorization Pending。**
自动审批拒绝读取 sealed inputs，理由缺少此次解封的明确 Human 授权。已集中提交请求，未读取、上传或执行 spec，模型调用0。没有绕过审批，没有用 Holdout 调优，也没有把受控表达 fixtures 称为独立真实模型泛化。

## G. 未关闭义务与 C4 依赖

- 真正工程资格：最终修订无正常 G0 到可信 Candidate 成功；历史 Provider HTTP 原因在现存证据中 UNKNOWN；新诊断保留可取得的 typed failure 字段，是否足以定位新失败需据实判定，不能凭 duration 猜测或重复 Work 碰运气。
- Holdout：待明确解封授权后独立按冻结身份验收，不能反向调优。
- 完整链：最终版本的 Worker/Git/Verification/Seal/适用 Guardian、PE/Attempt actual image、真实 Human pending 仍需新合法证据。C2 Worker 证据只保留原范围。
- C4 尚未开始，advanced recovery/successor accepted Source 仅保留依赖；未扩大至 N1 23项 Closure。
- Artifact-only revision fallback 的 drift 风险作为后续审计输入，不冒称这次 G0 原因，不扩张修复。

共享测试模型 key 按 Human 明确授权复用，未输出、修改或轮换；C3 data/control/Gitea 独立。没有制造授权、Runtime Commit 或 Human Acceptance，也不以无日志证明任意效果绝无发生。

ECS 外部 /data/watt/runtime/source 实际 clean branch codex/admin-work-ai-diagnostic-export-ecs、HEAD5de657f3cb65780adf50f6557b54171a6c3cfae5，actor/time UNKNOWN；单独 refs/heads/main 仍 canonical ee5bd86a53891f9391785c91d0ccef81ad2d56c3。C3 没有 checkout/reset/fetch/写该目录或正式服务，不归因外部变化、不擅自复原。

## 持久恢复位置

- 公共代码与证据：Watt/Guardian 同名 C3 远端分支，本报告目录受 Git 版本控制。
- ECS 持久事实及私有原始证据：/data/watt/c3-semantic-convergence-20261009；第二条 Work 在 retry-1；DB/Owner 原始路径见 exact receipt。
- 最终 exact inputs/image：terminal-fix-inputs 和 terminal-fix-qualification。
- 私有检查点：详见 [恢复位置](recovery-position.md)，不将 env/credentials/raw inspect/dump 提交 Git，不宣称异地备份或恢复演练。
- 换电脑可拉取远端 C3 分支后，经获授权 SSH 读取上述 ECS 资料；本地未跟踪目录不是唯一证据来源。

这是 C3 新的有界工程与 qualification 报告。最终仍 **C3 PARTIAL — Exact Engineering Blocker**；不关闭 N1，不授予 Human Acceptance，不启动 C4。
