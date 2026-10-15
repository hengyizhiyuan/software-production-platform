# Watt · Guardian · ECF 三项目 AI-Native 系统完成度审计、实施方案与执行路线图

2026-10-15（Asia/Shanghai）。分支 `claude/c3-formation-ai-native-convergence`，HEAD `d25dbb2f`。
**只读审计与规划文档，没有修改代码、门禁、C3 状态或线上数据。** C3 状态由 Human 维护，仍为 PARTIAL。

## 0. 审计依据与三个目标

Human Governor 提出的三项目标：

| # | 目标 | 本审计的判定问题 |
| --- | --- | --- |
| G1 | 各模块完成 AI 原生能力改造 | 每个模块能否在自身边界内适应概率性输入/输出：语义适配、Reality 边界、UNKNOWN/CONFLICT/ALTERNATIVE/NEED_INFORMATION、有界收敛，而不是"调用模型 + Schema + 失败即报错"？ |
| G2 | AI 原生软件研发能力：联调打通意图 → 生产 → 部署/下载 | 当前源码与线上环境中，Human 意图能否自动走到可下载/可运行的软件？首个断点在哪？ |
| G3 | 足够聪明的问题解决：模块互相配合把随机性问题推进到解决 | 某个阶段失败后，是否有其他 Owner 接手推进（退回上游澄清、重规划、修复、问 Human 的具体问题），还是只抛异常/BLOCKED？ |

规范依据：[开发原则 §13/§14](ai-native-development-execution-principles.md)、[AI Native Standard v1.0](watt-ai-native-architecture-standard-v1.0.md)、[Maturity Reassessment v1.0](watt-ai-native-maturity-reassessment-v1.0.md)。

证据来源：三个只读子审计（模块能力、端到端链路、跨模块失败协作）逐条给出 `文件:行号`；关键结论经本人二次核对（第 6 节）。ECS 运行版本与数据库计数为只读查询。

---

## 0.5 三项目视角：Watt + Guardian + ECF

Watt 不是单独运转的。三个项目共同构成生产闭环：

```text
            ┌──────── ECF（工程上下文 Owner）────────┐
            │ assemble_context → READY/INCOMPLETE/    │
            │ CONFLICTED/STALE + 缺失类别/冲突来源链   │
            ▼                                          │
Human ─▶ Watt（编排 / 生产 / 验证 / Candidate）──────────┤
            │  AssuranceRequest（Candidate + 证据链）   │ ECFRealityRuntime：
            ▼                                          │ workspace/change/preview/
        Guardian（独立 Assurance Owner）               │ delivery 事实登记
            PASS / FAIL_REPAIRABLE / BLOCKED + Findings
            （Watt 需要 PASS 才允许 Candidate 授权）
```

| 维度 | 现状（已核对） |
| --- | --- |
| 集成方式 | 不是服务调用：api 进程通过 `PYTHONPATH` 进程内 import 挂载在 ECS `/data/watt/owners/{guardian,ecf}` 的源码，同步调用 |
| 版本对齐机制 | 只有部署脚本 `prepare-owners.sh` 写死提交号（ECF `8b2c7b68`、Guardian `27bf5691`）；无包版本协商；Guardian 包版本恒为 0.1.0；C3 资格镜像另用构建参数注入 Guardian `0d7aca95` / ECF `5aa4f883` |
| Guardian 分支 | 最新集成线是 `codex/c3-open-semantic-obligation-convergence`（`0d7aca95`），**比 main 多 17 个提交、未合入**；main 只多了 3 个文档提交 |
| ECF 分支 | Watt 实际依赖 `codex/managed-greenfield-context-closure-v1`（`5aa4f883`，新增 MANAGED_GREENFIELD 契约），**未合入 main**；main 头 `c6b568d` 被 Watt 测试明确当作"不兼容 Owner" |
| AI 原生定位 | 两者都**不调用 LLM**，是确定性 Owner。这是正确的：它们负责事实与独立保证，不该猜。按 §14.1，它们的 AI 原生责任是"守住自身不变量，并把真实失败谓词以可行动形式交给语义 Owner" |
| 不确定性输出 | ECF：缺什么写得清楚（missing classes、冲突双方来源、不足风险），但不给"谁来补"。Guardian：Finding 有 expected/observed/evidence/repairable，`UNAVAILABLE_DEPENDENCY` 带 owner；但**不可修复问题一律压成 BLOCKED**，没有 INSUFFICIENT/ESCALATE（自己的 roadmap Case C/D 未落地），`CONTEXT_COVERAGE_GAP` 不说明由谁补 |

