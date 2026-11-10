# 安装与首次运行 · v1.1.0

当前支持完整运行包、源码插件接入和完整源码开发三种入口。GitHub Source code ZIP 不是可执行软件包。

## 完整运行包

本地最新 `WISEYE-Full-20261110.zip` 约 27.3 GiB，内置大小城市。当前 v1.1.0 GitHub Release 只提供插件包；完整包尚无公开下载链接。

将整个运行包解压到可写目录，保留文件结构，运行 `WISEYE/WISEYE.exe`；训练端在 `WISEYE/Training/WISEYE-Training.exe`。桌面打开后不会自动启动 UE，选择场景并手动启动仿真。配置和输出保存在便携 UserData；关闭前先停止飞行。

普通用户不需要 UE 编辑器、VS、Git 或 Python；需要 Windows x64、支持 DX12/SM6 的显卡驱动和 VC++ x64 运行库。包内带运行库安装程序。压缩包和展开目录同时保留至少预留 60 GiB，缓存、采集和录像另计。首次加载可能编译缓存或流送大量城市资源，不要重复启动。

## 插件接入自己的地图

从 [v1.1.0 Release](https://github.com/Ws-3/WISEYE-Studio/releases/tag/v1.1.0) 下载 `WISEYE-Plugin-v1.1.0-UE5.8-Win64.zip` 与 SHA256，校验、解压后按[插件接入指南](PLUGIN_DISTRIBUTION.md)执行。需要 UE 5.8 C++ 宿主、VS 2022 C++ 工具链和支持安装器的 Python；不要求下载 City Sample。当前插件版本已验证 UE 5.8.4/Windows x64，其他平台未验收。

## 完整源码开发

基础软件：Git、UE 5.8（当前验证 5.8.4）、VS 2022“使用 C++ 的游戏开发”及 Windows SDK、CMake、Python 3.12 或更新版本、FFmpeg。包中已有编译原生依赖不代表可省略宿主 C++ 编译工具链。

```powershell
git clone https://github.com/Ws-3/WISEYE-Studio.git
cd WISEYE-Studio
Set-Content .\scripts\engine-root.local.txt 'C:\Program Files\Epic Games\UE_5.8'
```

默认 UE 工程启用了 City Sample 兼容模块。构建城市示例前先通过 Epic/Fab 合法取得同版 City Sample，再依次准备依赖；所有路径换为本机实际路径：

```powershell
.\scripts\Setup-CitySample.ps1 -SourceProject 'D:\Scenes\CitySample\CitySample.uproject' -EngineRoot 'C:\Program Files\Epic Games\UE_5.8' -Stage Dependencies -SkipBuild
.\scripts\Setup-ProjectAirSim.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.8'
.\scripts\Build-JSBSim.ps1
.\scripts\Setup-DeveloperEnvironment.ps1 -Python python
.\scripts\Setup-RTSP.ps1
```

Project AirSim 固定源码和补丁位于仓库 `builds/dependencies/ProjectAirSimSource`，不再默认创建外部 Evaluation 工程。开发 Python 环境为 `.venv`；脚本也支持已有 Tools/Python 或 builds/python-env。新环境助手已做语法检查，本机不是干净安装验收，不承诺全新电脑零配置。

然后按[城市接入指南](CITY_SAMPLE_SETUP.md)准备 Assets、Duplicate、Assemble；必须保留 World Partition 外部 Actor，不能只复制 umap。已有完整本地城市不重复装配。自己的地图走插件路线，不需要先构建城市示例。

## 日常启动与更新

双击根目录 `Start-WISEYE-Studio.vbs` 或执行 `scripts/Start-Desktop.ps1`，再从界面启动仿真。已有实例可显式连接；打开界面本身不启动 UE。自定义宿主使用 `scripts/Start-CustomEnvironment.ps1 -ProjectPath 'D:\MyScene\MyScene.uproject' -Scene custom`。

```powershell
# 若 PowerShell 执行策略拦截，仅本次进程绕过
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Desktop.ps1
```

源码更新前保存并关闭 UE、提交或保存本地改动，再 `git pull --ff-only`；原生/资源变化需重建相应模块，依赖变化按发行说明处理。插件安装器当前拒绝覆盖不同内容的已有文件，升级请先备份宿主并使用清洁副本重新接入，不能假定支持原地自动升级。完整包手动解压到新目录并保留用户数据，尚无在线更新器。

详[用户指南](USER_GUIDE.md)、[插件指南](PLUGIN_DISTRIBUTION.md)、[打包指南](RELEASE_BUILD.md)及[目录依赖](PROJECT_DEPENDENCIES.md)。
