# C3 Closure Delta

**C3 PARTIAL — Exact Engineering Blocker**。本轮 R1/R2/R3 有界修复已取得资格；完整 G0 与独立 Holdout 尚未取得资格，不启动 C4/N1/N3。

## 确切交付身份

- 分支：`codex/c3-open-semantic-obligation-convergence`。
- 源码：`e8e04b296b31d776a13dda728fa19469681cbaab`；Tree：`a349e40ea0c328ad55574dc668e884a137a19944`。
- 新镜像：`sha256:4d3c64b1e3543a3574cd69b435d6f703fad6edc23b9db7d54d799dc1a652bf6e`。
- Guardian：`d01bac1ad153e1eadefafe87d2ea4f5d65896ab6`；ECF：`5aa4f8833c359c15bd059eda5972aa3915bcc18c`，本轮均未改动。
- 新建隔离数据库：`spg_c3_continuation_fixture`，迁移 `20261007_72`；资格后已停止其 PostgreSQL。

[构建身份](continuation-final-image/build.json)、[实际导入](continuation-final-image/actual-imports.json)、[321 项镜像内回归 PASS](continuation-final-image/watt-continuation-receipt.json)、[5 项 PostgreSQL Owner/状态回归 PASS](semantic-owner-pg/receipt.json)。没有源码/测试覆盖，没有真实模型替身冒充 G0。元数据中的 unsupported ECF 仅为负向测试输入，不是运行 Owner。仅执行了一次新 Docker 构建；此前 `0d324c1…` 准备归档未构建，后续格式提交形成最终确切修订。

## Findings 的变化

| 项目 | 本轮真实结果 |
|---|---|
| P0 | 一次获授权的历史库存请求诊断：已发送，HTTP 200，随后 `INCOMPLETE_RESPONSE` / `max_output_tokens`。**本次输出上限阻塞已证实，未证明有效容量修复**。不是已证实的超时或 HTTP 拒绝；历史原因仍 UNKNOWN。[详情](provider-diagnostic-delta.md)。 |
| Runtime 前停止 | 保留已资格的 `UNRESOLVED → BLOCKED`，未重复实现；相关原有停止回归在新镜像继续 PASS，不创建 Runtime/PWU 或权限。 |
| R1 | 新建目标无需伪造已有源码引文；仍必须具有真实 Human 来源、exact Tree/revision、完整行为覆盖、路径与权限资格，Proposal 独立复核。既有修改仍要求精确源码引文。**22 项正负向回归 PASS**。[审查](../r1-greenfield-target-proof-review.md)。不是已修复历史 Work408 的证明。 |
| R2 | 原 Semantic Step / Model Runtime / Self-Refine 收据保留失败阶段、稳定码、候选 SHA、脱敏反馈、血缘与预算。失败不复用旧成功观察；终态已有用量及实际重试次数可安全保留，缺失值仍 UNKNOWN。**13 项语义失败、12 项 HTTP/终态诊断回归 PASS**，另有 3 条真实 PostgreSQL Semantic Step 路径通过。[审查](../r2-semantic-failure-continuity-review.md)。与 Formation 分开资格。 |
| R3 | Admission 的 READY 与 Task/Runtime 就绪仍分开。确认了“新投影未读取有效持久 stop”的独立缺口，现仅对当前 Work/Reality/PRODUCE Step/Source Owner 严格匹配记录显示既有 BLOCKED。**38 项回归 PASS**，过时/错误身份及后续 Human/Candidate Gate 优先级受保护。保留 [旧镜像 1 FAIL 反例](pre-fix-stop-projection-control2/receipt.json)。[审查](R3-R4-review.md)。 |
| R4 | 保留 Work408 Human Attention 责任 Finding/Handoff：自动预算耗尽可以停止，但不自动构成 Human 必须修改产品目标的依据。**未实施 C4 路由/高级恢复，也未重新运行 Work408**。 |
| UNKNOWN | Work408 第二次 ValueError 的原因、阶段、候选及事故 Runtime 身份；历史 C3 Provider HTTP/原因/用量；已消失的 C2 容器实际 image。独立 Product Source 检查不冒称事故 Runtime 身份。 |

证据等级：E1 为保留的 Owner 历史记录，受其实际采集覆盖限制；E2 为新确切镜像/SQL 的受控观察；E3 为精确源码检查。源码判断不追认为历史效果，HTTP 200 不等于 Work、Candidate 或 Assurance PASS。

## 真实投入

- 开发快照一：73 PASS / 2 FAIL，12.132s；两项严格契约测试的接线/断言已按日志修正，产品门禁未放宽。快照二：118 PASS，12.754s。
- 最终构建：23.627s；镜像内 321 PASS：21.885s；独立 PostgreSQL 5 PASS：22.143s。开发重复执行不叠加为最终独立覆盖。
- benign synthetic Provider 诊断：1.837s，156 tokens；历史库存诊断：56.329s，数值用量 UNKNOWN。共两次逻辑模型诊断入口；未新建真实生产 Work。推理 token 属于 output，不重复累加。
- 原反例首个控制器 0 tests/exit 4（workdir 缺失）与修正控制器 1 FAIL 均保留，不算 PASS。
- 新镜像恢复归档：41.653s，336,433,522 bytes，SHA256 `04cd43b67227e7aa70c3c8b47e6cd3c379564d1f78631abf6a8c85c1f3b260ae`；文件权限 0600。
- 金额、CPU/GPU 秒数、Codex reasoning 用量 UNKNOWN；没有提高模型、测试或重试预算。

## 具体剩余资格与下一行动

1. 在不改变请求语义、不增预算、不放宽校验的边界内，取得可证明的 Provider 条件变化或既有 formation 边界的有效修复。当前仅已知新诊断的输出上限原因，模型行为、容量与表示开销尚未因果分离；没有再盲试 Work 的依据。
2. 有上述依据后，才在最终确切修订/镜像执行新的隔离正常入口 G0，完成 Worker → Git → Verification → Seal → 适用独立 Guardian，保持 Human Integration/Acceptance 待决。当前受控资格不能替代该链路。
3. Holdout 仍封存、未读取、未资格；本补充指令不构成解封授权，内容未用于实现调优。审查者的独立资格仍未完成。
4. R4 仅交接 C4；不改变 Roadmap、N1 或历史验收，不伪造 Human Acceptance，不合并/部署 main。

## 持久化与保护

代码和公开证据推送到原 C3 分支；ECS 恢复位置为 `/data/watt/c3-semantic-convergence-20261009/continuation-20261010/`。新镜像归档及 SHA 见 [恢复收据](image-recovery-receipt.json)。旧六库/cold 检查点 `private/checkpoints/20261009T134034Z-2d204f9031494a77b922f76c95b7569a/` 保留。新 fixture 凭据和原 Provider 文件均在私有目录，不入 Git。跨电脑以远端分支、ECS 路径和哈希恢复；未宣称已做 restore、异地备份或多库原子快照。目录名称是标识，实际采集时间为 2026-10-09 UTC。

未修改原事故 Work、密封 Candidate、Human Decisions、Quality Ledger。未写入 main 或重启生产角色。最终只读观察：ECS source HEAD `5de657f3…` 属于独立 admin 任务，ECS main ref 仍 `ee5bd86…`；本轮 C3 push 前远端 Watt main 是 `5b7bf217…`。这些是不同身份，不归因为本轮修改。只推送明确 C3 ref，并核对远端 SHA。
