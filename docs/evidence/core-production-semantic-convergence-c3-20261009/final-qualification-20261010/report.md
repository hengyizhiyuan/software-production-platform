# C3 — Final Frozen G0 & Independent Holdout Qualification

**C3 PARTIAL — Exact Engineering Blocker。未达到 C3 CLOSED。**

本次执行 Human 明确批准的一次真实 G0，以及独立 Reviewer 解封后的 Holdout。两个资格均已执行并保存终态；失败并非等待授权。未根据 Holdout 修改实现、改变预期、追加模型尝试或重跑业务 Work。原有 C3 修复和历史证据全部保留。

## 1. 确切身份与证据边界

| 项目 | 实际身份 |
|---|---|
| 原任务分支 | `codex/c3-open-semantic-obligation-convergence` |
| 本轮证据父提交 | `3c89d91f38a60a69d6a91b5d916729d8722422d0` |
| 冻结 Watt source | `34e9ca9cc5cd5623a9463b42ba4c26ede061640f` |
| Git Tree | `00f053019cf3c1ba0cd43fa1b1fca023ef638a71` |
| 实际应用 Image ID | `sha256:697b80141e1a11a70111166a1bb66db674457f8461ce9bea5fa21affebdbcbec` |
| Guardian | `76c1e87a1b29d151f4ed949748e3298f2169c5b1` |
| ECF | `5aa4f8833c359c15bd059eda5972aa3915bcc18c` |
| 新 G0 DB / Migration | `spg_c3_finalg0_qualification_20261010` / `20261007_72` |

API、Coordinator、Worker、Tool Host 均由实际 Docker inspect 保存 Image ID；容器内安装模块导入身份另有收据。未向旧镜像覆盖应用文件。独立 Holdout 使用相同确切镜像与实际导入检查，数据库为新隔离实例。

E1 指本次实际 Owner 持久记录、Provider 元数据、Docker 事实及只读数据库快照；确定性重放只证明原 Candidate 对当前冻结契约的判定。受控 Owner 探针与独立审查分别标明范围，不替代真实生产效果。历史无法恢复细节仍 UNKNOWN。本轮应用源码修改为零。

## 2. 一次真实正常入口 G0

- Product：`49074219-d220-4f2c-9294-1bacb638fff1`。
- Work：`c703f518-52a2-5531-90d1-e751b809fe68`。
- Work Reality：`4d674f62-99c6-5fed-ba6e-45f90ca2f9a2`。
- Interaction / Turn：`2a6caa70-dedf-48e4-a31e-1a34b32a4c2a` / `7bfc0169-d032-4082-be1a-2f6958d330e2`。
- 原获授权 G0 输入未改变，SHA256：`a47cd835924ba5082397fd8d1e3fb0ab2805f6336f365f9af6db27272e4cced9`；引用已版本化的 `../original-g0-input.json`，本轮不公开新增完整 Prompt。

通过普通 Product 创建及 Experience turn API 发起，没有预植 Fact、Constraint、模型输出或 Human Decision。新 IR/Work 自行形成 **20 项来源**，库存 fingerprint `08e8423786f0cc864fa6d9f846be66a8ac0f015dcc95b49bb0c2448bd9cd408f`。这是新正常入口库存，不能用此前固定 26 项库存的通过结果替代。

实际 Worker 进程 UID/GID `10001/10001`，同进程挂载根目录的非业务写入探针成功并删除；这是工作根目录 readiness，不是本 Work 的 Task Workspace 或生产执行资格。Native Provider readiness 配置存在，不代表已发起 Native 请求。

G0 隔离 profile 的 WIC/Formation/Reviewer 使用现有共享 `none` override；Native Worker 保持原 `high`。Holdout WIC 保持原 `low`、Formation/Reviewer 使用已校准 `none`。均未改生产配置、模型、16384 输出上限、120 秒及既有传输恢复约束。两条资格不同 WIC 配置的适用边界不混淆。

### 实际停止与反馈

| Formation | Route 数 | 实际结果 |
|---|---:|---|
| 1 | 29 | 完整 JSON，确定性拒绝；首要谓词 `OBLIGATION_PROJECTION_CONFLICTING_DISPOSITION`，11 条完整失败集合 |
| 2，使用唯一既有反馈 | 29 | 完整 JSON，确定性拒绝；首要谓词 `OBLIGATION_CURRENT_CLAUSE_CANNOT_BE_CONTEXT_ONLY`，9 条完整失败集合 |
| 独立 Semantic Review | 0 次 | 未通过确定性前置条件，合法未调用 |

