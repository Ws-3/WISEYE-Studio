# WISEYE 桌面窗口运行说明

> 实时图像已接入：CH1 可见光、CH2 红外。首次使用先运行 `scripts/Setup-RTSP.ps1`，详见 [RTSP.md](RTSP.md)。`Start-ProjectAirSim.cmd` 会自动启动视频服务。

当前窗口同时连接本机 UE（50051）、AirSim 飞控（50052）和 RTSP（8554），支持起飞/悬停/降落、物理复位、自动/手动飞行、Mavic 3/Avata 外观切换、云台、旋翼、CH1/CH2 画面和激光点云。

## 这台电脑每天运行

1. 保存并关闭 UE 后，在仓库执行 `git pull --ff-only`，同步另一台电脑的成果。
2. 双击仓库根目录 `Start-ProjectAirSim.cmd`。等待 UE 自动播放和无人机起飞。
3. 双击 `Start-Desktop.cmd`。点击“连接 UE”；窗口会同时连接 50051 和 50052。
4. 选择“手动飞行”后按住九键控制区按钮飞行；切到“激光点云”查看实时扫描。复位会按物理航迹返回原点。
5. 结束时先断开/关闭窗口，停止 UE 播放，在 UE 保存全部资源。

本机位于 `E:\Projects\WISEYE-Studio`，UE 位于 `E:\Programs\UE_5.8`，桌面 `.venv` 已配置，不需要重复安装。

## 新电脑首次配置

### 从 GitHub ZIP 下载的情况

ZIP 不包含 `.venv`，所以首次点击 Start-Desktop 可能提示 `Desktop environment missing`。在解压后的项目根目录创建本机环境即可，不需要重新下载工程，也不需要激活 conda WISEYE：

```powershell
cd D:\Projects\WISEYE-Studio
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\Start-Desktop.cmd
```

上面的目录请按本机实际位置修改。当前启动脚本固定使用 `.venv\Scripts\pythonw.exe`；只在 conda 环境安装依赖不能满足该检查。更新 ZIP 时保留本机 `.venv`，如 requirements.txt 有变化，再运行安装命令。ZIP 没有 `.git`，不能直接在解压目录执行 git pull；需另行 git clone 才能使用 Git 同步。

以下 E 盘路径和“已配置”状态来自另一台电脑的历史记录，不代表刚解压的电脑已经安装依赖。

安装 Git、UE 5.8（验证 5.8.3）、Visual Studio 2022 C++ 游戏开发工作负载（MSVC v143、Windows SDK），以及 Python 3.12 或更新版本。当前本机实测 Python 3.14.6 / PySide6 6.11.0。

在 PowerShell 中执行（引擎路径按本机修改）：

```powershell
cd E:\Projects
git clone https://github.com/Ws-3/WISEYE-Studio.git
cd WISEYE-Studio
Set-Content -Path scripts\engine-root.local.txt -Value 'E:\Programs\UE_5.8'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\Start-WISEYE.cmd
```

UE 加载后点击播放，再运行：

```powershell
.\Start-Desktop.cmd
```

不需激活虚拟环境；启动脚本固定使用本仓库 `.venv`。不要复用或升级已有训练环境。模型、材质、关卡都在 Git 中，无需重新导入。每台电脑的引擎路径与虚拟环境不上传。

## 排查

- 连接失败：确认 UE 已点击播放；仅打开编辑器不会启动 TCP 服务。地址使用 127.0.0.1、端口 50051，并检查 UE HUD 的 Bridge 状态。
- 提示缺少桌面环境：按上面创建 `.venv` 并安装 requirements。
- 使用 Anaconda 创建 venv 时出现 QtCore/QtWidgets `DLL load failed`：2026-10-15 的桌面入口已处理系统 ICU 与 conda 同名 DLL 的冲突；用 Start-Desktop 或 `python -m apps.desktop_app.main` 启动，不要删除 conda 的 DLL。
- 首次 UE 构建失败：检查 VS 的 C++ 工作负载和 SDK；关闭已保存的旧 UE 编辑器再构建。不要只复制另一台电脑的 Binaries。
- 引擎找不到：修正 `scripts/engine-root.local.txt` 为包含 Engine 子目录的安装根目录。
- CH1/CH2 不更新：确认由 `Start-ProjectAirSim.cmd` 启动了 RTSP 服务，`ffmpeg -version` 可运行，并检查 `logs/rtsp-gateway-error.log`；“保存当前传感器”仍是单帧 PNG/PLY 导出。
- 桌面报错：在仓库运行 `.\.venv\Scripts\python.exe -m apps.desktop_app.main` 查看终端输出，日志在 `logs/desktop_app.log`。

当前桥仅监听回环地址；另一台电脑需自行运行 UE 和桌面窗口。跨电脑同步的是 Git 工程，当前不是两台电脑远程连接仿真。
