# WISEYE Studio（智瞳）

> 2026-10-27：当前源码包含V3多设备工作台、真实City Sample小城市、可编辑RTSP接口、增强红外试验、硬件性能栏和时间/雾/雨控制。此前已验证免装UE的独立内测包，本轮正在生成包含上述新功能的完整Shipping版本；交付状态以[发布说明](docs/RELEASE_BUILD.md)为准。日常操作见[使用指南](docs/USER_GUIDE.md)。

GitHub提供代码、配置、自有模型和项目文档，不包含UE编辑器、Python环境、完整城市资产或大型运行ZIP。源码开发需按[安装说明](docs/INSTALLATION.md)配置依赖，城市副本由[本地City Sample接入流程](docs/CITY_SAMPLE_SETUP.md)生成；普通用户使用完整独立包，无需安装开发环境。

无人机光电仿真与智能感知平台。目前已接入 Project AirSim Fast Physics/SimpleFlight 无人机动力学、两轴地面云台真值跟随、云台激光扫描、可见光/红外原尺寸低延迟预览和对外RTSP、起飞/悬停/降落控制与 Mavic 3/Avata 外观切换。完整产品流程见 [docs/SYSTEM_UX_DESIGN.md](docs/SYSTEM_UX_DESIGN.md)，视频通道见 [docs/RTSP.md](docs/RTSP.md)。

## 桌面系统入口

城市场景使用 `Start-CitySample.vbs`，等待UE播放与缓存完成，再运行 `Start-Desktop.cmd` 连接。已有UE运行时通过桌面场景编排切换，避免重复启动。

AirSim 模式先双击 `Start-ProjectAirSim.vbs`，脚本会打开 UE、自动播放后在地面待命；再双击 `Start-WISEYE-Studio.vbs`，连接后点击“起飞”。这两个入口隐藏后台命令行；原 `.cmd` 入口保留用于诊断。界面可选择画质优先、均衡或节能档位。

新电脑请先按 [完整安装说明](docs/INSTALLATION.md) 配置；日常操作与排查见 [桌面运行说明](docs/DESKTOP.md)，人工上传/下载见 [Git 操作说明](docs/GIT_WORKFLOW.md)。

AirSim 动力学演示先运行 `scripts/Setup-ProjectAirSim.ps1`，之后双击 `Start-ProjectAirSim.cmd`。配置、架构和验证结果见 [Project AirSim 接入说明](docs/PROJECTAIRSIM_INTEGRATION.md)。

已加入多地图功能：在桌面左侧选择“原始沙漠场景”或“通用测试场”，点击“切换到所选场景”。“地图管理 / 导入”支持标准场景包和通过 UE 接入社区地图，详见 [场景管理说明](docs/SCENES.md)。新场景复用标准设备装配；云台和无人机按整体选择和移动，保留内部转轴关系。

## 在另一台电脑运行

推荐用 `git clone`，这样以后可以直接更新。安装 UE 5.8（当前验证5.8.4）、VS 2022 C++ 游戏开发组件、Python 和 FFmpeg 后，在仓库根目录依次完成：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Set-Content .\scripts\engine-root.local.txt 'C:\Program Files\Epic Games\UE_5.8'
.\scripts\Setup-RTSP.ps1
# 当前工程启用了城市兼容模块，先从已获取的同版CitySample安装本地源码。
.\scripts\Setup-CitySample.ps1 -SourceProject "E:\Projects\Scene\CitySample\CitySample.uproject" -EngineRoot "C:\Program Files\Epic Games\UE_5.8" -Stage Dependencies -SkipBuild
.\scripts\Setup-ProjectAirSim.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.8'
```

完成后双击 `Start-ProjectAirSim.cmd` 启动 UE、实时视频和空气动力学，再双击 `Start-Desktop.cmd`。首次配置的准确参数、ZIP 下载方式、VS 组件和故障排查见 [安装说明](docs/INSTALLATION.md)。模型、纹理、地图和 WISEYE 源码随仓库提供；Project AirSim 与 MediaMTX 由安装脚本按固定版本获取。

独立 UE 模式可双击 `Start-WISEYE.cmd`，进入编辑器后点击绿色“播放”。

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

- 默认由 Project AirSim Fast Physics 和 SimpleFlight 驱动无人机；旧运动学航线保留为 C++ 回退后端。云台使用 UE 中 AirSim 机体的实际位置进行指向。
- bottom 固定；bottom2 只水平转；camera 和 ptz 同时水平、俯仰转。
- 独立旋转轴、转速限制、俯仰限位、实时相机画面、暂停/复位/变焦/截图。
- 设备尺寸：Mavic 3 展开机身（不含桨叶）34.75×28.3×10.77 cm，初代 Avata 含护圈 18×18×8 cm，云台总高 80 cm；四组独立旋翼轴心，自动与手动飞行、云台方向保持均可切换。
- 可见光 1920×1080（16:9）与模拟红外 640×512（5:4），共用光学位置和水平 FOV，垂直 FOV 不同，预览保持原比例。红外按模拟热强度渲染，包含机身/电机/旋翼差异、背景和噪声，可白热/黑热切换，并处理遮挡；不是可见光灰度转换，也不是物理辐射测温模型。
- 已恢复被删除的云台模型，资源隔离在 `/Game/WISEYE/PTZRecovered`；用户已确认恢复正常。
- 云台激光默认 48×12 射线、10 Hz、300 m，随俯仰轴转动，可导出局部坐标 PLY，并在桌面实时显示俯视点云。
- 无人机按 DJI 官方外形尺寸缩放，云台按用户要求设为 80 cm；未按厂商图纸计量标定；光心与旋翼轴心为几何近似。AirSim 飞控已接入，尚不是 YOLO 视觉闭环。

## 内容和接手

```text
apps/desktop_app/         PySide6 主窗口与 TCP 客户端
core/                     配置、协议和状态模型
configs/app.json          本机连接默认参数
integrations/             Project AirSim 飞控桥与 RTSP 网关
tests/                    协议与真实 UE 窗口验收
Models/                   原始 FBX 与附带纹理
ue5/WISEYE/               完整 UE 源工程（Config、Content、Source、test.uproject）
ue5/scripts/              编辑器维护/验证脚本
scripts/                  安装、构建、启动与验证入口
docs/AI_HANDOFF.md         下一位 AI 的工作与运行说明
docs/evidence/            历史验证和恢复记录
third_party/patches/      固定版本 Project AirSim 适配补丁
WISEYE_ProjectPlan.md      长期计划与历史记录
```

完整目录职责见 [文件结构说明](docs/FILE_STRUCTURE.md)。让下一位 AI 先读 [AGENTS.md](AGENTS.md)、[AI 交接](docs/AI_HANDOFF.md) 和 [项目计划](WISEYE_ProjectPlan.md)。具体 UE 参数见 [ue5/README.md](ue5/README.md)，迁移检查见 [PORTABILITY](docs/PORTABILITY.md)。

不包含 UE 引擎、VS、编译产物、缓存、自动保存、用户配置、日志和本机备份。第三方模型未附授权资料，本次同步不额外声明其许可证。
