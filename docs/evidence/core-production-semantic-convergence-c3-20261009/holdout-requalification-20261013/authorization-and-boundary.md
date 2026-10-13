# C3 独立 Holdout 新修订复验：授权与证据边界

Human 于本轮明确批准进入独立 Holdout 复验。2026-10-13（Asia/Shanghai）。本轮只验证，不以 Holdout 调优、改输入/Oracle、加特例、改变 Validator/Guardian 或历史工程事实。

执行前核对：

- 原 C3 分支 HEAD/remote `5007cf0980796d5343e545b828ae659755b63d77`，与冻结应用修订相比 `src/`、`tests/` 无差异；预先存在的文档修改和未跟踪开发文件保留。
- Watt `f52d39965826ba2e9ddcdba44c85e79bf5c43fc0`，Tree `c8ad5b06283905e218786ef785e940a82edd1dbf`。
- Docker 实际 Image ID `sha256:24d9f809ad3cd6b98d68948020fccd3997c09ee947f9cb5acd57e48abb44e5b1`；实际源码与 Owner 标记对应冻结组合。
- Guardian `0d7aca954588c8ad3883dbedb730e59dc1d7b867`；ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c`。
- 原封存八项库存身份 `3f093e0d09bec5d2f213ba4e823adbb6dcf42678acc4f76847bf4bb46b1eedb0`。这是已执行库存的新修订独立复验，不称为首次未见资格；不重开旧终态 trial 或改写原 1/4 live PASS、3/4 FAIL。

由原独立 Reviewer 执行原输入/Oracle，只向实现者提供脱敏、可关联的结果和收据。封存文本、Oracle、原始 Candidate 不交给实现者。不读取原成功 G0 的定向人工修复上下文。

每 Case 最多两次 Formation、一次现有反馈、每个确定性合格 Candidate 一次独立 Review，最多四次 Formation/Review 逻辑调用；原 suite 的其他累计上限、模型/推理配置、16384 输出上限、超时和传输恢复规则保持。新修订试次使用独立执行身份和收据；不把旧 trial 剩余预算视作重开权限。未知终态、容量、身份和权限失败按原契约停止，不附加概率重试。

复验需逐场景报告原/新 Projection、证据 Owner 映射、确定性/独立语义结果和 Guardian 的实际调用范围。候选计划的语义通过不是真实 Evidence PASS；受控 Owner 负向验证不能冒称该场景取得真实 Work Assurance。

保留已有 G0/Work/PWU/Git/封存 Candidate/Verification/Preview/实际独立 Guardian 历史资格；不重新生成生产结果，不自动 Integration/Acceptance/Delivery。C3 原 Mission 与 Closure Contract 不变。最终按真实结果报告 CLOSED 或 PARTIAL。
