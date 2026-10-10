# C3 Option A — Semantic Formation Contract Calibration Implementation

**有界实现及受控资格完成；C3 PARTIAL。Option B 未实施。**

依据 Human / Architecture Lead 对 Option A 的批准，从审查提交
`76dfaa976762e5776009e2d66eb3d1cb6fb8cfad` 及原应用
`e0df8196cb51480f542af13b40cfa77fca6b6a6e` 继续原 C3 分支。
本报告是新的实现证据，不替换旧报告、历史 Candidate 或 Work。

## 1. Exact identity 与资格边界

| 项目 | 最终受测身份 |
| --- | --- |
| Watt source | `a91442c21ed487b10d8dc38023b0807787a29648` |
| Watt tree | `80778b67a7147902d10e9f14d669150e6df6d809` |
| Guardian source | `76c1e87a1b29d151f4ed949748e3298f2169c5b1` |
| Guardian tree | `6066a6d6b8d91bec610021409ab320309ed0e437` |
| ECF unchanged source | `5aa4f8833c359c15bd059eda5972aa3915bcc18c` |
| ECF tree | `878d39d9c259272bb05f2e02bdf9d60c22fad460` |
| Actual image | `sha256:90f2cd847ad891fda6ca95b5736c84b680c9d58bd6a3203bf0ea31c970da0f16` |
| Isolated PG migration | `20261007_72` |
| Branch, both changed repositories | `codex/c3-open-semantic-obligation-convergence` |

身份来自 Git archive、构建输入散列、Docker 实际 image/container 观测和
安装后逐文件导入核对，不由请求配置代替。源码和测试未覆盖到旧运行镜像。
ECF 不修改；unsupported ECF 快照仅用于已有接口拒绝回归。

证据等级：**OBSERVED** 为实际离线谓词、Git、Docker、PG 和收据观测；
**CONTROLLED** 为合成语义候选及独立 Owner 记录构成的回归；
**REVIEW** 为工程分析与建议；未实施的真实模型、端到端 G0、独立 Holdout
及其泛化效果均为 **NOT QUALIFIED / UNKNOWN**。受控 Semantic Review 的
布尔值不代表真实模型判断已合格，受控 Guardian 结果也不代表现网 Assurance。

## 2. 已证实原因与最小修复

原 57 条 Route 既包含真实候选错误，也暴露契约粒度及消费接线不足。
来源出现不等于语义完整履行；不能删去重复、UNRESOLVED 或保留路由后追认成功。

| 边界 | 原因 | 当前实现 |
| --- | --- | --- |
| 组件身份 | `(source_ref, capability)` 无法表示同来源、同能力的不同组件；历史 8/9 仍确为相同组件重复 | SHA256 绑定库存、精确 source_ref、完整 component_basis；Route 再绑定 capability。rationale 不产生新身份 |
| 定位与完整性 | 模型协议未明确端点；原 57 项都截去最后非空白字符，模型选择原因 UNKNOWN | Unicode code point `[start,end)`、StrictInt、精确原文切片及全部非空白覆盖；locator 仅定位既有唯一完整引文，绝不扩展截断引文 |
| 组件处置 | 来源整体归属不足以表达合法内容、背景与后续生命周期混合 | 明确每个组件的来源、Owner/Phase/Method/Gate；新混合表示要求逐组件独立 Review；相同物理贡献的矛盾处置拒绝 |
| 背景保留 | 不能让保留路由消除当前义务；原 8 条保留并非都合法背景 | 部分背景必须与独立当前/生命周期组件并存、不重叠当前 Fact、不携带义务的 linked Fact；消费时再验证完整计划与 Review，并要求当前 Owner 证据 |
| UNRESOLVED | 混合来源存在未决成分，不能隐藏成 PASS | 保留明确未决成分；最终存在未决时沿用整个 Formation stop / Runtime admission BLOCKED 路径，不增加预算或要求 Human 改目标 |
| Qualified Scope | exclusive 限定及 Scope 描述不能被丢弃或当作未知普通字段 | 仅复用有精确安全路径值、严格 `exclusive: true` 的现有 Scope；原 Fact fingerprint 保留限定、值和 Scope；任意其他限定仍未决/拒绝 |
| 排除来源 | Work exclusion 包装与原 Production Intent / negative Clause 的对应不能凭 wrapper 猜测 | 绑定精确 Production exclusion、原 Human 当前否定 Clause、实际同能力路由及组件 Review；不生成缺失 typed effect |
| 否定义务证据 | 已接纳否定 Scope Fact 不能当 HTML 内容，也不能把排除值当允许路径 | 权限组件绑定原 Clause 与相同实际 Gate；文件组件绑定原 Clause 的当前 Git scope、Task 允许目标与真实 Diff；明确禁止当前允许目标时拒绝 |
| 内容消费 | 混合 Acceptance 的当前组件需消费原子事实证明，原始 checker 行并非绑定后的证据 | 消费完成的精确 Fact 身份、Candidate revision/tree 与逐组件证据；缺失/循环依赖失败，未来 Seal 仍由 Candidate Owner 负责 |
| 多组件结果匹配 | 相同来源的结果不能仅按 source_ref 匹配 | 使用 exact binding fingerprint / component identity 匹配派生内容检查及消费结果 |
| 反馈 | 首个错误不足以提供本次候选可评估失败集合 | 同一候选有界结构化集合：稳定错误码、source ordinal、route ordinal、component ID；最多 64 项及额外数量；Review、实际 Owner evidence、Assurance 标明 NOT_EVALUABLE |