第二次九条失败为：2 条当前 Clause 被仅保留背景；2 条未来 Candidate Seal 的来源证明不足；5 条支持来源对应不足（禁止 Deploy、禁止 Publish、三条 Git Diff Scope）。原 Candidate 原样只读重放，未删减或修补：详见 [完整谓词及组件身份](g0/receipts/original-candidate-readonly-review.json)。反馈绑定原 Wire fingerprint、库存、Work Reality、Attempt 及请求/响应收据；两个原候选 fingerprint 分别为 `f17a646936472ce82db3f4d4b83ac14f474034644a0495197ac5acddfb826579`、`17f7d497b13b792d85ea7192e2255ea825166800ea6c51d944fbf2bef8383e3f`。

最终验证收据 `27e2d8d8-d095-40c0-88a3-b4cb188c815e`，governance row `b1c466c7-63c0-47e6-84d1-73899c13c8b0`。不是 Provider 容量或传输终态失败：本次两响应完整、实际 reasoning Token 为零、未出现容量耗尽。已证实边界是 **合法来源的语义处置与 Owner/Gate 前提未在有界反馈内收敛**；来源类型、Clause 背景资格与模型解释谁承担每个底层问题，尚不能仅由错误码完全定因。不能将所有 CURRENT 描述机械升级为执行义务，也不能按字段特例豁免这些失败。

范围 Self-Refine event `f8c447ff-5368-4379-a335-a76517cddc51` 局部恢复并返回 DESIGN；随后 event `07e64eec-325f-4828-b986-5f2d31aa69d4` 因 Formation 合同不匹配终止，未恢复。局部 `LOCAL_OBLIGATION_RECOVERED` 不证明完整 Work 成功。

[最终只读快照及状态](g0/receipts/real-g0-terminal-review.json)：业务 PWU、Attempt、Native Binding、Queue、Worker execution、Git 生产 Artifact、Verification、软件 Candidate Seal、适用 Work Guardian 均 **未到达**。数据库这些对应记录为零。源仓库 README bootstrap 不属于 Worker 产物或 Human 已接受 V1。

API interaction `COMPLETED` 指入口 turn 完成；`work_complete=false`、`automatic_progression_state=STOPPED`、`human_attention_required=false`。Work projection 与存储 condition 均 `READY`；Work Admission 不等于 Runtime 就绪。驱动器 `BOUNDED_OBSERVATION_WINDOW_ENDED` / exit 0 表示观察结束，不能算 Work PASS，也不单凭 READY 推断状态不一致 Bug。

## 3. 独立封存 Holdout

原封存 SHA256 `770828adeabec942548218c17bc6e9dbb9222ce19df19bc89c260f28ed8f4cf0` 核验一致，**24 案、8 类全部对账**。Reviewer 直接保有私有输入、预期、候选与收据；实现者仅收到脱敏判定，没有读取私有 oracle 或以其调优。

| 结果 | 数量 | 证明范围 |
|---|---:|---|
| FAIL | 8 | H01/H02 模型 Formation 与独立模型 Review 均通过，但独立封存比较发现禁止效果的主组件错误/额外映射 Git Diff Scope；另六个合法语义案未收敛 |
| PARTIAL_NOT_AT_REQUIRED_GATE | 1 | H08 保留原要求，未创造效果或权限，但停在 Formation；没有到达要求资格的权限 Gate |
| PASS_SCOPED_CONTROLLED_OWNER | 14 | 现有冻结 Owner 受控正/负向消费；不是开放模型泛化 PASS |
| NOT_REACHED | 1 | H19 缺少真实软件 Candidate Seal；不以 fixture 补造 |

另在新隔离 PostgreSQL 中执行 Watt/Guardian 联合契约 **20 PASS**：缺失权威 Owner 记录、虚构未来授权、禁止效果等现有消费者拒绝。不是本 G0 的业务 Guardian Assurance。详见 [独立 Reviewer 报告](../holdout-final-qualification-20261010/report.md) 与 [逐案收据](../holdout-final-qualification-20261010/qualification-review.json)。

H01/H02 是真实语义 Review false positive，不是 Guardian 自行放行生产。它表明此前一次 35-route 通过和受控语义负例尚不足以证明独立 Review 对开放输入的可靠性。不能让 broader supporting provenance 向主组件移植不属于其自身的权限/Scope 含义。

Holdout 已对独立 Reviewer 解封并观察。今后不得再次称其为未见 Holdout；仅可明确作为已曝光回归，或使用新的独立封存集合。

## 4. 实际消耗、历史保护及恢复

