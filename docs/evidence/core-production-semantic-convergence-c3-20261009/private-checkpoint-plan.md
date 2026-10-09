# C3 私有恢复检查点（控制方案，尚未执行）

本方案仅针对 `/data/watt/c3-semantic-convergence-20261009` 及其 `retry-1` 子目录。它不提供通用备份服务，也不改变 Work、Candidate、Human Decisions 或任何治理事实。

## 执行入口

控制文件：`harness/freeze_c3_private_checkpoint.py`。它支持 ECS 主机 Python 3.6。

默认运行仅打印静态计划，不访问 Docker、数据库、网络或 ECS 文件：

```text
python3 freeze_c3_private_checkpoint.py
```

只有 root agent 在真实资格、取证和必要收据完成后，核对该控制文件的冻结 SHA256，并明确选择本检查点执行，才可在 ECS 主机运行：

```text
python3 freeze_c3_private_checkpoint.py --execute-private-checkpoint
```

该操作会停止已核对的 C3 应用和依赖角色，默认保持停止。不会重启、删除、清理、重建、恢复或推进 Work。应用若已停止则只核对状态。PostgreSQL 必须仍可运行以便一致性导出；脚本不会自行启动已停止的服务器。

## 恢复资料及覆盖范围

执行时必须存在原轮和 retry-1 的最终 `isolation-preparation.json`、`runtime-role-preparation.json`、`driver-runtime-identity.json` 和 `build.json`。缺失、版本漂移或范围不明确时停止，不猜测。

- 私有位置：原 C3 `private/checkpoints/<UTC>-<uuid>/`，目录 `0700`、文件 `0600`。原私有文件、旧构建、旧失败 Work 和历史收据完整保留。
- 公开结果位置：原 C3 `evidence/private-checkpoint-<UTC>-<uuid>.json`。仅含时间、确切源码/镜像/容器身份、数据库名、归档整体散列、状态与边界。
- 实际应用容器：原轮与 retry-1 的 API、Coordinator、Worker、Tool Host，共八个明确角色，容器 ID、image ID、标签、用户和 mounts 均核对收据。
- 共用 C3 主 PostgreSQL：分别导出 `spg_c3_qualification_20261009`、`spg_c3_retry1_qualification_20261009`、原 C1 真实夹具库 `c1_contract_continuity` 和 `c3_independent_holdout_20261009`。已声明空库 `c3_contract_regression` 如实际存在也独立导出；如不存在则明确记 `ABSENT_OBSERVED_NO_DUMP`。逐库记录实际存在、迁移头与导出状态。独立 Holdout 数据仅进入私有 dump，不读取或公开其内容。
- retry-1 独立夹具 PostgreSQL：导出 `c1_contract_continuity`。其实际容器 ID/image 与 bind 数据目录来自新 retry isolation receipt，不把它误认为共用主 PG 的数据库。
- 两个 PostgreSQL 的 roles/globals 私有导出；角色口令等敏感内容不会进入公开材料。
- 原轮与 retry-1 两个 workspace volume：根据实际 Docker Mountpoint 和标签单独冷归档。
- 冷归档整个原 C3 根目录，自然包括 retry-1、Ownerstore、Production Environment Owner、Native executor/workspaces、managed Git、Gitea 配置和 SQLite 数据、source archives/build inputs、私有 env 与全部历史证据。仅排除原根自身 `private/checkpoints`，避免自我递归。
- 所有实际持久 bind mounts 必须位于本 C3 根目录并由根目录归档覆盖。Docker socket 仅记录配置，绝不归档。未声明 volume、外部可写 bind 或不能覆盖的文件系统边界保持 BLOCKED。
- `docker image save` 保存原 `54355780…` image、实际最终 retry image、PG/Gitea 依赖和关联已退出 C3/Native 控制容器使用的确切 image IDs；不保存整个 Docker 镜像库。
- 全部 C3 容器、网络、volume、image 的原始 inspect 仅私有保存，包含必要恢复配置。对外部服务只保存安全 ID/state 对照，不导出其配置或 env。

