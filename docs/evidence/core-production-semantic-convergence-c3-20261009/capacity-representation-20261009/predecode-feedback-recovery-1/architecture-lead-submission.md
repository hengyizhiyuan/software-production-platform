# Architecture Lead — C3 Predecode Feedback Recovery

**最小修复已完成，C3 保持 PARTIAL。**

- application `e7afb5a15df4c187a9248b4a073391a62037677f`，actual image `sha256:e42fcb7dfe18254f1396f2faaaadd95b0d24efe445db6ce19beedfdebac32726`。
- 原始 Wire SHA256、库存、Attempt、请求/响应持久收据、Work/Source 与 Wire 元数据绑定；下一请求引用反馈收据；恢复/重放重算核对，漂移 truthful stop，不增加模型请求。
- 原 Wire/schema/source index、Owner、权限、两候选一反馈预算不变；无 FACT-only 新索引空间、语义 Alias 或新协调层。
- 最终镜像 299/299 回归、9/9 PostgreSQL 集成通过，包含独立 Guardian 既有证据核验路径；Guardian/ECF 无需变更。
- 旧 raw 提案依然拒绝：两份分别得到 2/6 项明确错误；未修补、替换历史反馈或修改 Owner。
- 新模型调用 0；受控“反馈后新合法候选”证明机制正确性，不能证明真实模型一定修复，也不能替代独立语义泛化资格。

下一项必要资格：仅针对这组冻结身份进行限定真实模型收敛验证，保留原库存、一次反馈、累计预算与独立 Review。
本轮没有发起该验证、G0 或 Holdout。Option B 不因本次工程回归自动获得必要性证明。

完整实现、失败收据、预算/恢复与未关闭义务见 [review.md](review.md)。
