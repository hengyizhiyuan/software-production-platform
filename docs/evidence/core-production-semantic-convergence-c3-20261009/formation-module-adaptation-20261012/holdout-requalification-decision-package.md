# Human Decision：是否进入独立 Holdout 复验

本轮指定步骤 5 的决策材料；**不是 Integration、Acceptance、Delivery 或生产部署申请**。

## 可审查的实现与证据

- Watt `f52d39965826ba2e9ddcdba44c85e79bf5c43fc0`，Tree `c8ad5b06283905e218786ef785e940a82edd1dbf`。
- 实际 Image ID `sha256:24d9f809ad3cd6b98d68948020fccd3997c09ee947f9cb5acd57e48abb44e5b1`。
- Guardian `0d7aca954588c8ad3883dbedb730e59dc1d7b867`；ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c`。
- [修复报告](report.md)：当前 Owner 的生成准备和联合反馈消费；最终镜像 15/15、真实 PostgreSQL 27/27，相关负向保护通过。Validator、独立 Review、Guardian 及已有预算未降低。
- 尚未进行任何新的真实模型调用，输入表示增量已测量，实际 Token 与收敛收益仍待证据。受控验证不替代真实资格。

## 建议的决策

建议批准**在上述固定组合上进入独立 Holdout 复验**，以真实结果检验本模块的有界消费/收敛收益。未批准前不执行。

批准后的执行条件：

1. 独立 Reviewer 执行原封存库存与原 Oracle；执行者不查看私有输入、Oracle、失败候选或用结果调优。
2. 保持原 C3 Mission、适用资格范围、模型、推理配置、16384 输出上限、超时与传输恢复规则。每 Case 最多两个 Formation Candidate、一次既有反馈、每个合格 Candidate 一次独立 Review、最多四次 Formation/Review 逻辑调用；其他原有 suite 累积上限继续适用，执行前与独立收据核对，不增加预算。
3. 原 Holdout trial 已终态，不重置旧 trial/Work 的计数，不替换失败 Evidence。新修订复验使用新的资格收据和独立隔离执行身份。批准复验才授权这次新的有界资格执行；不会将旧 trial 剩余预算解释为自有重开权限。
4. 既有封存项已经执行过，应标为**原封存库存在新修订上的独立复验**，不能重新称为首次未见 Holdout，也不声称新的未知样本资格。不得修改原输入、预期或资格条件来获得通过。
5. Provider/容量/身份/权限失败及未观察终态按原契约停止。失败不自动触发源码调优、另建 Work 或额外请求。独立 Reviewer 保存实际 Token、调用/反馈血缘及终态，按真实资格判断 C3 Closure。
6. 保持原 G0 生产结果及封存 Candidate；不重新生产、集成或授予 Human 接受/交付。正式服务与生产数据不动。

如果选择暂不进入，则当前停点为“工程修复和受控开发验证完成，真实模型泛化资格未取得”。不能宣告 C3 CLOSED。
