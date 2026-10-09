# C3 持久恢复位置

实际检查点：CAPTURED_PRIVATE；开始2026-10-09T13:40:34.625071Z；完成2026-10-09T13:45:27.559991Z。

私有目录：/data/watt/c3-semantic-convergence-20261009/private/checkpoints/20261009T134034Z-2d204f9031494a77b922f76c95b7569a。目录0700、文件0600；包含 credentials/env/raw inspect，禁止发布到 Git。
公共身份收据：[private-checkpoint-20261009T134034Z-2d204f9031494a77b922f76c95b7569a.json](private-checkpoint-20261009T134034Z-2d204f9031494a77b922f76c95b7569a.json)。

## 实际覆盖

- 仅停本 C3 原轮与 retry-1 八个应用角色，以及 C3 主 PostgreSQL/Gitea/独立夹具 PostgreSQL，默认保持停止。未删除、清理、重启或恢复任何资源，未创建/推进 Work或Human决定。
- 原轮与 retry-1 失败 Work、事实、事件、managed Git、Ownerstore、Gitea、来源与build输入、private原始export由冷ROOT归档保存；两个workspace volume另保存。
- 六个实际数据库分别取得read-only exported snapshot并custom dump，roles/globals仅私有保存。这不是跨数据库/Git/文件系统的原子快照。
- 与本C3控制容器关联的确切image IDs保存，包括原54355780、retry6f8d9b3a、最终51c0b8be及依赖；不是整个镜像库。
- private/checkpoints自身从ROOT tar排除防止递归；原首次失败检查点仍在ECS原目录，未覆盖，公开root-cause见checkpoint-attempt-1。
- 当前数据库迁移、container/source/image身份、archive全体SHA256、PG restore-list与tar/image manifest目录可读均记录。没有执行恢复演练，也没有完成异地复制。

## 冷归档

| 归档 | Bytes | SHA256 |
| --- | ---: | --- |
| images | 1576141824 | 95df7bfe5ea42b39a485f807d6b8d99f2db6b0d7ef07cfa5b37486f102a72722 |
| root | 559790080 | ed42e5db7258176dceaed0db6bc6f89ced673327ba8b4af1a96726c6b2515971 |
| watt-c3-retry1-workspaces-20261009 | 61440 | 3ada0ffe6af8640b2dbce8043b5517c377a4814511446da3e1b162f5c0459f65 |
| watt-c3-workspaces-20261009 | 10240 | ab4e3c91c1a55fc5a4971dc5c782f7ad631612c023fecbcfec0df3af338e003c |

## 数据库

| 实际数据库 | PostgreSQL Owner | 实际迁移头 | Dump状态 |
| --- | --- | --- | --- |
| spg_c3_qualification_20261009 | C3 主 PG | ["20261007_72"] | CONSISTENT_DUMP_CAPTURED |
| c3_contract_regression | C3 主 PG | [] | CONSISTENT_DUMP_CAPTURED |
| spg_c3_retry1_qualification_20261009 | C3 主 PG | ["20261007_72"] | CONSISTENT_DUMP_CAPTURED |
| c1_contract_continuity | C3 主 PG | ["20261007_72"] | CONSISTENT_DUMP_CAPTURED |
| c3_independent_holdout_20261009 | C3 主 PG | ["20261007_72"] | CONSISTENT_DUMP_CAPTURED |
| c1_contract_continuity | retry-1 独立 fixture PG | ["20261007_72"] | CONSISTENT_DUMP_CAPTURED |

C3 主 PG 容器 ID：8b84f8448e7415e2d9d583c79731f7ebd7da3ea756d8e8e34f3a470a5fb84a8e。
retry-1 独立 fixture PG 容器 ID：62edd2892aa09223700d21c561e8be73ef428507e60bf57c580bb5ef8c6e14cc。
两个同名 c1_contract_continuity 属于不同 PostgreSQL Owner，恢复时必须按公开 receipt 的 container_id 和 dump path 区分。

## 外部保护

外部checkout HEAD/branch/dirty及单独main ref开始/结束相同；main ref保留ee5bd86a53891f9391785c91d0ccef81ad2d56c3；实际checkout另在合法Admin诊断任务分支。外部container state对照一致。该观察只覆盖检查点时间窗口，不追认此前外部变化的来源。
outside_container_states_unchanged=True；work_created_resumed_or_modified=False；production_or_external_checkout_written=False。

## 换电脑读取与恢复边界

1. 从Watt和Guardian远端codex/c3-open-semantic-obligation-convergence分支取得公共代码/报告与exact IDs；公共新资料也复制到ECS本C3公共delivery目录。
2. 使用获授权SSH连接watt-ecs进入同一ECS，读取公开receipt并核对上述private目录、archive和dump SHA256。新电脑只需要合法SSH访问，不依赖旧电脑未跟踪qualification文件。
3. 需要离线/异地迁移时，仅通过受控私有传输复制整个private checkpoint，不输出key/env，不将其放入Git或普通共享目录。本次没有声称已经发生复制。
4. 要恢复运行，先审阅actual inspect，在新的空隔离root/网络/DB/volume中恢复；不覆盖旧失败Work或生产。加载exact image后核对ID，PG冷目录与logical dump恢复方式择一，不混用。原始检查点保持只读。
5. 本次检查点不授予Work恢复、Integration、Acceptance或Delivery权限；历史失败不得因恢复可读而改判PASS。

当前C3保持PARTIAL。独立Holdout未读取/执行，等待明确解封授权；已停止环境的后续资格启动必须继续满足冻结identity和历史保护。

独立 Holdout sealed specification 尚未获准解封，也未上传 ECS，仍保留于当前公司电脑 D:/hy/software-production-platform/.c3-holdout-reviewer/。这是未执行验收的输入，不计为已完成 qualification evidence。获授权后须独立核验 seal 并私有持久化；当前 ECS 检查点不包含该 spec。
