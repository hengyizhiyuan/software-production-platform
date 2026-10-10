# C3 Option A — 真实模型有界收敛结果

日期：2026-10-10。状态：**C3 PARTIAL — Exact Formation Wire / Feedback Blocker**。
本次批准的独立验证已结束并停止；没有继续模型调用、修复、G0 或其他阶段。

## 1. 冻结身份与证据边界

| 对象 | 精确身份 |
|---|---|
| Watt application commit | `a91442c21ed487b10d8dc38023b0807787a29648` |
| Watt application tree | `80778b67a7147902d10e9f14d669150e6df6d809` |
| 执行前证据 HEAD | `d879e28bcb485390329bf2dcfe676f6ba45a0af3` |
| Guardian | `76c1e87a1b29d151f4ed949748e3298f2169c5b1` |
| ECF | `5aa4f8833c359c15bd059eda5972aa3915bcc18c` |
| Docker 实际 image ID | `sha256:90f2cd847ad891fda6ca95b5736c84b680c9d58bd6a3203bf0ea31c970da0f16` |
| 实际 container ID | `08fb61d073076a7f219cb1869a683bedbaffa88894ad811741bc8f373e5ffb6d` |
| 26 项库存 fingerprint | `7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf` |
| 12 个 Capability fingerprint | `a2e695783b122373f0ed308a959fa4e3116c4a9df5454dbedd81695071153b17` |
| 原始 basis 文件 SHA256 | `9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c` |
| 实际 import attestation SHA256 | `d28d6924095851996f94b83e21545fd294b2bc9197fa5a9bae0492be4122060f` |

只读取历史 Work `048189aa-0613-5307-b6f4-c430e7977f93` 的脱离数据库的已保存输入，
Work Reality `332a3a38-8719-580c-a1a2-c331ae14a5ae`，Product Source `465038ded6cf4ba335a11577de76acb1dea55b76`。
新观察收据不是原 Work 的新 Owner 事件；未连接业务数据库、未修改历史记录。

无网络预检验证实际安装的 278 个 Watt、5 个 Guardian、5 个 ECF 文件散列。
隔离容器使用 UID/GID 10001:10001、read-only root、cap-drop、no-new-privileges；
只挂载只读 basis/import attestation/probe 与本次新证据目录，没有源码覆盖、数据库或 Docker socket 挂载。
实际 Docker 身份与挂载见 `live-container-before.json` / `live-container.json`。
Formation 使用 deepseek-flash / none / 16384 / 120 秒；Review 配置仍为 low / 16384 / 120 秒但未调用。
复用现有两候选、一次反馈流程与传输恢复约束；没有新增模型重试、预算或权限。

## 2. 真实调用、用量与终态

| 观察 | Formation 1 | Formation 2 |
|---|---|---|
| Response ID | `299cd390-9f47-41af-b27f-1bcded4d6c06` | `0b45eaa3-9f96-42e6-8a23-b6f2d2ab72e4` |
| HTTP / Provider 终态 | 200 / response.completed | 200 / response.completed |
| 实际 input tokens | 17588 | 17718 |
| 实际 output tokens | 2758 | 1883 |
| 其中 reasoning tokens | 0 | 0 |
| 其中 cached input tokens | 0 | 14336 |
| 实际 total tokens | 20346 | 19601 |
| 调用观察耗时（秒） | 9.147083193 | 6.818657965 |
| 原始输出字节 | 8852 | 5794 |
| 原始输出 SHA256 | `c60c7f4d1060017a8ddbdd289105350bbfa4aefca0a94f3845d9cc496d83267b` | `98b70541f2b10f3f00a04ba797d0e393781a4143ecac0af109c4d31f437132df` |
| raw compact route 数 | 37 | 28 |
| 确定性结果 | WIRE_FACT_KIND_INVALID | WIRE_FACT_KIND_INVALID |

流程开始 `2026-10-10T02:35:00.568565Z`，结束 `02:35:16.709012Z`，耗时 **16.140484873 秒**。
累计 input **35306**、output **4641**、total **39947**、reasoning **0**、cached input **14336**。
cached 是 input 的子集，reasoning 是 output 的子集，不能重复加总。
共 **2 个逻辑调用、2 个 HTTP 请求、1 次反馈、0 次 Semantic Review、0 次传输恢复**。
Provider usage 均实际可观测；可见 JSON 的单独 Token 数及货币成本为 **UNKNOWN**。
本次未观察到容量耗尽或传输错误；不能据此替换旧失败的历史原因。

## 3. 完整可评估错误集合与身份

两次原始 wire 均通过 JSON / compact schema、请求 fingerprint 和索引表 fingerprint 校验，
但在构造 canonical Fulfillment Candidate 前被严格 decoder 拒绝。
因此 canonical Candidate / component identity **未形成**；分析 JSON 中的 route / proposed component hashes
均明确标记 `RAW_PROPOSAL_ONLY_NOT_CONSTRUCTED_OR_VALIDATED`，不得作为合格候选身份。

只读分析在 exact image、network=none、私有文件只读挂载下检查全部可独立评估的 wire 索引和跨度；
未删除、修补、重解码或接纳候选。输入前后散列相同。

