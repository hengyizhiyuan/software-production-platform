# Trace 分析修订反馈与简明报告 — 2026-10-13

## 本轮结果

本轮只处理截图中分析未形成报告、报告页面布局和简明下载。已更新正式 API，独立分支 `codex/watt-trace-self-analysis`；C3、canonical main、Worker、N1、协调器和数据库 Schema 未修改。

- 分析修复源码：`3d154a1ea4b8c2c1f1ec695a0528627db268d40a`。
- 最终展示与部署源码：`6c9095214c8724ab32058ffa5f199d4acc161e5b`。
- 真实 Work：`408e408a-fab8-5a34-b101-b922043cb6fd`。
- 新分析：`3ca692e0-10ea-48a0-b23a-6af5d661a0be`，**COMPLETED / RESULT_READY**。
- 11 次推理、25 次工具、399.36 秒；原预算仍为 12 / 48 / 600，没有重启相同候选碰运气、重置预算或人工改写模型报告。
- 最终报告摘要：`cc2277e94159288a51eb60f0a5dfa4b84257bb2f6d435b89f64d33be00d71b1d`，最终 result_claim 与 Native 自审一致。
- 已保存的合格简明 HTML：**15,321 字节**；历史失败记录 HTML：**1,850 字节**。

## 这次失败与上次入口拒绝不同

上次修复了静止的 WAITING_HUMAN / WAITING_ACCEPTANCE 被分析入口误拒绝。本次历史请求 `9215d087-50bd-4c7b-9ccb-aadd1477145a` 已进入 Native 分析，但三轮草稿校验被拒：

1. 把 repository.search 的记录当作带 `/content` 的原文引用。
2. 缺失证据没有关联到对应 Finding 的范围核查。
3. 把 availability=PRESENT 的检查当作缺口依据。

Native 随后触发原有三轮无进展保护，工具投影为空；模型如实返回 UNABLE_TO_COMPLETE，没有完成修订、自审与报告提交。这是分析流程失败，不等于原生产 Work 的根因已确认。

通用修复位于 `src/spg/infrastructure/trace_analysis_evidence.py`：独立可检查的引用、关联、范围核查和缺失证据错误一起反馈，最多 12 项并记录省略数；给出具体字段位置、检查身份及已保存 availability。候选不被自动改写，原草稿保留，验证和权限门禁不放宽，Kernel 的无进展保护不修改。

新的真实分析一次收到 8 项来源反馈，随后通过同一次 `analysis.revise` 修复。自审又识别“把 Owner 准入诊断当作完整仓库枚举”和“把本轮未观测当作确定未导出”两类过度推断，模型修订并重新自审通过。

## 页面与下载

页面使用四个横向 Tab：**重点结论、生产过程、改进方案、证据与校验**。首页突出失败现象／偏离、原因总结及改进方案；失败分析的完整终止说明和拒绝项放在证据 Tab。

`src/spg/application/trace_analysis_presentation.py` 投影已有报告及失败回执，不增加模型调用、不创建分析架构层。失败状态中文摘要仅翻译既有协议拒绝码，不依据关键词判断模型语义或修补结论。

`GET /api/admin/works/{work_id}/analyses/{request_id}?view=summary` 排除草稿和执行整包；历史列表只传元数据。新的下载接口为同一路径下 `/report`，输出有身份、引用、UNKNOWN 边界和截取提示的简明 HTML。既有 Owner 鉴权保留，下载带 no-store、nosniff、内容摘要及限制执行的 CSP。完整工程记录仍保存，页面下载按钮不再拉取十几兆 JSON。

## 回归与真实资格

相关回归最终覆盖 **263 项 Python、38 项 JavaScript**，全部通过。首次后端运行有一项测试夹具使用错误的退出接口，导致未清除会话；改用清除测试客户端 Cookie 后 API 权限回归通过。保留首次失败与后续回执，最终汇总按每个用例最后有效回执合并，非伪称一次全量通过。

真实新分析通过来源／结构校验、完整目标自审及终态摘要门禁。Work、PWU、Self-Refine、验收四组原始记录前后摘要均为 `0a6c68fe0790615bc321872dd3aa14fa4d8b3ec3858350604abc3db51dd6c216`；本分析没有更改原 Work。

Native 资格实际执行在 `3d154a1e`。之后 `6c909521` 只缩短失败展示与调整 JavaScript；其余 **275 个源码文件逐字节相同**，包括调查服务、工具、引用验证、Kernel、Context、Schema 和权限。最终镜像全部 277 个源码文件和实际导入位置核对通过；复用既有 Native 资格并单独验证最终显示与 HTTP 下载，没有再跑模型资格。