历史已退出 C3 开发/测试容器可能只读引用 C2 code。这些引用仅留在私有容器 metadata；不复制、修改或归档 C2 数据。临时测试容器的可写层不作为可恢复生产数据，公开收据明确该限制。Native 必须使用只读根文件系统，持久资料全部位于已批准 mounts。

## 一致性、停止与失败边界

1. 先核对实际角色身份、所有相关 containers/mounts/volumes、镜像和磁盘空间。发现活跃 Native 或未知 C3 写入者时返回 BLOCKED；不停止它们。
2. 仅停止八个明确 C3 应用角色。停机前后复核相关容器集合，避免并发产生新的 Native 副作用。
3. 导出前要求独立资格库没有其他活跃 client backend。每个数据库分别在 `REPEATABLE READ READ ONLY` 事务中取得 `pg_export_snapshot`，`pg_dump --snapshot` 使用该实际快照。记录导出开始/结束和快照观察时间。
4. 各数据库不是一个跨库、Git、文件系统原子快照。应用已 quiesce、各库导出一致、之后依赖冷停止的边界分别报告。
5. 导出结束后仅停止已确认的本 C3 共用 PG/Gitea 和 retry 独立夹具 PG，各只处理一次。再进行根目录和 volume 冷归档。
6. 验证 PG custom dump magic 与 `pg_restore --list`、tar 目录可读、归档整体 SHA256、image save manifest；不执行恢复演练，不宣称通过恢复资格或已经异地备份。
7. 不足磁盘、导出/归档失败、身份漂移会保留私有部分结果和命令 ordinal/原始 stderr。公开仅安全错误类别/固定错误码。不自动清理或重启。

`/data/watt/runtime/source` 是外部合法工作区。检查点在开始/结束只读记录实际 HEAD、branch、dirty 布尔及单独的 `refs/heads/main`。不要求当前 HEAD 等于历史 canonical main，不切换/重置/fetch，不写入该工作区。若外部状态变化，标记 `UNKNOWN` 的外部变化来源，不能冒称本轮改动或擅自恢复它。旧19服务、C2、production 和外部 main 均不在停止范围。

## 后续恢复（人工审查后，当前不执行）

1. 保留原私有 checkpoint 原样；验证公开与私有收据的全部整体 SHA256，先在受限目录检查 tar 路径和链接。数据包含 credentials，不得复制到公开证据或普通共享目录。
2. 使用新的空隔离 root、网络、DB、volume 和端口。禁止覆盖原 C3、retry-1、旧 Work、production 或任何现有环境。查看私有实际 inspect 后确认必要 UID/GID、bind destinations、Ownerstore 路径与 image IDs。
3. 加载确切 image archive 到获授权的隔离 Docker 环境；验证 exact IDs。将冷 root/volume 数据恢复到新私有位置，保持 numeric owners 与权限。
4. PostgreSQL 可以择一使用已冷停止的数据目录与相同 PG image，或在新的空独立服务器中恢复 roles 和各 custom dumps。不得同时将两套方式混合恢复到同一数据目录/DB；角色口令只在私有操作中使用。
5. Gitea 用原 rootless image、实际配置与冷数据复制重建到新隔离路径，避免指向旧主机资源。重建前审查原配置中的地址/密钥，不在报告输出。
6. 根据实际持久 Owner 记录复核 Work/PWU/Attempt/Candidate/Verification/Guardian/Source identity 与授权状态。应用重新启动和 Work 恢复另行获得明确执行授权；本 checkpoint 不授予 Integration、Acceptance、Delivery 或重复执行副作用的权限。

这是本地持久恢复准备。真正跨电脑恢复还需要管理员将整个私有 checkpoint 和公开 identity receipt 经批准的私有传输迁移到受控位置；本轮不宣称该复制已经发生。
