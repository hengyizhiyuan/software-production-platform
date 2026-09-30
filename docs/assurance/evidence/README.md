# Watt × Guardian 受控资格验证收据

验证于 2026-10-01（Asia/Shanghai）在隔离的 Git 仓库、HTTP Preview 和一次性 PostgreSQL 数据库上执行。Guardian 源码为 `65bd3c4ea6d39fe0214d78d1ba2cbed8da5cce21`（资格验证时）、`f71484fedcde13d78b5ce38f5a83e43e03bc3c2b`（只调整模块说明的最终提交），分支 `oct/watt-assurance-integration`；Watt 从指定基线 `ed83d69f5970fe31d23e7511876047defafe2d1a` 构建本分支。收据中的 Candidate commit/tree、Preview、请求、Finding 和 Gate 均为测试实际产生的身份和持久化事实。

- [Q1／Q2／Q4：Watt 闭环](Q1-Q2-Q4-watt-loop.json)：Watt 的确定性 Executor 首先写出技术测试通过、但 `/details` 实际返回 404 的 Candidate；Guardian 对 served runtime 发出 `FAIL_REPAIRABLE` 和独立 Finding。Watt 在同一 Work／工程范围内执行修复，产生不同的 Candidate commit/tree，Guardian 对新 Preview 复验为 `PASS`。收据同时保存 API 创建后读取的证据，以及当时 Human Acceptance `PENDING`、Delivery Authorization `NOT_AUTHORIZED` 的状态。
- [Q3：直接通过](Q3-direct-pass.json)：满足明确导航和 API 持久化要求的受控 Candidate 直接获得 Guardian `PASS`，无虚构的修复步骤。
- [Q4：接受与交付分离](Q4-acceptance-delivery-boundary.json)：另一个完整应用样例在人工接受后，远程交付授权表记录数仍为 `0`。这一段使用 Watt 既有完整应用交付流程，与 Q1／Q2 的受控 Python 候选是两个隔离样例。
- [Q5：Human 依赖阻塞](Q5-human-dependency.json)：缺少明确 Human 依赖时，Guardian 返回 `BLOCKED`、不可修复 Finding；没有生成 PASS 或自动修复授权。

Q1／Q2 的 Preview 是从 Candidate Git commit 的源文件执行路由函数的受控 HTTP 适配器；并非 Docker 完整应用部署。完整历史资格活动和远程交付均不属于本次验证。Guardian 的持久化请求与结果完整嵌入收据；Watt 只在运行时保存 Guardian 结果引用和门禁投影。
