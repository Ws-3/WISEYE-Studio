# WISEYE Studio 安装说明

本文用于在一台新的 Windows 电脑上复现当前完整功能：UE 场景、Project AirSim 无人机动力学、CH1/CH2 实时视频、LIDAR 点云和桌面控制台。日常操作见 [DESKTOP.md](DESKTOP.md)，视频链路细节见 [RTSP.md](RTSP.md)。

## 1. 安装基础软件

- Unreal Engine 5.8；当前实测版本为 5.8.3。
- Visual Studio 2022，勾选“使用 C++ 的游戏开发”，并安装 MSVC v143、Windows 10/11 SDK 和 UE 工具。
- Git、Python 3.12 或更新版本。
- FFmpeg，并确保 PowerShell 执行 `ffmpeg -version` 成功。

其他 UE 大版本没有经过验证。工程包含 C++ 模块，首次运行必须具备 VS 编译工具链。

## 2. 获取工程

推荐克隆仓库：

```powershell
cd D:\Projects
git clone https://github.com/Ws-3/WISEYE-Studio.git
cd WISEYE-Studio
```

GitHub 的 Download ZIP 也能运行，但 ZIP 没有 Git 历史，之后不能直接 `git pull`。模型、纹理、地图和 WISEYE 源码都在仓库内，不使用 Git LFS。

## 3. 配置桌面环境与 UE 路径

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Set-Content -Path .\scripts\engine-root.local.txt -Value 'C:\Program Files\Epic Games\UE_5.8'
```

把最后一行替换为本机真实的 UE 安装目录。`.venv` 和 `engine-root.local.txt` 只属于本机，不会上传。当前桌面入口固定使用仓库内 `.venv`，只在 conda 的 WISEYE 环境安装 PySide6 并不能替代这一步。

## 4. 安装实时视频和 Project AirSim

先安装 MediaMTX：

```powershell
.\scripts\Setup-RTSP.ps1
```

再获取固定提交的 Project AirSim、应用仓库补丁并构建插件：

```powershell
.\scripts\Setup-ProjectAirSim.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.8'
```

脚本默认把 Project AirSim 放在 WISEYE 同级目录 `D:\Projects\ProjectAirSim-Evaluation`，并把所需插件目录联接到 UE 工程。若 VS 无法自动识别，可追加：

```powershell
.\scripts\Setup-ProjectAirSim.ps1 `
  -EngineRoot 'C:\Program Files\Epic Games\UE_5.8' `
  -VisualStudioRoot 'C:\Program Files\Microsoft Visual Studio\2022\Community'
```

Project AirSim 源码、构建产物和 MediaMTX 二进制可由脚本重建，因此不存入 WISEYE 仓库。适配补丁保存在 `third_party/patches/`。

## 5. 启动完整系统

1. 双击 `Start-ProjectAirSim.cmd`。它会启动 MediaMTX、编译并打开 UE、进入 Play，然后启动 AirSim 飞控服务。
2. 等待 UE 场景和无人机出现后，双击 `Start-Desktop.cmd`。
3. 在桌面窗口点击“连接 UE”。选择手动飞行后，可用界面按钮或 W/S、A/D、R/F、Q/E 控制无人机。
4. CH1 为可见光，目标输出 30 FPS；CH2 为红外，目标输出 25 FPS；LIDAR 页显示云台点云。

首次构建、着色器编译和纹理准备耗时较长。后续启动会复用本机生成的缓存。

## 6. 只运行基础 UE 演示

不使用 Project AirSim 时可双击 `Start-WISEYE.cmd`，然后在 UE 中点击绿色“播放”。该入口仍可用于场景编辑和运动学回退演示；完整动力学和桌面手动飞控请使用 `Start-ProjectAirSim.cmd`。

## 7. 更新与迁移

开始工作前先保存并关闭 UE，再执行：

```powershell
git pull --ff-only
```

更新源码后重新运行启动脚本，它会编译 UE 模块。若 `requirements.txt`、Project AirSim 固定提交或补丁发生变化，重新执行相应安装步骤。不要复制另一台电脑的 `.venv`、`Binaries`、`Intermediate` 或 UE 缓存。

当前完整限制：Mavic 3/Avata 切换只改变显示模型；红外为热强度近似；两路视频在当前完整场景约产生 20 FPS 的独立新渲染帧，RTSP 按 30/25 FPS 输出并重复最新帧。达到独立 1080p30 需要后续接入 GPU H.264 编码。

## 8. 常见问题

- `Desktop environment missing`：在仓库根目录重新执行第 3 节的 `.venv` 创建和依赖安装。
- 找不到 UE：修正 `scripts/engine-root.local.txt`，路径下必须存在 `Engine` 文件夹。
- 缺少 ProjectAirSim 插件或模块：先完成第 4 节，保存并关闭正在运行的 UE 后再构建。
- RTSP 无画面：确认 `ffmpeg -version` 可用，并重新运行 `Setup-RTSP.ps1`。
- 连接 50051 失败：确认 UE 已进入 Play；只打开编辑器不会启动 WISEYE 控制桥。
- 连接 50052 失败：从 `Start-ProjectAirSim.cmd` 启动，并等待 AirSim 场景初始化完成。
