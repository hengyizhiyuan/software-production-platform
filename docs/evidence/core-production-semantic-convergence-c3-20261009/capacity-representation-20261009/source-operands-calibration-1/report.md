# C3 路径、来源与 Owner 证据前提校准

记录 UTC：2026-10-10T08:10:55.786010+00:00

专项结果：**实际验证仍受阻；不宣称专项闭环**。C3 整体未关闭。

## 原五项失败与根因

| 原 Route / Source | 原始 Wire 事实 | 正确的既有 Owner 要求 |
|---|---|---|
| 4 / 4、31 / 23、32 / 24 | `t=[]`；rationale 提到了目标 | Git Diff 必须提供完整接纳的允许变更路径。禁止新增其他文件不能用空 allowlist 表示 |
| 29 / 21、30 / 22 | `u=[13]`；只引用原禁止条款 | 派生 Work Constraint 必须同时关联 Production 推导来源和当前否定条款；单一支持引用不能证明 Work 推导 |

门禁拒绝正确。修复前反馈只给出错误码和路由身份，未提供精确 expected/observed 路径及证明集合的合取含义。只读反事实还揭示 Fact 的支持条款必须自身绑定同一 Gate，这一真实 Owner 谓词此前未进入反馈。反事实不是有效模型结果。

## 工程修复边界

- 既有前提和反馈提供完整路径参数、支持证明集合、缺失成员及跨来源同能力绑定缺口。Fact Gate 的完整校验与反馈复用同一谓词。
- 必要证明集合属于条件前提，不要求模型枚举所有能力。支持引用不改变主来源的 polarity、phase 或 Authority；反馈修复不能破坏其他原本合法的证明。
- `68d0c8b` 真实模型错误地用 GIT_DIFF_SCOPE 消费 CARDINALITY Fact，二次候选仍重复；还把当前禁止部署/发布的派生约束转成未来授权。新增类型前提复用既有关系/阶段/来源谓词，明确对应非法绑定；不把文件 qualifier 改写为 SCOPE，也不把当前禁止改成未来许可。
- `68457b4` 第二次候选仅剩否定 SCOPE 误送内容 Owner。此时反馈虽报错，单独维护的类型前提仍未显示对应拒绝。`8c2b3d2` 改为由实际无副作用 Fact 校验器生成必要前提观测，不再逐条复制其规则。临时探测 Route 不返回、不接纳、不持久化；不构成语义匹配、权限或证据 PASS。
- 通过 `existing-owner-typed-prerequisites-v1/v2/v3` 可选观测标记协商前提；v2 补齐既有内容检查 NONEMPTY_ADMITTED_SUBSET 目标参数和 Fact 背景保留前提，v3 复用实际 Fact Owner。历史形状按原标记重算。Wire Schema 未变，完整 Wire、库存、Attempt、请求/响应持久收据及反馈 fingerprint 继续绑定。
- Review 复用既有 `fulfillment-compact-v1` 无损候选表示；现有 decoder 往返必须与完整原 Candidate 相等。保留完整库存、组件索引、原值/顺序/限定条件/Fact 链接和独立 Review 输出契约。
- 无新增 FACT-only 索引、Wire Schema 版本、分阶段 Formation、Owner、Alias、权限、重试或预算。Guardian/ECF 不需改动。

## 实际模型验证连续性

| 源码 | 实际调用 | 真实终态 |
|---|---|---|
| `7b1b9ba` | 2 Formation / 1 feedback / 0 Review | `STOPPED` / `OBLIGATION_FORMATION_WIRE_JSON_INVALID` |
| `b33e4e1` | 1 Formation / 0 feedback / 1 Review | `STOPPED` / `OBLIGATION_FORMATION_TRANSPORT_ModelProviderError` |
| `68d0c8b` | 2 Formation / 1 feedback / 0 Review | `STOPPED` / `OBLIGATION_FACT_EVIDENCE_METHOD_MISMATCH` |
| `5782506` | 2 Formation / 1 feedback / 0 Review | `STOPPED` / `OBLIGATION_CURRENT_FACT_CANNOT_BE_CONTEXT_ONLY` |
| `68457b4` | 2 Formation / 1 feedback / 0 Review | `STOPPED` / `OBLIGATION_NEGATED_SCOPE_EVIDENCE_OWNER_MISMATCH` |
| `8c2b3d2` | 2 Formation / 1 feedback / 1 Review | `STOPPED` / `OBLIGATION_FORMATION_TRANSPORT_ModelProviderError` |

`b33e4e1` 第一次 Formation 全部确定性校验通过：26 来源、75 组件，72 BOUND_PENDING_EVIDENCE、3 RETAINED_CONTEXT。独立 Review 返回 HTTP 200，但 incomplete/max_output_tokens；16,384 output tokens 全为 reasoning、无可见输出。不是网络超时，不计 Review PASS。
`7b1b9ba` 的多余闭合符、证明丢失和主来源极性冲突原样保留；历史拼装原因 UNKNOWN。b33 的流式与终态输出 fingerprint 一致。未保存隐藏推理。

