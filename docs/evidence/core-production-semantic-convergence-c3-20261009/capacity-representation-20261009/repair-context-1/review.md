# C3 — Evidence-Grounded Continuation / Repair Context Review

2026-10-10。**C3 PARTIAL — Exact Formation Convergence Blocker**。
本次由 Human 与 Codex 共同决策；不设置 Architecture Lead 审批角色。
原历史决策、Human Authority、独立 Guardian 和工程事实保留。

## 1. 执行与冻结身份

| 对象 | 确切身份 |
|---|---|
| 起点证据 HEAD | `78c5e517172c4718916659fd27db9dfe8d7305a9` |
| 首次真实验证 Watt | `e7afb5a15df4c187a9248b4a073391a62037677f` |
| 首次实际镜像 | `sha256:e42fcb7dfe18254f1396f2faaaadd95b0d24efe445db6ce19beedfdebac32726` |
| 本次交付 Watt Source | `ddb9b0cb62a26d13cca0eb46d693d95ef618f476` |
| 本次交付 Watt Tree | `c0fdc19311d094fd5f8ab94497b9c94156fd6f27` |
| 本次实际镜像 | `sha256:619598878ebef02b80635efb0e991fece07038d9ee8e93ad78d2a1e57beb8377` |
| Guardian / Tree | `76c1e87a1b29d151f4ed949748e3298f2169c5b1` / `6066a6d6b8d91bec610021409ab320309ed0e437` |
| ECF / Tree | `5aa4f8833c359c15bd059eda5972aa3915bcc18c` / `878d39d9c259272bb05f2e02bdf9d60c22fad460` |
| 库存 fingerprint | `7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf` |
| 12 Capability fingerprint | `a2e695783b122373f0ed308a959fa4e3116c4a9df5454dbedd81695071153b17` |
| 原始 basis SHA256 | `9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c` |
| 新隔离数据库 / Migration | `c1_contract_continuity` / `20261007_72` |

源自已保存历史 Work 库存的诊断，不是该 Work 的新执行。
两次隔离验证各有独立 execution-started marker、实际 Docker identity 和只读输入。
Formation 为 deepseek-flash / none / 16384 / 120s；Review 仍 low / 16384 / 120s，但两次均未达到调用条件。
每次最多两候选、一次反馈、四逻辑调用；没有追加传输重试或重置预算。
应用代码来自完整新镜像，无 Python 源码覆盖。

## 2. 已证实缺口与有界修复

首次验证第一候选可以完成 Wire 解码，但被重复 Route、错误归属和来源对应谓词拒绝。
第二次请求含 17 条结构化错误，却没有第一候选本身；Route 序号和 component hash 缺少可直接对照的提案。
这证明反馈输入缺少修复上下文，不证明它是模型所有错误的唯一原因。

修改仅限已有 Watt Work Formation/Provider Owner 与测试：

- 反馈携带原样、未获接纳的上一份 Wire，不重复完整库存，不自行修补 Route。
- 绑定原始 bytes SHA256、库存、Work Reality、Source、Attempt、请求/响应持久 receipt IDs；原有 predecode 诊断绑定继续成立。
- canonical 失败反馈也绑定原始提案及派生 candidate fingerprint；下一请求引用实际反馈收据。
- 恢复、重放和后续候选前重算原提案、可评估谓词及反馈。删除上下文、修改原文、候选、失败码、收据或绑定均停止。
- Provider 明示 f 可使用的现有 FACT 源序号。仍是原 source index 空间；模型不能将 Clause/Constraint 作为 Fact 引用。
- 模型自行形成新候选；旧提案仅是待修复输入，不能成为事实、许可或 PASS。

未修改 Engineering Facts、Wire `fulfillment-compact-v1`、Wire schema fingerprint、反馈 v2、Owner/Phase/Evidence 权限或预算。
未修改 Guardian、ECF、canonical main、正式服务、历史 Work、Candidate、Human Decisions、Quality Ledger。

## 3. 精确修订的受控资格

