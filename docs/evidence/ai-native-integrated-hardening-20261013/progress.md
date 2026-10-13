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

## 语义提案局部恢复资格

统一 UI 源码 `6545b19b` / Tree `496c7b5d69b0b8c1b61d5dcefe259e2ad9b732e9` / image `sha256:9f3879c2ba7d33a4936a318a8444b525df02b72aa033f6b9289538fc4f93f625` 安装资格与镜像内 423 项受影响回归 PASS。

第三次非 Holdout 对照两项均初次引文不存在，QUOTE_NOT_OBSERVED 正确拒绝；原修复机制将未能定位的安全语义提案认定无可用 basis，提前停止，未进入第二次 Formation/Review。不可记 PASS，也不能自动定位不存在的文字。

已在既有模块修复这一恢复前提：新协商的临时候选编辑 v2 保留安全且结构完整的原始语义提案为 UNLOCATED_SEMANTIC_PROPOSAL；不是原文证明或 Fact。模型可在原第二候选额度内明确修改引用/消费者/来源选项，Owner 不自动修补语义；全部新引用精确定位后才构造正式 Wire v1，继续原 Validator/独立 Review。诊断包括所有可评估的 quote 失败、route/source/fingerprint，UNKNOWN 和 NOT_EVALUABLE 不转为证据。

v2 是模块内部临时候选与恢复协议，不新增 Engineering Fact/Owner/状态机、正式 Wire Schema 或模型阶段/预算。已持久的 v1 请求按其原协议重算，不因新 Provider 默认而升级，库存/反馈/Attempt/原始 Wire 与持久收据仍精确绑定。隐藏推理及任意原始私有 Human 输入不进入公开报告。

`semantic-unlocated-repair-1.xml` 100/100 受控定向 PASS；`postgresql-semantic-unlocated-1.xml` 2/2 PASS，分别覆盖 v1/v2 已观测第二编辑后的剩余 Review 恢复及终态重放。错误引用、删必要组件、重复原始 JSON key、无进展、错误父 basis、错误版本/身份继续拒绝。能力必须在下一确切镜像取得实际资格，未提前声明 C3 Closure。

## Trace 产品能力收敛：真实资格

统一分支 `6545b19b`、确切镜像 `9f3879c2...`，Admin POST `/api/admin/works/{work_id}/analyses` 在正常鉴权、Origin 和 Work admission 后，真实 DeepSeek Native 调查原 C3 Work `6ba2cffa-0bf3-565a-81e0-7f3c6696f21e`。请求 `3ad5e57d-a815-4432-8bc3-256e80ec9a93`：COMPLETED / RESULT_READY / CITATIONS_AND_STRUCTURE_PASS。Owner invocation 563.30s、12 inferences、24 tools，原 12/48/600 envelope 未提高。先引用失败→analysis.revise，再自审反馈→analysis.revise→重新自审，通过后才返回报告。

只读 C3 qualification PostgreSQL 事务，Migration `20261007_72`；原 app/workspaces readonly，无 Docker socket、生产数据库、原生产重放或旧服务修改。范围内原 Owner 记录摘要前后相同。报告及 Native CAS 在 ECS `trace-native-api-1/`；HTTP history/result/Markdown hash 通过，真实 API summary 在当前 Admin 模板渲染四个 Tabs，带真实证据与未知边界，下载引用精确 request。前端检查不是浏览器视觉检查；未将展示视为独立语义 Assurance。

报告仍 ADVISORY_ONLY / HUMAN_REVIEW_REQUIRED，自审不是 Guardian/Human Acceptance。使用实际 Provider ID/status/usage 收据；完整总 Token 暂 UNKNOWN，部分有 numeric usage，reasoning_tokens 已被旧通用 redactor 遮蔽。`trace-native-usage-and-convergence-v2.json` 分别列实测部分统计与未观测/已遮蔽字段，部分合计不是完整成本，不猜测。当前 `f423bd6a` 对 Trace/API/Native/页面无代码差异，此范围资格可追溯复用；不宣称 Formation 新源码已由旧调查验证。

旧 `codex/watt-trace-self-analysis` 已完成必要产品能力增量迁移，标记 **待归档 / 停止新增开发**。本分支是后续统一基线；旧分支及历史资格保留、未删除。当前尚未发现需要该分支继续独立开发的已形成产品功能缺口；后续相关工作均在 C3。