同一 75 组件 Candidate 的只读容量对比：canonical Candidate 44,104 → existing wire 15,815 字节；实际旧请求 104,657 → 无损反事实请求 76,150 字节。字节变化不是 Provider Token 估计，也不是实际模型资格。

## 最终确切身份与回归

- Watt：`8c2b3d224e898b3dc8e8220f78f6a6723c158941`；Tree：`bd24f1b4a459b528737732edce04b7baff7c2152`。
- Image：`sha256:97a8db7f77c2898a65bdc975bb0f49f0f3350fe3e20c6e3650f4aeb3e54c01fa`；实际导入 Owner/容器身份见镜像和 live 收据。新镜像从确切源码构建，未以旧镜像文件覆盖冒充资格。
- Guardian：`76c1e87a1b29d151f4ed949748e3298f2169c5b1`；ECF：`5aa4f8833c359c15bd059eda5972aa3915bcc18c`；两仓库源码保持不变。
- 确切安装包：378 PASS；PostgreSQL/Guardian 联合：45 PASS；独立数据库迁移：`20261007_72`。
- 负向保护：错误路径/版本/来源、丢失或错误支持、主条款极性、CARDINALITY→SCOPE 非法重解释、未来授权替代当前禁止、引文/Fact 索引漂移、错误独立 Guardian 记录、反馈身份漂移。小/中/复杂库存及合法多组件继续受保护。
- 当前镜像对六组真实历史收据只读重放：终态、收据保持不变，零追加调用；详见最终 readonly-owner4。前一修订第一次分析容器因 UID 无权读取历史私有文件失败，原日志保留；随后以 root 在只读挂载、无网络容器读取，不改变历史权限。
- dev-16 定向回归为 100 PASS /1 FAIL：我新增的测试对 SimpleNamespace 调用 model_dump 导致夹具错误；修正为 vars 后，最终确切镜像全部 378 项通过。原失败收据保留，不计该试次 PASS。
- `2f7be3b` PostgreSQL 收集因我的测试夹具导入缩进错误中断，原 XML/log 保留；69b/68d 仅修正夹具，重新构建后 45 项合格。中断未计 PASS。另一次只读容量报告字段 KeyError 已保留失败日志，无模型调用。

## 专项边界与后续

最终真实终态仍为 `OBLIGATION_FORMATION_TRANSPORT_ModelProviderError`。第二次 Formation 全部确定性校验 PASS：45 Route、42 BOUND_PENDING_EVIDENCE、3 RETAINED_CONTEXT。原五项机械失败已不再出现，但不是独立语义合格。
最终独立 Review 请求实际输入 20,758 tokens、请求体 65,745 字节；仍为 HTTP 200/incomplete/max_output_tokens，16,384 output tokens 全为 reasoning，零 output_text delta、无 Review JSON。这是有证据的 Provider 输出容量终态，不是传输失败或第二次候选限制。继续缩减输入不能根据现有证据保证收敛。
剩余具体语义风险：当前候选 Route 41/source 23 将文件新增排除绑定到 DENY_PREVIEW（同源 Route 42 另有正确 Git Diff 绑定）；Route 21/source 13 同样提议 DENY_PREVIEW。实际该 Gate 会禁止 preview.inspect，不能据结构 PASS 将其当成合法的原始排除含义。独立 Review 没有结果，语义不合格/合格终态均不能伪造。详见 remaining-review-capacity.md。
上述结果不产生真实 Work、密封 Candidate、内容 Verification PASS、实际 Guardian Assurance、Human Integration/Acceptance 或 Delivery。C3 整体仍需正常用户到生产 Candidate 的资格及获授权的独立 Holdout；本轮没有新 G0、Holdout 解封或 C4/N1/N3。

每次独立验证仍为原 26 项库存/12 Capability：deepseek-flash，Formation none、Review low，16,384 output tokens、120 秒，最多 2 Formation /1反馈 /4逻辑调用。每次验证前都有确切修复依据和新冻结源码；没有在同一验证内重置预算。

实际累计用量（本目录六次验证）：`{"input_tokens": 388254, "output_tokens": 71118, "cached_tokens": 175104, "reasoning_tokens": 32768, "total_tokens": 459372}`；货币费用及完整项目累计成本 UNKNOWN。

## 可跨电脑恢复的位置

- 本目录公开报告、控制器和原始公开收据在原 C3 分支推送；manifest 保留原字节 SHA256。
- ECS 最终源码镜像、数据库资格收据、公开交付与恢复检查点：`/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/source-ownerprobe-qualified-20261010`。
- 最终私有 Wire/Candidate/库存/Owner 收据：`/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/source-ownerprobe-live-1/private/model-observations`；不进入 Git。
- Image archive 的路径/SHA256 见 `image-recovery/receipt.json`。未执行 docker load 恢复或异地复制，不声称已完成异地备份。
- canonical main、正式 ECS 服务、历史 Work/Candidate/Human Decision/Quality Ledger 不变。
