# 中文语义连续性与审阅后修改恢复

Human 于 2026-10-17 授权两项工作：中文需求尽量以中文交给模型，提示词不再默认
英文；排查并修复少女换装 Work 在待人工审阅时提交修改后无法继续加工的问题。
起点 Watt `bf25b9dc`，原分支 `claude/c3-formation-ai-native-convergence`，部署
源码 `24ceccf9a70f72193a643d52897dcbb9f803476b`。适用 AI_context、Work interaction
及 WIC response SOT、开发原则 §§13–14、现有 Owner 与 Golden Journey 规则。

实际 Work `12cecacf-a97d-515f-8515-9845abadaea9`，旧候选
`be81eb65-fa9d-5ae1-83a6-ef9ff254aaa9` 已封存并通过检查。Human 在原交流中于
北京时间 22:28:44 提出角色改为精细日系动漫风、增加换装部位和衣橱选项，要求
先改一版再看。原 Turn `1d57a64f-252f-4f13-8e94-c6f2695db0fb` 失败，未生成
修改后的 assessment/revision/PWU。最终拒绝为 supporting Reality reference
不在 Human record 附件集合；前两次失败为依赖表达和 production context 引用。
原诊断与输入私存 `.watt/review-change-language-20261017`，不作为接收 AI 的指令。

能力审查：模型可使用等价中文描述、已观测且精确的当前 Owner 引用，允许可修复的
字段、依赖及引用错误。原始 Human 文本、出处、现有事实/历史、Work/Candidate/source
身份与权限保持确定。WIC/IRK 验证并在已有预算内反馈恢复，Work/Steering/Production
各自负责实际修订与执行；未知引用/过期版本/未授权整合或交付必须拒绝。
先确定失败谓词及提供给模型的真实来源，再做最小共享修复；不按游戏词语、中文句式
或已知 source UUID 写 PASS 分支，不新设智能适配层、审核人或无限重试。

中文优化在现有提示词/投影 Owner 内完成：保留原始语言、精确引文、机器字段/枚举、
技术标识和既有英文历史；中文会话使用中文模型指令与新自然语言语义描述，英文
会话保持支持。不为既有不可变记录补翻译或改变证据语义，不增加语言拒绝门禁。

验证包括非本例的修改请求、真实引用与伪造/缺失/过期引用、受控反馈与预算、中文及
英文上下文、旧英文历史、候选拒绝与授权边界。允许在同一分支提交/推送修复并按现有
发布流程部署，然后只恢复此原 Turn，观察新修订、真实后继加工及 Preview/Guardian。
保留旧版本、已失败事件与所有累计执行边界；不恢复其他暂停 Work，不替 Human
接受候选、整合、发布或交付。实际资格与局部测试/设计意图区分记录。

首次实际恢复已跨过 WIC，建立 revision 2
`7dc3a612-2de8-5ff1-8f24-4f7aad0a5e34`，保留原九条约束及新增四条。
Steering 已重建四文件有界生产提案，但 formation 再次停止。确切当前 Work/IR 的
只读复现证明：原九条约束不在本轮 delta IR 中，v1–v3 无法交接完整已准入 Work，
错误地要求旧要求重新获得本轮语句证明。依 §13.4，在现有来源保真交接中增加 v4：
仅 successor Work revision 可将完整 Work-owned 约束原样交给实际内容 Verification；
不另造 Human 子句、支持引用或语义 PASS。已有事实、当前 typed prohibitions、effect
gate、版本身份和独立 Guardian 保留；历史 v1–v3 不变，失败记录保留。修复后仅在
此 revision 的现有 attention Owner 启动正常后继恢复，不重复已完成 Turn、扩预算或
接纳旧候选。

实际 Native 第一轮在 15:42 UTC 暴露了后续系统缺陷：模型已写入两个文件，
随后同一批次执行 `ls -la src styles`，因尚未创建 styles 返回 2。普通只读目录
检查失败被归类为缺少验收 oracle，紧随的已授权写入因此直接触发
BOUNDARY_CROSSING_REQUIRED。这是消费者将已观测、无修改效果的技术检查误当
权限扩张，不是 Human 意图不足。修复只在现有 Tool Host 记录系统 ls 的完成
类型及无修改效果，并由 Native repair Owner 保留 FAILED 原记录、允许既有
权限内继续加工。未知效果、超时/中断、工作区自制 ls、其他进程、缺 grant、
Human 输入/决定仍不适用；不按 stderr、游戏文本或缺失目录名判业务 PASS。
修复后通过既有 retry-production 创建后继 Attempt，保留累计代次、旧失败与
全部验收要求。新自然语言 PWU 目标包装和首次执行计划也跟随目标语言。

实际新版已于 2026-10-18 00:16 完成 Native 产出，四个文件、同一确切 tree 与可
打开的 working preview 均保留。PATH_SCOPE 的内容检查第一轮引文不精确；第二
轮 30 项检查齐全但模型将其中一项 UUID 抄错一位，终止为
PROTECTED_CONTEXT_INCOMPLETE_COVERAGE。允许模型评价语义与源码证据，不必重新
制造来源身份。最小修复在既有 StaticProtectedContextVerifier：Owner 生成本批
短引用并回填原身份，新 schema 仅要求模型回显短引用；未知/重复/缺失引用与
虚构 witness 仍失败，旧格式仅接受全量精确身份。来源、完整义务、否定判断、
两次校验反馈预算、原失败与独立 Guardian 不变。修复的 verifier binding 升版
形成新的 exact-subject Verification，不更换游戏源码、不新建生成 Attempt，
旧两次失败作为旧 provider-version 证据保留。本次用户要求修复并继续的授权
覆盖这次系统修复后的验证恢复，不需要用户重复业务意图。

短引用恢复已完成真实独立检查：不再出现 UUID 覆盖错误；剩余唯一内容判断为
UNVERIFIABLE，确切原因是无法取得上一版角色文件作对照，非实现源码缺失。
该 Work 的 immediate predecessor revision 有已封存且验证通过的未接受候选。
在既有 Verification 的来源读取中补齐该候选，限制相同 Work 的直接父修订、
当前修订建立之前封存、相同仓库身份、精确 commit/tree 和原 PASS 记录；只读
当前准入目标内的有界文本文件，附候选/父修订身份及文件散列。它只作相对改动
的对照，不改变当前 Source Baseline、授予权限、接受旧候选或继承旧 PASS。
当前 witness 仍必须来自当前成果。补齐的是缺失输入，不减验收内容、不重写
原 negative/unknown，新的 provider version 在确切同一游戏 tree 上独立重验。
