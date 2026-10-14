# WISEYE 工作规则

先读 `docs/AI_HANDOFF.md` 和 `WISEYE_ProjectPlan.md`，检查 git status，按用户当前需求工作。

- 唯一 UE 源码在 `ue5/WISEYE/Source/`。不要编辑旧电脑外部 Scene 工程或创建重复源码副本。
- 使用 `scripts/Start-WISEYE.ps1 -EngineRoot <实际UE目录>`。UE 5.8.3 已验证，首次构建需要 VS 2022 C++ 工具链。历史 D 盘路径不是新电脑依赖。
- 保留模块 test、构建目标 testEditor 和 `/Script/test` 类路径，不擅自升级引擎。
- bottom 固定；bottom2 只水平转；camera 和 ptz 一起水平及俯仰转；光学组件跟随 PitchPivot。
- 导入模型使用独立目录，避免覆盖通用 Mesh 名称。恢复云台在 `/Game/WISEYE/PTZRecovered`。
- World Partition 的 Content/__ExternalActors__、__ExternalObjects__ 必须提交。编辑器修改对象要 modify 并保存，不能仅改内存。
- 不覆盖未提交变更、不删除用户模型/权重/实验数据；不上传凭据、Saved 日志或缓存。
- 操作 UE 前确认工程与关卡，不强制结束有未保存数据的编辑器。
- 只报告实际执行的验证，历史测试不代表新电脑测试通过；真值跟随不等于视觉闭环。
- 完成任务后更新交接与计划，记录修改、运行方式、验证、限制及下一步。

- 桌面源码在 apps/desktop_app 和 core；运行先读 docs/DESKTOP.md，控制协议见 docs/PROTOCOL.md。网络/GUI 应保持非阻塞，断连不能保留有效状态；当前图像为快照，不要宣称实时流。