source ordinal 由反馈中的完整 inventory fingerprint 固定，内部 source_ref
仍由原库存绑定。反馈不含真实引文、敏感 Prompt 或隐藏推理。
无法独立评估的后续执行不伪造结果。原值、顺序、Scope、Qualifier、Authority、
来源版本与 source_record 身份由原 Fact / IR / Work Reality 持续持有。

## 3. 实际代码与跨 Owner 范围

Watt 复用现有模块：

- `domain/governed_obligation.py`：组件身份、StrictInt span、逐组件 Review、严格限定 Scope helper；旧 Review 不序列化新增 null 字段，旧收据形状保留。
- `application/governed_obligations.py`：组件/来源/归属校验、原 Fact→Clause→Gate 对应、有界反馈、持久收据与恢复；未决保持原 stop。
- `providers/fulfillment_candidate.py`：准确定位说明、独立组件 Review 输入与输出契约；compact Formation wire 不改。
- `providers/managed_context_fulfillment.py`：精确绑定匹配、原子内容证据、限定与否定 Git scope、合法背景消费。
- `providers/protected_context_verifier.py`：派生组件检查键与精确来源证据匹配；原静态 witness 要求不被全局豁免。

Guardian 的对应窄范围修改为 `src/guardian/runtime.py` 和
`docs/04_integration/watt-software-assurance-v1.md`：独立读取原 Work、PWU、
Formation/Review 观察、Verification、Native、Candidate 记录，校验版本、
组件、归属、原 Clause、权限、Task scope 与 current evidence。
复制的 Review、Watt 的覆盖声明或日志缺失均不能替代这些证据。
既有 v1 请求及 `governed-obligation-v2` 证据入口保留；未改变 Assurance
权限或 Gate/Finding 核心语义，不增加 Owner、状态机或 Refine Coordinator。

源码提交：Watt `62d2ebf`、`a91442c`；Guardian `79b53b3`、`76c1e87`。
第二组修复来自最终核对发现的同类文件排除消费缺口；第一镜像和全部历史
资格保留，但不用于冒充第二组修订已合格。

## 4. 最终修订上的实际回归

| 资格 | 结果 | 原始收据 |
| --- | --- | --- |
| Watt C3/C1 相关模型边界、来源、容量、停止、Context、Adapter 与新增组件回归 | **231/231 PASS，0 skip** | [receipt](receipts/final-image/watt-continuation-receipt.json) / log / JUnit |
| Guardian 独立 Owner evidence、当前/未来边界、C1 continuity 与联合组件契约 | **163/163 PASS，0 skip** | [receipt](receipts/final-image/guardian-receipt.json) / log / JUnit |
| 独立 PostgreSQL Formation/Review 收据、预算恢复、stop 投影与真实 Git/Verification/Candidate 的受控集成 | **5/5 PASS，0 skip** | [receipt](receipts/postgresql/receipt.json) / log / JUnit |
| 原始 26 项来源 / 57 条 Route 的未修改 Candidate | **REJECTED AS REQUIRED** | [negative replay](receipts/retained-negative/historical-replay.json) / [controller](receipts/retained-negative/controller.json) |

新增 Watt 40 项、Guardian 28 项为上述相关总数的子集，不能重复相加。
定向回归涵盖同能力多组件、真正重复/矛盾/遗漏、末字符截断、完整限定、
混合当前/背景/Seal、未决停止、原权限 Clause、缺失 typed effects、文件
排除、错来源/版本/能力、非法压缩、缺失原子证明/Review/Seal/Native Gate、
注入未授权 grant 与独立 Owner 记录不匹配。真实隔离 Git 文件结果也包括
错误段落、空 Diff、越界文档/新文件等负例。

PG 使用新生成资格凭据、独立 internal Docker network、数据库及持久卷，
不访问原业务数据库。测试中的 Work/Owner 数据是明确的隔离 Fixture，
未创建真实 G0、未调用模型、未产生 Human Integration/Acceptance。
精确镜像安装包而非文件覆盖；Guardian 测试输入来自同一 Git archive。

