# C2 — Exact Execution Readiness & Real G0 Qualification

## 结论与事实边界

**C2 PARTIAL — Exact Engineering Blocker**

取证日期：2026-10-09；本文时间均为 UTC，原始 Owner 事件可能使用 +08:00。正常入口只提交了一条新的 G0 Work。实际模型、Native Worker、工具效果、Git 产物、ResultReady、Completion 与 proposed snapshot 均已发生；当前阶段 Verification 没有全部通过，Candidate Seal 和适用 Guardian Assurance 未到达。未写入 Human Integration、Acceptance、Delivery、Runtime Commit 或 Manifest。

主阻塞：PATH_SCOPE 返回 UNKNOWN / PROTECTED_CONTEXT_WITNESS_NOT_OBSERVED，GIT_DIFF_CHECK 单项 PASS。Work 保持 NEEDS_ATTENTION / STOPPED，Convergence 为 NON_CONVERGING。另有证据缺口：短生命周期 Production Environment 容器已经消失，其实际 Docker image identity 没有被 Owner 持久化，不能从请求配置追认实际镜像。

本轮已完成 C2 范围内的 Worker Preflight 诊断修复、新镜像构建、定向正负回归和一次真实正常生产尝试。未实施 C3/C4；N1 原 23 项 Closure Conditions 与历史失败保持不变。本报告不构成 Runtime Conformance Qualification，也不重开或关闭 N1。

## A. Repository Reality 与实际修复

| 身份 | Exact revision | Git Tree |
| --- | --- | --- |
| C1 Watt qualified code | 00e2a77e6b80ea79185d74a12db2cec8eeb9445e | 5d9c8f9714d698c695484efc1091bc092862f6bd |
| C1 Watt evidence HEAD / C2 base | e7c1b70ac30b89940a7596f835c6f0ccc928a9ba | 824ee3d7fb5dce2dfba04f910667cf0c6adf3f45 |
| **本轮应用与测试实际修订** | **88f1d9805d3ed1aa779ed3c78902b193fae240f8** | **69a35717087bfb46c18f5cfc9616a7a2a0acbdf7** |
| Guardian | 6b974748df22d84b88f6908ea8ee90a9752fd183 | c9a1bf4e102d8365a1ce27c9cced88f8ab0cd129 |
| ECF | 5aa4f8833c359c15bd059eda5972aa3915bcc18c | 878d39d9c259272bb05f2e02bdf9d60c22fad460 |
| 仅负向兼容测试使用的旧 ECF | c6b568d006022e39b95daebedfecfb55e562ebe5 | f102fa082bbd0a1abd827e77d6aa1340db8b83c5 |
| ECS canonical source | ee5bd86a53891f9391785c91d0ccef81ad2d56c3 | 保持原检出、干净 |

开始时核对了 C1 远端 exact HEAD，C1 evidence HEAD 与 qualified code 的 src/tests 差异为空。C2 独立分支为 codex/c2-execution-readiness-real-g0；后续证据提交不是新的已实测应用修订。交付 HEAD 及远端核验见 ECS delivery-receipt.json；应用身份始终为上表 88f1d98。

复用了 Workspace Manifest、SourceVector、ProductionWorkspaceObservation、ExecutionWorkspacePreflightRejected、Worker allocation/epoch fence。只修改三个现有源文件：

- src/spg/infrastructure/executor_runtime/production_evidence.py：固定诊断字段；实际路径与映射、Work/PWU/Attempt/Workspace/source 身份、检查条件、时间、UID/GID/PID/namespace、lstat 类型/errno/权限；非写入的有效 write/search access 校验；exact SourceVector tree 校验。Git 只记录操作与返回码，不保存 stderr、凭据或文件内容。
- src/spg/infrastructure/executor_runtime/worker.py：失败诊断在 terminal settlement 前通过现有 Owner 持久化；拒绝后不进入 kernel；使用实际 runtime_version。
- src/spg/application/executor_runtime.py：现有拒绝事件可接受固定 scalar allowlist，16,384 字符总上限，验证 exact binding/source/tree 和 Worker epoch；旧 message-only 调用保持兼容，不补造诊断。

新增 10 个 path/Git 单元用例及 2 个真实 PostgreSQL 事件用例。另有 Dockerfile 的外部 frontend 指令移除和重复测试 basename 更名；没有数据库迁移、Guardian/ECF 源码修改、权限放宽、Workspace 自动替换或新 Owner。

