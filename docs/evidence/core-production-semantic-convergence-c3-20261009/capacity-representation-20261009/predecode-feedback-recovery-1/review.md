# C3 — Predecode Feedback Recovery Review

2026-10-10。**专项有界修复完成；C3 保持 PARTIAL。**

## 1. 已证实问题与实际修复

原两次 live Formation 均完成，但把 IR_CLAUSE 来源 6、8 放入 FACT-only 的 f 字段。
原 decoder 正确拒绝；canonical Candidate 尚未形成，原反馈只有错误码、空 violations。
本次没有改变引用类型规则，也没有修补历史 Candidate。

实际修改仅位于 Watt 的既有两个职责点及其测试：

| 模块 | 修复 |
|---|---|
| `src/spg/providers/fulfillment_candidate.py` | 保留严格 decoder；有界收集 source/capability/引用索引、FACT 类型、可确定跨度和原文覆盖错误；提供原始 Wire bytes SHA256 与 raw route fingerprint。JSON/schema 无法建立合法 Wire 时，保留解析失败并标记路由与后续检查 NOT_EVALUABLE。 |
| `src/spg/application/governed_obligations.py` | 现有 Work Owner 将诊断绑定原请求/响应持久收据、Attempt、Work Reality、Source Revision、库存及 Wire request/table/schema fingerprints；反馈绑定诊断 fingerprint，下一请求引用产生反馈的 CANDIDATE_VALIDATED 收据。 |
| 同一 Work Owner 的恢复/重放 | 在终态重放、恢复解码和后续候选前核对原始 bytes/hash/长度、Owner 身份、收据唯一性、原始诊断与精确反馈，重算并比较；漂移返回 UNRESOLVED / truthful stop，不再调用模型或重置预算。 |

恢复时被替换成合法提案的 raw output 也会先被 SHA256 拒绝，不能绕过旧错误去触发 Review。
PostgreSQL 的 subject 查询保留 scope fingerprint 异常记录供检查，避免异常收据被过滤掉后重新打开预算。
诊断不形成部分 Candidate、不产生合格 component ID、不自动移动 f/u、不删引用或扩大跨度。
显式 q 需要原有 locator 时，该来源的 raw coverage 标为 NOT_EVALUABLE；原有 locator、完整候选检查与独立 Review 继续约束。
最多保留 64 条可评估错误并记录额外数量；不可评估的 Owner/Phase/Evidence、Review、实际证据和 Assurance 不伪装成已通过。

## 2. 约束保持与身份

| 对象 | 精确身份 |
|---|---|
| 原 application | `a91442c21ed487b10d8dc38023b0807787a29648` |
| 本次 application | `e7afb5a15df4c187a9248b4a073391a62037677f` |
| 本次 Git tree | `82ea0c6ff143c3a3694b30062633f1e3f2fae4d7` |
| Guardian（未改） | `76c1e87a1b29d151f4ed949748e3298f2169c5b1` |
| ECF（未改） | `5aa4f8833c359c15bd059eda5972aa3915bcc18c` |
| 原实际 image | `sha256:90f2cd847ad891fda6ca95b5736c84b680c9d58bd6a3203bf0ea31c970da0f16` |
| 本次实际 image | `sha256:e42fcb7dfe18254f1396f2faaaadd95b0d24efe445db6ce19beedfdebac32726` |
| Wire schema fingerprint（保持原值） | `5668e226eb8d38c0f4bf9004ea8fc7aa363e9d388f64927783252f562d78ad40` |
| 原 26 来源库存 fingerprint | `7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf` |
| 原 12 Capability fingerprint | `a2e695783b122373f0ed308a959fa4e3116c4a9df5454dbedd81695071153b17` |

保留原 source index 空间、`fulfillment-compact-v1`、反馈 v2 和 Candidate/Review 契约。
没有 FACT-only 新索引空间、Wire Schema 升级、Subject Alias、语义特例、全局协调器或新 Owner。
两候选、一反馈、最多四逻辑调用及现有传输/Token/timeout 约束保持不变。
模型配置、Human Authority、接纳事实和 Guardian 门禁未修改。
Guardian 的正式证据契约不消费这些 predecode 诊断作为 Assurance 证据，故无需修改独立 Owner；
现有 Watt/Guardian 联合路径在本次精确镜像的 PostgreSQL 集成资格中保留独立核验。

## 3. 本次资格与失败收据

