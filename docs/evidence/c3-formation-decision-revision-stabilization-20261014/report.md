# Formation Decision Revision Contract Stabilization

2026-10-14；原 C3 分支。**契约接入与恢复身份资格通过；真实模型未证明 Consumer 修正能够稳定保持。ordinary34 完整 Formation 资格未通过，C3 保持 PARTIAL。**

## 1. 修改及边界

源码提交 `6afd558eabe5437b597611c3be39c99d8966941d`，Git Tree `be0176138e7915bf831164819988787b29085b33`。仅两个既有运行模块和对应定向测试变更：

- [`fulfillment_candidate.py`](../../../src/spg/providers/fulfillment_candidate.py)：新增 Owner 构造的 `formation-decision-revision-requests-v1`；用稳定 `decision_revision_requests` 取代请求副本原型的 `semantic_assumption_review`。记录原决策、未接纳解释的精确引用/哈希、待复核假设、复核理由、保持项及允许重评字段；共享假设挑战不提供替代 Consumer。
- [`governed_obligations.py`](../../../src/spg/application/governed_obligations.py)：在既有请求/响应收据中协商并校验契约 marker，沿原反馈绑定及局部修复入口传递。Owner 从原记录重建 `repair_targets`，模型不能提交派生状态。
- 原始 Wire SHA、库存 fingerprint、attempt、request/response receipt ID、route/component/source 身份及诊断 fingerprint 连续绑定。重放沿首次协商结果，旧收据不自动升级。不存在来源引用时不猜测填补。
- 不修改 `validate_projection_candidate`、Wire 接纳谓词、Independent Review、Guardian、权限、输出 Schema 或候选/Token/超时预算。不新增风险分类规则、普通34特例、Consumer 自动选择或协调层。

本次稳定化没有把原型中来自更晚一次历史响应的具体解释继续植入生产上下文。稳定契约引用**当前首候选自身**的 rationale，并提出通用的对象身份/来源支持与实际义务之间的假设挑战。因此本轮是稳定表示与真实行为再资格，不能用此前原型成功替代。

## 2. 精确镜像及回归

最终实际镜像：`sha256:e2883e109e5697fff5d932b9d606f6ffb333bc16c99c7fabf7ef2edbf22690e1`。完整源码离线重装，无运行时源码覆盖。构建输入和实际安装包逐文件核对见 [构建身份](receipts/image-build-final.json)、[安装身份](receipts/installed/installed-code-attestation.json)。本机镜像没有 registry RepoDigest，不编造远端 digest。首次安装校验的详细输出被同名运行摘要覆盖，已另存完整禁网重核收据，工具也已改用不同摘要文件名；不把原摘要冒充逐文件证明。

