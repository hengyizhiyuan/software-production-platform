# C3 Formation Semantic Responsibility Boundary Calibration

记录时间：2026-10-14 11:52 +08:00。结论：**有界 Owner 资格入口修正及定向回归完成；C3 仍 PARTIAL。** 本轮没有形成新的真实模型 Candidate、独立 Review PASS、Work 或 Guardian Assurance。

## 1. 基线与证据等级

| 项目 | 精确身份 |
| --- | --- |
| 分支 | `codex/c3-open-semantic-obligation-convergence` |
| 改动前应用源码 / Tree | `d27707cb49558a0bc0071d9e3c4250fe88234427` / `04f146f4937a7fc7b0bbda21cd70dcad40dd4053` |
| 本次代码提交 / Tree | `f72707ab96ed67d167cd1dd26a8ddb55b716e323` / `8975640a56518a7bc5abc69dcab4a2c65c2b98e4` |
| 原资格镜像 | `sha256:73da30f5567f5766b9767855c1e772fc5421d93a9da54f99a971db9d2f48ce53`，仍对应 **d27707cb** |
| Guardian / ECF | `0d7aca954588c8ad3883dbedb730e59dc1d7b867` / `5aa4f8833c359c15bd059eda5972aa3915bcc18c`，本轮未改 |

E1：原普通开发场景的持久模型、Owner 与 Review 收据。[归责分析](../c3-semantic-review-failure-attribution-20261014/analysis.md)给出完整链路。私有原件在 ECS `/data/watt/ai-native-evolution-20261013/nonholdout-{14,15}/private/`，分别绑定 ordinary41/34；原收据 SHA256 为 `8adfad4256b19e5ce8c4b751fb0256c2617c337edbd2f9d94e0ae19e2de519e2` / `8eea94156781896350044e1c8635f76d648d3212c9a0663b27909ec2d7930d4f`。E2：本次无网络的受控回归与只读反事实，见 [收据](qualification-receipt.json)。E3：上述确切源码。E2 不能追认 E1 的失败为成功。

## 2. 责任边界与已证实根因

| 边界 | 本次校准后的责任 |
| --- | --- |
| Formation 模型 | 理解原义，提出消费者、组件、证据方法与支持来源的**候选**；错误选择可进入现有有界反馈，但不能变成事实或权限。 |
| Work / Fact Owner | 从现有 Reality/IR 精确绑定来源、版本、原文、Human provenance、阶段和目标路径；只确认某方法**有资格被审查**，不替模型判断开放语义，也不宣告证据已满足。 |
| Validator | 保持完整来源、原值、阶段、支持引用、目标集合与权限校验；结构合法不等于语义 PASS。 |
| 独立 Semantic Review | 审查原义与**提交的候选方法计划**是否等价、能否在其 Owner 阶段取得证据；实际内容、Git Diff、Seal、Human 决策及 Guardian 仍由对应后续 Gate 证明。 |

**ordinary34：** 原候选的字面内容 Fact 已有 `ARTIFACT_CONTENT`，却又给同一 EQUALITY 值加了两个 `GIT_DIFF_SCOPE`。第二候选只修复 4 个字符覆盖缺口及 7 个来源引用，保留了错误消费者。独立 Review 对 route 1/3 的拒绝有依据；文件关联不能证明标题/段落值。Owner 不应替模型删除这两条，也不能把 Review FAIL 改为 PASS。Reviewer 对混合内容与未来 Seal 要求实际履约证据的 source3 判词则混淆了计划阶段；source4/11 与同源派生项对“新增页面”的解释仍不一致。

**ordinary41：** 派生 Work 约束“其他文件不得变更”可精确追溯到当前 `production.exclusions[4]`。原 `cl-5` 是 Human explicit、CURRENT、AFFIRMATIVE 的排他文件范围，已接纳 SCOPE Fact 保留同一原文和 `index.html` 值。旧 Owner 给此派生约束列出的 Git Diff 支撑集合都强制包含 NEGATED `cl-7`；然而该 Clause 讲部署/发布/新增页面/README，不独立证明任意其他文件不得变更。这是**候选方法资格入口的 Owner 缺口**，并非 Wire 无法携带多条支持。原候选第一次只引用范围来源 9，缺派生 origin；第二次只引用 origin 6，缺范围依据，故两个历史拒绝都保持有效。

## 3. 最小修改

