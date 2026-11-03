# 2026-10-29 启动状态、位置微调、可见光与持续采集

后续修正：本页下方放置按键/保存加载说明已由[LIVE_PLACEMENT.md](LIVE_PLACEMENT.md)替代。当前为WASD/QE/RF、确认或编辑坐标即应用，无需重载；原本待验收的按键交互已在后续实际UE测试通过。启动、可见光与保存目录说明保留。

根入口不变：Start-WISEYE-Studio.vbs 自动启动 UE、飞控和桌面。preview_session 为每次启动建立独立状态文件，通过环境传给当前桌面，界面显示“UE启动中 → 飞控初始化 → 自动连接”。只有当前场景和新 run_id 的飞控 ready 才自动连接，不会把旧飞控状态当就绪。启动失败/300秒超时会显示原因及日志提示，保留桌面供查看，退出时仍由原 Job 清理自有子进程。Qt不执行阻塞式启动查询；日志保留在preview-data/logs。

到UE预览放置时：鼠标选表面，空格锁定/解锁；方向键沿世界X/Y、PageUp/PageDown沿Z每次10cm，Shift为1cm。第一次微调自动锁定，Home清零偏移；左键或锁定后的Enter确认草稿，右键/Esc取消。超时延长120秒，微调会刷新超时；Z不允许低于已选表面的设备底部。仍需保存布置并加载场景才移动真实设备，确认后也可编辑编排页坐标；并非运行中搬动飞行器。preview状态增加nudge_supported/locked/nudge_cm。幽灵模型继续不进入VIS/IR和GT。

可见光在USceneCapture源头添加保守日间监控相机响应：饱和度0.88、对比0.96、Gamma1.03、Bloom0.08、暗角0.08、FilmGrain0.04。仅作用于可见光传感器；预览、JPEG保存和GT对应同一成像源。没有裁切/几何变换，雾、云、光照继续由环境控制，不把参考图的某一种天气固定覆盖到全部场景。参考照片为不同天气场景，当前参数只是基础外观近似，未做实机辐射/MTF标定，也未对新模块进行实际场景图像对比验收；用户已认可的红外外观不改。

保存根目录例如 C:/Users/Administrator/WISEYE-Training：

```text
WISEYE-Training/
  visible/
    images/       VIS_机型_天气_场景_设备_会话_组ID.jpg
    labels/       同名.txt
    annotations/  同名.json
  IR/
    images/       IR_机型_天气_场景_设备_会话_组ID.jpg
    labels/
    annotations/
```

已有目录直接追加，文件名保持原可读命名，双路共享后缀配对。无pairs，无逐组samples目录；历史数据不迁移/改名/删除。annotations保留采集环境、原始GT、时差与校验和；YOLO使用images/labels。普通写失败/发布失败回滚本次新增，不覆盖旧数据；两个模态目录无法整目录原子提交，强杀/断电的坏组会被训练读取检查拒绝。训练读取支持schema3固定目录、schema2组目录以及旧单路，--sensor继续选择模态。

验证：86核心、43相关Qt通过，含启动跨run等待/失败保留、界面状态及一次自动连接、连续追加/重复保存/策略跳过/负样本/写入发布失败回滚/旧目录读取。此前真实采集3组JPEG和GT重导出到新结构并通过读取/校验。Editor带后缀模块编译成功，F/E四个修改源码SHA一致；模块清单已指向UnrealEditor-test-1029.dll，下次新UE进程加载。证据 evidence/startup-placement-visible-storage-20261029/validation.json。

测试时发现用户常规UE PID1848仍在运行，未停止、切场景或改其环境。没有在用户会话上请求GT或注入按键；新UE键盘微调/可见光观感及完整根入口冷启动尚未做现场验收。当前运行实例仍加载旧模块，需要用户正常退出整套程序后从根入口重开。没有重新Cook、打包、提交或推送。