## 局部编辑的反馈消费接线

第四次真实 Formation：ordinary34/41 均两候选、0 Review，仍 FAIL。可定位缺陷不再使第二候选提前丢失，但当前/未来贡献、来源对应与新引文偏差仍未收敛。准确错误集合见 `nonholdout-model-f423bd6a-4.json`，不根据标签冒称 Validator Bug。

代码审查发现新局部协议覆盖了 `_formation_repair_instructions` 的原反馈读取方向，丢失原“完整拒绝集合与 Owner 观察”消费接线。修复为复用该机制并声明局部编辑输出形态，避免要求模型重生完整计划；没有追加业务词汇禁令、Owner 能力、权限或重试预算。`local-edit-feedback-1.xml` 定向 86/86 PASS。下一镜像只做受影响资格；不能把反馈说明自身视为实际模型收敛成功。

## 语义角色候选表示（模块内部）

第五轮仍未进入 Review。原始方案普通34缺覆盖；普通41两次均把非 Fact 放入 f。已核对第四轮的 mixed acceptance Fact：它同时要求确切标题/段落验证与 reviewable Candidate，仅 CANDIDATE_SEAL 确实漏当前贡献。其他提案把当前义务归背景、使用 DENY_PREVIEW 及错误支撑，拒绝有实际来源依据；未证明 Validator 错拒。

本模块内增加语义角色提案 v3：source_ref、capability、component_quote、current_fact_dependencies、target_paths、provenance_support_refs、rationale。均使用原始 Source refs、现有能力与准予路径；Owner 精确映射到同一个既有 ordinal space 和正式 Wire v1，不另建 FACT 索引或语义 Owner，不选消费者、不改原 Fact/引文/权限/门禁。

Header/版本由实际请求 Owner 提供，模型不能新增声明。局部 edits 严格绑定原始 response SHA 和持久反馈/库存/Attempt，保留未改原提案。合法旧完整 Wire 和紧凑语义表示继续被消费；修复输出按实际 basis 选择原形态，不强制统一外部模型形状。未知引用/混合字段/非 Fact dependency/不存在的引文不变成 Fact、证明或 PASS。

输出字段变长是明确成本，不以缩短 JSON 为目标；减少模型对压缩字母/不同角色/精确编码的同时猜测负担。仍原 2 Formation/1 feedback/每候选最多1独立 Review、最多4逻辑调用；不提高模型预算、不改变 Provider。当前 Source/phase/evidence Validator 与 Guardian 不放宽。

`role-reference-focused-2.xml` 169/169 受控通过；PostgreSQL v1/v2/v3 各自中断与持久恢复 `postgresql-role-reference-1.xml` 3/3，通过后仍需真实模型资格。两项新增测试准备错误（fixture 没 IR_CLAUSE、单独构造缺 presentation negotiation）均保留失败收据，随后修正并局部 2/2。不能将历史模型 Candidate 改写后当作成功。

## 原始提案格式恢复前提（2026-10-13 恢复对账）

`65b9fdca` / Tree `6329ca64a4456d0c66837dc6d6b46023a23b395a` / image `sha256:c9e6b31277430fc30733475818db10111a729346ebbf3e0853b5f8c82d76cb15` 安装身份及定向镜像验证通过。第六次非 Holdout 没有任何接纳投影或独立 Review，两个实际库存不能计为成功。Provider 三次均 completed、无传输重发；实测 Total 177424（Input 167143 / Output 10281 / Reasoning 0 / Cached 256），币种费用 UNKNOWN。

普通34一份完整 JSON、20 条 role routes，三个 Route 的 current_fact_dependencies 含数字而非原来源引用。Schema 正确拒绝；既有修复 basis 必须先满足全部字段类型，导致安全原始提案也无法进入第二候选。这是恢复前提过强的已证实能力缺口，不是来源/权限门可被省略的理由。

在既有 Owner 中增加已持久协商的 `existing-bound-unadmitted-role-repair-v1` 标记：仅完整、无重复键、隐私安全、bounded routes、已知字段且有明确 source_ref/capability 的原 JSON 可成为未接纳修复 basis。原值逐项保留，不转换数字、不补来源/语义。第二次显式 replacements 仍须严格类型和完整最终校验；未修字段继续拒绝。结构失败集合只含位置、稳定谓词和 NOT_EVALUABLE，不含敏感输入。旧无此标记的请求/停止按原机制重放，不能因新 Provider 默认而复活或漂移反馈身份。