### 0.6 立即处置项（P0，线上回归，已核对）

**10-15 部署的 Watt `e13d8258` 与线上 Guardian `27bf5691` 契约不兼容：** Watt `guardian_assurance.py:407` 无条件传 `evidence_contract_version`，线上 Guardian 的 `AssuranceRequest` 没有该字段且 `extra="forbid"`（已在线上 api 容器中确认）。v2 受管 Web 路径还会 import 线上不存在的 `ProductionEvidenceLineage`。

后果：线上任何 Candidate 走到 Guardian 评估都会在构造请求时失败，按 `candidate_preview.py:538-545` 记为 `BLOCKED / GUARDIAN_PLATFORM_DEFECT`，Candidate 无法获得授权；重启对账路径（`:456`）是否被外层捕获未知。截至审计时日志中尚未触发，但线上有活跃用户请求。

这是部署时只验证了 Watt 自身镜像、没有验证三项目组合造成的。处置选项（需 Human 决定）：
- **A 回滚**：api 恢复部署前镜像（回滚标签 `watt-cloud-worker:c3-predeploy-rollback-e13d8258`，脚本已就绪），最快消除风险；
- **B 前移对齐**：线上 Guardian 升级到 C3 资格版本 `0d7aca95`、ECF 确认为 `5aa4f883`，并与 Watt 组合跑兼容性门禁后再放行。

教训直接进入 R0：**三项目组合版本必须作为一个发布单元被资格化和部署。**

---

## 1. 总体结论

**Watt 的"骨架"已经是对的：Owner 分离、候选与权威接纳分离、证据门禁、未知效果保护、有界修复与如实停止都真实存在。但它目前是"一组各自谨慎、彼此不协作的 AI 模块"，不是"能把问题推进到解决的 AI 原生系统"。**

三个目标的现状：

| 目标 | 完成度判断 | 一句话 |
| --- | --- | --- |
| G1 模块 AI 原生 | **约 40%**：没有模块达到 L3；4 个 L2、其余 L1 或更低 | 修复以结构性重试为主；ALTERNATIVE/NEED_INFORMATION 只有字段，几乎没有生产者和消费者 |
| G2 端到端打通 | **代码链路 100% 接通；当前三项目组合下真实跑通 0 次；线上组合存在确定的契约不兼容（§0.6）** | 最近一次意图 → 下载真实成功是 09-17（C3 前代码）；当前源码首个断点是 Formation，其后 Human 授权 → 集成 → 下载在 C3 后从未真实执行 |
| G3 协作解决问题 | **约 20%**：只有 2 条自动闭环 | 唯一通用通道是"收敛预算耗尽 → 问 Human 是否暂停/改目标"；没有"退回上游 Owner"，Formation 失败与 Guardian BLOCKED 是无人接手的死胡同 |

百分比是规划用的粗估，不是可靠性统计或资格结论。

**最重要的判断：** 过去两周的主要投入集中在 Formation 单模块的收敛（C3），这是必要的，但它把系统层面的两个更大缺口掩盖了：
1. **失败之后没有人接手**（G3）——即使 Formation 完美，Verification、Guardian、Executor 失败后仍会以同样的方式停住；
2. **全链路长期没有真实贯通**（G2）——线上 worker/coordinator/tool-host 仍运行 10-07 的 `ee5bd86a`，api 运行 `e13d8258`，版本混合部署，且没有任何一次用当前代码走完意图 → 下载。

继续单独打磨 Formation 的边际收益正在下降；下一阶段应转向**系统级协作通道 + 全链路贯通**，在真实链路里继续提升各模块。

---

## 2. G1 审计：模块 AI 原生能力

等级按 Standard v1.0 §4（L0 Deterministic Wrapper → L3 Autonomous）。

