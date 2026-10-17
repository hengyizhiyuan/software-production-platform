# 当前资格与部署记录

中文请求现在在 WIC 语义解释、对话表达、Steering 语义步骤、生产计划及 Native
执行指令中使用中文；新 PWU 目标包装和首次计划也跟随目标语言。机器字段、
确切引文和已有历史不改写。系统无须先将用户问题翻译为英文；原默认英文模板
及新生成的英文描述造成了此前的语言漂移。

本次真实失败跨了三处现有 Owner：当前 Owner 引用在 WIC 最终准入时被错误
缩减为 Human 附件；追加修改中的既有约束被要求在当前 delta IR 重新证明；
Native 将只读目录检查失败误当成需要新验收 oracle 的边界。各处修复均保留
确切来源与身份、完整当前需求、既有权限与预算、失败历史及独立最终验证。
已部署源码与镜像见 deployment-qualified.json，较早的两次发布保留在独立
receipt。后续证据提交不改变冻结的运行源码。

原 Human Turn 已完成，不需要重发修改意见。原 Work 已形成 revision 2、32项
完整绑定并进入实际执行。首次实际执行写入文件后遇到目录检查错误并真实
终止；修复部署后，既有 attention/retry Owner 已开启后继 Attempt，保留原
执行序列和失败历史。后继工作区从原始准入基线创建，完整成果需重新生成；
原失败尝试的文件未带入新工作区。一次 Provider 不完整响应已保留，后续自动
恢复成功返回并写入衣橱数据；其余文件与实际内容仍待完成。精确身份与当前
阶段见 runtime-recovery.json。

此 checkpoint 资格为“修改接续及实际执行恢复”，新版游戏 Candidate、内容
Verification、served Preview 和本轮 Guardian 仍待实际产出。旧 Candidate 的
PASS 不用于证明新版完成。Human 接受、整合、游戏交付均未代行。CUA 浏览器
动作/截图桥在本会话超时，未声称实际浏览器交互或美术效果已通过人工检查。

回归范围见 qualification.md：相关局部检查和部署 release gate 通过；真实
PostgreSQL 选择中一个未改基线即可复现的失败仍如实记录，不声明全套 PASS。
