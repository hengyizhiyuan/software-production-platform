# Formation Decision Revision Action Consistency Calibration

2026-10-14。原 C3 分支。**结构化处置—动作一致性校准完成；本次真实探针观察到实际 Consumer 改变，但整体候选仍失败，未获得 Independent Review，C3 保持 PARTIAL。**

## 1. 代码与最小边界

源码：`a1d99fd8e60967e7601fe1e265fa9ef6c66ecc0e`；Tree：`5aeaf6236c67e8f7ac7a510a720b1f82301c2c81`。仅修改两个既有运行模块及对应测试，依据[行为归责](../c3-semantic-revision-behavior-attribution-20261014/analysis.md)。

- [`fulfillment_candidate.py`](../../../src/spg/providers/fulfillment_candidate.py)：在原 Decision Revision 契约内协商 `formation-decision-revision-actions-v1`；提供处置指导，在既有局部候选构造过程中记录并核对结构化声明与显式操作。
- [`governed_obligations.py`](../../../src/spg/application/governed_obligations.py)：沿既有请求/响应及反馈绑定持久化契约 marker；恢复沿首次协商结果，旧收据不自动升级。Owner 仍唯一构造 repair state。
- 未改 `validate_projection_candidate`、Independent Review、Guardian、最终接纳条件、候选次数、Token、超时或传输策略；没有新 Agent、模块、Validator 服务、静态 Consumer 选择或普通34规则。

### 必要的局部封套扩展

旧封套只有实际动作，没有独立的结构化处置声明。既不能解析自然语言，又要比较声明与动作，就必须有单独的结构化输入。因此**仅在已协商且存在重评目标的局部编辑响应中**，增加 `decision_revisions` 数组，每项包含：

`original_route` / `disposition` / `revised_fields` / `justification`。

它是未接纳的模型 Claim，不是新 Engineering Fact。现有 `basis` 及 Owner 派生目标将它绑定到原 Wire、库存、attempt、收据、原 route/component/source。模型无需重复生成这些身份。原 replace/remove/append、canonical Wire v1 与最终候选 Schema 均不变；**受影响的请求局部编辑 Schema 确有扩展**，没有把它描述成全部 Schema 未变。

## 2. 一致性语义及证据

| 模型声明 | 既有 Owner 构造时核对 | 不代表什么 |
| --- | --- | --- |
| retain | 原 Consumer 保留；必须有非空方法理由；其他必要操作数修复仍允许 | 不证明保留的 Consumer 在语义上正确 |
| revise | 原 route 有显式 replace；声明的每个非 rationale 决策字段实际改变 | 不证明新 Consumer/方法满足原要求 |
| remove | 原 route 有显式 remove，不能同时 replace，不能原样重插相同结构化选择 | 不豁免原来源/组件完整覆盖 |
| unresolved | 原 route 显式 replace 为既有 UNRESOLVED；不能声称已解决 | 不允许将未决计划接纳为履约完成 |

每个被请求的原决策都须恰有一项声明。错误目标、缺失/重复声明、未改所声明字段、处置与动作不符等，进入既有构造失败/诊断通路：`OBLIGATION_FORMATION_DECISION_ACTION_INCONSISTENT`。没有增设最终语义验证器。

证据保留在原 `MODEL_RESPONSE_OBSERVED.wire_presentation.candidate_construction` 中：契约、parent binding fingerprint、声明 fingerprint、原 route fingerprint、声明字段、实际改变字段、实际操作及理由 SHA。失败时同一诊断集合记录不一致原因，后续语义/Review/实际 Evidence 标为未能评估。结构一致时只记录 `STRUCTURALLY_CONSISTENT; SEMANTIC_VALIDITY_UNKNOWN`。

**不会读取理由中“removed”等词决定操作。** 若结构化声明是 retain，而文字声称已删除，本校准不会把文字转成 remove，也不据此断定语义正确；现有 Independent Review 保留其职责。检测能力限于显式结构化声明—动作关系，不能宣称已经检测任意自然语言矛盾。

## 3. 真实调用前的验证

最终镜像上的[定向回归](receipts/installed/focused.xml)：**156 PASS、0 FAIL/ERROR/SKIP**，包含[本次24项契约测试](../../../tests/test_c3_decision_revision_contract.py)及关联旧回归；156中已包含24，不重复累加。

直接证明：

- 声明 remove 却同 Consumer replace，在现有构造路径被拒绝，不调用 Review。
- 合法 retain（包括文件路径值的 EQUALITY）和合法 remove 可继续原有验证/Review；没有强制 Consumer 必须改变。
- revise 必须实际改变其声明字段；仅改理由、字段未变均不能冒称修订。合法的组件表达改变仍允许。
- UNRESOLVED 保留且不被接纳；remove 后原样 append 重插被拒绝；缺少声明不能从实际动作反推补造。
- 自然语言不作命令；结构一致不能覆盖独立 Review 否定；原 Wire、action marker、响应及派生身份漂移不能重开模型额度。
- 旧协议收据在 Runtime 新能力启用后仍不升级。

真实隔离 PostgreSQL [10 PASS](receipts/installed/postgres-final.xml)：原协议及当前 action 契约均覆盖。已持久化第二响应后关闭 Provider 能力开关，再恢复，仅执行剩余合法 Review；终态重放不重新生成。测试使用全新内部 PG、原 sandbox 数据库名及独立凭据，已停止资格 PG，未访问业务数据库。