`raw-role-repair-1.xml` 定向验证通过；`postgresql-raw-role-repair-1.xml` 4 条持久恢复通过（包含原 v1/v2/v3 和新标记）。身份漂移、重复键、删除义务、无进展仍拒绝；第二响应后崩溃只恢复独立 Review，不重复模型生成。

普通41第二候选已明确修正一个非法来源 ref，但剩余六项为真实候选缺陷：三个 Work Constraint 的候选支撑集合不具备原 Owner 所需证明，三个 GIT_DIFF_SCOPE Route 的目标路径集合为空。完整原文/作用范围没有被伪造或压缩；尚未证明 Validator 错拒。此分支不因预算耗尽继续盲目调用模型，亦不通过自动选择支撑/目标获得 PASS。只对有明确修复依据的普通34恢复缺口进行下一确切镜像资格。

Trace 真实结果的 Admin 展示校验补充 `actual-trace-admin-presentation-2.json`：使用原始 Git blob / 实际已安装 JS 字节，修正前次 Windows 工作副本 CRLF hash 与已安装 LF hash 的区别。四个实际数据面板结果相同；旧收据保留，不冒称浏览器视觉验收。Trace/API/Native 源码在 Formation 后续修订没有改变；镜像只读重放 `trace-final-image-replay-2.json` 证明原 CAS、API 与下载兼容，未增加模型调用。

## Phase 2 内部语义理解 → 角色绑定

第七次真实结果 `aeb49d2a` / image `809206d0...`：普通34两次 Formation、0 Review，仍未接纳。Provider 两次 completed、无重发；累计 Input 126355 / Output 8908 / Total 135263 / Reasoning 0 / Cached 37888。初次漏四条 Clause 原始贡献；第二次明确 remove/append，但重复 retained 的同一 Fact/Seal 组件，并使用不充分权限/来源证明。原始 JSON、反馈和终态保持不变；不冒称自动收敛成功。

按已批准 Integrated Phase 2 的模块内分工实施[语义理解与绑定](formation-interpretation-binding.md)：第一候选可保存未审查的 source-referenced understanding/alternatives/unknowns；第二候选构造完整真实方法计划。原始库存、跨来源上下文、已接受 Fact 和正式 Wire v1 不改；2 Formation / 1 feedback / 最多4逻辑调用不增。完整最终 Validator、独立 Review、执行与 Guardian 门禁不改。安全但未被观察的来源/引文或不完整 Claim 保持 UNKNOWN，不提升为事实/证据；第二候选必须对所有原始要求合法绑定。

临时协议 v4 是现有 Owner 的构造路径，不新增 Runtime 编排系统、IR、全局 Owner、跨项目 Evidence 契约或独立 Refine Coordinator。新实例不能升级旧收据；最终方法和原始事实之间的证明仍来自原 Authority/消费者，不来自第一候选的解释。此计划落实已有 Phase 2，尚不宣称其真实模型收益。

`interpretation-binding-1.xml` 保存首轮 3 FAIL/79 PASS（测试读取不存在 Binding.inventory_fingerprint）；改为实际 formation receipt 字段后 `interpretation-binding-2.xml` 11 PASS。最后的未知 Claim/身份漂移扩充 `interpretation-binding-3.xml` 14 PASS，`postgresql-interpretation-binding-2.xml` 6 PASS。受控 Provider 仅证明机制，不替代真实生产。下一资格以新冻结的应用/镜像身份为准。

## Owner 收据引用与容量停止真实性

`0108e842` / Tree `6e85899bdaaaf8dc80026c7201211ff022b3a650` / image `sha256:49f5738481eed9c7f01321d7d64476cb8b4359a1194e6576ae8fe3b7c42c16da` 安装身份及聚焦回归通过。真实非 Holdout 第八次：普通34第一步形成全部19条合法形状且原文位置已观察的理解候选，仍全部 UNREVIEWED_CLAIM / NOT_PROVIDED。第二步完整计划因非 Fact 使用 EXACT_PRODUCT_SOURCE_IDENTITY、权限和支撑对应缺失而拒绝，2 Formation/0 Review。实际 Source consumer 的 Fact-only 条件已经进入 Owner 的 ineligible_binding_prerequisites，不能把这次不遵守契约说成缺少 Gate 或 Validator 错拒。

