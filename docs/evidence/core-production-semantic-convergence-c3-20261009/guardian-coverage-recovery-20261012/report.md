# C3 Guardian Coverage Recovery — Closure Delta / 2026-10-12

**真实普通 G0 已到达 SEALED Candidate → READY Preview → 独立 Guardian PASS。C3 PARTIAL — Independent Holdout Qualification Pending。**

本轮恢复原 C3 Mission，仅校准已证实的 Guardian 证据消费缺口。依据固定 Program ADR-0002、Watt 开发原则 §§13–14；没有改变 Closure 定义、权限、预算或原始工程事实。

## 1. 根因、归属与历史 FAIL 对账

[安装态原始诊断](evidence/binding-diagnostic-2.json) 对请求 `b705e6f6-d358-5ea0-9a7b-2b337c5b49fa` 直接读取 PostgreSQL/Owner：

- 请求仅引用 Candidate 已接纳的 PATH_SCOPE `5d603bcf-4245-5c64-8333-179d1fc797d6` 和 GIT_DIFF_CHECK `a0c9307e-f5fe-516a-95e8-fe17b27e985b`，两者均 PASS、Revision/Tree 精确匹配。历史 FAIL 未混入当前必需 Coverage；Watt Adapter 的既有修复有效，不重复修改。
- Guardian `5c88ffb` 的 `_continuous_binding_permitted` 原 `runtime.py:1126` 错误拒绝 Fact `9f0b4f54-82d6-5a37-ae59-27838cf11cd2` 的 deploy/publish 组件。该 Fact 为 HUMAN_EXPLICIT / CONFIRMED / SCOPE，原 qualifiers 为 `{}`；已有 v3 计划、独立组件 Review、同源 CURRENT NEGATED Clause 和实际 Native 无部署/发布权限证明。Guardian 仍要求固定 `{negated:true}` 的旧表达。
- 此全局 production-lineage 前提失败导致全部 8 个受保护项报 Coverage Gap；八条 Finding 不是八个独立内容错误。
- 越过该前提后，[同一数据的后续诊断](evidence/retention-source-diagnostic-1.json) 定位两个 IR Clause 背景贡献：`pi-n1-index-page:c1/c3`。已协商 v3 / `existing-primary-contribution-background-v1`，完整计划经真实独立 Review，并有当前 sibling/Fact 消费者。Guardian `_reviewed_background_component` 仍套用旧 ASSERTION/DISCUSSION 规则及反向引文包含判定，将完整来源中的背景贡献错误判成必需产物内容。

归类：**B — Guardian 当前 v3 消费适用性与 Watt 已接纳契约不一致**。不存在本轮需要重试模型才能创造的缺失权限或证据。错误来源、未决事实、矛盾 negation、错版本、缺 Review 或真实 Gate 仍应正确拒绝。

## 2. 最小修复与边界

