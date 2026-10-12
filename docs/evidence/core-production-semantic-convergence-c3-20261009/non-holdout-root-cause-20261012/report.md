# C3 Holdout 根因定位：非 Holdout 开发对照

2026-10-12。范围：责任归属与只读对照；没有修复、模型调用、新 Work、Holdout 重跑或条件调整。**C3 仍为 PARTIAL，Holdout 仍为 1/4 live PASS、3/4 FAIL。**

## 结论

**两类终态拒绝均可在已知开发场景复现，不是 Holdout 专有问题。** 在冻结镜像中，未经修改的历史开发模型 Wire 返回与历史相同的来源覆盖和组件处置拒绝。另运行了 24 项既有开发正负对照，全部通过。

直接失败边界是现有 `WORK_FULFILLMENT_PROJECTION` 的 Formation / 组件消费与接纳契约，发生在独立 Semantic Review 前。当前已证明真实候选未满足该契约，尚未证明合法结果不能被表达或被 Validator 错误拒绝。**一般性不足是实际模型候选在既有有界反馈内未稳定收敛；不能据此直接认定需要修改 Validator、Guardian 或新增 Owner。**

| 现象 | 非 Holdout 对照 | 责任判断与证据边界 |
| --- | --- | --- |
| `OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST` | ordinary34：19 来源，两次原始候选均 25 Route；当前冻结代码分别识别 6、7 个来源的字符覆盖缺口。包含一个标点字符缺口，另有引文部分及派生 Work 文本前缀未覆盖 | Formation 的来源组件提案与原文跨度覆盖不符合现行契约；组件消费者执行非空白字符覆盖检查。一个字符缺口不等于已证明业务义务缺失。现行字符覆盖是否对合法语义产生错误拒绝，尚未建立反例 |
| `OBLIGATION_PROJECTION_CONFLICTING_DISPOSITION` | ordinary41：23 来源；第二次原始候选 24 Route，同一来源、同一跨度及引文同时提交 `UNRESOLVED` 与 `GIT_DIFF_SCOPE`，当前代码仍拒绝 | Formation 对同一物理组件提出不一致处置；不能归因为不支持多个组件。24 项对照证明不同组件可合法使用相同能力，以及背景、当前要求与未来阶段可分别处置 |
| 第一候选 Wire 语法失败 | ordinary41 首次原始 Wire 仍为 `OBLIGATION_FORMATION_WIRE_JSON_INVALID` | Wire 解码边界。部分原始 Route 只用于诊断观察，未把截取的 JSON、修补候选或删减结果当作有效 Candidate |
| 反馈之后仍失败 | 两个开发场景的第二次请求均与前一次反馈文本、收据身份匹配；Holdout 的独立只读收据也匹配 | 不是已证实的反馈丢失或身份漂移。反馈确实送入下一逻辑请求，不代表模型正确消费语义。实际 HTTP 请求体的独立捕获仍 UNKNOWN |

## 执行身份与方法