原两秒 availability wait 未增加。历史 Attempt e3addc05-7ee4-49f4-9043-c69b6466bcf8 的故障原因仍 UNKNOWN；当前成功不追认其修复或 PASS。前置审查与现况只读取证见 [workspace-preflight-review.md](workspace-preflight-review.md)。

### 实际 Worker Workspace

预业务 root probe 于 07:30:06 在实际 Worker 中完成；只创建并移除自己的小探针，没有模型请求或 Work。它不代替 Task preflight。随后 actual Attempt 的事件 54e0e368-0802-4a4c-a7c6-e828504c7b27 和结果事件 b87c7299-b16d-4f91-abb5-2dcd236ecd17 持久化了真实 Worker 诊断：

| 字段 | 实际值 |
| --- | --- |
| Worker ID / hostname | watt-c2-real-worker-20261009 / 91cdfeae4b00 |
| UID:GID / PID / namespace | 10001:10001 / 1 / mnt:[4026533947] |
| Workspace host path | /var/lib/spg/native-workspaces/74ba6435-c067-4277-9d2d-2d0bae4a87a5 |
| Tool mount | primary → /workspace/primary |
| 状态 | 真目录、非 symlink、effective write/search 可用，availability_wait_ms=0 |
| SourceVector expected / observed HEAD | a52e2d39683642c2ecb5c89bbf1761411cc715a9 |
| expected / observed input tree | 3bc248484b72b997aa0c1189b4fec38d4da3d018 |
| write_scope / forbidden_paths | index.html / .git、README.md |
| 结果 | index.html 158 bytes；SHA256 4f70e4b6b34b02b77a40f838643a8889fe3a2415a336c0efad14e84ac411839c |

上游 READY 之外，实际 Worker 自己观察到了合法输入目录，随后真实工具执行与结果观察均发生。[artifact-readiness.json](artifact-readiness.json) 保留 Manifest、SourceVector、Owner events、Worker、预算及 usage 引用。

## B. 新镜像、运行 Owner 与隔离范围

新镜像 watt-c2:88f1d98；Image ID：

sha256:205f7b42539767939675cebd6e8380be2757c5ebd6d7fbb08828bffae7799209

RepoDigests=[]，仅本地构建，未声称有 registry digest。Build 基于固定 dependency image 6c1f48e35ec485de278e8638f51d6aed75679b02a24d45355959bc8ddd7c0d14；COPY exact Watt、Guardian、ECF 源码后离线重装 spg-runtime。实际导入 /opt/spg-venv 的安装包，不使用 /app/src overlay。构建输入及安装文件分别逐项 SHA256 证明；最终四个应用角色各自完成 import attestation。Python 3.13.16，Owner API 使用原 C1 选择与 strict adapter。

- Runtime：实际 DeepSeek Provider、Native Worker、LONG_LIVED_STEERING，repository code verifier；delivery runtime disabled。既有模型/Refine 预算未增加。
- 新数据库 spg_c2_qualification_20261009，migration 20261007_72；C1 fixture 使用独立 c1_contract_continuity。
- 新 Gitea namespace watt-c2-qualification、新 Operator/Tool Host/PostgreSQL/Gitea 凭据、新 Owner/checkpoint/app stores、新 watt-c2-workspaces-20261009 volume。
- API、Coordinator、Worker、Tool Host 均运行上列 image ID、UID/GID 10001。两个 Workspace root 配置均明确为 /var/lib/spg/native-workspaces。
- 新网络与挂载、实际 Docker 配置见 [runtime-role-preparation.json](runtime-role-preparation.json)。API 只发布到 loopback 18200；独立 control 与 internal executor network；API/Tool Host 按现有架构使用共享 Docker daemon，不能宣称物理主机或 daemon 完全隔离。
- Human 在本轮明确批准复用已有测试 DeepSeek key，scope 为 HUMAN_AUTHORIZED_SHARED_TEST。不将其宣称独立凭据。原服务配置与凭据未修改或轮换；敏感值未进入报告/Git。

07:58 的留存核验显示六个新 C2 服务已停止但容器/目录/数据库/volume 保留；原 19 个 running container ID 仍 running，canonical ECS source 干净。见 [quiescence-and-preservation.json](quiescence-and-preservation.json) 与 [local-preservation.json](local-preservation.json)。

