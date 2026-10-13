# AI Native Integrated Hardening — execution checkpoint

2026-10-13，Asia/Shanghai。Human 已批准 Integrated Hardening Program v1.0；本记录随实际实施更新，不以计划代替资格。

## 起点与权限

- 原 C3 分支 `codex/c3-open-semantic-obligation-convergence`，证据 HEAD `039212a17b811e3087c35bec0b9154309125d727`。
- 应用 `f52d39965826ba2e9ddcdba44c85e79bf5c43fc0`；最近资格镜像 `sha256:24d9f809ad3cd6b98d68948020fccd3997c09ee947f9cb5acd57e48abb44e5b1`。
- Guardian `0d7aca954588c8ad3883dbedb730e59dc1d7b867`；ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c`。
- Trace 独立分支最新证据 `6aada04010631b6833b9b9487addb11f9ec36f6b`，实测源码 `e207b92ce7b6a670bd48e4a58639593447262637`。其入口修复、新 Native 单事件成功与历史失败分别保留，不自动合并或据此宣告整体 Level 3。
- 保留原未提交取证文件、历史 Work/Candidate/Human Decision 和全部旧失败。正式生产、canonical main、凭据及已接纳工程事实不在本任务修改范围。

## 已批准阶段与具体接入

| 阶段 | 接入既有能力 | 当前事实 |
| --- | --- | --- |
| 0 | v1.0 Standard / Maturity Reassessment | 已有，复用，不重做 |
| 1 | Work Formation 内理解状态、来源/证据角色、收敛决策 | 实施中；不建立独立框架或新 Owner |
| 2 | 同一候选空间中的局部编辑、完整投影校验与独立 Review | 实施中；旧 Wire/历史请求兼容，模型/预算不增 |
| 3 | 原 Owner 内按失败类选择 Repair/Ask/Stop，记录真实进展 | 待定向及实际资格 |
| 4 | Trace 自主调查状态/证据充分性/替代解释/停止 | 待其独立 Owner 范围处理，保留最新正例与旧失败 |
| 5 | WIC/Planning/Verification/ECF/Guardian/Executor 逐步消费 | 按真实接线缺口推进，不同时重构 |

## 第一批实现边界

在原 Formation 的两次候选、一次反馈及独立 Review 额度内：

1. 理解状态是派生 Candidate，不是 Fact；来源身份、原约束及权限由原 Owner 保护。
2. 区分已接纳事实、实际观察、候选推断/声明和真实履约证据，缺失证据不自动完成。
3. 初次候选通过现有语义选择和 Wire；可安全定位的第二候选使用明确局部编辑，Owner 从原始、身份绑定的提案构造完整新候选。
4. 保留原始响应、库存、Attempt、请求/响应/反馈收据及派生构造血缘；恢复重算，不重置预算。
5. 新候选仍经全部现有 Validator、独立 Semantic Review、实际 Verification/Guardian 门；不自动删冲突、补跨度、选支撑或创造 Authority。

这是当前批准 Mission 内的临时候选表示接入，不改变 Engineering Fact、正式 FulfillmentBinding、Guardian 决策或 Wire v1 的最终接纳含义。无法安全定位/缺合法 authority/未知传输效果时如实停止。尚未取得实现/真实泛化资格，不宣告 C3 CLOSED。

## 资源与验证

本机 Docker 与 ECS SSH 可用。专用本机测试虚拟环境位于 `D:/hy/watt-ai-native-evolution-validation-20261013/venv`，不覆盖系统 Python；生产环境不用于回归。

定向机制验证→受影响 PostgreSQL/Owner 集成→冻结 exact source/image→非 Holdout 实际资格→独立 Holdout；Holdout 仅验收，不用于实现调优。模型预算与权限沿用现有契约。构建/调用/费用以实际收据更新，尚未计量为 UNKNOWN。

## 首批代码与开发资格

已在既有 domain/refinement contract 定义理解状态、Evidence 角色和 Owner-local 收敛决策，并由 Work Formation 实际消费。它们都是派生状态；未确认 Fact record 只列为观察，不列为已确认 Fact，Formation 不创建履约 Evidence。

第二候选新增临时 `owner-local-wire-candidate-edits-v1`：模型明确 replace/remove/append，Owner 保留未改 Route，构造完整 Wire v1。原响应、原反馈、库存、Attempt、持久收据及派生构造 SHA 都保持独立血缘。JSONB 重排键后的派生编码固定为规范顺序；没有修改原 Provider 字节或旧请求的格式。最终 Validator/独立 Review/正式 Binding 没有放宽。

Source/格式/组件冲突均可在原一次反馈内局部修复；真正遗漏、wrong path、identity drift、重复编辑和无进展仍拒绝。若独立 Review **输出契约**错误，允许保持已通过确定性校验的候选，仅在原候选/Review 额度内修复 critic 输出；不强迫修改合法产物方案。已无安全原始 basis 时停止，不追加盲目请求。COMMIT 只表示派生计划接纳，不是 Runtime Commit 或 Human Authorization。

| 收据 | 实际结果与边界 |
| --- | --- |
| `receipts/local-construction-final.xml` | **18/18 PASS**：小/中/复杂库存、局部来源/格式修复、冲突、critic 输出修复、未确认记录、删除必要项、错误路径/身份/重复键、无进展、重放。受控 Provider，无真实模型 |
| `receipts/postgresql-local-edit-final.xml` | **1/1 PASS**：观测第二次局部编辑后中断，从 PostgreSQL 只完成剩余 Review，不再生成候选；终态重放不增加调用 |
| `receipts/formation-grouped-2.xml` | 前一开发点 **117/117 PASS**，既有反馈、JSON frame、来源/修复上下文控制；不能代替此后的最终状态或真实模型资格 |
| `receipts/formation-grouped-final.xml` | 后一开发点 **125 PASS / 1 FAIL**；失败为测试读取不存在的 Binding.capability，已改为正式 owner/phase/state 断言，最终 18 项收据验证。未放宽 Runtime |
| `receipts/postgresql-grouped-3.xml` | **48 PASS / 8 FAIL**；旧 C1 `_produce_chain` 在 PATH_SCOPE 验证遇其禁止模型调用的 verifier helper，或 MODEL_UNAVAILABLE。不能记全绿 |
| `receipts/baseline-reproduction-f52-2.xml` | 两类代表失败在未改 `f52d3996` 复现：literal-bound-work 的 helper AssertionError、open-current-scope-work 的 MODEL_UNAVAILABLE。其他参数项虽共用该 helper，尚未逐个独立基线复验 |

首次本机 Windows 收集停于 `fcntl` 缺失，未执行断言；之后改为隔离 Linux 容器，不修改业务代码适配测试。首次 PostgreSQL 停于测试库名称保护，之后在新建网络 none 的专用容器里创建允许的测试库；不触及业务数据库。第一次新恢复断言失败揭示派生编码键序不稳定，规范编码修复后通过。首轮 6 FAIL/8 PASS 的局部测试中失败仅为重放计时差异，最后断言排除每次调用自身 elapsed，但仍核对全部持久收据/绑定。

当前角色接线只在 Formation，尚未宣布各模块完成迁移。Phase 1/2 的开发机制已有实际代码；真实非 Holdout、最终镜像、独立 Holdout 及后续 Trace/Core 迁移仍待完成。C3/Integrated Program 都未关闭。实际模型调用仍为 0，部署为 0。

## 构建恢复检查点

首批源码提交 `ddd517c04067f06f32f21c9b962ae05c2dc55224`，Tree `115e7f384a0c6a4e6eb21e690378a6fc2ab19104`，已推送。Raw Git blob 导出 279 个 src 文件，归档 SHA256 `260f29f299f1685756294997a2445fd9c5705222a849454261187f7749bc501b`，ECS 留存在 `/data/watt/ai-native-evolution-20261013`。

第一构建 FAIL / `DEPENDENCY_LOCK_MISMATCH`，未重装源码成功，未取得镜像资格或模型调用。核对确认：原 attestor 的 lock 常量是旧 CRLF 捕获值 `ee2c5e...`；真实 Git blob 为 LF，SHA256 `ac853305...`。原 `f52d3996` 与新 `ddd517c0` 的 uv.lock Git blob 均为 `071627a271c51880c67cc58bc0a5c913c842c7ac`；旧镜像 lock 将 CRLF 转 LF 后与 Git blob 字节完全相同，TOML 包、版本、依赖及顶层元数据完全一致。

因此仅更正 attestor 对真实 Git lock 字节的绑定，不改变依赖、不转码导出内容、不降低源/镜像校验。旧 attestation/失败与旧镜像保持不变。重新冻结这一构建检查修正后再构建；不得把旧镜像覆盖文件算作新资格。

## 第一候选的语义提案接入

不把改善第二次修复误称为消除了第一次精确编码负担。已在同一新协商构造契约中增加第一候选 `{routes:[s,c,q,f,t,u,r]}` 语义提案：模型选择贡献原文/消费者/支撑/目标，Owner 从实际请求身份及唯一原文位置构造完整 Wire v1。不能自动选择消费者、补原文或扩跨度；重复引文或不存在的引文拒绝。合法旧完整 Wire 仍按原身份与全部谓词检查，历史请求不升级。

这是模块内 Candidate Generation → Semantic Interpretation/quote location → 原 Source/Evidence 角色与约束校验 → 完整 Projection → 独立 Review 的接线，不新增模型阶段或请求。临时表示不是 Fact，不修改正式 Binding/Guardian/Wire v1 的接纳职责。

最终聚焦组合 `receipts/semantic-grouped-final.xml` **129/129 PASS**；第一提案控制 `semantic-construction-1.xml` **20/20 PASS**；`postgresql-semantic-proposal-1.xml` **1/1 PASS**：已观测第二编辑后只恢复剩余 Review，不重新 Formation。均无真实模型，不替代后续实际资格。

第二构建源码 `f52ea2cd784abf9cae5d1e9a60b6353177d8ff48`，Tree `f74e125f9c6a35de789a32bdeac5b82f44b1d88e`；输入校验 PASS、包构建完成，安装态校验 FAIL / `IMPORTED_PACKAGE_CONTENT_MISMATCH`。新 Provider 文件安装 SHA 与 Git 原始输入一致；未变更的 `spg/__init__.py` 安装字节仍为 CRLF，等于继承的 `/app/build/lib/spg/__init__.py`。这是 image-local 增量 build 输出保留导致的字节漂移，不改源码内容，也不以换行归一化豁免安装态校验。Dockerfile 仅补清空新镜像阶段的 `/app/build`、`/app/dist`，保持锁、Owner、离线构建与全部字节核验。两次原始构建 FAIL 收据分别保留，不作 PASS。

## 新镜像与非 Holdout 实际模型结果

源码 `3c490a4f4da6f3635a69e7bc9f5b23488404e1cd` / Tree `6bdbda17d352022eaebd404381c806fcc431aaea`，新镜像 `sha256:9471199480bcbfd3fe9ebcd79863698cc0f5923398259f97d56dca89c6847b91`。安装态 attestation PASS；镜像内 baked tests 129/129 PASS，无源码 overlay。

两个既有非 Holdout 开发库存 readonly 模型资格：ordinary34/ordinary41 均 2 Formation / 0 Review / FAIL；没有创建 Work、数据库写入或 Guardian 调用。实际 Provider 正常，reasoning=none、16384、120s 不变。累计 Input 192589 / Output 6208 / Total 198797 / Reasoning 0 / Cached 512 tokens；货币费用 UNKNOWN。

ordinary34 第一次漏来源 7，第二次局部编辑删掉更多必要贡献，覆盖门正确拒绝。反馈已含逐来源覆盖和缺口，不能将其说成 Validator 错拒。ordinary41 多条 f 指向 IR_CLAUSE/IR_CONSTRAINT，类型门正确拒绝。两者都是未接纳提案，没有实际履约资格。

核对发现新候选 Schema 两个早退分支漏接了原 Wire 的 s/c/f/t/u 身份取值域和字段角色，属于本次表示接线缺口；已抽出同一个原身份域投影供旧 Wire、初提案及局部编辑复用。f 仍仅 FACT，u 仍为原来源空间；不新增索引、不自动选来源/能力/效果。覆盖错误纳入 SOURCE_CORRESPONDENCE，补缺仍必须模型明确 append，不能把 u 支撑当引用来源本身的履约。

`construction-domain-2.xml` 133/133 PASS（受控），`postgresql-domain-1.xml` 1/1 PASS（中断后剩余 Review 恢复，无候选重发）。首次修改有括号语法错误，collection FAIL 原收据 `construction-domain-1.xml` 保留，随后修正；不记作运行 PASS。下一实际资格须重新冻结并构建新镜像，原失败与库存不改。

跨电脑恢复：完整私有 Owner 收据、运行身份及构建事实在 ECS `/data/watt/ai-native-evolution-20261013`；公开脱敏收据在本分支 `receipts/`。没有 Holdout 内容用于实现；Program/C3 仍未完成。

## 第二次实际对照与 Owner 接线

`dd5fc214` / Tree `d5c1bc022065d1659085d50100cbc6e63ade19fc` / image `sha256:7de19c0d2f505f48b4934c9d0f98c8979793c5c922326722125995a8cc502533` 安装态资格 PASS。两项非 Holdout 仍 FAIL，均 2 Formation、0 Review；ordinary41 已越过 FACT_KIND_INVALID，停于来源对应证明；ordinary34 初次漏 9 个来源，第二次原始 JSON duplicate key，被严格拒绝。Pydantic 在普通 json.loads 后表面合法不能覆盖原字节解析的失败；不能去重后冒充有效候选。

第二次实际用量 Input 192984 / Output 6475 / Total 199459 / Cached 128 / Reasoning 0；耗时普通34 12.99s / 普通41 23.15s（Owner invocations），容器 40.04s。费用 UNKNOWN。无新 Work、原库存变化、生产变更或 Guardian 调用。私有收据在 ECS `nonholdout-2/private`，公开诊断只列稳定谓词、序号、SHA，不含原始对话/隐藏推理。

确认第二项同类接线缺口：新 Schema 未消费原有选定 consumer 后的必要来源证明。现复用 `_qualified_operand_generation_schema` 与 `_formation_binding_choices`，语义 proposal 仅省掉 Owner 可精确提供的 a/z；局部 replacement/append 保留同一前提。完整来源覆盖的既有必要条件进入生成契约，但 Validator 不改，模型仍选择语义；拒绝 unsupported/UNRESOLVED 的意义不变。追加约束针对所有实际库存身份，不针对开发或 Holdout Case、文字、文件名、组件。

Trace scoped 移植来源 `0e5ba3a985fecd659097d894bb17197429aae55e`，文件 SHA/接线 patch SHA 见 `trace-scoped-import.json`。复用已经实现的自主调查、自审、原文/字段引用、UNKNOWN、有限预算与原报告修订；未合并其整分支、未覆盖 C3 执行上下文保护、未部署正式服务。新理解/证据/收敛参考进入原 Native 观察，COMMIT 仅 advisory report，没有 Production/Human Authority。

联调确认并修复：Native registry 对已注册非内置工具错误访问未初始化 connector；新 Admin 只读/export 入口不应提前创建调查资源，改为通过原鉴权与 Work admission 后延迟创建；Context 复用 Trace 的容量内保留可用反馈策略和只能缩减的工具选择。原 C3 NativeContractExecutionView、精确来源、预算和全部效应门不回滚。

受影响组合 `native-common-stable-1.xml` 423/423 PASS；PostgreSQL `postgresql-native-integration-2.xml` 4/4 PASS，含鉴权/CSRF/原 Owner 不变、导出以及 Formation 持久恢复。第一次 Trace import 和联合失败、缺 jsonschema 的 collection failure、PostgreSQL 只读目录失败全部保留；不能计为 PASS。稳定组合与后续确切镜像的真实非 Holdout、实际 Trace/G0、独立 Holdout 尚待完成。

## 恢复及 Trace 统一基线指令（2026-10-13）

Human 明确指定当前 C3 分支为后续相关能力的统一开发与验证基线；`codex/watt-trace-self-analysis` 停止新增开发，保留 `0e5ba3a985fecd659097d894bb17197429aae55e` 历史与资格作为迁移依据，不再计划整分支 merge、不删除。

已核对并增量迁移 Admin 分析入口/交互、状态/历史、报告 Tabs、安全引用与 Markdown/诊断下载及对应 JS 回归，复用已迁 API/Owner 持久化与 Native 调查能力。前端 38/38 通过。Guardian 独立仓库与治理边界不变。

上一轮 `31028c15` image `f18b6021...` 的安装身份 PASS，但 installed test suite 421 PASS/2 FAIL：崩溃锁 fixture 预期构造服务立即创建目录；UI 测试从测试树猜测 src 路径。修正测试准备与 installed resource 读取后局部 2/2 PASS；不修改 Runtime 或将原镜像测试 FAIL 追认为 PASS。原 receipt 与修正分别保留；下一冻结包括 UI 迁移和这两项测试修正。
