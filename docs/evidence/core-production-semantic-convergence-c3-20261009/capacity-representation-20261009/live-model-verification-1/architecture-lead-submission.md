# C3 — 限定真实模型验证：Architecture Lead 结果提交

**结果：STOPPED — Formation Capacity Blocker；C3 保持 PARTIAL。授权的单次验证已完成并停止。**

本文件是 2026-10-10 Human 对 [限定决策包](../live-model-decision-package.md) 明确批准后的新增证据。此前专项报告中的“零真实调用／等待授权”描述其当时检查点；本次新增一次 Formation，不回写或替换旧收据。

## 1. 精确执行身份

| 项目 | 实际身份 |
|---|---|
| Watt 源码 / Tree | `e0df8196cb51480f542af13b40cfa77fca6b6a6e` / `d479d61f5fcac075a5af3a274f60cbe3f6e9f53f` |
| 实际镜像 | `sha256:7a4ac00e3599bda2dbcebe46b15dd0b45f3be86552021023ebd288eb732f7b35` |
| Guardian / ECF | `d01bac1ad153e1eadefafe87d2ea4f5d65896ab6` / `5aa4f8833c359c15bd059eda5972aa3915bcc18c` |
| 原始持久库存 | Work `048189aa-0613-5307-b6f4-c430e7977f93`；Reality `332a3a38-8719-580c-a1a2-c331ae14a5ae`；26 项来源，12 个已有 Capability |
| Inventory 指纹 | `7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf` |
| 库存快照 SHA256 | `9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c` |
| 模型配置 | DeepSeek `deepseek-flash`，reasoning `low`，`max_output_tokens=16384`，timeout `120` 秒；未改变 |
| 执行时间 | 2026-10-10 **00:58:44.028 → 00:59:44.619 Asia/Shanghai**；收据 UTC 为 2026-10-09 16:58:44.028 → 16:59:44.619 |

执行前通过离线预检：实际镜像、288 个已安装源码文件哈希（Watt 278 / Guardian 5 / ECF 5）、原始库存、模型配置、wire request/table/schema 指纹匹配。实际 HTTP 请求体 54,365 字节，SHA256 `9e9e5ab4753c4e20115e721b2c933cd9db20a1c36a7744dd7e037073eea3041d`，与决策包的冻结测量完全相同。不存在应用源码覆盖。

## 2. Provider 实际结果与用量

**E1 / PROVEN_SCOPED：** HTTP `200`；收到首个响应事件；最终 `provider_status=incomplete`，`termination_reason=max_output_tokens`，错误分类 `INCOMPLETE_RESPONSE`。请求 ID：`aba0aaa8-1db5-45c9-94a4-0cbac10341b4`。本次没有 HTTP 拒绝或超时终态。

| Provider 报告字段 | 实际数值 |
|---|---:|
| input_tokens | 17,466 |
| output_tokens | 16,384 |
| reasoning_tokens | 16,384 |
| cached_tokens | 0 |
| total_tokens | 33,850 |
| 可见 JSON 的独立 Token 数 | **UNKNOWN** |

Formation **1 次**；HTTP 请求钩子／发送阶段各 **1 次**；传输重发 **0 次**；Semantic Review **0 次**；Self-Refine **0 次**。观察耗时 **60.591191162 秒**，不是配置 timeout 的消耗推断。金额、CPU、峰值内存没有测量。

## 3. 可以确认与仍然 UNKNOWN

本次 Provider 报告的 reasoning Tokens 达到输出配置上限，且其报告的 output Tokens 与 reasoning Tokens 相等。没有观察到 `provider_first_token` 阶段，也没有完成的输出或可解析 Candidate。该精确请求在现有配置下仍因输出容量停止；受控样本的 78.254736% 输出字节缩减没有证明真实模型恢复。

**不能据此断言可见 JSON Token 数为零。** Provider 数值的统计含义未在本次被独立验证；流未记录可见 JSON 的独立 Token 计数。不得把 input、output、reasoning 相加重复计费，不得以字节换算 Token。

本次新增了足以区分容量终态与 HTTP 拒绝／超时的真实证据，但不能重建原始事故 Work 的请求、隐藏推理或历史 Usage，也不能证明复杂度由哪一段库存、Schema 或模型规划行为独占造成。旧历史 UNKNOWN 保持不变。

## 4. Candidate 与门禁结果

- Formal Candidate：**NOT_REACHED**；冻结 Runtime 在不完整终态抛出 typed failure，Provider 未得到完整输出进入 decoder。
- 来源、组件、Scope 与 Owner 的 Candidate 确定性校验：**NOT_REACHED**，不能报告 PASS。
- 独立 Semantic Review：**NOT_EXECUTED**，没有合格候选，符合条件调用规则。
- Runtime Admission、Work/PWU、Git、Candidate Seal、Verification、Guardian、Human 决策：**未执行／未授予**。
- Provider 的 `retryable=true` 只是错误元数据；没有据此执行另一次请求。

本次只证明限定验证的真实停止与证据连续性。既有 191 项受控回归和 4 项 PG PASS 仍成立于其原定范围；不能替代本次未取得的真实计划资格或完整 C3 资格。

## 5. 提交给 Architecture Lead 的结论

**紧凑表示机制在受控范围合格，但该精确库存的真实 Formation 容量阻塞未消除。** 新增证据把讨论重点收窄到 Provider 报告的 reasoning 预算消耗和语义形成复杂度，不能继续假定完整 JSON 回显字节数就是唯一原因。

下一项行动是由 Architecture Lead 审查此实际用量、不可见输出边界和既有容量分析，决定是否需要进一步有界原因取证或新的架构／资源决策。改变预算、模型路由或跨 Owner 契约均不属于本次执行。**本次不继续模型请求、G0、Self-Refine 或修复。** C3、C4、N1、N3 状态与路线不因此改变。

## 6. 原始证据与恢复

- [完整实际结果](live-model-result.json)：阶段、请求身份、Usage、失败、未执行状态。
- [离线预检](preflight-container.json)；[调用前容器事实](live-container-before.json)；[调用后容器事实](live-container.json)。实际镜像在容器存在期间读取。
- [授权记录](authorization.json)；[严格探针](verify_live_model.py)；[隔离控制器](run_authorized_verification.py)。新增控制器仅用于此次证据执行，不修改已冻结应用。
- [本次公开文件哈希](public-file-manifest.json)；[恢复与远端交付](delivery-and-recovery.md)。

ECS：`/data/watt/c3-semantic-convergence-20261009/capacity-representation-20261009/live-model-verification-1/`；公开结果在 `evidence/`，独立 Provider 凭据和受保护日志在 `private/`，不进入 Git。未保存隐藏推理、敏感 Prompt、密钥或原始 Provider 私有响应体。没有生成 Candidate 私有文件。

原始 Work、Owner、历史 Candidate、Human Decision、Quality Ledger、Holdout 和正式生产服务均未修改。运行容器已经正常退出，保留用于恢复和审查，不启动后续执行。
