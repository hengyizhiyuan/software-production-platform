# C3 普通 G0 履行绑定与最终资格 — generation 36

状态：执行中；尚不声明 C3 CLOSED。

## 已证实的故障分类

1. 普通 19-source 隔离形成：首候选 64 routes 被独立 Review 拒绝，原预算内一次反馈后形成 27 条合法 routes；完整来源、否定与排他范围保留。首 Review 对两条额外 scope routes 的逐项误判仍是质量限制，整个首计划没有被接纳。
2. 新正常用户入口 generation35 Work 的形成与独立 Review 通过；真实 Worker 产生 index.html，精确 Git Diff 通过。
3. 当前失败由两个 CARDINALITY Fact 缺少下游可执行计划契约造成。标题文本与段落文本已通过。PATH_SCOPE 包装结果 FAIL 不能被解释为真实路径越界；历史 Work 仍失败，不能用只读计数追认 PASS。

逐事实 ID、责任、证据和失败谓词见 ../generation35/review.md 与 real-g0/verification-failure-proof.json。局部恢复不等于完整 Work 成功。

## 最小修复与原门禁

复用现有静态内容 Owner 的精确 HTML/Git 检查器及两请求预算。第一请求提出派生计数计划；只有确定性契约合格才允许第二请求独立审查/修正计数对象及生命周期。完整原 Fact、值、unit、scope、qualifiers、权限、版本和完整 provenance 不可改变。首提案修复耗尽第二请求而没有独立 Review 时保持 NOT_EVALUABLE，不增加请求。

删除未经证明的“出现文件名且数量为 1 即新增文件”自动映射。实际计数不符为 FAIL，不触发计划重试。未知对象、不可表达限制、来源或版本错误、缺失收据及未完成请求均不授予成功。

重放要求首提案与第二 Review 原始 Wire SHA、唯一 component/attempt 观察、重新解码结果及持久验证记录一致；独立 Review basis 绑定原 Fact/source 和首 Wire/receipt。首确定性验证缺失或失败不能由后续 Review 代偿。复用既有 verification/native/refinement receipts，没有新 Owner、Schema、协调器或权限。

## 冻结身份与受控资格

- Watt source：9bd18c69c7b92f1eed7093134dacd16eab7fb0cc
- Git tree：7d55ab25247b6651da86cad5ff4193f950a55653
- 实际新镜像：sha256:f348a9092fae689b2557cf52ebe5faba37d3d8bd02727dedb93f77cdafb72b32
- Guardian：76c1e87a1b29d151f4ed949748e3298f2169c5b1
- ECF：5aa4f8833c359c15bd059eda5972aa3915bcc18c
- 完整构建：26.10539833200164 秒；安装态 634 项 C3 回归 PASS，83.32067810394801 秒。
- 同镜像额外静态语义回归：63 PASS，16.069386202958412 秒；无 source overlay、network none、模型调用 0。
- PostgreSQL/Guardian 联合资格：59 PASS，372.0944508709945 秒，迁移 20261007_72。真实 G0、Candidate、Assurance、Holdout：没有执行，不能由受控 PASS 代替。

资源准备第一次在创建前因旧资格网段占用停止，Work/model 调用均为 0；实际网络事实确认后改用空闲隔离网段。保留失败记录及原控制脚本，不改变应用源码或镜像。

## 跨电脑恢复

- 精确构建/回归：/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/g0-binding-generation36-qualified-20261010
- 新独立运行预留：/data/watt/c3-semantic-convergence-20261009/binding-g0-generation36-qualification-20261010
- 原 generation35 失败 Work、数据库、私有导出及历史模型 Wire 保持不变。
- 公共取证随原 C3 分支提交；完整 Human 输入、私有模型候选及凭据只保留在 ECS 受控私有目录。

不启动 C4/N1/N3，不修改 main 或正式环境，不授予 Human Integration/Acceptance/Delivery，不使用 Holdout 调优。

## 独立实际 Owner 核对发现的单位缺口

真实 generation35 原 Fact d8489958-60c6-5498-b9b8-772da5f677b8 的 unit=heading，b2715529-7f78-5806-8846-f64a7d689226 的 unit=paragraph。原始导出 SHA256 2fcc21556ff2ba5dc0043562697e87c3a1b4997d6c1b241fc7fc8f0f7bb97418 一致；先前归纳未列出 unit，受控 count fixture 也未覆盖非空单位。9bd18c6 会拒绝所有非空单位，因此其受控 PASS 不证明可以履行这条真实 Work。本轮未执行 generation36 Work 或 Provider 调用，失败历史与完整构建/回归收据均保留。

工程修正：原 unit 是开放语义操作数，保持在原 Fact、完整请求及重放 digest 中；不建立 unit/Subject Alias 白名单。现有第二请求独立审查必须证明所选原生计数 primitive 测量原单位，不转换、不丢失；无法对应或未知单位返回 UNVERIFIABLE。未知单位不因首提案契约合格而获准执行。仅修正当前 owner-specific 派生计划，不更改权威 Fact 或预算。

Development106：89 PASS；包括真实单位、非预列举中文单位、原样传递、未知/不兼容单位由独立 Review 拒绝，以及重放 unit 漂移负例。均为受控 source overlay，真实模型语义能力尚待最终新 G0/独立资格。因已证实真实接口缺陷，需要重新冻结源码与镜像；generation36 结果不会算作下一修订结果。

独立实际 Owner 对账：normal35 为 18-source / 27 routes，1 Formation + 1 合法独立 Review；与 ordinary35b 的 19-source 边界不同，不混用。Task FactReference 与 admitted Fact 一致；计数源完整原文跨度 [0,48) / [0,55)，唯一目标 index.html，baseline03a2a8787a729025388a1bed70268973a65d8657、Reality011483f7-de9d-5275-98ff-ab4c66c163aa。来源和组件全集、排除 rationale 的候选/组件指纹已独立重算匹配。除已证实 unit 硬拒绝外，没有发现该计数实现其余前提字段差异。
