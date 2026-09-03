# Production Orchestration Lite

## 1. 文档状态与目的

**MVP-ORCH-1：CLOSED / PASS**

Production Orchestration Lite 是 Watt 在 MVP 中对既有受治理生产流程的轻量自动推进能力。它不定义第二套生产状态机，也不改变既有 Runtime、Completion、Verification、Candidate、Repository Integration 或 Runtime Commit 语义；它只在当前事实允许时，调用现有应用服务执行下一项合法的非 Human 动作。

本文正式说明以下已经确立的产品与架构原则：

- Human-in-the-loop 不等于 Human-as-the-loop；
- Watt 可以自动推进到哪里、必须在哪里停止；
- Human Attention 负责什么、不负责什么；
- 当前 MVP 方案与未来 Managed Production 方向的区别。

本文细化但不替代 [SPG FVS-1 实现契约](spg-fvs-1-implementation-contract.md)、[MVP 架构](mvp-architecture.md) 与 [MVP 范围校准](../roadmap/mvp-scope-calibration.md)。Architecture Baseline 保持 `v0.1`。

## 2. 核心产品原则

### 2.1 Human-in-the-loop 不等于 Human-as-the-loop

Human-in-the-loop 的含义是 Human 保留必要的意图、判断与授权责任，而不是由 Human 手工触发每一个内部状态转换。

```text
Human defines intent.
AI amplifies capability.
System ensures trust.
```

在 Human 已经给出明确意图、批准受治理 Work Draft，并且下一步动作被现有契约明确允许时，Watt 应当继续推进，而不是等待 Human 点击一次次 `Advance`。Human 的职责是行使不能被自动推断的 Authority、处理真实异常与歧义，而不是充当生产循环的调度器。

因此：

```text
Human-in-the-loop
!=
Human-as-the-loop
```

Manual single-step Advance 仍可作为技术或操作诊断的有限后备入口，但不是正常产品路径。Web UI 通过查询与轮询观察服务端进展，不通过轮询制造生产转换，也不在浏览器中建立另一套生产状态机。

### 2.2 Controlled Autonomy

自动推进是受契约、Authority 与当前 Production Reality 限制的 Controlled Autonomy，不是无限自治。Watt 只能执行已经存在且当前合法的能力，不能因为能够调用 Executor 就获得验证、接受、集成或提交 Authority。

以下区分始终成立：

```text
Provider SUCCESS
!=
Observed Production Reality
!=
PWU PRODUCED
!=
Verification PASS
!=
PWU SATISFIED
!=
Candidate Authorized
!=
Trusted Baseline
```

Orchestrator 不得跳过这些层次，也不得从 Provider 报告、Human 意愿或历史成功中制造 Production Truth。

## 3. Watt 的自动推进模型

### 3.1 启动条件

MVP 的正常自动路径从 **Human Work Draft Approval** 之后开始。批准前，Work 仍处于需要 Human 决策的治理边界，Watt 不得自行把 Draft 转换为已获执行 Authority 的生产任务。

批准后，只要 Work 的最新投影是普通的 `READY` 或 `RUNNING`，Watt 可以启动一次有限的自动推进。每次推进都遵循：

```text
读取最新 Work / Runtime Reality
↓
选择当前唯一且合法的下一项非 Human 动作
↓
通过既有应用服务提交至多一个转换
↓
重新读取已提交的 Reality
↓
继续，或在边界处停止
```

Orchestrator 不预先生成一串必须执行的动作，不持有独立的权威生产状态，也不绕过既有服务直接操作 Provider、数据库或 Git。

### 3.2 当前可自动推进的范围

在现有 Work 和 Runtime 契约允许的情况下，Watt 可串联已有能力，包括：

- 创建初始 Execution Attempt；
- 组装 Context Package Lite 并准备隔离 Workspace；
- 通过既有 Executor 边界执行并独立观察生产事实；
- 执行 Completion Evaluation；
- 创建非权威 Proposed Repository Snapshot；
- 执行既定 Verification obligations 并判断 Production Admissibility；
- 在资格成立时 Seal Candidate；
- 在精确 Human Candidate Authorization 已存在后，执行 Repository Integration；
- 在 Integration 已收敛且全部资格仍成立时执行 Runtime Commit、推进 Trusted Baseline，并完成 Work 投影。