| 模块 | 用模型 | 修复能力 | 失败后 | 不确定性表达与消费 | 等级 | 最关键缺口 |
| --- | --- | --- | --- | --- | --- | --- |
| WIC | 是 | ≤3 次**结构**修复；修复指导按错误码关键词分派（`deepseek_interaction.py:134-197`） | Turn FAILED（`interaction.py:647`） | ASK_HUMAN 有消费；修复提示明确"不发明替代"（:163），无 ALTERNATIVE | L1+ | 失败即终止 Turn，没有"部分理解 + UNKNOWN + 追问"的降级 |
| IRK / Semantic Truth | 否（消费 WIC） | Reality 刷新 2 次 | BLOCKED_WITH_EVIDENCE / 交 Human | UNRESOLVED、GUIDANCE_REQUIRED（问题+提议）、2–4 选项均有消费 | **L2** | 无一等 CONFLICT；也是唯一已有"给 Human 提选项"能力的地方 |
| Guided Design / Design Intent | 否 | 0 | 关键词默认值 | UNKNOWN 仅投影到 DTO | L0–L1 | 意图框架是关键词规则 + 常量置信度（`design_intent.py:22-110`），属 Rule Accumulation |
| Steering / Planning / Task Contract | Steering 是；Planning 默认规则 | 线格式 1 次、scope 2 轮、refine 1 次 | Exhausted → BLOCKED → Work 级收敛 | NEEDS_REFINEMENT、unresolved_questions | L2- | 单步修复反馈为自由文本；**不消费下游失败事实来重规划**（见 G3） |
| Formation | 是 | 2 候选 / 1 反馈；本周新增按来源重述、标点编译 | UNRESOLVED → NotReady → BLOCKED | Owner 三件套齐全，但 ALTERNATIVE/NEED_INFORMATION 不外送 | **L2** | 真实接纳率低（Holdout 0/4，最新 1/6）；失败后无人接手 |
| Native Executor | 是 | 拒绝 2 次、无效 3 轮、自适应预算、可修复性五分类 | UNABLE / BOUNDARY_CROSSING | 效果 UNKNOWN 处理完善 | L2- | 无任务语义层的 NEED_INFORMATION；失败不回 Planning |
| Verification | 是 | 2 次，结构化 failed_predicate，禁止修复中翻 SATISFIED | UNVERIFIABLE / UNKNOWN | UNVERIFIABLE 有消费 | **L2** | UNVERIFIABLE 不说明缺什么、该谁补；FAIL 不反馈给 Executor |
| Guardian 集成 | 外部（Guardian 自身不用 LLM） | — | PASS / FAIL_REPAIRABLE / BLOCKED | FAIL_REPAIRABLE 被 Steering 消费（唯一回到生产的闭环） | L1+ | BLOCKED 无人接手；Guardian 侧无 INSUFFICIENT/ESCALATE，Finding 不说明由谁补 |
| ECF 集成 | 否（ECF 自身不用 LLM） | 0 | NOT_READY → BLOCKED | CONFLICT 引用（全仓唯一一等 CONFLICT） | L1+ | NOT_READY 后无取证/等待策略；ECF 包不给"谁来补" |
| Trace Analysis | 经 Native kernel | 2 轮修订 + 自审 | FAILED | Owner 三件套 + 自审 UNKNOWN，且回灌模型上下文 | **L2** | 失败无部分结果；目前是 Human 触发，不参与运行时自救 |
| Preview / Delivery | 否（确定性） | 传输层 3 次退避 | NEEDS_HUMAN_ATTENTION | 效果 UNKNOWN 合格 | 不适用 | 按确定性模块对待即可 |

**共享 Self-Refine 契约（`domain/refinement_contract.py`）的真实使用：**
- `record_bounded_refinement` 被多处写入，但只是事后遥测，不改变控制流；
- `OwnerUnderstanding/Evidence/ConvergenceDecision` 三件套只有 Formation 和 Trace 使用；
- `OwnerConvergenceDecision.action="ASK"` **全仓从未产出**；三件套**没有任何跨 Owner 消费**；
- 真正被跨 Owner 消费的只有 `WorkConvergenceObservation`（Steering、Human Attention、Guardian 门控）。

