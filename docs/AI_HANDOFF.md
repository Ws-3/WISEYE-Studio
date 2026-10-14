# AI 交接（2026-10-14）

## 当前工作

用户已确认修复后的云台正常，要求直接同步可迁移 UE 工程、模型和代码，并让另一台电脑的 AI 继续工作。不要再次重新导入或覆盖已确认的场景。

先读根 README、AGENTS、长期计划并检查 git status。确认 UE 路径、版本和 VS C++ 工具链。原机验证 UE 5.8.3、MSVC 14.44.35229、SDK 10.0.26100.0；其他版本未验证。

## 启动、编辑、验证

在仓库根运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-WISEYE.ps1 -EngineRoot "实际UE目录"
```

仅构建用 `-BuildOnly`；已有匹配产物可 `-SkipBuild`。工程 `ue5/WISEYE/test.uproject`，关卡 `/Game/WISEYE-test`，点击播放。
必须在 UE 内执行 `py "实际仓库路径/ue5/scripts/verify_demo.py"`，不能用普通 Python 运行。报告输出到工程 Saved/WISEYE，持续40秒。
正常演示不依赖 conda。原机 WISEYE 环境为 Python 3.11.17，本次未升级或安装其依赖。

代码入口：`ue5/WISEYE/Source/test/WiseEyeDemo.h/.cpp`。AWiseEyeDemo 管运动、云台与相机；AWiseEyeHUD 管显示；AWiseEyeGameMode 管游戏模式。修改后重新构建，不要编辑已经退出使用的旧电脑 `D:/Projects/Scene/test/test`。
Content 包含地图、World Partition 外部 Actor、所有网格和材质；Config/WISEYE/calibration.json 保存布局。Models 是原始 FBX/.fbm，运行使用已导入资源，不必再次导入。

## 云台约定与已处理问题

bottom 固定，bottom2 挂 YawPivot 只水平转；camera 与 ptz 挂 PitchPivot 同时水平/俯仰；EO_Camera/EO_Capture 跟随镜头。
网格 +Y 朝前、控制光轴 +X，通过安装变换对齐。Actor 原点不一定是机械轴，要用独立 pivot。
历史问题：通用 Mesh 命名发生导入冲突；云台组件被删除；World Partition 属性修改不标脏导致运行时读到旧数据。已恢复网格、独立隔离资源并保存。不要覆盖 `/Game/Mesh*`。
恢复资源位于 `/Game/WISEYE/PTZRecovered`，`restore_ptz.py` 不再依赖本机 Backup-Content。仅损坏时运行，会恢复保存的布局坐标。

## 证据与边界

- 原机 C++ 编译、40秒 PIE 验证通过（77 个采样）；有两张不同时间 PNG 和目视检查。
- docs/evidence/verification.json 是恢复前的测试，不代表恢复后重新跑过同一测试。
- docs/evidence/ptz_recovery.json 是恢复后的部件/资源/轴向记录；恢复后用户确认正常，按用户要求没有重复完整运动测试。
- 本次迁移验证另见 docs/PORTABILITY.md。
- 尚未接 YOLO、TCP 图像流、PySide6 UI、动力学或打包成品。跟踪读取 UE 真值。
- 真实比例未校准（历史无人机宽约45米）、光心近似、少量零件分离，不宜用于定量设备性能结论。
- PNG 为最后完成渲染帧，元数据时间为请求时刻，尚需传感器时间同步。

建议下一步先标定模型尺寸/相机安装，再做最小跨进程图像通道，随后接视觉算法；以用户需求为准，不要按旧计划顺序推翻当前演示。