普通41随后在第二请求记录前触发既有 131072-byte receipt limit；容量停止丢弃最新大载荷后，finish 仍读取其 candidate_construction_state，产生 KeyError。没有第二请求成功资格，不能记 PASS。此诊断 harness 仅在整 Case 返回后写私有收据，异常导致该 Case 的完整内存观察未落盘，其实际 Provider Usage/输出和精确原始收据尺寸继续 UNKNOWN；不能从当前输入或时间推测历史数据。

在同一个 FulfillmentFormationReceipts Owner 内修复重复载荷：新 v4 的第二请求通过原 CANDIDATE_VALIDATED 收据 ID 和完整字符串 fingerprint 引用反馈；响应通过同一 Attempt 的 MODEL_REQUEST_PENDING 收据引用完整 Owner 上下文。原父收据保留全部数据，实际 Provider 输入不改；读取对同 Work/Revision/Inventory/Source/路径、角色、Attempt、字段与 hash 校验后物化。缺父收据、改 hash、错用途、跨 Work、改父载荷或循环均由既有身份停止拒绝。旧无引用收据的格式与事实不改。

容量停止不物化被裁减载荷、不复活终态；finish 只读取实际保留的理解状态，缺最新状态不会抛 KeyError 或伪造 PASS。原 131072-byte 界限和模型额度不增加。`owner-reference-capacity-1.xml` 的 1 FAIL 揭示原容量停止校验假定反馈必须被裁减；现精确校验保留的反馈引用，`owner-reference-capacity-2.xml` 80 PASS；`postgresql-owner-reference-1.xml` 6 PASS。原 FAIL 收据保留，不追认。

下一验证仅重验该可证实的普通41记录阻断。对普通34正确的模型/治理拒绝不继续相同条件下盲目调用；尚未产生新的 Work、Artifact、Verification 或 Guardian 成果。C3 仍 PARTIAL，历史生产/Holdout 保持不变。

## 失败反馈自身引用原始 Wire（只读重建，不增加模型尝试）

普通41第九次 Source `1f74d76e` / image `a2d727a2...`：请求/响应引用修复已让第二请求实际完成，模型两次 completed，无传输重发，实际总 Token 139323（Input124191/Output15132/Reasoning0/Cached40576）。仍未接纳，0 Review；第二候选存在重复 Route。CANDIDATE_VALIDATED 的完整反馈包含 115394 bytes 的 validation_feedback，整收据 133150 bytes，原 131072 限制正确停止。原始第二响应及实际阶段收据已由私有 harness 每次 append 后原子落盘，因此此次可以依据真正保留的事实只读重建错误，不通过新模型请求碰运气。

同 Owner 的 v4 失败反馈现在引用对应同 Attempt MODEL_RESPONSE_OBSERVED 的原 Wire 字符串：保存原字符串 SHA、JSON frame 的精确 prefix/suffix；只对唯一且与真实父响应完全相同的字段建立引用。读取恢复完全相同反馈字节，并核对完整反馈 SHA/bytes。没有重新编码其他字段、删除失败、缩减约束或生成不存在的证据。父/用途/Work/version/hash、prefix/suffix 漂移继续停止；历史被裁减的终态不复活。

`feedback-wire-reference-2.xml` 定向正负与原容量回归通过；`postgresql-feedback-wire-reference-1.xml` 6 条持久恢复通过。这只是记录能力资格，不能让原非法 Candidate 合格，不宣称过去运行取得 PASS。后续实际模型资格仍需真正的合法方法计划和独立 Review。

## 账号切换后的恢复与消费契约接线核验

恢复 HEAD `c4dbbac5213b995bacec168bc55eb72eef854b99` / Tree `435b1e2eaffbf727c2ca67e1b8a9d76bd760d3f5`，没有遗留资格容器正在执行。镜像 `sha256:d936c1a8861c6d3658cfeba85b56859cc9b693e40312b5d624221354f83455bd` 的安装 attestor 和受影响镜像内回归通过。根工作区的其他分支和旧 g50/g51 未提交材料保持原样。

