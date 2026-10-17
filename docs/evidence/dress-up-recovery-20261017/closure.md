# 少女换装原 Work 恢复结果

2026-10-17，修复已部署，原 Work 完成生产，形成通过现有验证及独立 Guardian
检查的 Candidate。当前等待 Human 对该候选的正常整合授权；未验收、整合或交付。

## 根因

北京时间 18:56:09 提交原始需求，18:58:17 补充校园风，18:58:29 创建正式 Work。
补充发生在正式 Work 准入之前，同一 revision 已包括五种风格、画面与音乐要求。
正常补充操作暴露平台缺口，并未破坏执行中的合同。

三次重试的六次 formation 失败最终均为
`OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN`：来源保真交接不支持
跨轮携带的原始 Human 画面验收要求及 MP3 目标；模型回退错误地用校园风肯定补充
为已准入的排除项寻找否定依据。修复将完整已确认要求及确切原始来源交给现有
成果验证与审阅 Owner，避免生产前重复解释，保留实际内容及后续审阅义务。
另补齐受限音频格式观察、两条精确预览资源服务及 managed Web 执行上下文。
Guardian 在独立源码库适配；来源、权限、路径、大小、CSP 和验收边界保留。

## 发布身份

- Watt `24ceccf9a70f72193a643d52897dcbb9f803476b`，三个修复提交已推送原分支。
- ECF `1d3feddf0c7e7726fea23c58d194d64034547a7a`，保持原 pin。
- Guardian `26bb402563bb781731749b7b8fb4fe5aed74f669`，独立发布。
- 镜像 `sha256:8631d76f82a3d5bf2f6d549d643ceea3e5e6cd41cd94da947f3e0ccc51d405e5`。

四个运行服务使用同一镜像，Owner release gate PASS，见
[部署证据](deployment-qualified.json)。后续证据提交不改变部署源码身份。

## 真实执行

Work `12cecacf-a97d-515f-8515-9845abadaea9`，原 Work Reality revision
`7d90f52b-7a76-51c4-8bbd-430a94623457`、source
`012e4165074ea2bb561597f51bb666fd5ea166b3` 及五个文件范围均不变。
首轮恢复跨过 formation，旧 Task 缺音频上下文，在 Native 准入前停止；旧记录保留，
现有 Steering Owner 生成同一 Work 的后继步骤，见 [恢复证据](context-owner-recovery.json)。

后继 PWU `bdafe96e-0158-4283-92ef-e1b25c55fef1` 携带 20 个待实际验证绑定，
formation 模型调用为 0。Attempt `8d8df8b8-97dd-4a13-ad74-352388aea1fb`
完成 17 步，queue `50f310e7-29b4-4f59-808d-681f22a02e30` 为 COMPLETED。
PATH_SCOPE、GIT_DIFF_CHECK 均 PASS。

- Candidate `be81eb65-fa9d-5ae1-83a6-ef9ff254aaa9`。
- fingerprint `ae946c540c50abaaf89508c0bdfa7cb5df159363753d986b61249f11a9ce43cd`。
- revision `d3292ecfcf5dc1ce2f4579c7211f585cd07387c5`。
- tree `6c25ce6eb8887a2b40cfe148a5e94e44cea2a746`。
- Preview `5fb948c3-a383-42d6-aca6-c6a0cd210ae8` 为 STATIC_PREVIEW READY，
  真实服务入口 HTTP 200，确切 revision/tree 匹配。
- Guardian `44ec7cf6-d2ed-50a6-ab87-69bb21740d9a` 为 PASS、0 findings，
  evidence `06abbba4-576c-4c05-8881-abc3319cae03`。

北京时间 22:10 从正式鉴权精确 Candidate 预览接口再次读取全部五个文件，均 HTTP
200，revision/tree 一致。音乐 319005 字节，`audio/mpeg`。哈希与最新投影见
[在线成果证据](live-candidate-qualified.json)。

浏览器 DOM 确认原工作台显示执行完成、两项独立验证通过、质量检查通过，并提供
“打开预览”和“授权”。浏览器自动化连接在点击与截图时超时，未确认服饰交互或
实际播放；本次不声称完成视觉/听觉体验验收。Preview 服务证据与该限制分别记录。

原工作台：<http://8.130.172.58:8080/products/6ea83f51-f97e-4d78-ae3a-7cc82aaf2c79/workspace>。
`authorization_pending=true`，accepted version 仍为 0；其他暂停 Work 未恢复。

受影响回归已通过，独立 Guardian 全套 350 项通过。测试组选取有交叉；原基线
receipt fixture 失败保留，见 [验证范围与限制](qualification.md)。不宣称全仓库或
所有 Golden Journey 均已通过。