现有一反馈、两 Formation Candidate、最多四逻辑 Formation/Review 请求，
Provider/timeout/transport/token 配置均保留。受控例证明：一次反馈后合法
组件可被接纳；无法校验或包含 UNRESOLVED 时如实停止；PG 重放不会创建
重复模型请求。此结论不推断真实模型第二次输出一定收敛。

## 5. 原失败与实施过程中失败均保留

历史 Work `048189aa-0613-5307-b6f4-c430e7977f93` 及 Reality
`332a3a38-8719-580c-a1a2-c331ae14a5ae` 不修改。
最终 replay 前后输入 SHA256 相同：Candidate
`e9020a908ba354c2e12ab4db297b32b7d17041fd12e4180a740f39d9fb42c9b5`。
它仍首先失败 `OBLIGATION_PROJECTION_DUPLICATE_ROUTE`，同时反馈暴露
覆盖、处置、来源与 Owner 失败；Independent Review / actual evidence /
Assurance 为 NOT_EVALUABLE。没有把修补副本当成真实成功。

实施期间发现并保留的失败：

- Dev1 严格支持校验误伤不晋升的 UNRESOLVED，修复为未决不要求不存在的晋升证明；旧 truthful-stop 回归恢复。
- 实际 Git 内容回归暴露 raw checker 行与已绑定原子 Fact 结果的消费错位，按上节修复；未放宽内容要求。
- Dev PG 第一次 4 PASS/1 FAIL 是测试将恢复时重新计算的 `elapsed_seconds` 当作恒定身份；修正断言，其余收据/身份/预算仍逐字段相等。
- Guardian 负例第一次复用同 request/store 命中已密封的幂等结果；改用独立 store 检验损坏记录，不改变 Runtime 幂等语义。
- Dev8 第一次错误 Python 路径导致容器未执行；随后两个失败是 Fixture 将 WORK_CONTEXT 错转成执行 Gate，修正 Fixture，源代码门禁保留。
- 早期 replay 仅输出目录权限失败；另一次 final 控制器仍引用前一镜像。两项均保留原始收据，分别修正隔离输出目录和镜像选择；只有 final2 的确切 a91442c replay 计入最终资格。
- 本机长路径 prepare/upload 及异步归档收据尚未完成时的复制失败属于取证工具准备问题，不计入 Runtime 或 Candidate 成功。

Development overlay 结果仅用于修复定位；不替代最终新镜像资格。
原始失败日志、第一次 PG 失败及旧镜像收据见 `receipts/dev-*`、
`receipts/prior-source-*`、`receipts/controller-wrong-replay-image`。

## 6. 消耗、恢复与剩余事项

本轮实际模型调用 **0**，无 Provider 请求/Usage 收据；真实模型 token 消耗
不以 Fixture 用量冒充。历史 3722 output token 属于旧 reasoning=none 请求，
不属于本轮。新逐组件 Review 的实际模型输出成本、准确性和收敛率 UNKNOWN。

两次必要构建分别 16.9695s、17.4473s；最终 Watt 8.5638s、Guardian 14.1843s、
PG 22.5837s。完整 Dev 执行、归档和构建输入散列另见收据；未取得的累计
CPU、内存、模型成本、计费数值 UNKNOWN，不把各次测试数相加当覆盖规模。
最终镜像保存 154.0378s、293170097 bytes；它是恢复材料，不计作额外运行资格。

跨电脑恢复位置：

- Git：Watt 与 Guardian 同名 C3 分支；本目录公开脱敏收据、控制器与 manifest 随提交持久化。
- ECS：`/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010`，`final-inputs-2` 为精确 Git archive，`final-image-2/evidence` 为实际构建/测试身份，`owner-pg-final-2` 为隔离 PG 恢复材料，`retained-replay-final2` 为不可变负例收据。
- 精确 Docker 镜像保存于 `image-recovery-final/exact-image.tar.gz`；SHA256、实际 image ID、权限及保存时间见 [recovery receipt](receipts/recovery/receipt.json)。恢复测试和站外备份明确 NOT_PERFORMED，不声称已完成灾备资格。
- 原始私有 Candidate 仍在既有 `capacity-representation-20261009/semantic-contract-calibration-1-run2/private/read-only-original-candidate.json`；公开 Git 只保存身份与谓词，不复制私有候选/对话/凭据。

**下一项必要行动：Architecture Lead 审查此次契约资格与限定真实模型验证建议。**
建议见 [submission](architecture-lead-submission.md)。未执行真实模型、G0 或
Holdout；未更改生产 main、正式服务、历史事实或 Human/Quality Ledger。
真实模型对校准契约的输出及独立语义审查仍待资格，原 C3 端到端和封存
Holdout 条件未被豁免。**不得据此声明 C3 CLOSED、N1 CLOSED 或 C4 完成。**