[禁网预检](receipts/ordinary34/preflight-result.json)确认新指导、处置输出 Schema、两个 Owner 目标及全部原覆盖/来源反馈进入第二请求。没有以测试或预检声称真实模型成功。

## 4. 精确运行身份

实际镜像：`sha256:58c07b462a438aa936ba59857624559e77230258d24bd960512706a90d121803`。

离线完整源码重装构建，非旧镜像文件覆盖。[构建结果](receipts/image-build.json)、[Git/归档身份](receipts/source-manifest.json)、[实际安装包核对](receipts/installed/attestation.json)保留完整输入和逐文件身份。镜像无 registry RepoDigest，未编造远端 digest。

继承并核对 Guardian `0d7aca954588c8ad3883dbedb730e59dc1d7b867`、ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c`，独立 Owner 未修改。对照应用源码 `6afd558e...` 的实际镜像为 `sha256:e2883e109e5697fff5d932b9d606f6ffb333bc16c99c7fabf7ef2edbf22690e1`；新资格不引用旧镜像 PASS 代替。

## 5. 唯一一次 ordinary34 受控资格

不是新 G0/Work，也不是重新生产已有软件结果。使用原19项库存 `b023bae819f456da05abe983f48da4f2157da60df412de909f9f834991bcef29`，原首 Wire `893f167cab558759ab2eb2a2a3664e2d57650e71a0077b2fcf6e5553928ebc4e` 为明确标记的受控首响应，再由当前 Owner 形成反馈，执行**一次真实第二 Formation**；只有现有门禁允许才可 Review。

[实际结果](receipts/ordinary34/retained-first-result.json)、[动作及失败观察](receipts/ordinary34/action-observations.json)、[实际容器](receipts/ordinary34/retained-first-container.json)。真实 request `bf74aa3e-13f7-4889-89dd-39c64441ee1f`，响应 SHA `48d9d575159a5db2a99f92e97c73d79916d7e709a5c7ef16ed2b272a43127428`。

| 原 route | 模型显式处置 | 声明修订字段 | 实际编辑 | Consumer 变化 |
| --- | --- | --- | --- | --- |
| 1 | revise | capability | replace；capability及rationale改变 | GIT_DIFF_SCOPE → ARTIFACT_CONTENT |
| 3 | revise | capability | replace；capability及rationale改变 | GIT_DIFF_SCOPE → ARTIFACT_CONTENT |

本次声明与结构动作一致，Owner 没有替模型选择 Consumer。相比[前次仅改理由的控制](../c3-formation-decision-revision-stabilization-20261014/receipts/ordinary34/candidate-observations.json)，**观察到了实际映射变化，而不只是检测能力增加**。但不同输入各一次，不能证明契约变更的独立因果效果或稳定泛化能力。

### 原门禁保留的真实失败

- 原内容路线仍在，新增改成内容的路线与它们重复：source0/route1、source1/route3 为 `OBLIGATION_PROJECTION_DUPLICATE_ROUTE`。改成另一个 Consumer 不等于形成合法完整方案。
- source3、4、10、11 的字符覆盖缺口未修复，最终仍 `OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST`。
- Owner 前提另记录 source3/route5 的 `OBLIGATION_LINKED_FACT_CURRENT_PROOF_UNAVAILABLE`。
- Independent Review **0次**，没有新的语义接纳、Assurance 或 Human 授权。此前 supporting-source 错误没有在本次诊断中重现，不代表全部来源语义已获证明。

原两候选槽位和一次反馈没有增加；首响应是受控历史输出，不能计为本轮 Provider 成功。结束后终态重放没有追加调用，没有第三候选、第二次资格或失败后的补丁调参。

## 6. 结论、限制与恢复

**本轮专项完成：显式处置—动作矛盾可被结构检测；合法保留、修订、移除和未决不被静态 Consumer 规则取代；本次真实模型确实改变了 Consumer。整体 ordinary34 仍不合格，不能关闭 C3。**

剩余是完整候选的去重、覆盖和必要证明协同问题，不是本次检查错误地阻止了相符动作。本轮没有据此扩大修复、放宽门禁或追加模型调用。

实际1次 Formation、0次 Review、0传输重发；Provider completed。模型 deepseek-flash、reasoning none、上限16,384、timeout120s保持。input **89,606** / output **4,303** / reasoning **0** / total **93,909 tokens**，cached1,152为输入子集；实际模型约**17.792s**、资格全程约18.988s。构建35.090s；最终关联回归容器57.159s、PG回归29.449s。货币/CPU/能耗成本 UNKNOWN。物理收据最大66,257 bytes，原131,072-byte上限未变。

生产、canonical main、原始 Work/Candidate/Evidence、Human Decisions、Quality Ledger和Holdout不变。输入文件及原历史收据前后SHA核对在结果中。私有请求/响应与 Owner 收据保留：

`/data/watt/ai-native-evolution-20261013/decision-action-consistency-20261014/private/qualification/retained-first/`

同根 `private/qualification/preflight/` 为禁网接线控制，`image/`、`evidence/` 为构建和验证证据。[安全恢复清单](receipts/private-evidence-manifest.json)记录私有文件身份。公开工具、代码、脱敏收据与本报告持久化到原 C3 分支；未把私有完整 Prompt、响应或凭据推入公开证据。
