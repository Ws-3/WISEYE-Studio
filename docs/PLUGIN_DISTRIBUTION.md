# WISEYE 源码插件包与完整运行包 · v1.1.0

发布入口：[v1.1.0](https://github.com/Ws-3/WISEYE-Studio/releases/tag/v1.1.0)。下载 `WISEYE-Plugin-v1.1.0-UE5.8-Win64.zip` 和同名 SHA256 文件，使用 `Get-FileHash <ZIP路径> -Algorithm SHA256` 比较后解压。源码插件/清单版本均为 1.1.0；完整运行包本轮只在本地生成，未附到 GitHub Release。

## 两种交付

- 源码插件接入包：UE 5.8 / Windows x64 开发者使用，需要 UE、VS C++ 工具链和 Python。安装到自己的 UE 工程，编译后连接 WISEYE 桌面端。
- 完整运行包：普通用户使用，保留桌面端、UE cooked 运行时、场景与依赖目录，运行不要求安装完整 UE 编辑器或 VS。构建仍走 scripts/Build-Release.ps1，旧运行包不自动更新。

源码插件包不包含 City Sample 地图、MassTraffic 城市资源或用户场景。当前兼容层保留 `/Script/test` 与 `/Game/WISEYE` 及历史根设备资产路径，因此它是“Plugins + 宿主资源安装器”的完整接入包，不是只拷一个裸插件文件夹。宿主项目自身若有名为 test 的模块会拒绝安装；不能直接改模块名，否则已有资产类路径会失效。

## 导出

在完整源码仓库中运行 `scripts/Export-WISEYEPlugin.ps1`。默认输出至 builds/distributions 的新目录，拒绝覆盖既有输出。包中包含 WISEYE 模块源码、ProjectAirSim/Drone 依赖、SimLibs、设备/传感器资源、JSBSim 和许可证资料，不包含编译缓存或城市地图。生成的插件源码不是新的开发工作副本，修复应回到 ue5/WISEYE/Source/test。

本机依赖已准备好。新克隆开发者需先用 Setup-ProjectAirSim.ps1 获取固定版本并构建 SimLibs，使用 Build-JSBSim.ps1 准备适配库，再导出；这些依赖构建步骤需要 VS 和 UE 路径，不等于直接编译启用了城市的示例工程。导出脚本优先使用仓库 Python，其次系统 Python，也可传 `-Python`。接入已经导出的 ZIP 时不需要重新构建这些 SimLibs，但仍需用匹配 UE/MSVC 工具链编译宿主与插件。

源码桌面与构建 Python 环境可在原生依赖准备后运行 `scripts/Setup-DeveloperEnvironment.ps1` 创建于仓库 .venv；使用 Python 3.12 或更新版本。Build-Distribution/Build-Release 支持 `-Python`，不要求其他电脑具有本机 Tools/Python 副本。该环境安装助手已做语法检查，尚未在干净电脑完成整套联网安装验收。

## 安装到自己的项目

先关闭该 UE 工程，保存已有工作。示例：

```powershell
python .\install.py --project 'D:\MyScene\MyScene.uproject' --map /Game/Maps/MyMap
python .\install.py --project 'D:\MyScene\MyScene.uproject' --map /Game/Maps/MyMap --apply
```

第一条只检查。第二条写入通过哈希校验的资源、启用插件，并保留原有 .uproject 备份。存在不同内容的同名文件会在写入前拒绝，不能覆盖宿主资产。Config/WISEYE/Scenes/custom.json 提供默认设备位置，先按地图地面/楼顶高度修改它。该默认位置不是对宿主地图的自动地形判断。

宿主应为 C++ UE 工程（纯蓝图工程请先新增一个 C++ 类并生成项目文件），编译 Editor，打开指定地图（建议先在 UE 内制作副本；World Partition 必须保留外部 Actor）。在 UE Python 控制台执行：

```python
exec(open(r'D:/MyScene/Scripts/WISEYE/initialize_custom_scene.py', encoding='utf-8').read())
```

该工具在当前匹配地图中放置已配置设备、设置该地图 GameMode 并保存。禁止重复安装；先保存其他未保存工作。此处不创建或替换用户环境。

使用完整源码仓库的桌面端接入（关闭宿主编辑器后启动独立仿真，避免占用同一项目）：

```powershell
.\scripts\Start-CustomEnvironment.ps1 -ProjectPath 'D:\MyScene\MyScene.uproject' -Scene custom
```

脚本为该宿主建立独立 UserData 配置、指定宿主工程，打开桌面但不自动启动 UE；在桌面选择自定义场景并点击启动仿真，RuntimeManager 会启动宿主地图与 Python 飞控。自定义场景使用经过 UE 确认的初始位姿及通用动力学模板，不套用城市坐标。已有用户配置不覆盖。若选择手动在 UE 中 Play，则还需启动仓库内飞控工作进程；安装插件本身不自动启动 Python。

## 能力与边界

无 City Sample Traffic 插件时，人车生成适配明确不可用，核心双光、云台和无人机不应依赖该城市插件。自己的地图仍需检查碰撞、出生点、光照/天气以及热材质分类；普通场景接入不意味着自动获得城市同等热外观。构建版本、兼容性与已执行实跑以本次交接记录为准，不用“能导出”代替“已在干净电脑验证”。

完整城市运行包采用 DX12/SM6，不再附带未经本轮验收的 DX11/SM5 回退；源码插件不替宿主强制选择 RHI。自定义宿主打包时，接入器提供的 ThirdParty/JSBSim/Resources 也会声明为运行依赖，避免仅 Editor 下可读。

完整运行包可另带城市，源码插件包不应强制用户下载城市。发布前须核查自有代码与第三方模型的再分发授权；保留 ProjectAirSim、JSBSim 等上游许可证。当前打包工具不会替作者作出资产授权声明，也不会自动发布 GitHub。