## 部署与隔离

- 镜像：`sha256:69268f468f0c0f9d632127d8313b94b754c8d0543b9079ba887cb90dbfbc755e`。
- 只替换 `watt-cloud-worker-api-1`；原 4 个 Compose 文件保持，追加 API 镜像覆盖。
- 部署前：未释放分配 0、活动队列 0、分析锁不存在。
- 健康、实际源码身份、登录／来源校验、未知 Work 拒绝、JS/CSS 实际哈希、报告读取、小 HTML 下载：PASS。
- 同请求 POST 幂等返回，事件和推理记录不增加。
- 其他 **24 个**已有容器身份、启动时间、状态和重启次数均不变。
- 回滚镜像：`watt-cloud-worker:trace-owner-rollback-6c909521`；保留原 Compose 与镜像配置。部署目录 `/data/watt/trace-analysis-releases/6c909521`。

## 结论边界

新报告对原 Work 的选定事件分类和根因仍为 **UNKNOWN**。来源只支持首轮反馈、记录中的 attempt_count=2、second_error_type=ValueError 和升级人工决定；原始候选、第二次异常细节、真实调用次数及历史 Worker 加载版本未确认。源码只作明确限定的当前实现比较，不将 Owner 分类标签当成缺陷证明，也不推断交付或验收已完成。

Kernel 公开终止叙述仍提到一个较早草稿摘要；正式 result_claim、自审和已接受报告摘要一致。成功简明报告使用已接受结构化报告，不用该叙述替代结果身份。此原始记录保留，不顺带扩大为整个 Native 叙述规范改造。

旧分析记录保持 FAILED；用户应打开最新 COMPLETED 记录。本轮不承诺所有未来模型输出一次通过，也不继续扩大取证或原生产故障修复。

## 证据入口

- [简明报告](../evidence/work-trace-report-focus-20261013/concise-report.html)
- [结构化报告](../evidence/work-trace-report-focus-20261013/report.json)
- [原生终态](../evidence/work-trace-report-focus-20261013/native-result.json)
- [原生自审](../evidence/work-trace-report-focus-20261013/native-self-review.json)
- [源码与报告复核](../evidence/work-trace-report-focus-20261013/independent-review.json)
- [展示变更的资格复用依据](../evidence/work-trace-report-focus-20261013/qualification-source-reuse.json)
- [实际 HTTP 验证](../evidence/work-trace-report-focus-20261013/http-replay.json)
- [部署结果](../evidence/work-trace-report-focus-20261013/activation-result.json)
- [容器隔离](../evidence/work-trace-report-focus-20261013/container-isolation.json)
- [最终回归汇总](../evidence/work-trace-report-focus-20261013/regression.junit.xml)
- [新布局截图](../evidence/work-trace-report-focus-20261013/report-tabs-completed-preview.jpg)：真实已保存报告在本地展示夹具中渲染；部署身份与 HTTP 资格由 ECS 证据单独确认。


## 下载格式更新（同日）

按 Human 要求，默认简明下载改为 UTF-8 Markdown（`.md`），源码 `32db38cac756ba120a180788ff31e9b4fea8fc6a`，已部署并保留原下载地址。内容、引用、UNKNOWN 与权限边界沿用已有保存报告，没有重新调用模型。

- 下载格式／权限相关 Python 回归 2/2、JavaScript 回归 38/38 PASS。
- ECS 实际 Content-Type 为 `text/markdown`，附件文件名以 `.md` 结尾，下载摘要与内容匹配。
- 真实已完成报告 14,499 字节；历史失败报告 1,321 字节。
- 部署前未释放分配 0、活动队列 0、分析锁不存在；仅替换 API，其他 24 个已有容器不变。
- 镜像 `sha256:8bdb8db9b7ec8ed761a193131e64bb2454b5dfe0834c468cd5c774fda4c036af`；回滚 `watt-cloud-worker:trace-owner-rollback-32db38ca`。
- [Markdown 报告](../evidence/work-trace-markdown-20261013/concise-report.md)、[实际 HTTP 验证](../evidence/work-trace-markdown-20261013/http-replay.json)、[部署结果](../evidence/work-trace-markdown-20261013/activation-result.json)、[隔离检查](../evidence/work-trace-markdown-20261013/container-isolation.json)。