### 不能补造的 Production Environment image 证据

Owner 留存了 Environment 06bd8517-0f6f-42de-969d-3a7e005d5780、Workspace f31c92c6-0715-4d48-8b3f-6a7d18b7edca、原 handle 40a95832d05f210b3c40cb497742cda759286f4da371fbc6be0ffa49ce4415e9、ACTIVE/READY → SUSPENDED/STOPPED 和 mount identity。请求配置指向 immutable image 205f7b…；四个持续运行角色的实际 image/import 证明完整。

原 PE container 在冻结前已退出并移除；现有 WHERE Owner 没有保存 Docker image 字段，原时间窗 Docker events 返回空。**该已移除 PE 的实际 image identity 独立观测为 UNKNOWN**。已留存请求配置与 Owner 生命周期，未创建替代容器或用现在的代码反推当时 digest。见 [actual-production-environment.json](actual-production-environment.json)、[original-pe-docker-events.json](original-pe-docker-events.json)、[where-owner-addendum.json](where-owner-addendum.json)。这是 exact execution evidence 的未关闭义务。

## C. 一次真实正常入口 G0 证据链

沿用原 G0 input 的 exact 文本，来源 original-g0-input.json / 旧 input record c7a403a4-866c-4a9b-81b5-868e6cff184c。它是此前 agent-authored qualification input，在 Human 隔离资格授权下使用；持久 Actor=HUMAN 不是 Governor 对 Candidate 的接受。

要求：只创建 index.html；恰好一个 h1 “N1 Software Control”和一个 paragraph “Isolated qualification only”；只允许目标文件变更；禁止 deploy/publish、增页、修改 README；形成 reviewable Candidate 后等待 Human。

正常 Product POST 与 experience turn POST 各一次；driver 在 POST 前持久化 operation state，未知结果不自动重复 POST。没有 fixture admission、手造事实、Product Decision、手工 fulfillment binding、ScriptedInferenceAdapter 或 DeterministicTestExecutor。

| Owner 身份 | ID |
| --- | --- |
| driver run | 6cc07c85-be58-4c15-8c78-57187146a32a |
| Product | f31b1b12-36e3-48f2-966c-d8574f23999c |
| Interaction / Turn | d7d0bb62-3106-4791-b7fb-09ee6d937031 / a4e5543d-5b55-45aa-b5d9-4034b98724c7 |
| 实际 input record / IR | acb26081-9a2f-468a-98ba-7de48d68a3ba / 8be9e92b-2cb0-5da8-a595-cf70b7f52f67 |
| Work / WorkReality | b9c67d91-2cc1-5f91-bf61-8d7939b45cc3 / f9473edd-7b80-58df-ab5b-129e4dd5ec59 |
| Run / Task | 3577f872-af8d-48c7-b1da-b036589351a6 / ed1f17a1-00a5-5182-b031-319df4b9c91f |
| PWU / Queue | f918050c-4937-40b4-b60f-1b59aad2dba0 / d3c4b3b9-26d7-4e3c-9bbf-5cf26dae2133 |
| Attempt / NativeWorkspace | 74ba6435-c067-4277-9d2d-2d0bae4a87a5 / c2d92a24-cf95-5a23-8e50-7edfd5cde42e |
| ECF ContextPackage | a5e8edc0-5a4a-4ec7-802d-6754ee6f03a5 |
| ECF fingerprint | 96cea7371d910876dd7c0903630d280b9b11f45d0a501a9312101b4abfab74ec |
| SourceBaseline | 505aefa6-ed3f-4766-af26-b67cac6790a5 |
| Completion / ProposedSnapshot | d66435db-ae3a-5ce3-a7be-073c538a4641 / 741b2075-d050-5455-a138-07dd21a91ff6 |