这只是对既有合法转换的自动串联，不授予新的 Domain Authority。尤其是 Candidate Authorization 不会被推断或自动生成。

### 3.3 强制停止边界

Watt 必须在以下任一条件出现时停止当前自动激活：

- Work 处于 `DRAFT`、`NEEDS_REFINEMENT` 或 `AWAITING_APPROVAL`；
- 需要 Human Attention；
- Production Reality 为 `BLOCKED`；
- Work 已 `COMPLETED`；
- 无法唯一、安全地确定下一项合法动作；
- 执行动作后权威 Reality 没有变化；
- 达到配置的有限转换上限；
- 基础设施错误或应用关闭。

停止不是失败的同义词。它可能表示正常 Authority Gate、真实阻塞、终态、安全边界或需要诊断的异常。系统必须保留已发生的事实，并向 Human/Operator 呈现原因，而不是盲目循环、重放或把停止改写成成功。

### 3.4 并发与重启边界

当前实现使用单进程、进程内的临时 daemon 调度，并以 process-local per-Work guard 避免明显的同一 Work 重复调度。该 guard 不是分布式锁，也不提供跨进程 exactly-once 保证。

应用启动时只能重新调度最新投影仍允许普通 `READY` / `RUNNING` 确定性推进的 Work。既有 Dispatch 等持久事实会阻止自动 Provider redispatch；重启不意味着 Provider retry、Provider Resume、Attempt recovery 或 Human Authority 的补造。

## 4. Human Attention 的职责

Human Attention 是“当前需要 Human 介入”的产品投影，不是把所有内部工作交还给 Human。它应集中呈现 Watt 缺少合法自主 Authority，或无法安全确定下一项生产动作的情形。

### 4.1 MVP 中的明确 Human Authority 点

当前 MVP 至少保留两个不可自动化的 Human Authority 点：

1. **Work Draft Approval**：Human 决定是否接纳已整理的目标、Engineering Scope、Artifact Target、约束与生产契约，使其获得执行 Authority。
2. **Exact Candidate Authorization**：Human 针对一个不可变的、精确指纹绑定的 sealed Candidate，决定是否授权其声明范围内的 Repository Integration。

第二项授权必须绑定精确 Candidate、目标 repository/ref、expected source revision 与 proposed revision。`approve latest` 或对后续变化自动沿用授权均无效。

### 4.2 Human Attention 处理的事项

除上述 Authority Gate 外，Human Attention 用于处理：

- 目标、范围、约束或 Artifact Target 需要补充或修正；
- 下一动作存在实质歧义，系统无法安全裁决；
- Completion、Verification 或 Production Admissibility 未满足；
- Provider Reality 与独立 Production Reality 不一致；
- `UNKNOWN`、`DIVERGED`、`STALE`、`BLOCKED` 或 Recovery Barrier 需要分类、判断或授权；
- 达到有限自动转换上限或遇到基础设施故障，需要 Operator 检查。

Human Attention 的输出可以是批准、拒绝、要求 refinement、修订契约、选择受治理的恢复路径或停止工作。具体动作仍必须通过对应的应用与治理契约执行。

### 4.3 Human Attention 不拥有的能力

Human 不能通过一个注意力动作：

- 把 Provider `SUCCESS` 变成 Production Truth；
- 制造缺失的 Artifact、Completion 或 Verification Evidence；
- 把 Verification `FAIL` 改写为 `PASS`；
- 让过期 Evidence 重新有效；
- 绕过 Candidate、Repository Integration 或 Runtime Commit；
- 直接修改数据库或权威 Git ref 来伪造收敛；
- 把历史 Attempt、Recovery Assessment 或失败事实改写为成功。

Human Authority 改变治理许可，不改变工程事实。

## 5. MVP 当前方案

Production Orchestration Lite 在 MVP 中刻意保持轻量：

