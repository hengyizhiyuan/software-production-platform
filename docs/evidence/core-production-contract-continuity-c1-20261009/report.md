# Phase C1 — Cross-Owner Contract & Evidence Continuity

**状态：C1 CLOSED — Contract Integration Qualified**
取证日期：2026-10-09（Asia/Shanghai）。本报告是新产生的受控契约集成资格，不替代历史事故收据。

## 1. 结论与边界

C1-F1–F4 在下列确切 Owner 组合上闭合。两条实际 CompletionContract 构造路径均经过 Task/PWU、Native admission/binding、真实 Git 产出、Verification、ECF Protected Context、Candidate sealing 和独立 Guardian 核验。最终 172 项通过，0 failure/error/skip，两个 pytest 进程 exit 0。

这是受控数据库和确定性输出下的契约集成资格。没有运行 live model / Native Worker 的正常软件生产 Work；没有取得新的应用镜像资格；没有执行 Integration、Human Acceptance、部署或发布。**N1 保持 PARTIAL。完成 C1 后停止，不启动 C2/C3/C4。**

权威架构约束：[Program ADR-0002](https://github.com/hengyizhiyuan/software-production-system/blob/1e2c1fdf37d9252c0a9bd480fc2ff15c88d0fee1/docs/04-decisions/ADR-0002-STOCHASTIC-NATIVE-ENGINEERING.md)。Phase B 审计依据为 `f6f078bc665cb2415c1992f3d697127543bf478f`，保持原报告不变。

## 2. 确切源码与兼容组合

| Owner | 修订 | Git tree | 用途 |
|---|---|---|---|
| Watt | `00e2a77e6b80ea79185d74a12db2cec8eeb9445e` | `5d9c8f9714d698c695484efc1091bc092862f6bd` | 本轮已资格代码/测试 |
| Guardian | `6b974748df22d84b88f6908ea8ee90a9752fd183` | `c9a1bf4e102d8365a1ce27c9cced88f8ab0cd129` | 独立 v2 核验 Owner |
| ECF | `5aa4f8833c359c15bd059eda5972aa3915bcc18c` | `878d39d9c259272bb05f2e02bdf9d60c22fad460` | 实际受支持 Managed API；源码未改 |
| ECF 不支持对照 | `c6b568d006022e39b95daebedfecfb55e562ebe5` | `f102fa082bbd0a1abd827e77d6aa1340db8b83c5` | 实际 current-main 模块的拒绝资格 |

Watt 从 N1 `5fd2579f8ab67db12f6ea122048613184276175f` 建立独立分支 `codex/c1-cross-owner-contract-continuity`；Guardian 从 `7cdd58540b59767d9a68a5d16038c06f89059a5d` 建立 `codex/c1-governed-evidence-continuity`。旧 N1/Owner 工作区和历史记录保持不变。没有合并任何 main。

本报告及附件通过后续 evidence-only commit 交付；该提交不改变上述已资格应用/测试代码。含报告的分支 HEAD 与确切已资格代码提交须区别使用。

[exact-source-manifest.json](exact-source-manifest.json) 记录仓库、base、archive SHA256 和修改 blob SHA256。[source-attestation.json](source-attestation.json) 在最终测试后再次逐文件确认实际导入树等于确切 Git archive（Watt 1921、Guardian 27、ECF 42、对照 ECF 41 文件）；导入位置为 `/c1/watt/src`、`/c1/guardian/src`、`/c1/ecf/src`。

## 3. 四处根因及最小修复

| 缺陷 | 实际根因 | 修复及保留的拒绝边界 |
|---|---|---|
| F1 Work / Steering | Work 和 Steering 各自构造 CompletionContract，后者部分路径缺少已接纳 IR 的 FulfillmentBindings | 两者复用 `admitted_fulfillment_bindings`；Steering 读取当前 Work Reality/assessment 并检查请求版本。存在 source_assessment_id 但缺对应权威 assessment、错误 Work Revision、丢失/陈旧/注入绑定仍拒绝；Native `OBLIGATION_GATE_BINDING_DRIFT` 未禁用 |
| F2 Fact / Constraint | 合法 `IR_CONSTRAINT` 履行记录只有 Item/Clause；Managed 消费路径按 Fact ID 处理 | route 明确 source_kind + WorkRevision；typed source-ref 区分真实 Fact UUID 与 IR Item/Clause；Managed 按真实来源、版本和 gate/native digest 消费，贯通 Protected Context/Guardian。没有伪造 Fact ID，也没有把 UNKNOWN 改成无证据 PASS |
| F3 input / output | Native Source Vector 是执行输入，Guardian Candidate Source 是输出；原路径直接比较二者 | 在原 assurance v1 中 opt-in `governed-obligation-v2` 和 `ProductionEvidenceLineage`。分别保存 baseline input、qualified PWU output、final sealed Candidate。Guardian 从 canonical Owner records 独立校验图谱、版本/tree、摘要和 protected-set 双向完整性；不能以 Watt COVERED 替代证据 |
| F4 同名版本 | ECF 两个修订都标 VERSION 0.1，但实际 enum、Request 参数、注册契约不同 | Gateway 检查真实 Managed DecisionType、`required_context_classes` 和注册的 base/applicability 必需类。缺失即 `ECF_MANAGED_CONTRACT_INCOMPATIBLE`，不回退 PRODUCT_UI_CHANGE。固定本轮 5aa 组合；c6 的原 repository contract 仍单独保留 |

实际修改：Watt `governed_obligations.py`、`work.py`、`steering_production.py`、`managed_context_fulfillment.py`、`guardian_assurance.py`、`decision_context.py`，两份 C1 测试及 ECF 接线文档。Guardian 仅原 software_assurance contract/runtime、独立回归和原集成文档。

Guardian 的 `legacy-v1` / `governed-obligation-v1` 仍接受；旧含义和历史结果不重写。v2 必须具有 lineage 和独立证据，不静默降级。Watt resolver 读取既有 Candidate、Verification、PWU、proposedSnapshot、NativeAttempt、trustedBaseline；没有新证据数据库。

Guardian 核对 canonical Candidate seal/fingerprint/output、Verification membership、plan/run/PWU/generation/Work/Task/ECF、snapshot/Attempt、baseline ref/revision/tree、Native SHA256、完整 protected identity set 和 typed source/gate/binding。缺失或不完整 capability grants 也拒绝。一个 Clause 的 deploy/publish 两个合法 gate 可共存；完全重复的证据身份拒绝。当前 Attempt 的权限边界证据不被宣称为完整历史无副作用审计。

## 4. 环境和夹具事实

ECS 新资格根目录：`/data/watt/c1-contract-qualification-20261009`。专用 PostgreSQL 数据库 `c1_contract_continuity`，既有 migration `20261007_72`；无 schema 修改。新 PG 容器 network-none、无端口、tmpfs 数据；runner 共享该隔离网络，仅挂载新的 C1 根目录，无生产卷/配置/凭据/Docker socket。见 [runtime-isolation.json](runtime-isolation.json)。

依赖 runner 镜像 `watt-n1-gof:84d16b1`，image ID `sha256:6c1f48e35ec485de278e8638f51d6aed75679b02a24d45355959bc8ddd7c0d14`，原应用 revision `84d16b1f98ee124a4a7fb11761c821e25223ad24`。它只提供依赖 runtime；本轮实际导入上述 exact archive。不能称为已构建/已资格的新 C1 应用镜像。PG image ID 为 `sha256:d741b376874687de90374fd34f55c6b2760e8f7bd7e4ae5cd47f50757fc08cf8`。

集成测试明确使用：

- typed IR oracle，三个原始 Human 约束和两个派生 exclusion；一条真实 Fact 内容要求与三个 binding（Git Diff scope、continuous deploy、continuous publish）共同传递。
- Work 路径实际 submit/refine，然后为**新夹具**显式持久化 `SyntheticAuthorityFixture` typed WorkReality/初始 authority，再调用实际 approve；不是普通 immediate WIC/IRK 入口资格，不转换或重置既有 admitted Work。
- Steering 路径实际 WIC 初次 admission 产生 LONG_LIVED READY Work，实际 proposal/planner Owner 使用受控 planning persistence，再实际 PRODUCE/admit_cycle。
- 实际 Native `_admission` 和 runtime admit，实际 Execution/Completion/Verification/Candidate services；输出由 `DeterministicTestExecutor` 生成。没有 live 模型执行。
- loopback HTTP 服务读取确切 Candidate Git blob，由真实 Guardian HTTP observer 独立观察。Guardian focused 单测的 observer stub 与这一完整链路区分。

收据标为 E2，这是本报告的受控契约集成证据分类，不是生产资格等级或真实 Human authority。原始 Fact/IR/WorkReality 未被重解释或删减来取 PASS。

## 5. 最终测试证据

| 最终 suite | 项数 | 内容 | 结果 |
|---|---:|---|---|
| Watt C1 whole-chain | 50 | 2 条正向（两构造路径）+ 48 个两路径负向项 | PASS |
| Watt C1 ECF API | 5 | 实际 5aa、实际 c6、base/applicability 弱化拒绝 | PASS |
| Watt 原有相关回归 | 44 | Managed Context 15、Decision Context 19、GOF 7、Guardian Adapter 3 | PASS |
| Guardian C1 | 65 | independent lineage、typed evidence、完整 protected set、缺失 grants 等 | PASS |
| Guardian 原有相关回归 | 8 | governed evidence 3、software assurance 5 | PASS |
| **总计** | **172** | 最终各 testcase item 各计一次 | **0 failure/error/skip；exit 0** |

Watt [final-watt.xml](final-watt.xml)：开始 `2026-10-09T06:06:38.633073+00:00`，204.800 秒，99 项；SHA256 `0a734f5b9fc4740029447513932ce4a0fc199c251419cbac5dc0c86750362c7b`。Guardian [final-guardian.xml](final-guardian.xml)：开始 `2026-10-09T05:48:59.584901+00:00`，9.824 秒，73 项；SHA256 `7516ce4e3b7d3319d85c90177d36d4019a1d62dd2fc57d0f0b6b22f92014be21`。运行 Python 3.13.16、pytest 9.1.1；依赖版本见 attestation，httpx distribution metadata 不可得，标 UNKNOWN。

### 六项正向验收

| 原要求 | 实际证据 |
|---|---|
| 1 Work approve 合法 Contract | 实际 approve 产生持久 CompletionContract/PWU，Native admission 成功；显式 authority 夹具边界如上 |
| 2 Steering 等价合法 Contract | 实际 Steering PRODUCE/admit_cycle；同一 admitted binding 构造规则；两路径完整链路均 PASS |
| 3 mixed Fact / IR Constraint | actual Verification checks 同时存在 Fact ID 和无 Fact ID 的 IR_CONSTRAINT；实际 ECF/Guardian 消费成功 |
| 4 有变更且输入/输出血缘正确 | 输入输出 revision/tree 不相等；真实 `A index.html`，独立 Owner 图谱和可恢复 Git 对象证明 |
| 5 Managed ECF 匹配 Context | exact 5aa assembly 注册契约 READY；Native/Task/Guardian package fingerprint 绑定 |
| 6 当前履行 + future Human pending | Git Diff/内容证据及 continuous 权限门禁被消费；Candidate sealed；Human auth rows 空，Acceptance PENDING、Delivery NOT_AUTHORIZED |

### 八类负向验收

| 原要求 | 实际调用与拒绝结果 |
|---|---|
| 1 binding 丢失/过期/注入 | 两路径各 missing/stale/injected/constraint_identity；actual Native `OBLIGATION_GATE_BINDING_DRIFT` |
| 2 Fact/Constraint 身份错配 | 两路径 actual Repository verifier 的 Fact identity 拒绝；Guardian focused source kind/Item/Clause/gate/digest 错配拒绝 |
| 3 错误 Work Revision | actual Repository Verification 不 PASS；两路径独立 Guardian WorkReality lineage BLOCKED |
| 4 baseline/output/tree 错误 | actual Repository output revision/tree 不 PASS；两路径 Guardian input/output/Work/PWU 六种 corruption BLOCKED |
| 5 缺失 Owner Evidence | 两路径实际 resolver 缺 verification/candidate/native-attempt/source-baseline/proposed-snapshot/pwu 均 BLOCKED；单侧 COVERED 不足 |
| 6 未授权 Deploy/Publish | 两路径真实 CloudDelivery/GitHubDelivery authorize 入口 `OBLIGATION_DELIVERY_PROHIBITED`；Human auth rows 仍空 |
| 7 不兼容 ECF API | 实际 c6 模块明确报不兼容；删 base/applicability 注册要求亦拒绝，无 managed 降级 |
| 8 虚构 future authority | 两路径实际 Guardian contract 拒绝 ACCEPTED / AUTHORIZED；不把候选生成或架构批准当作 Human 接受 |

这些负向项成功表示拒绝保护成立，并不表示注入的错误工作通过。没有跳过 Guardian 核验。

### 预检失败保留

[preflight](preflight/) 保留四次 ERROR、一次 FAIL 及早期通过结果。依次是新 DB 夹具缺 migration-owner seed、把已 READY 长 Work 再 refine、Constraint 引文不在对应 Clause、非空 genesis origin/错误 governance fixture 触发 ECF 必需类、最后 pending 断言发现原始 handoff constraint 未完整进入 typed fixture。按各自真实原因修正新夹具；未放宽运行时门禁。早期 49/66 项和两条预最终正向 PASS 不重复加入最终 172。Windows collection 的 fcntl 限制也不作为 PASS。未对同一未修正失败签名反复重试。

## 6. 两条完整链路的持久身份

| 身份 | Work approve | Steering |
|---|---|---|
| Work | `c9539308-eebc-4570-b84d-25ddff38e704` | `85cc380f-2183-585c-9771-42054a25ac7d` |
| WorkReality Revision | `6acf54b1-7444-4a2f-9724-046e0ae54d79` | `1ad56172-a011-5c8e-a14b-c1909e11d2bb` |
| PWU | `7aafcd5d-8721-403b-9928-ae3a8c92f26f` | `9773b6a6-0f98-4972-977b-71e2c1d8a379` |
| Attempt | `ad1a9ae8-2626-4651-9a03-7a790c3bdd5e` | `8dbbdf68-66a7-415c-afa2-2d26ae45311c` |
| Candidate | `ffbe6c9f-e7dd-5412-ab19-f9b14875fd6c` | `258fee06-05e3-58e8-8eb7-0eb191fb34b9` |
| fingerprint | `da61e71644e72a67a7110418fc216d030a7036830c00d167d87b87c3e2135c5e` | `58b2302624fb8d3292823e12401f63fcb2b3fac7a31904821f3deef8d13d7f1e` |
| input revision | `9967ecf9a58bfbb23db027313bfa24f4640d1ffe` | `6b3f7648210f1b4a0a06133f9afdf78fe2b51839` |
| output revision | `b12a04d7978b9880f17f802774b3ec2cb9021835` | `acf085f0b869e818f82bc20e69d4cdc7e4d3cf97` |
| Guardian request | `208f0927-3871-542e-8b01-e69646710302` | `4efe0bc3-4632-5ab8-ad83-142564576985` |
| Guardian result | `d61fb1ff-f3cb-4415-befb-dec9bd2f40d9` | `6da79119-037b-489d-9072-837886d40066` |

两者 input tree `6ed77f11ba8456ba3c1342af247884809be1498e`；output tree `29e2294feabcae289b268559f8037d7e487789c1`。输出 blob `9ad5cdcb01546c8386c67fbb6793248907194f41`，HTML SHA256 `40eebeb8a519981b9506fe62c513d8a9e845b2b199da67e4ca040038a0f9c6d5`。

[Work Owner 收据](evidence/exact-contract-chain/immediate_production-c9539308-eebc-4570-b84d-25ddff38e704.json) 和 [Steering Owner 收据](evidence/exact-contract-chain/long_lived_steering-85cc380f-2183-585c-9771-42054a25ac7d.json) 包含完整 typed IR/WorkReality、Task/Completion/PWU、Native binding、baseline/snapshot、各 Verification ID、sealed Candidate、Guardian request/result 和空 Human 授权记录，采集于 `14:06:56.723637+08:00`、`14:07:00.057766+08:00`。事件/记录 ID 来自本次新 DB，不冒充旧 Work 的历史事实。

## 7. 九项完成条件

| 条件 | 结论 |
|---|---|
| 1 四处已确认 seam | F1–F4 在 selected current-assessment 组合上闭合 |
| 2 两生产合同路径 | 实际 approve / Steering constructors 均成功，错误绑定拒绝 |
| 3 Fact + IR Constraint | typed 混合消费闭合，无 invented Fact ID |
| 4 独立 Guardian input/output | 确切 Owner 图谱核验，负向 BLOCKED，legacy 回归通过 |
| 5 Watt/ECF exact 组合 | 5aa Managed 支持；c6 Managed 明确不支持 |
| 6 集成和负向 | 上述六正向/八负向类别全覆盖；172 最终项通过 |
| 7 无重复架构 / Gate 降低 | 复用既有 Owner，未新增 IRK/生命周期/alias/refine coordinator/assurance plane；Native、Verification、Guardian 和 Human 分工保留 |
| 8 相关回归无未解释退化 | 最终 52 项原有相关回归通过；预检失败单独保留和解释，不声称全库回归 |
| 9 exact source/Owner/evidence | manifest、逐文件 attestation、JUnit、Owner JSON、Git pack 和 SHA 索引共同绑定 |

## 8. 保留风险与下一阶段输入

**未资格 Finding：继承 IR 的 ASSET_SCOPE_ADMISSION 前态。** 既有路径可能复制 inherited typed constraints 并清空 `source_assessment_id`。本轮共享 helper 沿用既有 no-local-assessment 空 binding 路径，不负责回溯；Native canonical IR 会回溯并继续 fail closed。不得将这一前态宣称为已闭合、正常生产成功或通用兼容。它不是本轮 selected current-assessment 构造链的新权限放宽，作为后续 Owner Reality Audit 输入保留，本轮不新增 admission 子系统修复它。

仍未宣称合格：普通 immediate WIC 入口、任意自然语言泛化、多 PWU live 软件生产、完整历史负向效果审计、真实 G0/N1 Closure、未来 Integration/Acceptance/Delivery，以及新应用镜像。没有当前 selected C1 chain 的未关闭硬阻塞。若未来使用上述未资格路径，须取得独立证据，不能复用本报告冒充。

C2 可用起点是第 2 节 exact Watt + Guardian + ECF 组合；Guardian Managed v2 双侧一致，c6 Managed 不可替换。应用镜像仍需下一阶段按授权构建并资格，本轮不自动启动。保留 Self-Refine、Post-admission Materialization、Engineering Truth、Native Effect Permit 和原历史证据。

## 9. 跨电脑恢复、清理及重现

Git 持久位置为 Watt `codex/c1-cross-owner-contract-continuity` 上本目录；Guardian 提交在其独立分支。ECS 同步位置为 `/data/watt/c1-contract-qualification-20261009`，包含 exact source archives、test dependency archive、收据和报告交付包。没有依赖旧电脑未跟踪 `.watt` 文件。

[evidence/git-objects/manifest.json](evidence/git-objects/manifest.json) 和 [recovery-check.json](evidence/git-objects/recovery-check.json) 记录两份 input/output Git pack。已在全新 bare 仓库恢复并验证两个 tree 和 Candidate blob。pack 仅为本次夹具对象；不是生产仓库备份。可用 `git init --bare`、`git index-pack --stdin < <work>.pack` 后按 manifest revision 读取，不需要旧测试临时目录。`export_git_witnesses.py` / `verify_git_recovery.py` 保留导出与核验逻辑，重现需指定新的 isolated 路径。

[cleanup-receipt.json](cleanup-receipt.json) 记录按完整 ID/name/qualification labels 校验后，仅 stop/rm 本轮 runner 和 PG 容器；未使用 prune 或删除 volume/image。新 tmpfs DB 已丢弃，Owner JSON/Git pack 留存；这不是可恢复的完整 DB dump。现有 running container ID 集合前后相同，ECS `/data/watt/runtime/source` HEAD 始终为 `ee5bd86a53891f9391785c91d0ccef81ad2d56c3` 且 clean。

重现入口见 [reproduction.md](reproduction.md)；artifact SHA256 索引见 [artifact-index.json](artifact-index.json)。本轮原始凭据、生产数据库 URL、ENV 和生产设置不在证据包中。未修改/轮换凭据。

记录的最终 pytest 时长合计 214.624 秒；完整任务计算/费用无法从现有记录准确取得，UNKNOWN。最终 suite 不调用 live model；没有为本轮构建新应用镜像。预检不计为最终 PASS。
