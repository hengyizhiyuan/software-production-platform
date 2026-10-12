# C3 Formation 模块修复与开发资格

2026-10-12。**本轮 Owner 内修复与非 Holdout 开发验证完成；C3 仍为 PARTIAL。** 历史 Holdout 在旧冻结组合上的 1/4 live PASS、3/4 FAIL 保留；新组合尚未调用真实模型或 Holdout，不能宣告真实收敛或 Closure。

## 根因与实际修复

[实施前架构分析](analysis-and-design.md)回答职责、确定性假设、A/B/C/D 分类及 UNKNOWN 边界。没有证明模块要求唯一实现路径或 Validator 错拒合法结果。

确认的系统缺口是：当前 qualified-operand 生成分支未接上旧分支已有的**完整物理组件处置一致性**投影。最终 Validator 拒绝仍然正确；修复把同一已有不变量接回当前生成准备，不扩张最终接受集合。

来源缺口仍是模型候选没有满足既有契约，不自动认定为业务目标缺失。已有反馈包含局部错误，但来源联合覆盖和物理组件处置需要修复者自行重新组合。本轮在当前 Owner 中增加联合观察，供原有一次反馈消费。

实际修改只有：

- [Provider 的确切修订](https://github.com/hengyizhiyuan/software-production-platform/blob/f52d39965826ba2e9ddcdba44c85e79bf5c43fc0/src/spg/providers/fulfillment_candidate.py)：复用完整组件冲突投影，接入当前生成分支；新增观察存在时，现有修复请求读取来源联合覆盖和组件联合处置。
- [Work Owner 的确切修订](https://github.com/hengyizhiyuan/software-production-platform/blob/f52d39965826ba2e9ddcdba44c85e79bf5c43fc0/src/spg/application/governed_obligations.py)：当前请求显式绑定 `existing-source-component-convergence-v1`；联合观察保留原文指纹、来源、原始 Route 索引、已定位跨度/引文指纹和处置。已有 Wire/库存/Attempt/收据绑定及恢复复核承接新观察。
- 三个相关测试文件：新增模块控制；补充 PostgreSQL 联合观察篡改；校正一个经旧镜像复现的原有拒绝错误码断言。

**没有修改 `validate_projection_candidate`、组件接纳谓词、领域绑定状态、Wire v1、独立 Review/Guardian 契约、权限、模型路由、重试次数或预算。** 不自动扩展引文、删除冲突 Route、挑选能力或补造证据。集合生成约束针对完整组件；合法部分组件仍开放，并由原有 Validator 与独立 Review 判断，不能声称所有错误都会被 schema 消除。

## 非 Holdout 验证结果

| 证据 | 真实结果与范围 |
| --- | --- |
| [最终镜像模块测试](installed-runtime-receipt.json) | **15/15 PASS**；镜像内安装代码和镜像内测试，均无运行时覆盖。不同合法分解、完整共享依据、多组件协作、部分证据缺失、真正遗漏义务、冲突与反馈身份篡改、恢复及重放均覆盖 |
| [关联开发回归](focused-receipt.json) | 230 项中 229 PASS，1 个旧断言不匹配。该原冻结镜像 [基线复现](baseline-receipt.json) 同样失败；校正测试对实际 `OBLIGATION_SEMANTIC_REVIEW_IDENTITY_BINDING_DRIFT` 的精确期望后 [该项单独 PASS](regression-assertion-receipt.json)。没有将首次运行改写为全绿，也没有改运行时错误码或拒绝语义 |
| [PostgreSQL 恢复](postgresql-receipt.json) | **27/27 PASS**；新建专用无外网命名空间、独立卷与数据库。新观察随既有收据持久化，篡改反馈/响应收据/库存/来源前提/联合观察均拒绝；合法恢复只调用剩余步骤，终态不重复调用 |
| [容量与部分证据负向](capacity-and-partial-receipt.json) | **5/5 PASS**；缺证据的兄弟义务不因已证明的另一义务而升级，容量停止和敏感值不进入收据，预算不重置 |
| [原始开发 Wire 对照](non-holdout-development-comparison.json) | ordinary34 两次候选分别观察到 6、7 个来源缺口；ordinary41 第二候选观察到 1 个物理组件冲突，新增生成约束捕获该组合。首次非法 JSON 的全覆盖继续 NOT_EVALUABLE；观察到的部分组件不能变为合格 Candidate。全部原始 Wire/库存指纹保留，不修补后冒充历史模型成功 |

初次新增测试 10/14、随后 13/14 的失败均留存。原因是测试错误地要求合法背景也为待证据状态、调用既有夹具时未启用覆盖故障选项，以及旧测试 serializer 对部分组件使用历史 q=null 数字跨度而不符合当前生成输入协议。仅校正测试对当前真实契约的使用，未放宽运行时接纳；最终安装镜像 15/15 收据是最终控制结果。

开发对照和独立审查夹具都是**受控 Provider 结果**，不证明真实模型会提出这些合法分解。正例证明现有表达/消费能力，不冒称任意语义等价实现已经被真实模型确认。

## UNKNOWN 与真实缺陷的区别

- 联合覆盖 `COMPLETE` 仅指原文几何完整，不是目标满足或内容 PASS。
- `semantic_fulfillment=UNKNOWN` 表示独立语义判断尚未建立；`actual_evidence=NEED_EVIDENCE` 是候选修复观察，不是新增运行时状态或 Evidence。
- 方法合法的计划使用现有 `BOUND_PENDING_EVIDENCE`；方法/来源无法合法建立时保持 `UNRESOLVED`；实际 Owner 证据不足保留 `UNVERIFIABLE_CURRENT`，不能升级为通过。
- 真正遗漏组件仍触发 `SOURCE_CONTRIBUTION_LOST`；同组件冲突仍拒绝；未知终态停止、历史反馈重算、身份漂移和独立审查门禁均保持。

## Exact source / image

- 代码提交：**`f52d39965826ba2e9ddcdba44c85e79bf5c43fc0`**；Git Tree `c8ad5b06283905e218786ef785e940a82edd1dbf`。
- Guardian `0d7aca954588c8ad3883dbedb730e59dc1d7b867`；ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c`，均未修改。既有 ECF 负向测试来源也保持原身份。
- [新构建镜像](image-build.json)：**`sha256:24d9f809ad3cd6b98d68948020fccd3997c09ee947f9cb5acd57e48abb44e5b1`**，tag `watt-c3-module-adaptation:f52d3996-20261012`。本地 Image ID 为实际 Docker 事实；RepoDigest 未发布，不以 tag 冒充 Digest。
- 使用既有 C3 Dockerfile、完整确切 Git archive、已校验 Owner 构建输入及缓存依赖基础镜像，离线重新安装 Watt；没有只覆盖旧镜像中的两个 Python 文件。[实际安装校验](installed-attestation.json) PASS，实际导入、完整构建输入、包版本、Owner 与源码身份保留。

前期开发回归明确使用旧基础镜像 + 只读开发源挂载，不能当作新应用镜像资格。Git 冻结后的新镜像重新安装并检验；最终 15 项无覆盖。早期测试夹具校正的血缘与最终源码对应见 [执行输入对账](execution-lineage.json)。

## 成本、风险与停止点

新增真实模型调用 **0**、实际模型 Token **0**；真实模型收益、推理成本和是否改善第二候选收敛 **UNKNOWN**。构建一次，52.545 秒。PostgreSQL 定向测试 51.417 秒；最终安装校验 2.233 秒、镜像模块测试 7.674 秒。其余每轮实际耗时见原始收据；货币成本及 CPU/峰值内存实测 UNKNOWN，资源上限不算用量。

Schema 原始紧凑 JSON 大小在两个开发库存上分别从 8,989→25,463、8,526→28,472 字节；联合观察约 12,558–14,231 字节。它们是实际表示字节数，**不是 Provider Token Usage**。输入体积增长与真实模型是否遵守集合约束仍是待实测风险，未提高任何预算；容量耗尽仍按既有契约停止。

原 Candidate、Work、Preview、独立 Guardian PASS、Human 决策和旧 Holdout 均未重放或修改。正式服务、canonical main、数据库 schema 未改。仅专用新测试数据库发生明确夹具写入；它已停止，独立卷保留。

本轮按 Human 指定的顺序，完成分析、最小实现及开发验证后停在 **Holdout 复验决策**，不因为控制结果通过而关闭 C3。见 [决策包](holdout-requalification-decision-package.md)。

完整恢复位置：`/data/watt/c3-semantic-convergence-20261009/formation-module-adaptation-20261012`。`private/` 留存失败日志和新隔离测试凭据（不发布）；`image/context/`、确切源码 archive、构建记录、所有容器/新 PostgreSQL 卷保留；公开证据与本分支一致。恢复未实演，不宣称恢复资格 PASS。
