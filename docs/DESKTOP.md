# WISEYE 桌面窗口运行说明

当前窗口连接本机 UE，显示仿真状态并控制暂停/继续、复位、自动/手动模式、云台跟踪、旋翼、可见光/红外、白热/黑热与 FOV。点击获取图像显示当前模式原生 PNG 快照。状态每 500 ms 更新；图像目前按需获取，尚无实时视频流。

## 这台电脑每天运行

1. 保存并关闭 UE 后，在仓库执行 `git pull --ff-only`，同步另一台电脑的成果。
2. 双击仓库根目录 `Start-WISEYE.cmd`。等待 C++ 编译和关卡加载，点击 UE 绿色“播放”。
3. 双击 `Start-Desktop.cmd`。点击“连接 UE”，默认地址 `127.0.0.1:50051`。
4. 连接成功后操作右侧按钮，点击获取图像。键盘飞行需在 UE 中选手动模式、点击游戏画面获取焦点，再使用 WASD、↑↓、Q/E；左 Shift 加速。
5. 结束时先断开/关闭窗口，停止 UE 播放，在 UE 保存全部资源。

本机位于 `E:\Projects\WISEYE-Studio`，UE 位于 `E:\Programs\UE_5.8`，桌面 `.venv` 已配置，不需要重复安装。

## 新电脑首次配置

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
- 首次 UE 构建失败：检查 VS 的 C++ 工作负载和 SDK；关闭已保存的旧 UE 编辑器再构建。不要只复制另一台电脑的 Binaries。
- 引擎找不到：修正 `scripts/engine-root.local.txt` 为包含 Engine 子目录的安装根目录。
- 获取图像后未随运动更新：这是快照，需要再次获取；保存位置为 `ue5/WISEYE/Saved/WISEYE/`。
- 桌面报错：在仓库运行 `.\.venv\Scripts\python.exe -m apps.desktop_app.main` 查看终端输出，日志在 `logs/desktop_app.log`。

当前桥仅监听回环地址；另一台电脑需自行运行 UE 和桌面窗口。跨电脑同步的是 Git 工程，当前不是两台电脑远程连接仿真。