只读使用普通41第九次实际保留的两个响应，在确切 c4 镜像中做反事实契约核验（network none，0 Provider 调用，原输入/收据 readonly，不重放生产 Work）。全部错误现在可以保留：重复组件、同组件矛盾处置、必须履约的 Clause/Constraint 被归背景、来源证明不充分以及 UNRESOLVED。最大新存储收据 94432 bytes，在原 131072 界限内。原候选仍非法；新的派生反馈 fingerprint 绑定本次反事实 Attempt，并非历史反馈身份或历史成功。

代码对账发现共同的 B 类接线缺口：temporary construction 分支覆盖原 `_primary_meaning_instructions`；v4 角色绑定进一步覆盖本地反馈方向。原 `_SOURCE_CONSUMER_INSTRUCTIONS` 中已有的原意/Consumer/完整支撑集合、当前与未来职责、背景不能替代当前履约等消费语义未进入角色构造请求。这个缺口不意味着原 Validator 错拒，不允许放宽门禁或改历史提案。

最小修复在原 Owner 中复用原消费说明的语义部分，将 Wire 编码说明与临时构造分开；只在实际角色计划构造/修复阶段提供，不把未来方法要求强加给第一步理解 Claim。临时字段名按已有表示映射，既不选业务消费者也不生成新事实。新请求持久绑定 `existing-consumer-semantics-in-construction-v1` 标记；旧无标记收据按原输入协议恢复，未知标记或身份漂移停止，不新增正式 Wire 版本、Owner、权限或请求额度。

`construction-consumer-contract-1.xml` 39 PASS；阶段边界调整后受影响 7 项 `construction-consumer-contract-2.xml` PASS。`postgresql-construction-consumer-1.xml` 8 PASS，覆盖原协议及新角色构造标记：第二响应落盘后中断只调用剩余独立 Review，不重做 Formation。错来源、伪造 Fact、越权路径、重复和缺证明仍拒绝。必须继续冻结新修订、镜像并验证实际收益，受控结果不关闭 C3。

## 已观测格式偏差的原 Owner 有界恢复

Source `148a25cece061d56365d9ba60e3dccfc39015274` / Tree `c0c8f614e68e5597efb2bea23952a8919d6feace` / image `sha256:1eb025875ec3c3dceca3174dfc20ca2b61610a0cb2a16638e7d3b9d8667de96f` 安装与镜像定向验证通过。普通41第十次仅 1 Formation/0 Review：Provider completed，原输出末尾 JSON 分隔符错误（位置16540，原文字符数16543，无 backslash），继有修复依据要求能先 parse，提前停在 LOCAL_REPAIR_BASIS_UNAVAILABLE。实际 Input40705 / Output3782 / Total44487 / Reasoning0 / Cached33536，无传输重发。此结果没有验证到第二步消费契约，不能假称已改善语义收敛。

这是 A 类格式波动伴随 B 类恢复前提缺口。仅在原 v4 Owner 内，增加持久协商的 `existing-bound-unparsed-claim-repair-v1`：原已观测、安全、精确绑定且可归因 JSON 格式失败的输出可以保留为 UNPARSED_PRIVACY_SAFE_PROPOSAL。它没有组件解析、来源几何、语义批准或证据；不补逗号/括号、不默默修 JSON、不改原始输出。剩余原候选额度从不可变完整库存构造方法计划，保留原 Raw SHA、父收据、Attempt、库存与反馈绑定，然后照常执行全部确定性和独立 Review 门禁。

无法证明隐私安全的 escape 输出、重复 JSON keys、身份/预算不明仍停止。旧请求不获得新协商能力，原 terminal 不复活；没有新增候选、Review、Token、权限、Owner 或正式 Schema。`unparsed-claim-repair-1.xml` 40 PASS，身份扩充后 `unparsed-claim-repair-2.xml` 11 PASS；PostgreSQL 新路径单项中断恢复 PASS，原8种协议仍使用上一已通过回归。再次格式失败必须在第二候选结束，不能追加第三次。控制证明只说明恢复可以合法执行，真实模型收敛尚待新冻结资格。

## 恢复修复机会与原来源角色反馈绑定

Source `67b9f4922a71f59891ea201dd94135caf9259789` / Tree `9bde194ec5a0721cace61d2fb43726197be47b0f` / image `sha256:357422a19a09ea27ee494a65b62bc1547256f1500776194299b0993e4d6aaa1d` 安装与镜像定向回归通过。第十一次普通41：Provider 两次 completed，全部23条理解 Claim 有观察到的原文几何，仍未获语义批准。完整角色计划只报来源覆盖缺失，没有新增权限/支撑/重复错误；0 Review。实际 Input122980 / Output5658 / Total128638 / Reasoning0 / Cached33664，不计为成功。