| 方面 | 当前 MVP 方案 |
| --- | --- |
| 驱动方式 | 单进程、进程内、临时 daemon 调度 |
| 权威状态 | 复用现有 Work 与 Runtime 持久事实；无第二状态机 |
| 推进粒度 | 每次至多一个当前合法转换，提交后重新读取 Reality |
| 自动范围 | `READY` / `RUNNING` 的普通确定性推进 |
| Human Gate | Work Draft Approval 与 exact Candidate Authorization 必须保留 |
| 停止策略 | Human Attention、BLOCKED、COMPLETED、歧义、无变化、上限、故障或关闭即停 |
| 重复保护 | process-local per-Work guard |
| 重启行为 | 仅重新调度安全 eligible Work；不自动 redispatch 或 recovery |
| UI 角色 | 展示 Work、Attention、Authority 与结果；轮询只观察 |
| 手工推进 | 非主路径，仅作为有限技术/Operator 后备 |

默认自动转换次数是有限的配置值，其作用是阻止失控循环，不是新的业务终态或长期调度策略。

## 6. 未来演进方向

未来方向是 [Managed Production and Human Attention](future-capabilities.md#managed-production-and-human-attention)：在契约、Verification、Recovery、Authority policy 和 Production State 足够成熟后，让 Human 的参与进一步集中在 Authority boundary、高风险决策、目标或架构变更、实质歧义、无法解决的 Verification 冲突与风险接受上。

该方向可以追求更长时间、跨中断或多项目的安全生产，但它不是当前 MVP 的能力承诺。以下能力保持未来方向或 `DEFERRED_BY_MVP`：

- durable orchestration 与跨进程恢复；
- distributed scheduling、Worker Fleet 或 message broker；
- 通用 Provider retry / Resume；
- 基于 policy/risk 的自动 Candidate integration；
- 多项目并发管理与 portfolio-level attention；
- 更完整的 Guardian、ECF、Policy 或风险治理能力。

未来演进必须继续复用既有 Authority 与 Production Truth 边界。更强的调度、恢复或智能不能把 `Execution Capability` 扩张成 side-effect Authority，也不能以减少 Human Attention 为理由降低 Verification 或信任要求。

## 7. 架构不变量

Production Orchestration Lite 必须持续满足：

1. Orchestrator 是既有受治理转换的 driver，不是第二套生产状态机。
2. 每次只执行一个当前合法动作，并在提交后重新读取 Reality。
3. Human Work Draft Approval 与 exact Candidate Authorization 不得被推断或自动生成。
4. Human Attention 只在缺少合法自主 Authority 或无法安全继续时请求。
5. Provider Report 与独立 Production Observation 始终分离。
6. Completion、Verification、Satisfaction、Candidate、Integration 与 Runtime Commit 不得折叠。
7. BLOCKED、UNKNOWN、DIVERGED、STALE 或无变化不得触发盲目推进。
8. 重启不得隐式产生 Provider retry、Resume、Recovery 或新 Authority。
9. 有限步数与 process-local guard 是安全护栏，不是分布式可靠性声明。
10. History Is Appended, Not Rewritten；停止与失败的历史事实必须保留。

## 8. 已验证的产品含义

MVP-ORCH-1 的真实 dogfood 已证明 Watt 可以在 **0 次 manual Advance** 的情况下，从 Draft Approval 后自动推进到真实 Verification 边界，并在 Verification `FAIL` 时停止。该次运行中 Provider 报告 `SUCCESS`，独立观察发现了受准入的 Artifact，Completion 为 `PRODUCED`，但 Verification Contract 与 Artifact Target 不一致，因此没有形成 Candidate、Authorization、Integration 或 Runtime Commit。

这同时证明了两点：

- 自动编排能够到达并尊重真实治理边界；
- 自动化不会修复薄弱的 Production Contract，只会更快地暴露或放大它。

因此，Production Orchestration Lite 的成功标准不是“尽可能不停地运行”，而是：在 Authority 与契约允许时无需 Human 充当循环；在事实、信任或 Authority 不足时准确停止并请求最少必要的 Human Attention。