| UTC | 已发生效果 |
| --- | --- |
| 07:30:08–11 | normal managed Product 创建、experience turn 接纳 |
| 07:30:52–55 | WorkReality、scope/resource/source basis 持久化 |
| 07:31:18–20 | DESIGN bounded Self-Refine 恢复、Steering PRODUCE、Task/PWU/ECF |
| 07:31:21–23 | PE READY、Native binding、queue allocation、实际 Worker workspace 观察 |
| 07:31:23–43 | 5 次 Native inference submission、7 个 settled tool effect |
| 07:31:43 | actual Worker FINISHED / RESULT_READY；ExecutionWorkerCompleted event 6ae05d8b-1bed-44a5-8c92-87cfeaec3fbd |
| 07:31:44–45 | PE suspended/stopped、Completion PRODUCED、proposed Git snapshot |
| 07:32:58.080686 | Verification 2d1d9a50-70c9-5249-b9a7-55e3f3045580：PATH_SCOPE UNKNOWN |
| 07:32:58.817939 | Verification 42e5e901-c5a2-5858-96f5-437990883994：GIT_DIFF_CHECK PASS |
| 07:33:00 | stop decision 561f9f15-acf7-46bf-ad2b-29bf595837b2；Convergence 125f16f1-9ce0-438d-8713-06de0fdce657 NON_CONVERGING |
| 07:33:05–06 | driver 观察 STOPPED / human_attention_required=true，没有写入授权 |

exact proposed output commit 为 7fcaeb4498b6f0bc2ca4d153414384308cb70cd9，tree 95b94416d825a3e87e85d2244eaa18300d390a6d；diff 只有 A index.html，158-byte blob 有一个正确 h1 与一个正确 paragraph。Native workspace 本身仍为输入 HEAD 加 untracked index.html；输出 commit 位于原 managed Work repository，不能误把输入 HEAD 当成输出 commit。

[git-witness/manifest.json](git-witness/manifest.json)、[git-witness/source-output.pack](git-witness/source-output.pack) 和 recovery-check.json 可跨电脑重建输入/输出 Git objects。人工只读取证结果不等同 Verification、Candidate Seal、Guardian 或 Human PASS。

## D. 精确阻塞、共同边界与未知项

DB repeatable-read snapshot、WHERE Owner 文件、Git objects、runtime receipts 冻结于新 C2 目录。canonical-freeze 保留全部 scoped Owner datasets、query_status、events、IR、contracts、authority/effect records；没有查询到的 dataset 明确标记，不把空展示当作全局审计。

已确认：

1. 真实 IR item kinds 只有 PRODUCTION_INTENT / FACT / FACT；没有 CONSTRAINT。7 个 clause 的 requested_effects 均为空；c7 为 NEGATED 并关联 pi-create-index。
2. WorkReality 保留 7 个 semantic facts（page.path/count、h1.count/text、paragraph.count/text、work.change_scope）及 provenance。ECF 保留 7 个 Protected Context（6 APPROVED_CONSTRAINT + PRODUCT_INTENT）。production 的 delivery_authorized=false、acceptance_required=true、preview_required=false 和 exclusions（deploy/publish/add pages/change README.md）均已保留；CONSTRAINT/requested_effects 驱动的对应履行绑定没有形成。因此不能把“文本存在”报告成所有治理义务映射已成立。
3. actual PWU completion_contract.fulfillment_bindings 明确存在且为 []。当前 materialize_continuous_gates 只消费 CONSTRAINT items 与 typed requested_effects；从实际 IR 会返回空。没有证据证明曾有 bindings 再在 transport 中丢失。
4. Managed Protected Context 随后走现有静态 source-witness 路径。protected_context_verifier.py 对每一个 disposition 都要求非空 witness、path 属于 exact material、quote 为 literal、且不是 .md。代码最多两次有界 generate；本次持久结果为 PROTECTED_CONTEXT_WITNESS_NOT_OBSERVED，逐调用次数与候选没有留存，不将代码上限当成独立历史观测。
5. repository_code_verifier 的异常路径只持久化异常摘要并置 UNKNOWN，未保留失败 checks/model_attempts。ModelRuntime result 与该 caller 的 response/output_text/checks 仅存于内存，没有接通持久 candidate sink。

共同边界是 **真实自然语言接纳/typed obligation 形成 → 现有 fulfillment materialization → Protected Context 的 Owner/证据消费**。上游实际表示不同于 C1 已验证 typed fixture；这是 C3 语义消费/泛化未资格的边界，不能在 C2 填入固定 alias、伪造 fact/effect 或降低 witness/Guardian 获得 PASS。没有观察到本轮 Worker workspace/handoff 是主阻塞；没有触发 ASSET_SCOPE_ADMISSION。

