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