**G1 共性缺口（不是单模块问题）：**
1. **不确定性没有"出口"。** 规范 §3.3 要求的 ALTERNATIVE / NEED_INFORMATION 在多数模块只有类型，没有"产出 → 交给能解决它的 Owner"的通道。模块遇到歧义只能二选一：猜一个，或者 UNRESOLVED 停下。
2. **修复多为"同一模型再生成一次"。** 反馈常是错误码或自由文本，缺少"失败谓词 + 受影响范围 + 可选方向"的结构化可行动反馈（Verification 和 Formation 例外）。
3. **两处 L0/L1 是规则替代语义**：Design Intent 关键词框架、WIC 修复指导按错误文本分派——正是 Standard §5 的 Rule Accumulation。

---

## 3. G2 审计：意图 → 生产 → 部署/下载

### 3.1 代码链路（全部在仓库中接通）

```text
对话/WIC ──Human admit──▶ Work ─▶ Fact 接纳(IRK) ─▶ Guided Design ─▶ Steering ─▶ Planning/Task Contract/PWU
   ─▶ Formation ─▶ 入队 ═轮询═▶ Native Worker/Tool-host ─▶ Verification ─▶ Seal ─▶ Preview ─▶ Guardian
   ──Human 授权──▶ Integration ─▶ Runtime Commit ──Human 点击──▶ 发布 / 下载 / 静态运行 / 云部署
```

除执行段在 worker/tool-host 外，**Formation、Verification、Seal、Preview、Guardian、Delivery 全部运行在 api 进程**（Steering daemon 线程与 Orchestrator 线程，`http.py:423`）。Human 节点 3 个：Work 准入、Candidate 授权、Delivery 操作。

### 3.2 真实贯通证据

| 时间 / 源码 | 最远到达 | 下载/部署 |
| --- | --- | --- |
| 09-10 两个 Delivery 切片 | Runtime Commit → 发布 / 静态运行 / ZIP 下载 | **是**（C3 前） |
| 09-17 "hello Watt" Golden Journey | 意图 → … → 直接下载，**Human 验收 PASS** | **是**（C3 前） |
| 09-27 系统稳定性收口（Tier-0） | Preview / review 边界，无 Delivery | 否 |
| 10-11 G53 / G57 / G60 | Formation 前后停止 | 否 |
| 10-12 G61 普通 G0 | Worker → Git → Verification → Seal → Preview → Guardian（修复后 PASS） | 否：Human 授权从未执行 |
| 10-13 Holdout 复验 | Formation 0/4 | 否 |
| 10-15 本轮资格（隔离，无 DB） | Formation 接纳 1/6 | 否（不含生产链） |

### 3.3 线上环境现实（ECS 只读核对）

| 服务 | 运行源码 |
| --- | --- |
| api（含 Formation/Verification/Guardian/Delivery） | `e13d8258`（本周部署） |
| native-coordinator / native-worker / tool-host / quality-runner | `ee5bd86a`（10-07 canonical） |

- 两者之间 `src/spg/executor*` 与 `infrastructure/executor_runtime` 有 7 个文件、约 390 行差异（Native 合同执行视图、Attempt 观察、工具选择等）。**api 新版本派发给旧 worker 的兼容性没有经过任何真实验证。**
- 线上数据库：47 个 Work Reality 修订、62 个 PWU（24 个仍为 PROPOSED）、19 个 sealed Candidate（最后一个 10-07）、2 条 Delivery Acceptance。最近一次新 Work 是 10-12。

### 3.4 G2 结论

**首个断点是 Formation；但更根本的问题是"全链路从未在当前代码上作为一个整体被持续运行"。** 每个阶段都在隔离环境里各自取得过证据，但没有一个常态化的、当前版本的真实 Golden Journey 把它们串起来。这导致：版本混部无人发现、Human 授权之后的段落（Integration/Runtime Commit/Delivery）自 C3 引入以来零真实执行、修好一段后下一段的问题才暴露（G61 修完 Formation 后才暴露 Guardian lineage）。

---

## 4. G3 审计：失败后的跨模块协作

### 4.1 现有的协作通道