| 项目 | 实际 Provider 用量 |
|---|---|
| G0 Formation 2 次 | input `58253` / output `4164` / reasoning `0` / total `62417` / cached `21376` |
| G0 可独立计数的局部 DESIGN 修复 | input `11317` / output `1883` / reasoning `0` / total `13200` |
| Holdout 33 逻辑调用 | input `629553` / output `159718` / reasoning `61467` / total `789271` / cached `167680` |

G0 唯一可观测用量下界 `75617` Token，WIC/base DESIGN 全量账单 UNKNOWN。相同 Formation 用量同时出现在 Self-Refine 元数据中，只计一次。Holdout 共 14 WIC 请求、16 Formation 候选请求、3 Review；适配器将后两者同记于 Formation Owner。reasoning 是 Provider output 的组成，cached 是 input 子集，不额外相加。独立 HTTP 发送总数、可见 JSON Token、费用 UNKNOWN。

G0 单次驱动观察 `09:35:03.626832Z`—`09:45:21.808980Z`；Formation 已于 `09:35:47` 停止，没有重复创建 Work。Holdout 容器实际墙钟约 `577.379s`，Provider 方法累计 `561.634s`；联合测试 `233.363s` 与其重叠，不相加成总体耗时。

准备阶段机械控制错误（IPAM 空值、控制脚本未定义 REV、只读分析容器权限/输出路径）均保留失败收据；没有在这些失败上产生新的业务模型或 Work。修正限于新控制脚本/新输出目录，未改应用 Gate 或历史权限。Reviewer 的机械 harness 失败亦保留；禁止效果分支证明不扩大为真实执行后幂等性审计。

所有新资格容器停止，卷、网络、失败记录保留。此前 19 个运行容器仍运行；ECS source HEAD `5de657f3cb65780adf50f6557b54171a6c3cfae5`、main ref `ee5bd86a53891f9391785c91d0ccef81ad2d56c3` 与历史 basis hash 不变。未修改生产服务、原失败 Work、Candidate、Human Decision、Quality Ledger；没有创建 Integration、Acceptance 或 Delivery 授权。没有以普通日志缺失声称全审计覆盖。

跨电脑恢复：

- 公共报告、指纹和脱敏收据：原 C3 Git 分支的本报告及两个资格目录；包含提交即为精确证据版本，最终远端 full HEAD 另保存于 ECS 交付 checkpoint。
- 新 G0 原始 Owner 导出及配置：`/data/watt/c3-semantic-convergence-20261009/final-g0-qualification-20261010`。
- 新 G0 冷备、PG dump、workspace archive：`/data/watt/c3-semantic-convergence-20261009/final-g0-recovery-20261010`；文件 SHA 和 pg_restore 列表验证见 [恢复收据](g0/receipts/private-recovery-checkpoint.json)。没有执行恢复演练；没有异地备份。
- Holdout 原 seal、私有输入、模型/反馈/Review 收据与新数据库卷：`/data/watt/c3-semantic-convergence-20261009/holdout-final-qualification-20261010`。
- 确切 image archive：`/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/review-primary-qualified-20261010/image-recovery/exact-image.tar.gz`，SHA256 `286053124619831b03f243c02f79b35df6408035fe86e234c752a40df465a377`。
- 本次汇总公共交付：`/data/watt/c3-semantic-convergence-20261009/final-closure-review-20261010`。

私有归档含运行凭据，只留受保护 ECS 目录，不提交 Git。Git 公共字节与 manifest 校验，不输出密钥、完整私有 Prompt、原 Provider 内容或隐藏推理。

## 5. Closure 判定与下一项必要工作

之前已资格的 frozen-image 398 项定向回归、46 项 PostgreSQL/Guardian 检查及固定库存专项结果作为原范围历史证据保留，本轮未重复执行，也不扩张为新 G0/Holdout 合格。当前资格缺口已从“未执行”变成“已执行但不通过”。

需要在现有 Formation/Review Owner 内先依据普通 G0 来源和完整失败集合检查共同语义处置、来源对应及 Gate 前提；同时把独立模型 Review 对主组件与支持引文语义边界的错误放行作为未关闭工程 Finding。底层原因明确后才能提出针对性修复；不得用 Holdout oracle 调优、增 Alias、降低门禁或以无根因重试取得通过。

正常用户生产到 Worker/Git/Verification/软件 Candidate/适用 Guardian 的正向资格，以及真正独立的泛化资格，仍未取得。Human Integration/Acceptance/Delivery 尚未发生。**不提交 C3 Closure，不自动启动 G0 重试、C4、N1、N3。**