| 项目 | 结果 | 边界 |
|---|---|---|
| 新镜像相关回归 | 309 PASS，0 FAIL/ERROR/SKIP | 包含容量、组件、反馈恢复、Provider、Work stop、Guardian Adapter 等；非真实模型资格 |
| 新隔离 PostgreSQL | 13 PASS，0 FAIL/ERROR/SKIP | 原 C1/Owner 路径及 predecode/canonical 反馈持久恢复、错误反馈/收据/库存；非真实 G0 |
| 原提案可用与负向身份保护 | PASS | 小/中/复杂受控库存；一次修复后独立受控 Review；不是 live intelligence |
| 默认运行配置 | 保留 | reasoning=none 仅用于获授权诊断；生产配置没有更改 |

开发记录全部保留：首次 214 PASS / 1 FAIL，发现超容量解码失败不应被误当作可绑定 canonical 提案；修正后 215 PASS。
随后补充的 40 项反馈身份检查 PASS。最终仅以新镜像 309 与 PG 13 计作交付源码资格。

## 4. 两次真实有界验证

| 观察 | 原 e7afb5a 验证 | 修复 ddb9b0c 验证 |
|---|---|---|
| Formation / 反馈 / Review | 2 / 1 / 0 | 2 / 1 / 0 |
| HTTP / Provider | 两次 200 / completed | 两次 200 / completed |
| 输入 / 输出 / 推理 tokens | 36650 / 4518 / 0 | 39912 / 4673 / 0 |
| total tokens | 41168 | 44585 |
| 实测流程耗时 | 15.4314s | 16.1352s |
| 最终停止谓词 | WIRE_FACT_KIND_INVALID | COMPONENT_SOURCE_CONTRIBUTION_LOST |
| 源绑定终态 | 26 UNRESOLVED | 26 UNRESOLVED |

原验证第一候选存在重复/矛盾归属、缺精确禁止来源及多条来源对应错误；第二候选再次产生非 FACT 引用。
修复后两份输出没有观测到非 FACT 引用，但都只有 23 个 primary source，29 条 raw Route。
它们都遗漏 source 9、10、12 的自身组件 Route；原样反馈与失败提案已发送，第二次仍未修复。
本次不能从有限样本声称 f 类型改进具有普遍因果效果。
两轮均没有 max_output_tokens 耗尽或传输失败；历史 low 配置容量失败继续保留。

累计四次 Formation、四次 HTTP、两次既有反馈、零 Review、零传输恢复：85753 actual total tokens。
cached 是 input 子集，reasoning 是 output 子集；价格、可见 JSON 单独 token 数与未观测计算成本 UNKNOWN。
确切请求/响应身份、Usage、反馈和原输出 fingerprints 在各自 live-result 与私有 Owner receipts 中。

## 5. 根因界定与来源语义追溯

只读复核没有更改 raw output，也没有把诊断视图作为合格 Candidate。

- source 9 为 c4 的 CONSTRAINT，source 10 为同一 c4 的 PRODUCTION_INTENT；两者原文 hash 相同，身份与职责不同。
- source 12 为 c6 的 CONSTRAINT，其原文与 source 5 Fact 引文相同；相同文字不能替代来源身份和完整履行处置。
- 三个来源仍存在于其他 Route 的 supporting refs。现有 u 支持引用没有对应原来源的组件跨度/处置证明，不能直接算完整来源覆盖。
- 缺失的是整份来源自身 Route，涉及实质文字和数字，非尾标点或简单 off-by-one。
- 独立 Semantic Review 未发生，故真实业务语义是否已由其他贡献等价覆盖为 UNKNOWN；不能把结构性遗漏直接冒称全部业务要求丢失。
- 未获接纳的 raw-route 诊断还揭示文件 Scope Owner 错配、禁止性 Fact 缺精确 Clause、当前 Clause 仅作背景、矛盾处置及支持来源对应未证实。补齐三个 Route 本身不足以 PASS。

