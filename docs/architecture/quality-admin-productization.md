# Quality Admin Productization v1

## 权威与边界

Admin 是既有 Quality ledger 和生产 owner 的可读投影与命令入口，不拥有第二份生产事实。六个主入口是总览、质量、问题、学习与改进、风险与保证、运行与资源。原始身份、枚举、指纹与 JSON 留在默认关闭的工程证据层。Workspace 四象限不受此改动影响。

总览优先展示不同问题和可证明的历史回退。比较严格绑定相同 Case version 与 policy fingerprint，使用固定 run member 的 cohort。缺少当前运行版本的验证不能沿用旧版本宣称合格；未观测、未知和失败均不会被当成通过。当前视窗为最近 500 次观测，不是整个产品的完整资格证书。后续通过可标记修复再验证，不能自动关闭原 Finding。

## Production Trace

`GET /api/admin/case-runs/{case_run_id}/trace` 返回历史资格投影。Story 和 Diagnostic 使用同一事实集，没有独立 Trace 表。来源包括不可变 Case lineage、独立 evaluator evidence、校验和约束的 qualification JSON、已发布完整 WIC conversation，以及按精确执行身份和历史时间边界读取的 source snapshot / effect receipt。

历史 Case 不读取当前 Product/Work 来填补缺失。封存 Holdout 不披露材料或答案。外部 JSON 必须位于当前 owner-runtime 的 qualifications 目录，满足 SHA256、大小和路径约束。工程视图同样过滤 credential 与隐藏思维链。未采集数据明确显示，不能虚构对话、搜索、资源消耗或部署。

`GET /api/admin/traces/{kind}/{entity_id}` 支持 Product、Work、Interaction、PWU、Candidate 和 Deployment 的当前 owner 记录查询；明确标记与历史资格快照的区别。此入口为未来支持工作提供可复用投影，不实现 Support Center。

生产单元使用 canonical plan graph 的依赖关系，输入来自 exact production snapshot；依赖输出缺失时不借用根节点或最新仓库修订。完整事件按 owner timestamp 展示，暂停、恢复、自修复和失败不会因最终通过被压缩掉。模型调用只展示结构化请求、可观测提案、provider receipt 与实际 token/耗时。工具提案与实际 effect receipt 保持区分。Guardian 独立保证与 Human Acceptance 是不同权威。

## 运行控制与学习

Start、Pause、Resume、Stop、Failed/Selected/All rerun 继续调用既有 QualityService。暂停停止以既有安全边界为准，持久化状态、lease fencing、Stop-the-Line、原结果不可变与新 run 的父子血缘不变。

两个候选的人工偏好增加五种方向。明确选择“差不多”保存 tie，没有胜出者，不能覆盖客观失败；不自动生成学习信号、策略晋升或生产配置变更。已有多候选记录和后端接口保持可读取，五方向表单仅用于精确的两个候选。

## 指标与限制

运行资源读取既有 Operations samples、服务探测、Worker registry 和 allocation。PWU tokens 与模型时间来自实际 provider receipts；排队与运行时间来自精确生命周期事件。CPU、内存、磁盘变化、网络、工具或验证时间未逐单元测量时展示“未采集”，不替换为零。当前不实现计费、分布式 tracing 或跨主机 Worker Pool。

旧资格缺少某阶段时只展示已保存事实与缺口。暂时不能从未见过的工程证据自动归因严重程度，不能把晚于资格观测的产品状态包装为历史。当某节点没有显式 DAG（旧单 PWU）时展示无已记录前序依赖，不能推断虚构依赖。
