# WISEYE Studio

**v1.0.0 · 2026-11-03 · 生日纪念版**

🎂 11 月 3 日是作者生日。今天发布首个功能较完整的阶段版本，纪念 WISEYE 从无人机与光电云台仿真走向独立桌面工作台和数据接口的这一阶段。

WISEYE 基于 Unreal Engine 与 Project AirSim，提供城市环境、无人机飞行控制、光电云台、多传感器预览和数据采集接口。完整功能、验证范围及限制见 [v1.0.0 发行说明](docs/releases/v1.0.0.md)。

感谢YZE、ZWT的大力支持！

## 当前功能

- 小城市与独立加载的大城市试验场景，设备管理、模型放置预览、航线和手动飞行、真实转速及起降。
- 云台角度、视场角、距离遥测，自定义仿真地理基准与坐标指向接口。
- 独立可见光 1920×1080 / 红外 640×512、激光点云、事件相机；各传感器独立启停。
- 可编辑 RTSP 接口、低延迟预览、双路图像与真值采集、训练/数据采集工作台、天气和夜间灯光。
- 仿真启动/关闭、连接/断开与退出保护；打开界面不默认启动 UE。

红外和事件传感器仍为近似模型，大城市仍为试验功能，尚未完成全城/长时/多机压力验收。

## 独立包直接运行

本机已生成 `WISEYE-20261102-Win64-Portable.zip`（约 23.68 GiB），完整解压后双击 `WISEYE/WISEYE.exe`，再点击“启动仿真”。不需要安装 UE 编辑器、VS 或 Python；仍需兼容 Windows、显卡驱动和系统运行库。便携包将配置、日志与输出写入旁边的 `UserData`，应放在可写目录。

**本次 GitHub 发行只提供源码与发行说明，不附大型运行包。** 自动生成的 Source code ZIP 不能代替独立软件包。校验和及打包验证见 [便携包说明](docs/PORTABLE_RELEASE_20261102.md)，尚无在线更新器。

## 源码开发入口

根目录 `Start-WISEYE-Studio.vbs` 只启动桌面，UE 由界面的“启动仿真”按钮启动；训练端可从工作台启动。新电脑先按 [安装说明](docs/INSTALLATION.md) 准备 UE 5.8（本轮验证 5.8.4）、C++ 工具链、Python、FFmpeg、Project AirSim 和合法获取的 City Sample。

仓库包含代码、配置、自有资源与文档；完整第三方城市、引擎、环境、用户数据和构建缓存不随 Git 同步。城市资源按 [接入流程](docs/CITY_SAMPLE_SETUP.md) 准备。

当前开发工作副本为 `E:\Projects\WISEYE-PortableBuild`，`E:\Projects\WISEYE-IR-Work` 用于 UE 构建；F 盘迁移因 USB 故障暂缓，不要同时在 F 修改形成分叉。详见 [交接文档](docs/AI_HANDOFF.md)。

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

上述配置用于常规源码工程；在 PowerShell 中运行 `scripts/Start-ProjectAirSim.ps1 -Scene city`，再运行 `scripts/Start-Desktop.ps1 -Connect`。本机 E 盘预览用上方唯一入口。首次配置的准确参数、ZIP 下载方式、VS 组件和故障排查见 [安装说明](docs/INSTALLATION.md)。模型、纹理、地图和 WISEYE 源码随仓库提供；Project AirSim 与 MediaMTX 由安装脚本按固定版本获取。

独立 UE 编辑模式可在 PowerShell 中运行 `scripts/Start-WISEYE.ps1`，进入编辑器后点击绿色“播放”。

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

新增无人机请按[模型接入规范与 AI 任务模板](docs/DRONE_MODEL_INTEGRATION.md)准备FBX、贴图、尺寸、朝向和旋翼轴心；目前为FBX静态网格导入。Mavic/Avata已加入[夜间自动红绿闪烁灯](docs/DRONE_NAVIGATION_LIGHTS.md)，在环境面板设夜间时间可查看。

不包含 UE 引擎、VS、编译产物、缓存、自动保存、用户配置、日志和本机备份。第三方模型未附授权资料，本次同步不额外声明其许可证。