另一次只读契约检查覆盖八个原 Clause 库存条目与十一条 Work Constraints：
十一条均具有现有精确原始来源或既有 exclusion 派生分支的成功前提。
这是成功分支的必要条件检查，不是所有语义、权限或全局候选都已合法的证明。
据此不能断言现有契约必然无法表达此库存，或必须放宽 Source Correspondence/Guardian。

证据等级：真实请求与 Docker/SQL 观察为新运行证据；只读候选/原库存分析为持久事实派生诊断；源码分支分析仅证明当前契约逻辑。
源码判断与新观察不追认历史失败原因。模型为什么仍选错/漏源的内部原因 UNKNOWN。

## 6. 原 C3 履行链的状态

| 链路义务 | 当前真实状态 |
|---|---|
| 完整原始 Intent/Fact/Clause/Work 库存 | 原持久输入只读、identity 不变 |
| 有来源的组件与合法 Owner/Phase/Evidence 候选 | 真实样本未收敛；UNRESOLVED |
| 可评估确定性身份、完整性、权限谓词 | 正确拒绝当前失败提案；受控回归合格 |
| 一次反馈的真实修复效果 | 已实际执行，未修复当前完整来源覆盖 |
| 独立 Semantic Review | NOT_EVALUABLE / 0 次调用 |
| 正常入口 G0 → Worker/Git/Verification/Seal/适用 Guardian | 尚未具备启动门槛，本轮没有创建 |
| 当前修订生产推理配置资格 | 未取得；none 诊断不能代替 low 生产资格 |
| 独立 Holdout | 封存，未读取、未解封、未资格 |
| Human Integration/Acceptance/Delivery | 没有新增授权或可交付 Candidate |
| C4/N1/N3 | 未启动、未关闭 |

## 7. 停止依据与下一项必要行动

当前的具体阻塞是：既有预算内，真实智能候选未形成完整且合法的源组件/Owner/证据对应。
传输、容量和反馈身份在本轮没有观测到阻塞；修复上下文补齐后仍有真实候选契约错误。
继续相同请求或创建新 G0 没有根因修复依据，因此停止实际调用。

下一步由 Human 与 Codex共同审查一份窄范围的候选履行契约校准：

1. 明确来源自身贡献覆盖与 supporting ref 的不同证明职责；不默认将引用变成已消费，也不丢弃重复原文的权威身份。
2. 核对现有 Owner 已可确定的合法原始来源/身份对应，是否应作为可审查候选输入提供；模型继续负责组件语义与正确消费选择。
3. 校准对文件 Scope、禁止源、当前内容和背景处置的可消费前提与反馈，保持原权限和独立 Review/Guardian。
4. 只有现有单次形成加一次反馈被证明确实不足，才共同决定有界分阶段形成及预算调度。当前样本不证明 Option B 必然需要。

本报告没有实施上述新语义契约变更、额外模型请求或更大架构；没有新增 Owner、Alias 或 Coordinator。
现有工程修复保留，C3 保持 PARTIAL。后续 G0、Holdout 和 Closure 不以受控 PASS 或只读分析替代。

## 8. 持久化与恢复

公共证据提交原 `codex/c3-open-semantic-obligation-convergence` 分支。
ECS 根：`/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/`。

- `feedback-live-convergence-1/`：修复前本轮两次真实请求，独立 marker 与私有完整输出/Owner receipts。
- `repair-context-20261010/`：新镜像、309/13 回归、开发失败、精确镜像归档和公共交付。
- `repair-context-live-1/`：针对性真实验证、完整私有提案/反馈/Owner receipts、只读诊断。

私有文件位于各 live 目录 `private/model-observations/`，未复制到 Git。
新 image recovery SHA256 为 `05e9c0129dfa8fce6e04b3adf7d0068bc7e272d2dbd0fe4d80416078ff50b1a0`；归档 0600。
restore load 和异地备份 NOT_PERFORMED。完整恢复以 Git 分支、ECS 目录、精确 hashes 和镜像归档为依据。