**UNKNOWN：具体哪一个 check、fact、path 或 quote 不合格；是否为空 witness、错 path、错 quote 或 .md subtype；失败模型 request IDs/usage/候选原文；移除 PE 的实际 image digest。** 当前源码解释拒绝条件，不等同恢复已丢失的历史模型输出。不能宣称 h1 检查失败、禁止发布事实就是某一特定坏 witness，或简单放宽规则就必然闭环。

只提交一个 [C2-to-C3-handoff.md](C2-to-C3-handoff.md)。没有对该 out-of-scope 根因反复建 Work；实际 G0 一次，未人为 refine/resume/reset 原失败 Work。C3 需要在已批准架构下核对共同映射路径及候选失败证据持久化；C2 不能以局部修复替代该能力资格。

## E. 正负回归、失败分类与成本

详见 [verification-test-summary.json](verification-test-summary.json)。最终 image 205f7b… / source 88f1d98 上，两组进程合计 **79 个不重复 case 通过**：

- 混合 default 进程：29 PASS，50 C1 fixture setup ERROR，exit 1。29 包括新 Preflight 12、现有 production evidence 6、Native Worker 3、ECF API 5、Guardian adapter 3。这个整体进程不是 PASS。
- 独立 C1 single-file 进程：50 PASS，0 failures/errors/skips，exit 0，墙钟 255.928 秒。创建真实受控 fixture Work，不调用 live model，不是 normal-entry G0。

覆盖正确 workspace、缺失/错误类型、root/nested symlink、越界/out-of-scope、nonroot write access、wrong revision/tree、具体缺失 artifact/errno、preflight reject-before-kernel、binding drift、legacy message-only、错误/缺失 Guardian Owner Evidence、未授权 Deploy/Publish 与旧 ECF API 拒绝。C1 有效契约和独立 Guardian 没有被降级。这里的负向权限证据来自受控用例，未在真实 G0 额外发起未经授权部署试验。

所有失败收据保留：

| 尝试 | 分类与处理 |
| --- | --- |
| 首个 image build | 外部 Dockerfile frontend 网络超时；没有应用编译；移除非必要外部 frontend 后离线构建 |
| 3355b99 mixed test | 新 unit/integration 相同 basename 导致 collection error；只更名 integration module |
| importlib / 最终 default mixed test | 29 PASS + 50 fixture setup ERROR；pytest 9.1.1 多 explicit paths 导致同 Dir nodeid 不同 Directory Node，fixture identity 不匹配 |
| C1 single-file 分组 | 同 final source/image，50 全通过；没有业务源码或 fixture 权限修补 |
| Tool Host preparation 两次 | read-only parent 尚无 receipts/native mountpoint；只创建新隔离挂载点后启动原新容器，未替换 Workspace、放宽权限 |
| driver 首次准备 | cap-drop root 无法读新隔离 input/operator 文件；POST 前失败无业务效果；以 UID10001 与 root:10001 的新授权文件解决 |
| 一次 probe 构造/readonly export | shell quoting / readonly tmp 写入失败；非业务控制命令，后改 exec stdin 只读取证；非 Work 重试 |

未运行全 N1 G0–G6、未重跑 Guardian 73 suite、未把旧 image 资格算入本次 79。Build receipts 含一个失败、两次成功；最终 88 build 07:20:57–07:21:21，24.424 秒。测试与资源采样原值保留，未推算总 CPU/费用。

真实 Self-Refine：

- b3281f8e-17fa-450e-91e4-5fa11363bb13：scope / SCOPE_INFLATION，已记录 SCOPE_INFLATION、authority_expanded=false；attempt 2、有界、RECOVERED/RESUMED；reported 15,557 tokens（input 12,420/output 3,137，cached 1,024/reasoning 868 为子分类）。
- 29dc0010-eee9-40da-a0ba-f1e5d30ff2d6：steering semantic / CONTRACT_MISMATCH，attempt 2、有界、RECOVERED/RESUMED；reported 27,295 tokens，额外约 21 秒。
- 两个 Refine 包含同一 DESIGN 操作的不同范围，不能直接加总为独立总消费；恢复后实际 Worker、Completion 推进，但完整 Work 未 PASS。不是 G5 故障资格或 Context Assembly 恢复证明。
- Native 已记账 5 次 inference / 7 tool effects；Provider usage 合计 122,139 tokens（input 119,390 / output 2,749；cache 13,440 / reasoning 1,955 为子分类）。此值不是整个 G0/WIC/Protected verification 的总模型成本。
- 全流程模型总量、失败 Protected candidate usage、累计 CPU、货币费用 UNKNOWN。未重置预算、未增加 retry、未制造重复副作用。

