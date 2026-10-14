# WISEYE Studio（智瞳）

无人机光电仿真与智能感知平台。目前已实现 UE 无人机运动、两轴地面云台真值跟随、镜头预览和 PNG 导出。视觉算法、跨进程图像流及独立桌面界面尚未接入。

## 在另一台电脑运行

1. 安装 Windows 版 **UE 5.8（验证版本 5.8.3）**、**Visual Studio 2022 的“使用 C++ 的游戏开发”工作负载、MSVC v143 和 Windows SDK**。这是 C++ 工程，只有 UE 不能首次构建。其他引擎版本尚未验证，旧版本不保证能读取资源。
2. 克隆仓库，或 Code → Download ZIP 后解压。模型、纹理、关卡均已包含；无需 Git LFS 或外部资源下载。
3. 在仓库目录执行，将引擎路径替换为新电脑实际路径：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-WISEYE.ps1 -EngineRoot "C:\Program Files\Epic Games\UE_5.8"
```

脚本编译 `testEditor`，打开 `ue5/WISEYE/test.uproject` 和 `WISEYE-test` 关卡。也可双击 `Start-WISEYE.cmd` 自动寻找 UE 5.8；找不到时用上面的命令指定路径。首次编译/着色器准备需要等待。

4. 点击 UE 绿色“播放”，点击游戏画面获取键盘焦点。

| 按键 | 功能 |
|---|---|
| Tab | 总览 / 云台相机视角 |
| 空格 | 暂停 / 继续 |
| R | 重置航线 |
| + / - | 放大 / 缩小 |
| P | 导出 1280×720 PNG 与相机参数 |
| Esc | 停止播放 |

输出在 `ue5/WISEYE/Saved/WISEYE/日期_时间/`。当前仿真无需 conda/Python 依赖；UE Python 只用于可选维护脚本。

## 当前状态

- 无人机沿“8”字航线运动，云台使用 UE 目标位置进行指向。
- bottom 固定；bottom2 只水平转；camera 和 ptz 同时水平、俯仰转。
- 独立旋转轴、转速限制、俯仰限位、实时相机画面、暂停/复位/变焦/截图。
- 已恢复被删除的云台模型，资源隔离在 `/Game/WISEYE/PTZRecovered`；用户已确认恢复正常。
- 模型真实尺寸与光心尚未标定，飞行是运动学演示，尚不是 YOLO 视觉闭环。

## 内容和接手

```text
Models/                   原始 FBX 与附带纹理
ue5/WISEYE/               完整 UE 源工程（Config、Content、Source、test.uproject）
ue5/scripts/              编辑器维护/验证脚本
scripts/Start-WISEYE.ps1  跨电脑构建启动入口
docs/AI_HANDOFF.md         下一位 AI 的工作与运行说明
docs/evidence/            历史验证和恢复记录
WISEYE_ProjectPlan.md      长期计划与历史记录
```

让下一位 AI 先读 [AGENTS.md](AGENTS.md)、[AI 交接](docs/AI_HANDOFF.md) 和 [项目计划](WISEYE_ProjectPlan.md)。具体 UE 参数见 [ue5/README.md](ue5/README.md)，迁移检查见 [PORTABILITY](docs/PORTABILITY.md)。

不包含 UE 引擎、VS、编译产物、缓存、自动保存、用户配置、日志和本机备份。第三方模型未附授权资料，本次同步不额外声明其许可证。
