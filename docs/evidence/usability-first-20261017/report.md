# 可用性优先：完整需求直接进入生产

本轮修复的是“已经接纳的完整需求，仅为了交给执行器，又要经过生成式拆解与审查”的重复门槛。普通的首版排除项已有 ProductionIntent.exclusions 原始来源，旧路径却要求另一份否定来源才能分配内容验证，最终在开工前循环失败。修复后，完整原文交给现有执行／验证责任方，标记为待证据；不把模型说法、待办分配或静态回执当作实现成功。

Watt 保留完整 Facts、IR 条款、约束和排除项，复制全段原文；源、目标、权限及完整性可直接核对时，无需 Formation/Review 模型调用。未知权限、未解决来源、真正的语义转换仍留在原有有界流程。真实产物由独立 Verification 检查，Guardian 独立读取原始记录复核。发布镜像锁定 Guardian 7910649aefadc6ed5447bda33ffe493f856b3f23，新增发布检查防止上下游只部署一半。

## 实际结果

通过正常 Product／交互入口，真实 DeepSeek、Native 队列、Docker PE 生成了“拾页”阅读清单。最终 Work de0d0971-0765-5ec6-8d02-f41d9699feff；PWU a50a6541-a486-4187-8e96-afb99b856b2b；成功 Attempt 0594069c-8676-473c-820a-7cbc9e21c00e。零 Formation／Review 模型调用，独立 Verification PASS，封存 Candidate cd731404-0366-5d1a-99f3-ba25b43e8e4b，产物 commit fc2d5b72f327f315330309da53529b0bbf0298f3 / tree 52c82cf69001b0c358da655c709d5a71fb692b64。

初次 Guardian 因旧审查链协议阻塞 11 条要求。修复其独立证据消费后，使用正常的预览停止／重建接口，创建新 Preview 64729979-2abe-4037-88c7-7aa0b3c1ea2e；新请求 bdc20a43-53bb-51e4-b1b4-e9444f89d8d8 为 PASS，零 findings，原 BLOCKED 请求 1c41831f-4758-540e-9450-e929cfa75b03 和原 findings 完整保留。Watt 界面投影已为 PASS／待 Candidate 授权。未替用户完成产品验收、Integration 或 Delivery。

浏览器实测：新增书名和作者、标记已读、筛选未读、刷新后数据仍保留；截图为 browser-reading-list.jpg，真实产物为 qualified-reading-list.html，SHA-256 6a3ba2d756666afbdf535d0414bf39df7565d71210d76f08a8777b6b0db64e1e。浏览器验证不代替 Human 产品验收。

## 保留的失败与边界

- Trial 1 / f230684d-d318-5a77-b844-7ab23674529f：旧路径无法接纳普通混合否定需求，未生产；最终代码只读重算可接纳。
- Trial 2 / 0776ac52-29de-5978-9ac6-271decf195a8：相同结构缺陷修复后经一次正常有界恢复进入 PWU。隔离环境 ToolHost 根目录配置错误，409 拒绝后产生效果不确定性，保持 RECOVERY_REQUIRED，未强制重放或清空预算。
- Trial 3 / 24ec6e6c-4a6a-5925-b17a-9efa73d34e9d：较长输入还包含显式预览／不对外部署；实际 IR 含 ACCEPTANCE_ASSERTION、未分类 REFERENCE、未来条款，继续走旧语义流程并失败。本轮没有资格声称该路径已修复。最终通过的 Trial 4 输入更短，不能用它替代 Trial 3 的覆盖结论。
- Trial 4 第一 Attempt 因 Mac 挂载目录 UID 与 PE 镜像用户不一致，Git 拒绝 dubious ownership，保留真实失败。仅隔离环境改用匹配宿主 UID 的 PE 镜像，再经正常 successor/retry 和 Attention 恢复，第二 Attempt 成功。线上 PE 配置未因此放宽。
- 较早不带正确 Origin 的本地 POST 被 CSRF 拒绝，无实体创建；改用正常 Bearer 认证。ToolHost 后续每次真实执行均使用 PE manifest 和 network-none Docker；未使用隔离回退路径。

线上原游戏 Work b1e59aa3-eaf3-5c6a-8bc0-fa0eff470ad9 仅只读观察：用户三次重试确实运行，但六轮 Formation 在 PWU 前失败。以 index.html 为资格验证目标假设，新路径对其原始来源的只读重算可形成完整待验证 brief（不证明实际 Planner 已接纳该目标）；没有启动它、改写来源、恢复预算或宣称它已成功。

## 验证与发布定位

Watt 新路径 25 项通过；Guardian 完整 318 项通过；有界恢复相关 51 项通过；PostgreSQL 5 项通过。初次受影响回归 1033 通过、3 个已确认基线失败（重复 wire feedback 两项、next_request_limit 一项）；未放松断言。固定 Owner 后的最终回归为 1046 通过、55 跳过、相同 3 个基线失败；详见 release-tests.log／qualification.json。源和证据已扫描隔离环境实际密钥值，未提交环境文件、数据库连接或登录凭证。

这是完整原文待验证路径的实测资格，尚不是所有普通表达／所有产品形态可用的证明。未来 Preview／Human／Delivery 条款以及需要解释的来源仍走旧流程。发布验证与应用版本保存在部署回执中；本文件不通过设计声明推导 Runtime PASS。