实际继承 Owner：Guardian `0d7aca954588c8ad3883dbedb730e59dc1d7b867`；ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c`。未修改独立仓库或调用 Guardian 授予 Assurance。

| 资格 | 实际结果 |
| --- | --- |
| 最终安装镜像定向回归 | [141 PASS](receipts/installed/focused.xml)，包含新契约9项正负验证 |
| PostgreSQL 持久恢复 | [10 PASS](receipts/installed/postgres-final.xml)；已持久化第二响应后恢复仅继续合法 Review，不重新生成；旧协议路径保持兼容 |
| 身份及权限负向 | 决策、派生状态、原 Wire、marker 篡改停止；未授权路径和独立 Review 否定仍被拒绝；重评不授予有效性 |
| 历史首响应的禁网接线控制 | [通过](receipts/ordinary34/preflight-result.json)；两个风险进入第二请求，原覆盖/来源反馈仍在，物理收据最大64,891 bytes，未提高131,072-byte上限 |

准备失败均保留：首次镜像构建因 Windows `core.autocrlf` 导出 CRLF 导致锁文件字节检查失败；[归一化比较](receipts/archive-byte-review.json)证明依赖未变，使用 `core.autocrlf=false` 重导出后原 attester 通过，没有修改锁或校验器。Docker 默认网络池耗尽后，在核对 Docker/IP 路由无重叠的前提下建立独立内部小网段。首次 PG 接线被原 sandbox host 限制拒绝（[10 setup errors](receipts/installed/postgres.xml)，不计应用 FAIL/PASS）；改用新资格 PG 的同一容器网络命名空间及原要求的数据库名后通过，没有放宽保护。两次资格 PG 已停止，正式数据库未访问。

## 3. ordinary34：完整真实 Formation 路径

使用原19来源的不可变库存 `b023bae819f456da05abe983f48da4f2157da60df412de909f9f834991bcef29`，新建私有资格收据，不写原 Work。执行两个真实 Formation，保留原一次反馈与 Review 资格判断；[实际结果及调用身份](receipts/ordinary34/live-result.json)、[容器身份](receipts/ordinary34/live-container.json)。

| 观察 | 首候选 | 第二候选 |
| --- | --- | --- |
| source 0、1 的 Consumer | 仅 ARTIFACT_CONTENT | 仍仅 ARTIFACT_CONTENT |
| source 2 的真实文件范围 | GIT_DIFF_SCOPE | 保留 |
| 字符覆盖失败来源数 | 9 | 0 |
| 局部编辑 | 无 | replace14、append8，无 remove |
| 当前 Fact 贡献与未来 Seal | source3 缺当前贡献 | 原问题仍在 |
| 其他未关闭项 | 多项来源未覆盖 | source18 UNRESOLVED；Owner 前提还发现 source4 缺对应同能力 source11 证明 |

终止：`OBLIGATION_SEAL_CURRENT_CONTRIBUTION_MISSING`。两次 Provider 均 completed，没有容量/传输失败。独立 Review **0次**，因此没有新的语义接纳或 Assurance。终态重放不再调用模型。

**这次首候选没有提出历史错误的额外 Diff，因此不能用该运行证明新契约修正了 Consumer。** 它证明当前正确的内容/文件范围选择被保留，原有覆盖修复继续工作；并不证明全部来源与阶段语义已正确。没有把示意链路继续推进到未获资格的生产阶段。

## 4. 冻结错误首候选：真实单次修复控制

为实际触发目标机制，另做一项有明确输入变化的控制：保留原首 Wire SHA `893f167cab558759ab2eb2a2a3664e2d57650e71a0077b2fcf6e5553928ebc4e`，作为明确标记的受控首响应，经相同 Owner 生成新反馈，再执行一次真实第二候选及适用 Review。不是重复创建真实 Work，也没有把控制首响应冒充新 Provider 结果或改写旧收据。每条路径仍只有两个候选槽位和一次反馈。

[控制结果](receipts/ordinary34/retained-first-result.json)、[候选观察](receipts/ordinary34/candidate-observations.json)：

- 两个 `decision_revision_requests` 确实绑定并进入 Repair Context；模型对原 route1、3 显式 replace，但两条都**仅修改 rationale，Consumer 仍是 GIT_DIFF_SCOPE**。没有自动替模型删掉错误路线。
- source0、1 的 ARTIFACT_CONTENT 和 source2 的 GIT_DIFF_SCOPE 保留。
- 原覆盖失败由4个来源减至1个（source10）；先前7项 supporting-source 前提错误不再出现在本次 Owner 诊断中，但没有独立 Review，不能称来源语义全部正确。
- 本次还出现 source4 重复路线。最终仍为 `OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST`，未进入独立 Review。原完整失败集合保留，没有仅保留主错误。
- 终态重放零新请求。没有第三候选或追加探针。

**结果没有重复原型中“删除额外 Consumer”的行为。** 已证明重评对象进入修复并被编辑；没有证明模型重新解释了原假设。改写理由不等于语义修正。真实偏差目前不足以证明 Validator 错拒、表示无法编码正确解，或需要新增架构；本轮不据此改门禁或增加静态答案。

## 5. 是否可由 Formation 采用

**可保留为身份受控的内部 Decision Revision 反馈契约；不可宣称其已具备通过资格的通用语义收敛效果。** 结构接线、现有修复并存、持久恢复和拒绝能力得到验证；本轮真实模型没有保持 Consumer 修正，完整 ordinary34 资格未通过，Independent Review 未取得结果。

下一项必要工作是基于已保存的原解释、两个真实 replace 的公开方法理由及原 Capability/Owner 契约，区分“挑战只促成理由改写”的运行时偏差与稳定上下文丢失必要语义信息；不得用强制 remove/自动选择 Consumer 来替代判断。已有本轮证据足够进行这项归责，无须现在再调用模型。保留本次边界，不自动扩张修复或开始 G0/Holdout。

## 6. 消耗、保护和恢复

真实请求共3次 Formation、0次 Review、0次传输重发；其中完整真实路径2次，冻结首响应控制1次。累计 input **209,008** / output **9,577** / reasoning **0** / total **218,585 tokens**；实际模型耗时合计约 **43.626s**。cached tokens是输入子集；货币、整体CPU及能耗成本 UNKNOWN。原模型 deepseek-flash、reasoning none、16,384 tokens、120s均保持。受控首响应没有真实本轮 Provider Usage，单独标记 UNKNOWN，未计入上述实际消耗。

没有创建 Work、修改生产/main、历史 Work、Candidate、Human Decisions、Holdout 或 Quality Ledger。原库存、basis和历史收据前后 SHA 未变，见两份结果中的输入身份。公开资料只有脱敏引用和指标；完整请求/响应与 Owner 收据保留在 ECS：

`/data/watt/ai-native-evolution-20261013/decision-revision-stabilization-20261014/private/qualification/`

`live/`为完整真实路径，`retained-first/`为受控首响应加真实修复，`preflight/`为禁网接线控制。构建及测试事实在同根 `build-lf/`、`evidence/`；安全文件清单见 [恢复清单](receipts/private-evidence-manifest.json)。公开报告、工具、原失败及通过收据随原 C3 分支持久化；跨电脑可按本路径和哈希恢复，不依赖旧电脑本地文件。
