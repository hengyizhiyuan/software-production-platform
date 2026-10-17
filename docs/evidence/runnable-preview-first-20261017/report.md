# 暂停原任务、恢复预览与验证链瘦身

按 Human 2026-10-17 的三项顺序执行，起点 Watt `2bae5c584eecb8ad3d0ab2b5a953aefa92d626c2`，分支 `claude/c3-formation-ai-native-convergence`。Guardian/ECF 固定版本不变。

## 原任务已暂停

Work `b1e59aa3-eaf3-5c6a-8bc0-fa0eff470ad9` 的 Work Reality `bfcb502b-855d-58d3-bacb-e93208997e1b` 写入明确 Human 暂停记录；当时活动执行队列为零，重启 API 终止进程内验证并加载暂停。使用原有持久暂停 gate，没有伪造新的 convergence incident；记录 rationale 保留这一兼容处理。新的正常暂停 API 使用 `WORK_PAUSED`，不再借用 incident 类型。调度入口与每次推进均读取当前暂停事实，暂停投影与普通用户文案不再显示无限验证。原失败/UNKNOWN、预算、Work 原诉求和既有图均保留。

## 原产物可实际预览

从原 Work 各 Attempt 工作区保留八个已生成文件，精确来源见 retained-artifact-lineage.json。入口 `src/main.js` 没有生成成功，补上连接现有状态、植物、僵尸、阳光、关卡和 renderer 的必要代码；index.html 仅补空 favicon，避免额外不存在的资源请求。没有重新生成八个模块或实现额外游戏功能。

快照 `6a3cf55153cf5e1e58fe062ae0b5bacb1ca14c232d27edb039b93af56a5021fe` 已在 ECS 的认证 Work 路由提供，并在普通工作区加入“打开已有成果预览”。真实 Chrome 打开服务器页面、开始游戏、放置向日葵，推进到第一波；没有脚本或资源加载错误。浏览器使用时钟推进 19.5 秒，不声称完成整关、原版素材复刻或完整功能验收。原 Work 继续暂停，没有重开生产 episode。

该预览明确是 `NOT_QUALIFIED` 的现有产物检查快照；它没有制造 Verification PASS、Candidate、Guardian PASS、交付或 Human Acceptance。原始压缩包与修复后的运行快照均保留在本目录。

## 验证链的实际变化

- 普通有界多文件实现默认一个可整体验证的生产单元，避免按文件名自动制造独立能力和整合门槛；明确独立单元/前后基线要求仍可形成多 PWU 图，既有执行容量要求保持。
- 实现生成后，Preview Owner 在便宜的准确版本/修改范围检查后先提供有界静态工作快照，不等待语义审查或最终 Candidate。可查看不等于已能正常交互，运行情况以实际观察为准；完整运行环境仍由原 Candidate Preview 处理。
- 同一确切产物的独立内容审查共用一批结果，Fact、Work 约束、ECF 已有政策和履约清单复用对应证据；负结果同样复用，不能反复换表述要求模型给 PASS。缓存只属于本次调用，不跨产物/来源/责任分配。
- 既有 ECF 产品不变量/批准决策直接对当前产物检查，去掉必须再制造 Work 条款绑定的错误前置条件。来源/版本/真实文件证据仍保留。
- Verification UNKNOWN 与内部责任绑定故障停止在验证 Owner，禁止据此重新生成业务代码；UNKNOWN 不再永久显示 VERIFYING。必需分支恢复耗尽时全图停止继续生成兄弟分支。
- 暂停投影直接表达确定的 Human 暂停，不再为暂停状态追加模型润色任务。权限、准确版本、最终独立 Verification/Guardian、交付授权与 Human 验收没有变成自动 PASS。

## 实际检查与保留限制

最终聚焦检查 105 通过；前端 12 通过；真实隔离 PostgreSQL 的暂停持久化/Native 控制 3 通过，串并行多 PWU 与真实分支整合 6 通过，Work 层并发调度/重启连续性 2 通过。开发期间较广检查初次 1276 通过、11 失败；其中 8 项是新暂停读取增加后测试替身尚未提供该 Owner 读取，已补齐替身并纳入最终聚焦通过。其余 3 项为前轮已保存的 duplicate-response、duplicate-validation、next_request_limit 起点失败，本轮没有改变对应生产实现或放松断言。这里没有宣称整个测试库全部通过。

另外做了一次真实模型/实际游戏源码的独立消费试验，停在 `PROTECTED_CONTEXT_WITNESS_NOT_OBSERVED`，没有制造通过或继续无限试验。这说明模型源码引用协议的失败仍可能存在；新行为让其停在验证 Owner，且不阻止已有快照预览。它不是完整新 Work 的端到端 PASS，本次也不作此声明。正/负聚焦用例验证了一次内容判断在多个内部表示间复用、负结果不升级、换来源/产物不能复用。

部署的准确应用提交、镜像、服务健康、暂停与预览后置观察记录于 deployment.json。后续只补证据文档不要求重新构建同一份运行源码。

## 部署结果

应用提交 `536e6bb010f350e7c79b79a497d153d03e242cef` 已推送并部署 ECS 8.130.172.58:8080，四个运行角色使用镜像 `sha256:fb12adc6803532991554551eada71335a9be219dce366c8ba6956f3a2399d7e3`。镜像内源码哈希、锁定 Owners、健康检查通过；部署前后原 Work/Runtime binding/Reality revision/queue 指纹一致。部署后正常认证浏览器通过新的暂停 API 记录 `WORK_PAUSED`，工作区显示暂停，预览按钮可见且可实际开始游戏。2026-10-17 11:39 上海时间的后台观察：活动执行 0，最初 Human 暂停后新增执行 0。初次浏览器测试请求未携带 Origin 被正常 CSRF 边界以 403 拒绝；补齐同源请求头后通过，没有修改安全边界。

最后的证据文档提交与上述运行应用提交分开；没有为补充这份记录重新构建镜像。