- 分支：`codex/c3-open-semantic-obligation-convergence`；执行前证据 HEAD `8e3464a29138776a08dd405435927016ad116d38`。
- Watt 源码 `01446afc7cccb03f99e8e6febbe4cfe9ed8388e4`；Tree `daa0a41b756755c7f88f347ee18c68ecd99273b0`。
- Guardian `0d7aca954588c8ad3883dbedb730e59dc1d7b867`；ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c`。
- 实际 Docker Image `sha256:8e403fd29c33d4f5ed9aac1b59087e4943f4a05aac78f20071b55ed91624ce55`，在容器启动前从 Docker 事实读取；未构建新镜像、覆盖应用源码或替换已安装 Owner。

两个诊断容器均为 network=none、只读根目录、UID 10001、cap-drop=ALL、no-new-privileges、1 CPU / 1 GiB 上限。没有提供凭据或业务数据库连接。既有测试从确切源码 `git archive` 导出，仅挂载测试，没有应用源码覆盖。

1. [既有定向对照](controls-receipt.json)：24/24 PASS，0 failure/error/skip，11.112 秒。覆盖合法多组件、精确半开跨度、背景与当前/未来处置、UNRESOLVED 停止、来源角色、覆盖反馈、一次反馈与恢复重放、矛盾组件拒绝。Provider 为受控测试结果，**不算真实模型收敛资格**。
2. [原始开发 Wire 对照](development-original-wire-comparison.json)：使用开发 ordinary34、ordinary41 的已持久化库存、原始候选、原请求前提与反馈。调用冻结 Owner 的解码、既有唯一引文定位及接纳前校验。未替换原请求的历史契约标记：source-role v3、typed prerequisites v11。四次原始候选重放全部保持原失败类别。该结果证明当前代码仍会拒绝这些历史输出，**不等于按当前新请求配置重新生成候选的结果**。
3. Holdout 对照仅使用独立 Reviewer 提供的 [结构收据](safe-structural-analysis.json) 和 [上游责任收据](safe-upstream-responsibility.json)。执行者不读取封存输入、Oracle、原始 Candidate 或成功 G0 的人工修复上下文来调优。

## Holdout 与开发场景的结构差异

独立只读观察：opaque0 的最终缺口为一个 IR_CONSTRAINT 内部非空白标点；opaque1、opaque2 分别存在 4、1 组同来源、同跨度及引文的冲突，涉及 `RETAIN_CONTEXT` 与执行能力。开发 ordinary34 包含同类单标点缺口，也有其他文本缺口；ordinary41 使用 `UNRESOLVED` 与执行能力冲突。**具体来源与处置不同，触发的是同一组通用覆盖/组件一致性谓词。**

该独立收据记录 Holdout 四个库存的来源数量分别为 18、19、25、16；开发对照为 19、23。数量、来源类别或 Route 数不同，不能单独证明复杂度根因。没有观察到不同跨度的合法组件因本次冲突谓词被误拒绝。

Holdout 八次 Formation 的 Provider 均记录 completed，终态文本与流式文本一致；输出 Token 均低于 16384，传输重发为 0。opaque0 首次 JSON 失败是完整 JSON 后的额外数据，不是已证实的容量截断。不能将本次失败归入此前已解决的 Provider 容量阻断。

上游收据证明封存输入身份匹配、WIC 到库存的 Clause/Item/Fact 与 provenance 保留，所有输入非空白文字有原始引文覆盖。**文本与版本保留不能替代 Input → WIC 的语义正确性证明**：当前/未来、背景/必需、否定性及路径意义的独立语义忠实度仍 UNKNOWN。也没有证明某个精确失败库存必然缺少合法 Owner 证明方法。

## 分层归属

| 分类 | 本轮结论 |
| --- | --- |
| A：模型映射偏差 | 已观察到：原始候选在跨度覆盖及同一组件的处置上不符合现行协议；真实的一次反馈后仍有此类偏差。不是偶然只发生在 Holdout |
| B：Contract 覆盖不足 / Validator 错拒合法结果 | **未证实**。受控对照能表达若干合法同类结构；这不能证明三个精确 Holdout 库存都存在完整合法绑定。严格逐字符覆盖与语义覆盖的关系属于待证明的契约边界，不能自行忽略标点或扩大跨度 |
| C：AI 原生模块语义消费能力不足 | **已证实限定范围的真实收敛不足**：Formation / 反馈模块未在既有预算内形成合格输出；其 deeper cause 是候选生成、语义组件划分，还是契约表达障碍，尚不能完全分开。受控修复成功不能代替真实模型能力证明 |
| 治理拒绝与证据前提 | 原文跨度完整性与同组件处置一致性门禁实际执行；没有来源漂移、预算重置或伪造证据的通过。本次失败尚未到独立 Review、下游 Verification 或 Guardian，不应归因于这些未调用 Owner |

这里的 C 是用户本轮“语义消费能力不足”分类，不是此前执行原则中的“Governance Blocker”缩写。A 与 C 并非互斥：错误候选是直接现象，模块未能有界吸收该偏差是资格能力表现；B 需要另外证明，不能用失败次数替代证据。

代码定位：[`validate_projection_components`](../../../../src/spg/application/governed_obligations.py#L1215)、[`validate_projection_candidate`](../../../../src/spg/application/governed_obligations.py#L1350)、既有结构反馈与 Wire 观察属于同一当前 Owner。它们检查表示一致性；在被拒绝的提案上没有独立语义判定，因此不存在可据本次结果归责的 Review 错误放行。

## 停止点、成本与恢复

本轮定位与对照已完成，**不进行修复**。下一项有证据价值的工作是仅在非 Holdout 库存上证明完整合法组件绑定与其语义一致性，从而判定当前拒绝是可恢复生成偏差还是合法表达受阻；本报告不启动该工程改动、模型重试或新的独立资格。

本轮新增真实模型调用 0、Token 0；未新增 Work、Review、业务 Owner 写入。定向测试 11.112 秒，原始 Wire 对照容器 4.130 秒。费用与 CPU/峰值内存实测 UNKNOWN；资源限制不是实际用量。初始宿主诊断脚本因 Python 3.6 不支持 `text=True` 停在准备阶段，保留原件，执行副本仅改为等价 `universal_newlines=True`；这不是应用修复或资格失败重跑。

全部新诊断恢复位置：`/data/watt/c3-semantic-convergence-20261009/non-holdout-cause-control-20261012`。受限 `private/` 保留开发原始库存/Wire/诊断日志，公开 `evidence/` 为本目录的脱敏结果；脚本与测试输入归档保留供恢复。独立 Holdout 只读收据另在其独立恢复目录保留，并发布经过允许的四个脱敏文件；原 Holdout 91 个文件前后 hash 一致。

应用代码、测试源码、生产环境、历史 Work/Candidate/Human 决策与原始 Holdout 保持不变；预先存在的未提交文件另行保留。本次只提交诊断文档和脱敏证据。文件级 hash 见 [证据清单](manifest.json)。
