# Trace Analysis Work — 本阶段修复与报告交付

## 结论

**已交付经过 Codex 辅助修订、来源校验和自审的中文报告；尚未证明 Watt Native 能自行稳定产出合格报告。未部署。**

不能将辅助报告的通过，改写为原 Native 执行通过。正常应用中的请求仍为 FAILED，未发布报告；未续跑原尝试、重置预算、放宽引用门禁或添加产品旁路。后续完整自动分析能力按 Human 要求另行演进，本阶段停止扩大取证。

- 独立分支：`codex/watt-trace-self-analysis`。
- 修复提交：`53af5abc81739be93fcf4343126ab5ab68f253fa`、`bde096d210894f9d249e7b3e5545b9df16b0ebe5`。
- 当前源码相关回归：254/254 PASS；Admin JavaScript：35/35 PASS。
- 真实历史 Work：`3ee622b5-b816-5679-afdc-e5de51cd2702`。这是已有资格演示 Work，不是客户留出样本。
- 最新 Native 请求：`1a9c6de8-8aea-4b80-aea9-e78331dcdd61`，FAILED / UNABLE_TO_COMPLETE。
- 辅助报告摘要：`5e5247071cbfc808cfb3029e49b28958ddc247e019ffe4802a26a2e7afb3f3e5`。

## 对照本阶段要求

| 要求 | 实际结果 |
|---|---|
| 读取关键 Owner/Evidence | Native 已读取关键原始记录与源码；审查只使用其已冻结捕获，未再次查询 Owner。 |
| 形成结构化报告 | 已有 Native 草稿；本次交付为 Codex 辅助修订稿，非 Watt 自动完成稿。 |
| 引用与事实一致 | 辅助稿经同一 Analysis Owner 校验；24 个被引用记录保存在证据包内，未发现剩余关联错配。 |
| 不支持结论 UNKNOWN | 历史加载源码、选取命令的决策依据、实际替代动作/重试次数和未分析事件根因保持 UNKNOWN。 |
| 完成提交 | 两个修复已提交，报告及审查证据随本交付提交。 |

“稳定自行生成可信报告”的资格仍未通过。此区别不是 UNKNOWN 被自动补齐，也不是取消 Native 自审或终态门禁。

## 本轮最小修复

### 原始纯文本的字段错误反馈

OBSERVED FACT：eb6d3941 的模型把原始用户输入的目录定位路径当成其内部 JSON 字段。真正的字段拒绝被导航反馈中的 JSONDecodeError 覆盖，修订再次触发同样错误。

VERIFIED FINDING：`EvidenceCatalog.field_navigation` 对纯文本 `body` 再执行 `json.loads`；现改为读取已经捕获的类型值，保留错误引用的位置与有限导航元数据。未新增字段别名、自动引用改写或措辞规则。

### 最低充分范围与预算

本阶段只允许一个详细 finding；其他事件可作为原始观察，根因未分析必须明确。约束体现在调查契约、工具 schema 和提交门禁，不依赖检测报告关键词。原 12 次推理、48 次工具、600 秒总预算不变，较早收起新增取证工具，预留提交、终止及两轮修订/自审容量。

### 自审引用集合由草稿 Owner 绑定

53af5abc 自审对 `/immediate_recovery` 的引用集合少一个、多一个，门禁正确拒绝。现在模型可省略重复抄写的 `evidence_ids`，Owner 将其绑定到不可变的已验证草稿目标。显式提供 ID 时仍严格匹配；未读引用、伪造 ID、漏审目标、不支持断言仍拒绝。语义判断、反证检查和修订仍由模型提出，不自动改写结论。

## 真实执行与辅助修订的边界

本轮保留三个未通过请求的记录，见 `failed-attempts.json`：

1. eb6d3941：原始纯文本导航错误；没有已验证报告。
2. 53af5abc：草稿结构引用通过，自审源集合不匹配，最终超时；不构成语义通过。
3. bde096d2：9 次推理、26 次工具，出现字段定位、占位草稿、缺少 EXECUTION 时间线和时间顺序错误；有界终止。终止前模型报告可用工具为空。其完整触发机制本阶段未进一步调查，不能直接判定为预算不足或 Kernel 缺陷。

没有在同一源码上换请求 ID 反复抽样直至 PASS。辅助修订是本次工程交付的离线审查，不是产品新增的分析管线，也没有改变服务端失败记录。修订者与自审者均为 Codex，不等同独立 Human Governor 审查。

辅助稿的具体修订：

- 按原始 Owner 时间排序；恢复投影引用 `updated_at`，不冒充新事件或精确动作完成时刻。
- 补充冻结捕获中的一条 SETTLED `file.read`、一条 PATH_SCOPE PASS 和明确 Human ACCEPT，且各自保留证明范围。
- 收窄当前状态引用到原始 Work 行；去除将受检范围 PRESENT 写成缺失的条目，未核对内容放在不确定性中。
- 历史根因与排他分类改为 UNKNOWN。当前源码只作条件对照，不凭最终 ACCEPT 排除平台缺陷或证明模型方差。
- 建议先核对真实权限和能力，不假定 `file.read`、`preview.inspect` 等名称天然能等效列目录；不扩权限、增预算或自动重开历史 Work。

已达到这份辅助报告的最低充分证据，停止读取。未追求全部 PWU、全部响应或全部异常覆盖。

## 文件与审查依据

- [中文报告](../evidence/work-trace-self-analysis-minimum-20261013/report.zh.md)
- [结构化报告](../evidence/work-trace-self-analysis-minimum-20261013/report.json)
- [来源记录](../evidence/work-trace-self-analysis-minimum-20261013/source-references.json)
- [语义审查及限制](../evidence/work-trace-self-analysis-minimum-20261013/semantic-review.json)
- [修订来源与失败状态](../evidence/work-trace-self-analysis-minimum-20261013/report-lineage.json)
- [辅助审查读取记录](../evidence/work-trace-self-analysis-minimum-20261013/assisted-read-receipts.json)
- [原 Native 草稿](../evidence/work-trace-self-analysis-minimum-20261013/native-draft.json)
- [失败请求汇总](../evidence/work-trace-self-analysis-minimum-20261013/failed-attempts.json)
- [254 条回归结果](../evidence/work-trace-self-analysis-minimum-20261013/regression.junit.xml)

`artifact-sha256.json` 保存证据文件哈希。完整私有捕获、容器配置及运行材料保留在独立任务证据目录，未将 ENV、凭证或 Provider 隐式推理写入 Git。

## 部署与剩余资格

源码与辅助报告通过不等于 Native 自动分析资格通过。本次没有重建正式 API、Worker、协调器、N1 或 C3 容器，没有修改 Schema、原始 Work/PWU/Self-Refine/验收数据或 canonical main。真实执行前后四组原 Owner 记录摘要一致，仅代表这四组核对，不是全库无变化声明。

当前剩余的明确资格是：**Watt Native 自行完成来源合格的报告、语义修订、自审及真实终止声明**。未达成时应真实失败或受治理地终止；不得用辅助报告回填为自动 PASS。本阶段不再扩大 Kernel、调度或跨项目审计，也不创建后续 Work。
