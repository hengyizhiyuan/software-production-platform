# C2 恢复与复核

## 身份与状态

本记录是 2026-10-09 的新资格，不冒充旧 N1 报告。结论 C2 PARTIAL。应用源码 88f1d9805d3ed1aa779ed3c78902b193fae240f8；镜像 sha256:205f7b42539767939675cebd6e8380be2757c5ebd6d7fbb08828bffae7799209。证据交付 HEAD 以后续 Git branch/远端 receipt 为准，不能替代应用身份。

新 ECS 根 /data/watt/c2-execution-readiness-20261009；六个新 C2 服务已停止并保留。原 G0 Work b9c67d91-2cc1-5f91-bf61-8d7939b45cc3 仍 STOPPED，不能 reset、修改或重写历史。保留原生产 canonical 与旧 N1/C1。

## 跨电脑恢复入口

1. 从远端检出 codex/c2-execution-readiness-real-g0；公开证据在 docs/evidence/core-production-execution-readiness-c2-20261009。用 evidence-index.json 校验每个记录的相对路径、长度和 SHA256；索引自身与对应提交由 Git 证明。
2. 通过已经授权的 watt-ecs SSH 读取上述 ECS 根目录。不打印 private 环境文件、数据库 secret 字段或完整 Docker environment；不要把 private 归档提交 Git。
3. image-recovery.json 记录 exact image tar.gz。校验 SHA256 后才 docker load；加载镜像不等于原 PE actual digest 的历史证明。
4. consistent pg_dump 与 quiesced archive 位于 private，root-only；哈希分别见 persistent-recovery.json / quiescence-and-preservation.json。quiesced archive 优先于早先 live archive。原 private/raw 冻结快照用于有权限的详细取证。
5. 恢复数据库应在新命名的隔离 PG/DB 中执行，不覆盖生产、旧资格或原失败 Work；恢复 Gitea/Owner stores/volume 也使用新隔离 root。原始新 C2 bind/volume 仍在 ECS，不必为读证据启动业务角色。
6. Git input/output 证据可以独立恢复：在临时空 bare 仓库，执行 git index-pack --stdin 输入 git-witness/source-output.pack；再以 git rev-parse / cat-file / diff 核对 manifest 中 input/output revision/tree 与 index.html SHA256。已执行的独立恢复收据为 git-witness/recovery-check.json。这不是创建 Candidate 或授权。
7. ECS delivery-receipt.json 记录推送后 exact HEAD、远端核验、最终公开包及 Git bundle 路径/哈希，便于 Git 服务或本机丢失时恢复。恢复 bundle 到新的检出，不能覆盖原工作树。

## 已运行测试与复现命令的边界

测试在 final exact image 中以 UID/GID10001、原现有权限规则、独立 fixture DB 执行。环境与命令详见 harness/run_c2_regression_final.py 和 c1-chain-final-88f1d98/receipt.json。不要把 harness 当幂等业务启动器：一些脚本断言 fresh path，创建资源或提交 Product/turn。

最终执行采用两个独立 pytest 进程：

~~~text
python -m pytest -p no:cacheprovider -o junit_family=legacy \
 tests/test_c2_workspace_preflight.py \
 tests/test_production_execution_runtime.py \
 tests/integration/test_c2_workspace_preflight_events.py \
 tests/integration/test_native_executor_runtime.py::test_production_worker_records_isolated_change_and_diff_evidence \
 tests/integration/test_native_executor_runtime.py::test_production_worker_verification_failure_cannot_claim_result_ready \
 tests/integration/test_native_executor_runtime.py::test_production_preflight_failure_keeps_exact_diagnostic_before_terminal \
 tests/test_c1_ecf_contract_compatibility.py \
 tests/test_guardian_assurance_adapter.py
python -m pytest -p no:cacheprovider -o junit_family=legacy tests/integration/test_c1_contract_continuity.py
~~~

以上只说明对应 suite；确切第一进程 node IDs、实际 argv 和 tests 路径应以已留存的 runner/JUnit 为准。第一实际 mixed process 同时包含 C1 文件，产生29PASS/50setupERROR；第二 single-file 50PASS。避免相同根目录的多个显式 DirectoryNode 造成 fixture identity 问题。没有授权或必要缺陷时不重复全库、模型和 G0。

本目录 harness/ 保留操作与导出源码，并不包含密钥。构建使用 git archive 的 exact input 与 Owner archive；Dockerfile.c2 是已执行 recipe，build-input-identity.json 与 build-88f1d98.json 记录材料哈希，runtime/import attest 记录实际安装模块。新应用源码无运行 overlay。

## 真实入口恢复限制

harness/c2_normal_entry.py 和 C2_NORMAL_ENTRY_DRIVER.md 实现 normal Product + experience turn，操作状态在 POST 前落盘。normal-entry-state.json 已记录两次POST各CONFIRMED及终态STOPPED：

- 可以读取现有 Product/Work/Attempt/trace；不得重复创建新 Product/turn。
- 不能删除 driver state、重用run ID假装新试验、自动批准Human、手造EngineeringFacts/bindings或重置原Work。
- 真实后续 Work 必须先在新修订修复共同故障且获得对应范围授权，再使用新的 identity；本轮没有进行该重试。
- 两次 local DESIGN Self-Refine 已发生、Worker随后完成；不要重新触发同一副作用。
- PE handle 已移除、实际 image observation UNKNOWN；不得新建替代容器来冒充当时观测。

## 证据等级

本报告不发明新的 Runtime 状态。使用以下报告级等级定位证据：

- PERSISTED_OWNER_FACT：事务快照、WorkReality/IR/Task/Native/Verification/WHERE/权限记录与事件；范围和 query_status 保留。
- CURRENT_RUNTIME_OBSERVATION：真实 Docker import/image、Worker path/stat/namespace、当次已发生检查；只证明记录时点。
- EXACT_GIT_WITNESS：可恢复 input/output Git object、blob、diff、SHA256。
- CONTROLLED_REGRESSION：同源镜像的 pytest 正负用例；不能替代真实 normal-entry Work。
- CODE_BOUNDARY_ANALYSIS：exact修订代码解释已观测结果；不是已丢失历史candidate的重建。
- UNKNOWN：未保存的模型失败check、完整费用、原历史Attempt根因、已移除PE actualimage等；不以当前代码或无日志推断。

公版文件已基于已知实际凭据扫描、脱敏；扫描零命中不构成未知敏感内容或全局审计完整性证明。共享测试 Provider key 为Human明确授权例外；新控制/存储凭据仍独立。凭据轮换、原环境重启与生产变更未实施。