## F. 十项核心验收与 C1 比较

| C2 核心验收 | 本轮真实结果 |
| --- | --- |
| 1 输入合法接纳且目标/约束不丢失 | 页面事实、原始文本与 typed production 权限/acceptance flags 已保留；对应 fulfillment bindings=[]，完整消费未资格 |
| 2 Task/PWU 与 C1 义务绑定连续性 | Task/PWU 已创建；actual binding=[]，不能宣称真实路径完成了 C1 typed 义务链 |
| 3 实际 Worker 正确 Workspace | 已有 actual-process 两次 Owner observation 与 exact input source/tree |
| 4 模型/工具实际产物 | 已发生真实 Provider/Native Worker/7 effects；index.html 留存 |
| 5 Git baseline/output/tree 一致 | 独立 Git object 取证与 GIT_DIFF_CHECK PASS；PE image identity 另有缺口 |
| 6 当前必需 Verification | PATH_SCOPE UNKNOWN；**未满足** |
| 7 适用 Guardian 独立 Assurance | Candidate 未形成，NOT_STARTED / NOT_REACHED；不是豁免或 PASS |
| 8 禁止 Deploy/Publish 门禁 | Native grant 不含 Deploy/Publish，runtime delivery disabled；C1 真 Owner 负向回归通过。未证明 daemon 全局审计覆盖，不能断言所有未观察非法效果绝无发生 |
| 9 Candidate Seal | scoped Candidate count=0；**未满足** |
| 10 Human 未授权/待决真实状态 | 无授权/acceptance/delivery 创建；Work 是故障 Human attention，而非合格 Candidate 的 review pending |

C1 的 typed integration fixtures 在新 exact image 仍通过；本轮发现的是正常 WIC 表示未形成相同履行绑定，并非已证实 C1 transport/Guardian contract 发生回归。真实 Greenfield 到可信 Candidate 尚未取得资格，不能把 C1 controlled PASS、正确 HTML 或局部 Refine 成功替代 C2 CLOSED。

## G. 留存、交付及后续依赖

公开完整恢复入口为本目录、evidence-index.json、[recovery.md](recovery.md) 及远端 codex/c2-execution-readiness-real-g0。ECS 持久目录：

/data/watt/c2-execution-readiness-20261009

保留新数据库 consistent pg_dump、新 Gitea/Owner/checkpoint/Workspace quiesced archive、原 Git objects、exact image archive、build inputs、私有原始快照、200 个 normal-entry receipts。敏感数据只在 ECS private（root-only）存放，不进入 Git；公版保留 query_status、数据来源、Owner/event ID 和证据等级。哈希证明字节身份，不把日志 absence 变成完整审计。

- image-88f1d98.tar.gz：335,972,932 bytes；SHA256 8f90a08ba814838161e8b281060733a9728fd92a83366cf110f7b56c510cdf16。
- private/spg_c2_qualification_20261009.dump：542,022 bytes；SHA256 4a7ce19bf2863051a88a31a9e9cf54e137da5a7b3d232fad79ea402dd5ad73ce。
- 优先恢复 private/runtime-data-quiesced-20261009.tar.gz：104,123 bytes；SHA256 0643ca572e4771c054e5f57c3eeea8e87926352db466749b3f2fe78d82bc41ef。
- Git pack SHA256 0fa66cccdcf02876fe205016eec847a7e281934c423fe48dfb01b2a64dcfc2f1，已经独立 bare recovery 验证两个 tree/blob。
- exact known credential publication scan 无匹配；不是声称能检测所有未知敏感内容。Human 共享测试 key 授权单独注明，不泄露其值。

C3 依赖：共同义务生成/消费路径的开放语义资格、失败 candidate 可恢复取证、PE exact image evidence。C4 不由本次局部 Self-Refine 结果提前宣告合格。没有合格新 Candidate，当前没有可提交 Human Integration/Acceptance/Delivery 的材料；不得将故障 stop decision 当作 Human 接受。

**退出状态保持 C2 PARTIAL — Exact Engineering Blocker。代码与证据提交、推送并核对远端，不自动开始 C3/C4。**
