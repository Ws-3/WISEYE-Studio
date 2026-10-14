# WISEYE Studio（智瞳）

无人机光电仿真与智能感知平台。目前已实现 UE 无人机运动、两轴地面云台真值跟随、镜头预览和 PNG 导出。已接入 PySide6 桌面窗口与本机 TCP 控制桥，支持状态查询、功能控制和双模态快照；实时图像流与视觉算法待接入。

## 桌面系统入口

本机先双击 `Start-WISEYE.cmd`，等待加载并点击 UE 播放；再双击 `Start-Desktop.cmd`，连接 `127.0.0.1:50051`，获取图像并操作控制按钮。

完整首次配置与排查见 [桌面运行说明](docs/DESKTOP.md)，人工上传/下载见 [Git 操作说明](docs/GIT_WORKFLOW.md)，今日成果见 [工作记录](docs/WORKLOG_2026-10-14.md)。

## 在另一台电脑运行

1. 安装 Windows 版 **UE 5.8（验证版本 5.8.3）**、**Visual Studio 2022 的“使用 C++ 的游戏开发”工作负载、MSVC v143 和 Windows SDK**。这是 C++ 工程，只有 UE 不能首次构建。其他引擎版本尚未验证，旧版本不保证能读取资源。
2. 克隆仓库，或 Code → Download ZIP 后解压。模型、纹理、关卡均已包含；无需 Git LFS 或外部资源下载。
3. 在仓库目录执行，将引擎路径替换为新电脑实际路径：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-WISEYE.ps1 -EngineRoot "C:\Program Files\Epic Games\UE_5.8"
```

脚本编译 `testEditor`，打开 `ue5/WISEYE/test.uproject` 和 `WISEYE-test` 关卡。也可双击 `Start-WISEYE.cmd` 自动寻找 UE 5.8；找不到时用上面的命令指定路径。首次编译/着色器准备需要等待。

每台电脑也可把实际引擎目录写入 `scripts/engine-root.local.txt`（一行路径），之后直接双击启动。该文件不提交；显式 `-EngineRoot` 或 `UE_ROOT` 优先。启动入口会启用 UE Python 编辑器插件，供维护和验证脚本使用。

两台电脑的同步步骤见 [Git 协作说明](docs/GIT_WORKFLOW.md)。

4. 点击 UE 绿色“播放”，点击游戏画面获取键盘焦点。

| 按键 | 功能 |
|---|---|
| Tab | 总览 / 云台相机 / 无人机近景，循环切换 |
| M | 自动航线 / 手动飞行；切换保持当前位置 |
| W / S、A / D | 手动模式前后、左右移动 |
| ↑ / ↓ | 手动模式上升 / 下降 |
| Q / E | 手动模式左转 / 右转 |
| 左 Shift | 手动移动速度加倍 |
| T | 云台跟踪 / 保持当前方向；无人机继续运动 |
| F | 旋翼动画开启 / 停止 |
| I | 可见光 1920×1080 / 红外 640×512 |
| B | 红外白热 / 黑热 |
| 空格 | 暂停 / 继续 |
| R | 重置航线 |
| + / - | 放大 / 缩小 |
| P | 导出当前模式原生 PNG 与相机参数 |
| Esc | 停止播放 |

输出在 `ue5/WISEYE/Saved/WISEYE/日期_时间/`。P 导出当前模式的原生分辨率 PNG，文件名前缀为 VIS、IR_WH 或 IR_BH；JSON 包含模态、调色板、分辨率和相机姿态。独立 UE 仿真不依赖 conda；桌面窗口使用 .venv 中的 PySide6。UE Python 用于可选维护脚本。

## 当前状态

- 无人机沿“8”字航线运动，云台使用 UE 目标位置进行指向。
- bottom 固定；bottom2 只水平转；camera 和 ptz 同时水平、俯仰转。
- 独立旋转轴、转速限制、俯仰限位、实时相机画面、暂停/复位/变焦/截图。
- 演示尺寸：无人机最大水平跨度约 60 cm，云台总高约 40 cm；四组独立旋翼轴心，自动与手动飞行、云台方向保持均可切换。
- 可见光 1920×1080（16:9）与模拟红外 640×512（5:4），共用光学位置和水平 FOV，垂直 FOV 不同，预览保持原比例。红外按模拟热强度渲染，包含机身/电机/旋翼差异、背景和噪声，可白热/黑热切换，并处理遮挡；不是可见光灰度转换，也不是物理辐射测温模型。
- 已恢复被删除的云台模型，资源隔离在 `/Game/WISEYE/PTZRecovered`；用户已确认恢复正常。
- 尺寸为可调整的演示比例，未按厂商图纸计量标定；光心与旋翼轴心为几何近似。飞行是运动学演示，尚不是 YOLO 视觉闭环。

## 内容和接手

```text
apps/desktop_app/         PySide6 主窗口与 TCP 客户端
core/                     配置、协议和状态模型
configs/app.json          本机连接默认参数
tests/                    协议与真实 UE 窗口验收
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
