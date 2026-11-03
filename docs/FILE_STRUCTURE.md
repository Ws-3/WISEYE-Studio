# WISEYE Studio 文件结构

2026-10-28：本机日常统一双击根目录 **`Start-WISEYE-Studio.vbs`**，一次启动当前城市预览、飞控和桌面。下方保留的分步 PowerShell 命令面向开发；在仓库 PowerShell 执行，遇执行策略限制加 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File`。已启动UE时仅重开桌面用 `scripts/Start-Desktop.ps1 -Connect`。详见[当前使用指南](USER_GUIDE.md)。

## 需要提交并在其他电脑复用

| 路径 | 内容 |
|---|---|
| `apps/desktop_app/` | PySide6 主界面、UE/AirSim 客户端和 RTSP 解码 |
| `core/` | 配置、协议、状态模型和场景注册表 |
| `configs/` | 桌面连接、通道和帧率默认值 |
| `integrations/ProjectAirSim/` | WISEYE 飞行 runner、AirSim 机器人和场景配置 |
| `integrations/rtsp/` | MediaMTX 配置与 UE 到 RTSP 网关 |
| `Models/` | Mavic 3、Avata、PTZ 原始 FBX 和纹理，供重导入使用 |
| `ue5/WISEYE/Config/` | UE 工程和 WISEYE 场景配置 |
| `ue5/WISEYE/Content/` | 地图、设备、材质、纹理和 World Partition 外部 Actor |
| `ue5/WISEYE/Source/test/` | 唯一 UE C++ 源码，保留模块名 `test` |
| `ue5/WISEYE/Plugins/*/*.uplugin` | 本地插件入口；具体第三方源码由安装脚本联接 |
| `ue5/scripts/` | UE 编辑器内的配置、导入、修复和验证脚本 |
| `scripts/` | 安装、构建、启动和联调脚本 |
| `tests/` | 协议、场景、AirSim 控制和真实窗口验收 |
| `third_party/patches/` | 对固定 Project AirSim 提交的可复现修改 |
| `docs/` | 安装、运行、协议、场景、设计、证据和 AI 交接 |

`ue5/WISEYE/Content/__ExternalActors__` 与 `__ExternalObjects__` 属于地图的一部分。保存 World Partition 地图后必须一起提交，否则另一台电脑会缺少场景对象。

## 每台电脑自行生成

以下内容已由 `.gitignore` 排除：

- `.venv/`：桌面 Python 环境。
- `third_party/mediamtx/`：由 `Setup-RTSP.ps1` 下载并校验。
- `ue5/WISEYE/Plugins/ProjectAirSim/{Source,SimLibs,Content,Resources}` 与 `Plugins/Drone/{Content,Resources}`：由 `Setup-ProjectAirSim.ps1` 创建目录联接。
- `Binaries/`、`Intermediate/`、`DerivedDataCache/`、`Saved/`：UE 编译、缓存和运行输出。
- `runtime/`、`logs/`、`data/`：本机验证结果、日志和实验数据。
- `scripts/engine-root.local.txt`：本机 UE 安装位置。

不要把账号令牌、`.env`、用户数据集、引擎安装目录或整个 Project AirSim 副本放入仓库。

## 主要入口

| 文件 | 用途 |
|---|---|
| `Start-WISEYE-Studio.vbs` | 本机唯一仿真快捷入口：当前城市预览、飞控与桌面 |
| `training_client/Start-Training.vbs` | 独立训练工作台 |
| `scripts/Start-ProjectAirSim.ps1` | 开发分步入口：常规源码工程、RTSP、UE Play、飞控 |
| `scripts/Start-Desktop.ps1` | 打开 WISEYE 桌面控制台 |
| `scripts/Start-WISEYE.ps1` | 基础 UE 编辑/回退演示入口 |
| `scripts/Setup-ProjectAirSim.ps1` | 获取、修补、构建并联接 Project AirSim |
| `scripts/Setup-RTSP.ps1` | 安装固定版本 MediaMTX |
| `docs/AI_HANDOFF.md` | 下一位 AI 应优先阅读的当前实现和验证状态 |
| `WISEYE_ProjectPlan.md` | 长期架构、里程碑和历史决策 |