| 资格 | 真实结果 | 边界 |
|---|---|---|
| 最终镜像的定向及既有回归 | **299/299 PASS，0 skip** | actual installed packages；无源码覆盖、network=none；涵盖 Provider/预算/来源/权限/Guardian Adapter/停止机制 |
| 最终镜像 PostgreSQL 集成 | **9/9 PASS，0 skip** | fresh 独立数据库、migration `20261007_72`；恢复、精确反馈/收据、scope inventory 漂移拒绝、既有 Git/Candidate/独立 Guardian 契约路径 |
| 新 feedback 受控正向 | PASS | 小/中/复杂库存：第一次非 FACT 引用拒绝 → 一次绑定反馈 → 新合法候选 → 独立 Review；不是 live intelligence |
| 新 feedback 负向与恢复 | PASS | raw bytes/hash/长度、Attempt、库存、来源版本、收据、diagnostic hash、反馈、重复观察、后续反馈引用和 terminal replay 漂移均不打开新模型调用 |
| 历史两份 raw 输出只读重检 | **继续拒绝** | 第一次 2 个错误；第二次 6 个错误，包括 source4/9/10/12 的原文覆盖丢失；生成新的派生诊断，没有替换原反馈或写历史 Owner |
| 新真实模型收敛、真实 G0、Holdout | **NOT_PERFORMED** | 本轮没有授权或发起这些资格 |

开发期间两份失败收据完整保留：

- dev-1：28 项失败，原因是新反例错误地只寻找 IR_CLAUSE，而既有 typed fixture 提供 IR_CONSTRAINT，未进入预期校验。
- dev-2：27 PASS / 1 FAIL，原因是测试对模拟中断 list 做 deepcopy，触发其 append 中断钩子。
- 修正测试夹具后 dev-3 206/206、dev-4 208/208；PG development 3/3、4/4。
- 后续身份核对小修订只以最终冻结镜像的 299/299 与 9/9 作为交付源码资格，不将 development overlay 当作最终 image PASS。

原始收据及 XML/log 见 `receipts/`，字节/SHA256/ECS 来源由 `receipt-manifest.json` 绑定。
actual import/build identity、container/image、SQL migration 与 fixture Work/收据 IDs 均保留。
测试中模拟的 Usage 不属于实际 Provider Token 用量。

## 4. 历史输出复核的事实边界

原 Work `048189aa-0613-5307-b6f4-c430e7977f93` / Reality `332a3a38-8719-580c-a1a2-c331ae14a5ae` 只读。
原两份 raw Wire SHA256：
`c60c7f4d1060017a8ddbdd289105350bbfa4aefca0a94f3845d9cc496d83267b`、
`98b70541f2b10f3f00a04ba797d0e393781a4143ecac0af109c4d31f437132df`。
各自原始请求/响应 receipt ID、Attempt、request fingerprint 与新派生诊断绑定见
`receipts/retained-recheck/retained-diagnostic-recheck.json`。
该复核没有发送新反馈到 Provider，没有修改原反馈、原提案、原 Owner 或 Human Decision；输入前后 SHA256 相同。
不能把新诊断存在解释为历史试次成功、模型修复有效或独立语义审查合格。

## 5. 消耗、恢复与未关闭资格

实际模型调用 **0**、本轮实际 Provider Token **0**；新反馈的实际模型 Token 开销和收敛效果仍 UNKNOWN。
构建仅 **1 次**，耗时约 **17.47 秒**；实际测试/构建/导出用时与开发失败次数见 `cost-and-attempts.json`。
计算费用、传输及未观测 CPU 成本 UNKNOWN，不将历史 39947 Token 算入本轮。

ECS 完整本轮目录：
`/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/wire-feedback-recovery-20261010`。
Git 公共证据：本目录；ECS 公共交付快照在上述目录 `public-delivery/` 与 `public-delivery.tar.gz`。
精确 image 已保存至 `image-recovery/exact-image.tar.gz`，SHA256 / 大小 / 权限见 `image-recovery-receipt.json`；
恢复加载和异地备份 NOT_PERFORMED，不以未来重新构建代替同一 image identity。
原私有输入继续位于相邻 `option-a-live-bounded-1/private/model-observations/`，没有复制到 Git。
以上位置通过已授权 SSH 可跨电脑恢复。

下一项必要资格是本次精确 application/image 上的独立限定真实模型收敛验证，
确认一次反馈能否实际修复且获得独立 Semantic Review；本轮不自动发起。
现有 Wire 契约通过受控正确性验证，没有提出新索引空间或 Schema 版本的依据。
真实模型收敛、语义泛化、G0 与 C3 其余 Closure 义务仍未因此完成。
**本次工程修复合格，C3 PARTIAL；不启动 C4/N1/N3，不合并或部署 main。**