| 失败场景 | 当前去向 | 是否形成闭环 |
| --- | --- | --- |
| Guardian FAIL_REPAIRABLE | Steering 重规划，Finding 写进新步骤目标，开新一轮生产 | **是**（唯一"带失败事实回到生产"的闭环） |
| Provider 可重试错误 | 指数退避，耗尽后问 Human | **是** |
| Multi-PWU 未产出 | 自动重试 ≤3 代（不改计划） | 有界是 |
| Executor Attempt 内失败 | Attempt 内自修 | 局部是 |
| Steering 语义步骤耗尽 / 单 PWU 未产出 / Verification FAIL | BLOCKED → Work 级收敛 → NON_CONVERGING → 问 Human"暂停或调整目标" | 仅经 Human，且问题不具体 |
| **Formation UNRESOLVED / 预算耗尽** | `steering_driver.py:581-589` 直接 BLOCKED，**刻意不记收敛**，不问 Human，无人消费 stop 记录 | **否，死胡同** |
| **Guardian BLOCKED** | 记一次观察后 `return`（`steering_driver.py:832-841`） | **否，死胡同** |
| **ECF / DecisionContext 未就绪** | 直接 BLOCKED（`steering_driver.py:590-597`），不问 Human | **否，死胡同** |
| Formation 内独立 Review 误判 | 1 次反馈后终态，无复核 | 否 |
| Attempt / Maintenance Recovery 服务 | 仅在 bootstrap 工厂和测试中存在，**运行时未接线** | 否 |

`AttentionKind.PRODUCTION_BLOCKED` 已定义从未产出；`OwnerConvergenceDecision.ASK` 从未产出；§14.3 "退回特定上游 Owner" 只存在于文档。

### 4.2 G3 结论

**系统目前的"协作"只有一种形态：把问题交给 Human，并且问的是"要不要暂停/改目标"这种 Human 很难回答的问题。** 它缺少的不是更多的 Self-Refine，而是一个**问题路由能力**：

```text
某 Owner 失败
  → 它知道自己失败在哪（已有：failed predicate / repair family / convergence decision）
  → 判断这个问题该谁解决（缺失）
      ├─ 自己再修一次（已有，有界）
      ├─ 上游语义不足/歧义 → 退回 WIC/IRK 澄清（缺失）
      ├─ 计划不可行 → 退回 Planning 重规划（缺失，仅 Guardian 有）
      ├─ 产物错误 → 带失败事实回 Executor（缺失，仅 Guardian 有）
      ├─ 证据/权限缺失 → 对应 Owner 取证或等待（缺失）
      └─ 真正的价值/权限选择 → 问 Human 一个具体问题 + 选项（部分：IRK 有能力，未被下游复用）
  → 接手 Owner 在原预算/身份/证据约束下继续推进
```

这正是交接文档 §2 所说的"同构关系：Owner 对模型 = Human 对 AI 协作者"，以及"先完成模块改造，再演进为系统"的那个"系统"层。

---

## 5. 实施方案

### 5.1 设计原则（全部来自已批准规范，不新增治理层）

1. **复用、不新建 Coordinator。** 协作路由放在已经拥有 WHAT NEXT 的 Plan Steering（`steering_driver`）内，消费已有的 `WorkConvergenceObservation` 与各 Owner 的 stop/failure 记录；不建全局 Refine Coordinator（Standard §8、§14.2）。
2. **失败要说清楚"缺什么、该谁补"。** 把已有的 `OwnerConvergenceDecision`（含 failure_class / repair_family / ASK 动作）作为跨 Owner 的标准交接物，而不是新造类型。
3. **严格的仍然严格。** 身份、来源、版本、权限、效果许可、证据完整性、独立 Guardian 不放宽；路由只决定"谁接手"，不授予任何权限，不重置任何预算。
4. **每次路由有界且可追溯。** 每条路由消耗 Work 级收敛预算，持久化原因与接手方；同签名无进展照旧停止，并以**具体问题**交 Human。
5. **真实链路驱动。** 每个阶段的完成以"当前版本在 ECS 上的真实 Golden Journey 走到更远"为准，不以单元测试或隔离资格为准。

### 5.2 六条工作流

