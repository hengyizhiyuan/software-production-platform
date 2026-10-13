# Trace 分析入口修复与链路验收 — 2026-10-13

## 结果

**截图报错已修复并部署到 ECS，真实 Work 的 Watt Native 分析已完成。**

修复源码：`e207b92ce7b6a670bd48e4a58639593447262637`，独立分支 `codex/watt-trace-self-analysis`。

本次仅处理入口准入、对应提示及链路验证。未修改 C3、canonical main、Worker、协调器、N1 或数据库 Schema。

## 报错原因与修复

服务日志确认两个请求返回 HTTP 409 / `ANALYSIS_WORK_NOT_TERMINAL_OR_BLOCKED`：

- `408e408a-fab8-5a34-b101-b922043cb6fd`：WAITING_HUMAN，DESIGN，无执行队列项。
- `f4fccf61-89ea-5abc-9871-55235df0b37d`：WAITING_HUMAN，PRODUCE，队列 COMPLETED。

原页面显示入口，后端却只允许 COMPLETED / FAILED / BLOCKED / STOPPED，漏掉等待人工决定与验收。因此在模型调用之前就拒绝请求，并直接展示英文错误码。

最小修复：

1. 允许静止的 WAITING_HUMAN / WAITING_ACCEPTANCE 进行只读分析。
2. 排队、领取或执行中的队列仍拒绝，不将 Human 状态投影当作绕过执行排除的依据。
3. 分析历史接口返回真实准入状态，页面禁用不可用的新分析入口；对应拦截提示改为中文。
4. 同一请求的历史结果在 Work 恢复执行后仍可读取，不再启动分析。

权限、引用、原始字段、关联、UNKNOWN、自审及真实终态门禁保留，没有新增针对某个 Work 的规则。

## 真实链路

针对用户最近点击的网页小游戏 Work `f4fccf61-89ea-5abc-9871-55235df0b37d`：

- 请求：`9e01e774-10a7-49c1-bc61-435d2285f0dc`。
- Watt Native：**COMPLETED / RESULT_READY**。
- 11 次推理、26 次工具，约 540.5 秒；仍在原 12 / 48 / 600 预算内。
- 模型生成草稿后处理两次来源校验反馈，完成自审并返回报告，**未人工改写报告**。
- 报告摘要：`424a961285eeb6067418528229a749208e16f292b0cb7b92eb8f2cf5ea86dfcb`。
- 四组原始 Owner 记录前后摘要一致；原 Work 仍等待 Human 决定。分析完成不代表生产 Work 完成。

本阶段只详细分析一个事件，未核对的历史实现、原始响应等保留 UNKNOWN。报告中的模型方差分类是 ROOT_CAUSE_HYPOTHESIS，不是排他根因的独立认证。链路验收不承诺所有未来模型输出均一次通过，也不追求整个 Work 的完整原因分析。

## 部署与接口验证

只替换 `watt-cloud-worker-api-1`，保留原 Compose 配置与已有 CPU 维护。

- 新镜像：`sha256:2968973bd2554b27c8c1d71996cac917e7146df700702a96445ad05729131d9e`。
- 回滚镜像：`watt-cloud-worker:trace-owner-rollback-e207b92c`。
- 上线前：无未释放分配、无活动正式执行队列、无活动分析锁。
- 健康检查与实际导入源码身份：PASS。
- 登录、来源校验、真实报告 GET、同请求 POST 幂等返回、实际 Admin JS 哈希：PASS。
- 两个报错 Work 的等待状态准入：PASS。
- 其他 24 个已有容器的身份、启动时间、状态和重启次数均不变。
- 相关 Python 回归 261/261 PASS；Admin JavaScript 37/37 PASS。

部署目录：`/data/watt/trace-analysis-releases/e207b92c`。回滚保留全部原 Compose 文件，只将最后的 API 镜像覆盖恢复为原镜像。

## 证据

- [Watt 原生中文报告](../evidence/work-trace-entry-fix-20261013/report.zh.md)
- [结构化报告](../evidence/work-trace-entry-fix-20261013/native-report.json)
- [Native 执行结果](../evidence/work-trace-entry-fix-20261013/native-result.json)
- [自审](../evidence/work-trace-entry-fix-20261013/native-self-review.json)
- [限定范围复核](../evidence/work-trace-entry-fix-20261013/independent-review.json)
- [上线结果](../evidence/work-trace-entry-fix-20261013/activation-result.json)
- [实际 HTTP 验证](../evidence/work-trace-entry-fix-20261013/http-replay.json)
- [其他容器隔离核对](../evidence/work-trace-entry-fix-20261013/isolation.json)
- [回归](../evidence/work-trace-entry-fix-20261013/regression.junit.xml)

刷新后台后，可在该网页小游戏 Work 的分析历史查看已经完成的报告；另一条等待人工决定的运营后台 Work 也已解除入口误拒绝。