同源镜像、同一库存，使用既有 v3 完整初候选→一次局部编辑路径做机制对照（第十二次，不建 Work、不写历史 Owner、不用 Holdout）：原一次反馈将覆盖失败从10个来源缩到2个，仍0 Review。实际 Input133103 / Output5708 / Total138811 / Reasoning0 / Cached1792，无传输重发。只读 Owner 谓词核验发现最后两项分别为 IR_CONSTRAINT 2个标点及 WORK_CONSTRAINT 27个字符（含24个字母）未覆盖，不能称作无害显示差异或直接放宽 Validator。

两步强制路径在第一完整计划出现前已耗完原2个 Formation 机会。新协商 `existing-complete-role-candidate-and-bound-repair-targets-v1` 在原 v4 内优先完整初候选，保留原一次反馈用于真正的计划修复；合法的理解 Claim/完整 Wire/语义方案仍可消费，理解-only fallback 不增加调用。复用原有字段、语义契约、完整验证、独立 Review 和额度，不将模型 Claim 变 Fact。

同 Owner 将来源覆盖失败的原 Source ordinal 规范化为原 Source ref 与相关 ORIGINAL Route indices/fingerprints，并引用完整原始 basis 与实际缺口。它不自动选消费者、权限、证明、路径或新 quote，不暗中扩大跨度。错误定位不能评估时保留 NOT_EVALUABLE；显式模型编辑后仍由全部原门禁判断。未证明这个引用接线问题单独导致上述剩余两项；其真实收益仍需最终镜像验证。

首轮新增验证 7 FAIL/2 PASS 因新路径初始化读取 None basis（无 Provider 请求），已修正条件，原失败收据保留。`role-convergence-2.xml` 10 PASS；新的 PostgreSQL 中断恢复单项 PASS，仅剩余 Review 被调用，原模式按其既有身份恢复。新协商目标、原输出、父反馈和旧默认漂移均不能产生新模型调用或成功。稳定修订继续真实资格；C3 仍 PARTIAL。

## 局部编辑统一目标结构

`3d5656ac4ff9665c9939a3d316b624fd86d777f5` / Tree `8a6362f9e12d456425e112bb20b7b706b3248694` / image `sha256:798187b017d70e3571a8e33683b5a620593de2d343bf9966daa5c4f553445c27` 安装及聚焦镜像验证通过。普通41第十三次：初次32个 Role 提案中存在未知原来源 ref，正确拒绝。第二次实际编辑为完整的唯一 JSON fence，包装 Owner 已正确解包；不是不完整 JSON 或缺失 replacement 字段。其 replace 提案为完整字段，remove 却使用 `[{"index":27}]`，而旧消费契约只接受 `[27]`，因此停在 LOCAL_EDIT_SCHEMA_INVALID，0 Review。实际 Input127020 / Output5169 / Total132189 / Reasoning0 / Cached52608，无传输重发，不计为成功。

已撤回“可能需要支持部分字段 patch”的未证实假设，不实施该变更。真正最小缺口是编辑命令同一原始索引的结构不一致：replace 用 index target object、remove 强制裸整数。在原局部编辑 Owner 内，新临时 v2 协商统一生成显式 index target；解码仍可消费同域的准确整数。没有字符串/布尔转整数、未知字段或越界接纳，duplicate/replace-remove 重叠仍拒绝。模型明确指定的原 Route 才可移除；最终完整来源、scope、权限、证明和独立 Review 门禁保持不变。没有 Scope/Subject Alias、语义猜测或新 Gate。

原 v1 协商保留，包括原 object removal 的历史拒绝；恢复不升级默认、不复活终态，也不更改 Model 原始输出、反馈、父 basis 或预算。`explicit-index-targets-1.xml` 15 PASS；精确旧协商选择补充 `explicit-index-legacy-1.xml` 单项 PASS；PostgreSQL 新 object target 的第二响应中断恢复单项 PASS，仅执行剩余 Review。下一确切修订仍需实际 Provider 资格；受控解码 PASS 不等于真实语义或 C3 Closure。