| 工作流 | 内容 | 涉及项目 / 位置 | 对应目标 |
| --- | --- | --- | --- |
| **W0 三项目发布单元与兼容性门禁** | 把 (Watt, Guardian, ECF) 三个提交作为一个**组合版本**来资格化与部署：一份组合清单（三个 commit + 镜像 + Owner 源码摘要）；部署前跑 `cross_repository` 测试 + 在组合上构造真实 AssuranceRequest / assemble_context 的冒烟；部署脚本校验 Owner 源码摘要而不是仅检查文件存在。把 Guardian C3 线、ECF managed-greenfield 线合入各自 main（或明确声明为当前集成线），消除"资格版本不在 main"的状态 | 三项目 | G2 |
| **W1 全链路基线与常态 Golden Journey** | 统一线上 api + worker/coordinator/tool-host + Owner 源码到同一组合版本；建立当前组合版本的端到端 Golden Journey（意图 → 下载），在 ECS 隔离栈上可重复运行并记录每段结果，包括 ECF 就绪判断与 Guardian 判定；Human 授权/下载用真实 Human 操作（或明确标注的受控授权）跑通 | Watt（Production Environment / Golden）+ Guardian + ECF | G2 |
| **W2 失败交接契约（三项目统一）** | 每个 Owner 失败时给出：失败谓词、影响范围、`failure_class`（模型偏差 / 系统缺陷 / 治理阻断 / 信息不足 / 歧义）、**建议接手方**、可选方向。Watt 内复用 `OwnerConvergenceDecision`。Guardian 侧：把 roadmap 已设计的 INSUFFICIENT / ESCALATE 落地，Finding 增加"由哪个 Owner 补、补什么证据"。ECF 侧：在不足/冲突包中通过已有 `AuthorityContext.owner_for()` 给出负责补齐的 Owner。两者仍不调用 LLM、不放宽判定，只让输出可被路由 | Watt + Guardian + ECF | G1、G3 |
| **W3 Steering 问题路由** | 在 `steering_driver` 中消费 W2 交接物，替换三个死胡同：Formation stop、Guardian BLOCKED、ECF/DecisionContext 未就绪。接手动作：退回 IRK/WIC 澄清（复用 IRK GUIDANCE_REQUIRED + 选项）、Planning 重规划（推广 Guardian FAIL_REPAIRABLE 已有路径）、带失败事实回 Executor、向 ECF 请求重新观察来源或等待、问 Human 具体问题（复用 `PRODUCTION_BLOCKED` Attention）。接线闲置的 Attempt/Maintenance Recovery | Watt（Plan Steering、Human Attention） | G3 |
| **W4 不确定性一等化** | 让关键模块产出 ALTERNATIVE / NEED_INFORMATION / CONFLICT 并被 W3 消费：Formation（歧义交 IRK 澄清，不猜）、Verification（UNVERIFIABLE 说明缺什么证据、谁能补）、WIC（失败降级为部分理解 + 追问）、ECF（NOT_READY → 取证或等待）、Guardian（证据不足 vs 真实缺陷分离） | Watt + Guardian + ECF | G1、G3 |
| **W5 规则替代语义的清理** | Design Intent 关键词框架改由现有 WIC 语义理解提供；WIC 修复指导从错误码关键词改为结构化失败谓词；Formation 契约版本分支收敛。只在真实链路证明需要时推进 | Watt | G1 |

Guardian 与 ECF 保持确定性 Owner 的定位，不引入 LLM：它们在 AI 原生系统里的价值是**可信地说清楚"哪里不成立、缺什么、谁能补"**，让 Watt 的语义 Owner 去推进。

### 5.3 不做什么

- 不新建全局 Coordinator、Adapter、Trace 系统或第二套治理；
- 不为单个 case 加规则，不降低任何门禁，不增加候选/调用预算来换通过率；
- 不同时重构九个模块；模块改造以 W3 路由需要它产出什么为牵引；
- 不把隔离资格或单元测试当作全链路完成。

---

## 6. 关键结论的二次核对

| 结论 | 核对位置 |
| --- | --- |
| Formation stop 直接 BLOCKED 且不记收敛 | `src/spg/application/steering_driver.py:581-589`（注释"cannot consume/reset its budget"） |
| DecisionContext 未就绪直接 BLOCKED | `steering_driver.py:590-597` |
| Guardian 非 FAIL_REPAIRABLE 只记一次观察即返回 | `steering_driver.py:836-841` |
| Attempt/Maintenance Recovery 未接线 | 仅 `bootstrap.py:236-247` 工厂与 `application/__init__.py` 导出，无运行时调用者 |
| `PRODUCTION_BLOCKED`、`ASK` 从未产出 | 仅定义于 `domain/product.py:102`、`domain/refinement_contract.py:39` |
| 线上版本混部 | ECS `docker inspect`：api `e13d8258`，其余 `ee5bd86a` |
| 线上 Guardian 契约不兼容 | 线上 api 容器内 `AssuranceRequest.model_config['extra']=='forbid'` 且无 `evidence_contract_version` 字段；Watt `guardian_assurance.py:407` 无条件传入 |
| 线上 Owner 源码版本 | 文件摘要匹配：Guardian `27bf5691`；ECF `decision_context.py`=`5aa4f883`、`runtime.py`=`8b2c7b68`（同一 blob） |