Guardian 提交：[0d7aca954588c8ad3883dbedb730e59dc1d7b867](https://github.com/hengyizhiyuan/guardian/commit/0d7aca954588c8ad3883dbedb730e59dc1d7b867)，Tree `92ac992c03bd84923a569bbe9f314c0786457040`，已推送原 C3 分支。

- 在现有 continuous 谓词内消费确切 v3 适用性：保留原 Fact qualifier；原 Fact/Clause 精确来源对应、当前负向 Clause、相同已接纳 Gate 及实际 Native 权限仍全部必需。明确矛盾 negation 仍拒绝。
- 在现有背景谓词内消费最终 Formation Attempt 的已持久化 source-context contract；区分 primary Fact 贡献与更宽的来源引文，保留完整组件、独立 Review、当前 sibling 及真实当前证据。所有原 Fact 的实际消费者仍由整体 inventory gate 独立核验。
- 同仓窄范围契约说明及正负回归同步；旧协商路径保持原严格前提。

没有改 Watt Runtime/Adapter、ECF、Wire Schema、Owner 权限或 Assurance 决策职责，没有新增 Alias/特殊 Case/中间层。没有修改期望值、源 Fact 或已密封 Candidate。

## 3. 精确代码、镜像与安装态资格

| 对象 | 本轮实际身份 |
| --- | --- |
| Watt 不变应用源码 | `01446afc7cccb03f99e8e6febbe4cfe9ed8388e4` / Tree `daa0a41b756755c7f88f347ee18c68ecd99273b0` |
| 本轮 C3 文档/证据基线 | `a138193af545a377ff519eb85b02cab26393f80c`；其 `src/` 与上述应用源码无差异 |
| Guardian | `0d7aca954588c8ad3883dbedb730e59dc1d7b867` |
| ECF | `5aa4f8833c359c15bd059eda5972aa3915bcc18c` |
| 新确切组合 Image ID | `sha256:8e403fd29c33d4f5ed9aac1b59087e4943f4a05aac78f20071b55ed91624ce55` |
| 保留的合格基底 Image ID | `sha256:8c3eda5e197c7778b2deb9e126ccdbeb0b2e716d1112f0dbe0f5a8804a2f7d3a` |
| 隔离业务 DB / Migration | `spg_c3_bindingg0g61_qualification_20261010` / `20261007_72` |

[构建](evidence/image2/build.json) 基于合格基底和 exact Guardian Git archive 创建新镜像；[完整安装态导入/字节核验](evidence/image2/actual-imports.json) PASS。未在旧运行镜像覆盖 Python 文件。未变 Watt/ECF 继承原精确版本，不能将其历史执行改标为本轮新 Worker 执行；`ecf-unsupported` 仅是保留负向 fixture。

| 资格 | 真实结果 |
| --- | --- |
| 最终安装态 Guardian 来源/组件/阶段/独立 Review/权限正负回归 | [155/155 PASS](evidence/image2/installed-guardian-regression.json)，9.311 秒，无 runtime overlay |
| PostgreSQL/Watt–Guardian 当前密封证明与历史失败选择 | [2/2 PASS](owner-pg/receipt.json)，23.898 秒，独立 fixture DB、Migration `20261007_72`；只挂载此前已修正的测试文件，运行代码无 overlay |
| 原数据只读反事实验证 | [当前 PATH_SCOPE lineage 合法](evidence/counterfactual-source-consumer-3.json)；仅用于定位，不是独立 Assurance |
| 同一真实 G0 独立 Guardian | **[实际 PASS / 0 Findings](evidence/actual-independent-guardian-owner.json)** |

初始开发测试的依赖路径/目录权限准备失败和第一次镜像 source-env identity 核验失败均保留，未改作 PASS。第一次镜像不得充当最终安装态资格；第二次构建修正实际版本元数据后才合格。反事实脚本的原安装 Guardian hash 与临时消费者 hash 分别见 [诊断身份澄清](evidence/diagnostic-provenance.json)。

## 4. 原 Work 的合法生产恢复

Work `6ba2cffa-0bf3-565a-81e0-7f3c6696f21e`；PWU `48781eed-8ead-4fee-9d21-973055ef6653`；Attempt `de98f392-b8d1-40ac-a442-a283fa938060`。

Candidate `4a4096c3-2846-5678-ab8c-37aed60a0c9c`，fingerprint `9446c018fcafc8512a56c00d46861feac90c440014e6dc72af373249825af823`；产物 Commit `43fa0621e0d0e06fd1b84c9b76e06b831a578d97` / Tree `c9942900fd4ad60eff68f4133bbf57181390da1a`。

只升级隔离 API/Coordinator 的实际 Guardian 消费端，保留旧容器；原 Worker/Tool Host 未被本轮替换。通过既有 Preview stop/request Owner 路径形成 successor Preview `f61f401e-8541-45d2-b85f-5b9ae4e1d84b`，Candidate 不变。

新实际 Guardian request `6b28aa08-4484-5860-9648-8aa2e8b3737d`，证据 `guardian:evidence:da7556a7-5aa1-4877-bc34-8bc80ab33c0a`，**PASS / 0 Findings**。八条 protected obligation 的 coverage references 均为当前 PATH_SCOPE；GIT_DIFF_CHECK 仅承担其实际 Diff 职责，不必伪装成完整语义库存证明。

[真实恢复控制收据](evidence/real-guardian-continuation.json) 前后哈希相同：Candidate、proposal、admissibility、PWU、Work Reality、全部历史 Verification、7 个 Native steps、9 个 Native effects、旧 Guardian BLOCKED 结果。没有重放已结算效果、Formation、Worker 或 Verification；没有新 Work / Human Authorization / Runtime Commit / Integration Effect。

[静态 Preview 实际观测](evidence/static-preview-actual-observation.json)：HTTP 200、193 bytes，与确切 Git Blob SHA256 `647a93ae5dead8fa8dc2229e10e2945907ddf11d16c9080fbcec80e7cb112116` 一致，Revision/Tree headers 精确匹配。此既有 profile 是 immutable Git blob 服务，独立 Preview Docker Image 为 NOT_APPLICABLE；实际服务宿主 API Image 为上述 `8e403fd…`。此前泛化 Docker lookup 的 UNKNOWN 不代表该 profile 创建过但丢失了容器身份。没有在 API 执行 Candidate 代码。

Self-Refine：沿用 [此前真实两候选内容恢复](../native-context-reference-recovery-20261011/real-g0-g61-generation65/actual-bounded-self-refine.json)；本轮针对 B 类消费契约缺陷修复，新增模型调用 **0**，未重置预算。不能把本轮确定性修复称为一次新的模型自动恢复。

## 5. Closure 对账与真实剩余项

- 已消除：独立 Guardian 因上述两个旧表达前提造成的 Coverage 阻断。
- 已达成：原普通 G0 的实际 Worker/Git/Verification/Admissibility/SEALED Candidate 与当前适用 Preview/独立 Guardian 边界；历史阶段资格依赖已留存的 exact-source byte continuity，非新镜像重跑声明。
- 未完成：**原 C3 的独立封存 Holdout 尚未执行**。最新 Human 指令明确“不解封 Holdout”，本轮未读取输入、Oracle 或调优，不能据普通 G0 成功豁免该 Closure 条件。下一必要行动是取得该边界的明确继续指令后，由独立 Reviewer 在上述冻结组合上完成原 Holdout 资格。
- Human Integration / Acceptance / Delivery 真实待决，不属于本次自动授权；实际 Guardian result 保持 Acceptance `PENDING`、Delivery `NOT_AUTHORIZED`。
- 没有新的已证实工程阻断；未验证泛化范围仍未验证。C3 保持 PARTIAL，不启动 C4/N1/N3，不添加理论完备性要求。

## 6. 保全、恢复与成本

公共安全收据 [publication manifest](publication-manifest.json) 含 39 项、逐文件 SHA256；完整私有 request/result/Owner export 留在 ECS restricted private，摘要见独立 Guardian 收据。恢复根目录：

`/data/watt/c3-semantic-convergence-20261009/binding-g0-generation61-qualification-20261010/guardian-coverage-recovery-20261012`

其 `private/actual-independent-owner-export.json` 为完整权威读取快照；`image2/context`、`evidence/image2`、`owner-pg` 分别保存确切构建输入、安装态及 PG 收据。通过获授权 `watt-ecs` SSH 恢复；本机未跟踪 staging 不是唯一证据，不宣称异地备份或恢复演练。

[最终运行库存](evidence/final-runtime-inventory.json) 保留真实角色差异：现有 Worker 的 idle-poll 镜像来自另一个任务，本轮未覆盖或冒称统一镜像。正式源码 HEAD `5de657f3cb65780adf50f6557b54171a6c3cfae5`、正式 main ref `ee5bd86a53891f9391785c91d0ccef81ad2d56c3` 不变。生产服务、凭据、原事故 Work、历史证据、Quality Ledger、Holdout 未被本轮修改。

本轮模型请求/新增 Token 为 0。两次镜像构建分别 2.075 / 0.426 秒；最终正式定向测试如上。开发测试、原失败与控制时间按原收据保存；整个既有环境累计 Provider 费用和 CPU/内存总消耗 UNKNOWN，不推测。