1. [Work Owner](../../../src/spg/application/governed_obligations.py)在既有 `work_constraint_sources_correspond` 中，仅对 `v3`、显式组件、`CURRENT_VERIFICATION` 的 Git Diff 候选，允许“当前 Production 的精确排除派生 origin + 当前排他文件范围 Clause”进入方法资格。范围 Clause 必须连到**同文、同来源记录、Human explicit、CONFIRMED、当前且目标路径完全一致**的已接纳 SCOPE Fact；继续核验 Clause/Item 的 Human 来源及当前 Production。原 Fact 关系、极性、值、Scope、qualifiers、权限都不改。
2. 生成前提 `_owner_source_preconditions` 与正式 `_projection_binding` 调用同一来源谓词。缺 origin、缺范围依据、错来源/值/版本阶段、额外无关支持、错误目标、旧契约以及以文件范围冒充持续 effect Gate 继续拒绝。候选状态仅 `BOUND_PENDING_EVIDENCE`；实际 Git Diff 必须仍比较全部 changed paths，独立 Review 必须审查整个原排除含义。
3. [独立 Reviewer 请求](../../../src/spg/providers/fulfillment_candidate.py)在既有请求中澄清：当前审查的是可执行的候选方法与后续 Gate 归属，`BOUND_PENDING_EVIDENCE` 不要求此刻已有内容或未来 Seal 收据；持续性 effect Gate 仍必须从当前阶段实际限制执行。这不改 Review schema、结果判定、调用次数或 Guardian。

没有新 Owner、Normalizer、Wire 版本、来源白名单、文件名特例、候选次数或预算变更。模型继续选择消费者，Owner 只编码和校验确定性身份/资格。

## 4. 验证结果及其界限

- 使用原 d277 镜像作为**受控测试依赖**，只读挂载本次两份源码和测试文件、禁用容器网络，运行新旧受影响测试：**161/161 PASS**。覆盖英语/中文不同排他表达、合法 origin+范围来源，以及缺失、错误来源记录/范围值、未来阶段、非当前派生、额外支持、越权路径、effect 冒充和旧契约等负例。相关原 Reviewer、来源和 Fact 方法回归一并通过。镜像本体仍是 d277；覆盖挂载只用于定向回归，**不是本次新源码的资格镜像**。
- 对原 ordinary41 私有库存和两次收据只读重算：旧前提无 `[6,9]`，本次前提有；原第二候选的 `[6]` 仍被拒。仅在隔离副本中把 support 换成 `[6,9]`，其**方法资格**为 `BOUND_PENDING_EVIDENCE`。没有改原 Candidate、给出实际 Diff 证据或运行独立 Review。
- 对原 ordinary34 的已保存第二候选及原 Review 只读复核：两个错误 Diff 组件（1/3）、五个负 source Verdict（0/1/3/4/11）不变；当前 Validator 仍以 `OBLIGATION_SEMANTIC_COMPONENT_MISMATCH` 拒绝。没有借 Owner 修正放行该错误候选。
- 本轮模型调用、实际独立 Review、新 Work、Guardian 调用均为 **0**。Reviewer 请求边界的文字校准尚无新模型行为证据；不能宣称历史 source3 错拒已消失，也不能把旧镜像或旧 Review 算作新修订 PASS。

受控文件 SHA256：Work Owner `502f1886b80218d94f8d3f71277432f9795e68c8448f79fa20f9c072096a8565`，Reviewer Provider `e113b300e84eb18389ad406d06d8447ef1aa3545a18e0eb63f29c96464566a96`，新定向测试 `094f75103880c85c5740c0df203f8e5b3665aaa5de106015a8d66f147b200d9e`；与 ECS 隔离挂载文件相符。

## 5. 尚未解决与下一项必要行动

| 项目 | 本轮状态 |
| --- | --- |
| ordinary34 额外 Diff 消费者 | **真实模型语义选择错误，仍由独立 Review 正确拒绝。** 现有显式局部修复可改相关决定，但原第二候选没有改它们；本轮不伪造第三候选。 |
| ordinary34 source3 计划/履约时机混淆及 source4/11 解释不一致 | **请求边界已澄清，真实 Reviewer 效果 UNKNOWN。** 不能以所有组件 true 强制 source true，也不能据一条 reason 改写“页面”语义。 |
| ordinary41 source20/21 UNRESOLVED | 原第二候选仍未决定“新增页面”完整语义；README 排除已有路径证据方法，但原模型未选择。属于剩余语义选择/证据充分性问题，本次 Owner 修正不自动解决。 |
| ordinary41 source22 | 合法支撑组合已取得**候选方法资格**；原实际候选仍缺必要引用并保持 FAIL。 |
| C3 Closure | **PARTIAL。** 新代码还需按原预算冻结确切运行镜像，在非 Holdout ordinary34/41 上取得真实 Formation/独立 Review 结果；若能合法通过，再沿原 C3 Contract 做必要后续资格。不得用本次受控回归代替。 |

正式生产、canonical main、历史 Work/Candidate/Evidence/Human Decision、原 Holdout 和 Guardian 门禁均未改。受控测试及私有对照可跨电脑从 ECS `/data/watt/ai-native-evolution-20261013/semantic-boundary-calibration-20261014/` 恢复；公开摘要在本目录。该目录中的源码覆盖仅是测试副本，不是已构建的新应用镜像。