其余逐条证据保存在三个子审计输出中，本报告引用的 `文件:行号` 来自它们，未全部逐行复核；标注 UNKNOWN 的项（如 Verification AUTO_CONTINUE 分支是否可达、`UNVERIFIABLE_CURRENT` 下游去向）需在 W2/W3 实施前确认。

---

## 7. 执行路线图

以"真实链路走得更远"为里程碑，每一阶段结束都在 ECS 上跑一次当前版本的 Golden Journey。

| 阶段 | 目标 | 主要内容 | 完成判据（真实证据） | 预计 |
| --- | --- | --- | --- | --- |
| **R0 三项目基线**（立即） | 知道三项目组合今天真实能走多远 | 先处置 §0.6 线上不兼容；W0 组合清单与兼容性门禁；统一线上 api/worker/coordinator/tool-host + Guardian/ECF Owner 源码到同一组合版本；在 ECS 隔离栈运行一次组合版本 Golden Journey（普通 G0 + 最简网页），逐段记录停在哪（含 ECF 就绪与 Guardian 判定） | 一份"组合版本端到端断点表"；线上无混部；部署门禁能拦下本次这类契约不兼容 | 3–4 天 |
| **R1 消除死胡同** | 任何失败都有人接手 | W2 交接契约（Formation、Guardian、ECF 先行，Guardian 落地 INSUFFICIENT/ESCALATE）+ W3 路由最小版本：三个死胡同改为"重规划 / 重新取证 / 问 Human 具体问题"；接线 Recovery 服务 | 构造的三类失败（Formation 耗尽、Guardian BLOCKED、ECF 不足）在真实组合栈中各自被接手；Human 收到可回答的具体问题 | 1.5–2 周 |
| **R2 全链路贯通** | 当前组合版本从意图走到下载 | 用 R1 的协作能力跑 Golden Journey 到 Guardian PASS → Human 授权 → Integration → Runtime Commit → 下载/静态运行（ECF 记录 preview/delivery 事实）；修复途中暴露的真实阻断 | 至少 1 个普通需求在当前组合版本上真实走到可下载产物，Human 验收 | 1–2 周 |
| **R3 不确定性一等化** | 歧义被澄清而不是被猜 | W4：Formation/Verification/WIC/ECF/Guardian 产出可路由的不确定性，经路由退回 IRK/WIC 澄清或交 ECF 取证 | 含歧义需求在真实栈中触发澄清，澄清后走通 | 2 周 |
| **R4 稳定性与泛化** | 多需求、可重复 | Tier-0 Golden 集合在当前组合版本重跑；非 Holdout 多样本；独立 Holdout 复验；W5 清理；三项目集成线合入各自 main | Golden 多案例重复通过；错误接纳 0；三项目 main 即可部署的组合 | 2–3 周 |

**R0 是下一步，且 R0 的第一件事是 §0.6 线上不兼容的处置。**

### 7.1 需要 Human 决定的事项

0. **§0.6 线上不兼容的处置**：A 立即回滚 api，或 B 前移对齐 Guardian/ECF 后放行。
1. **路线方向**：是否认可从"单模块 Formation 收敛"转向"三项目协作路由 + 全链路贯通"为主线（Formation 改进并入 R2/R3）。
2. **线上统一部署**（R0）：把 worker/coordinator/tool-host 与 Guardian/ECF Owner 源码一并升级到同一组合版本；或先在独立隔离栈上做 R0。
3. **Guardian / ECF 分支治理**：C3 Guardian 线与 managed-greenfield ECF 线是否合入各自 main，作为三项目的正式集成线。
4. **Human 节点**：R2 中 Candidate 授权与 Delivery 由您本人操作，还是允许受控授权并明确标注。
5. **预算**：R0–R2 预计真实模型消耗约 3–5M token，是否授权。
6. **C3 定位**：C3 原 Closure 契约要求的独立 Holdout 是否推迟到 R4 统一进行。
