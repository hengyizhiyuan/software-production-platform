# 普通 G0：重校准后的事实、失败分类与下一步

记录日：2026-10-11。这是新试次和只读分析，不改写任何历史Work或候选。

## 确切运行与实际结果

应用 `5cd33c9bf8a3aaa7e237d267dd09638025ad47ee`，Tree `a35b32b1c06d51b6a26b9026d840ef17fc449165`；实际安装镜像 `sha256:c87016e8fb5f73599b633ca6bf25e4ae77fa22901d202d45684cb71e7cc02446`。Guardian/ECF仍为本评估固定版本。

正常用户入口Work `109d783b-4632-5251-9470-276bdfa45e99`，Product `9de6f6e2-ad97-4ca8-adc6-2f20efdfc0a1`，Reality `2ae54e34-7c04-5e40-a8f4-d15e2f4cbfdb`。新库存25项，fingerprint `852b025ed68014f6a7d4603d032c4526dda626b458b644a21a6be6aaca00a8fa`；不是此前26项历史诊断库存。

| 实际 Formation | 输出 / Token | 结果 |
| --- | --- | --- |
| 1 | 27路线；9,375字节；48,914 tokens，reasoning 0；10.449秒 | 原文件边界Fact的Diff方法因BOUND关系被拒绝。反馈保留并绑定。 |
| 2 | 28路线；11,311字节；62,856 tokens，reasoning 0；11.190秒 | 相同文件边界拒绝仍存在；新增当前Fact的Seal绑定被拒绝。终止，未接纳。 |

两次Provider均为completed，传输重发0。Formation合计111,770 tokens，Provider完成耗时合计21.639秒；不是整个Work/C3总成本。全部Work模型成本尚未聚合，UNKNOWN。没有发生输出预算耗尽；不能用过去容量故障解释这次停止。

实际权威记录没有生产Run、PWU、执行、Git结果、Verification或密封Candidate；独立Semantic Review未调用。API显示Admission READY、automatic progression STOPPED、work_complete false、无Human请求。READY不代表Runtime接纳，也不能据此判断数据库不一致。所有记录保持原状。只读控制观察器在终止证据取得后主动停止，退出137有独立检查点；不是Provider崩溃，也不是Work PASS。

## 逐项分类：不从错误码推断语义

### 文件边界：B / P0–P1，已证实消费限制，语义接纳仍未取得

来源3是原始允许文件变更边界；其Fact关系为BOUND，原值为精确目标路径。两次模型均选择实际Git Diff Owner，Fact的值、关系和原文未被修改。

现有 `_fact_evidence_method_failure` 对Diff只接受SCOPE；`literal_file_scope_value_paths` 同样只观察SCOPE。同一来源在现有契约下只能机械通过内容或UNRESOLVED处理，前者不能单独证明其他文件未改变，后者正确阻断生产。因此继续原样生成，或者把要求改成HTML内容，不能解决这个消费能力缺口。

这一证据证明的是消费适用性限制。它不直接授予该路线语义PASS，不证明Diff已经执行，也不允许将BOUND重写为SCOPE。最小修复必须让现有独立Review评估原完整Fact和候选方法的对应，并由原Diff Owner执行确切版本/允许范围检查。不是增加Subject或文件名特例。

### 当前内容和未来Seal：未决；不能直接判为A类生成错误

来源0为当前页面生产目标。第二候选有自己的当前ARTIFACT_CONTENT路线，同时提出未来CANDIDATE_SEAL，原Fact值包含reviewable Candidate含义。原Fact关系仍为SCOPE。

当前确定性规则对所有非ACCEPTANCE_ASSERTION Fact禁止Seal阶段，因此先行拒绝。但这不是“把全部当前要求延后”的证据。准确问题是：原始目标、组件范围及已接管的Candidate Gate，是否足以支持这个未来组件；需要在保留当前内容消费者和原完整Fact的条件下判断。其独立Review尚不可评估，不能把规则拒绝当作模型语义错误，也不能自动认可候选。

### 背景来源：本次没有证实新缺陷

来源4/6在完整候选中满足既有背景候选结构条件：当前Fact自己的消费者仍在，同一Production Item有实际当前请求。独立语义等价仍未审查。最初单路线隔离探测没有传入完整计划的背景引用，产生额外拒绝；[完整计划复核](g53-source-consumer-full-plan-classification.json)纠正了该诊断范围。不得将原探测的额外拒绝归为真实运行失败或据此改平台。

### A / C 边界

重复检查、错误目标/方法、合法映射已可表达时的候选遗漏，继续由原有有界反馈处理。历史Review错误放行及修复证据保留，本次没有Review调用，不能把历史Review问题算作本次失败。

错误版本、替换来源、伪造权限、缺必要证据仍必须阻止接纳。本次停止未创建授权或越权执行。这里的零执行记录仅针对当前Work关联的Owner快照，不是完整平台“绝无非法效果”审计。

## 下一步的有界实现顺序

1. 在现有Formation/Verification责任内，分开“候选方法可交给独立Review评估”和“已经取得实际证据、可以接纳”。固定Fact关系不应自动替代开放语义方法判断；Fact身份、原值/关系/Scope/Qualifiers和Authority全部保持。
2. 为实际文件边界及混合当前/未来组件证明合法消费路径。复用现有组件、独立来源消费审查、Task允许范围、当前内容、Diff和Candidate Gate。仍无法证明对应时UNRESOLVED，不静默选一个方法。
3. 先做少量跨表达定向正负例：相同合法边界的不同表示、当前内容不可被未来Gate取代、数值/内容要求不可误当文件许可、错误路径/版本、不存在的Gate或证据持续拒绝。不是枚举本次字段；不提高请求、重试、Token或权限。
4. 受影响持久化与Watt/Guardian联调有具体变化时才重跑对应集成；稳定修订再冻结应用/镜像。文档变化无需重建应用。
5. 有效修复后在合法新普通G0使用既有两候选/一次反馈收敛。单次耗尽保持失败；工程修复不因两候选用完而自动结束。不得无改变重复建Work。
6. 普通G0到达Candidate/Verification/适用Guardian后，由既有独立Reviewer在最终版本执行封存Holdout；不读取或用其调优。真实Human Acceptance仍是其后续Gate。

本轮重校准完成了规则落库、最终源码受影响持久化资格和真实阻塞复核。以上消费校准是下一项必要工程工作，不宣称已经实施或通过，不将80%规划估计当作C3 Closure。

## 恢复与证据

[安全结果](g53-real-g0-review.json)、[完整计划只读分类](g53-source-consumer-full-plan-classification.json)和[固定证据SHA清单](g53-real-g0-safe-evidence-manifest.json)随既有任务分支持久化。

完整私有Wire、Owner快照和控制收据在ECS `/data/watt/c3-semantic-convergence-20261009/binding-g0-generation53-qualification-20261010/`；没有复制完整Human输入、模型私有内容或凭据到Git。确切资格构建/回归仍在G53 qualification根目录。持久路径不是异地备份或restore已经资格的声明。