| Attempt | zero-based raw route | source | capability | 不合法引用 | 实际种类 |
|---|---|---|---|---|---|
| 1 | 36 | 25 / WORK_CONTEXT | RETAIN_CONTEXT | f=6 | IR_CLAUSE |
| 1 | 36 | 25 / WORK_CONTEXT | RETAIN_CONTEXT | f=8 | IR_CLAUSE |
| 2 | 22 | 25 / WORK_CONTEXT | RETAIN_CONTEXT | f=6 | IR_CLAUSE |
| 2 | 22 | 25 / WORK_CONTEXT | RETAIN_CONTEXT | f=8 | IR_CLAUSE |

四个可评估错误均为 `OBLIGATION_FORMATION_WIRE_FACT_KIND_INVALID`。
source 6：`ir-clause:ceddc1a3-ba0d-5672-adae-85afc5309e67:work_kind_code_work:c1`；
source 8：`ir-clause:ceddc1a3-ba0d-5672-adae-85afc5309e67:work_kind_code_work:c3`。
没有发现其他独立 wire 索引/跨度错误；这不表示后续语义、Scope、权限或证据检查合格。

第一份 raw spans 覆盖全部 26 来源的非空白文本；第二份对 source 4、9、10、12 没有完整 raw span 覆盖。
相关精确来源、跨度与 raw route/component hashes 全部保留在 `retained-wire-analysis.json`。
raw 文本覆盖不是语义完整性证明；37→28 的 route 减少不能视为收敛成功。

## 4. 一次反馈与有界停止

第一次验证失败观察收据：`d1d48aae-5c34-413d-9fe4-4f99b1b54a11`。
反馈实际进入第二次请求，内容为：

```json
{
  "schema": "fulfillment-validation-feedback-v2",
  "inventory_fingerprint": "7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf",
  "primary_error": "OBLIGATION_FORMATION_WIRE_FACT_KIND_INVALID",
  "violations": [],
  "additional_violation_count": 0,
  "not_evaluable": ["INDEPENDENT_SEMANTIC_REVIEW", "ACTUAL_OWNER_EVIDENCE", "ASSURANCE"]
}
```

第二次失败终态观察收据：`b90673cc-d6f9-44c8-bdfc-9e8825a56c58`。
两候选预算用尽，终态 `OBLIGATION_FORMATION_WIRE_FACT_KIND_INVALID`；派生绑定为 26 个 UNRESOLVED。
收据阶段名 `CANDIDATE_VALIDATED` 表示记录一次校验操作；实际 `validation_passed=false`，不是 PASS。
请求、响应、反馈和六个观察收据的时间、ID、预算与脱敏字段见 `live-result.json`。

## 5. 已证实原因、未知与下一边界

**已证实模型输出违约：** frozen Instructions 明确 `f=linked FACT source ordinals`，索引表提供 source kind；
两个完成的输出均将 IR_CLAUSE ordinals 填入 f。decoder 按原契约拒绝，保护有效。
代码依据：`src/spg/providers/fulfillment_candidate.py` 的 compact wire Instructions 和 FACT kind 检查。

**已证实反馈信息缺口：** wire decode 失败时 canonical candidate 尚为 None，
`src/spg/application/governed_obligations.py` 的既有 `projection_validation_feedback()`
无法从 canonical routes 提供 source/component/route 级 violations；实际只传递 primary_error。
反馈后的第二份输出重复相同错误。不能从此证明模型为何忽略规则，也不能证明更详细反馈必然可修复。

**仍未资格：** 组件语义完整性、合法多组件、来源/Scope/Qualifier 对应、Owner/Phase/Evidence、
禁止权限和未来 Human Gate 的候选映射、独立 Semantic Review 均 NOT_EVALUABLE / NOT_REACHED。
当前没有通过 Formation 的 Candidate，没有内容 Verification、Guardian Assurance、Seal 或 Human 授权。
独立 Guardian 版本仅核对导入身份，没有执行 Assurance；不得称其本次已资格。

此次直接停止边界是 **模型 wire 引用类型错误及其 predecode 反馈定位不足**，不是观察到的容量耗尽。
是否需分阶段 Formation、是否现有反馈足以修复、完整语义是否合格仍 UNKNOWN；本次没有依据自动启动 Option B。
向 Architecture Lead 提交窄范围 Finding：评估在现有 decoder/feedback Owner 内保留可证明的 wire 错误定位，
在不放宽 FACT 类型、不改权限和不加预算前提下是否需要后续有界修复。
本轮未实施该修复、未修改 Runtime 或生产配置，也没有追加模型验证。

## 6. 持久化与恢复

Git 公共证据：本目录；`receipt-manifest.json` 绑定原始 ECS 公共收据字节与 SHA256。
`artifact-integrity-review.json` 只证明收据一致性和预算边界，不能作为 Formation / C3 PASS。

ECS 完整运行目录：
`/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/option-a-live-bounded-1`。
公开交付快照：该目录 `public-delivery/` 和 `public-delivery.tar.gz`，外置清单记录包散列。
私有完整输入、原始 wire、观察收据及最终未决 projection：`private/model-observations/`，目录 700 / 文件 600。
私有内容不进入 Git 或公开报告；通过已授权 SSH 可跨电脑恢复，不能声称另有异地备份。
精确镜像已存于上一阶段 `../image-recovery-final/exact-image.tar.gz`，本轮没有重建或替换镜像。
恢复仅用于取证；`execution-started.json` 表示这次授权已执行，不得重跑本次控制器。

本次仅交付 live bounded formation 的真实失败结果。**C3 保持 PARTIAL**，不代表 C3 CLOSED、
N1 Closure、G0、Holdout、Human Acceptance 或后续阶段已完成。
