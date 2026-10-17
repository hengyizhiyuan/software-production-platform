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
