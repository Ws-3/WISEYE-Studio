# WISEYE Studio

**v1.1.0 · 2026-11-10 · 源码插件与完整运行包双交付**

WISEYE 基于 Unreal Engine、Project AirSim 与 JSBSim，提供无人机飞行、光电云台、地面/机载双光传感器和数据采集工作台。支持中文、English。感谢 YZE、ZWT 的大力支持！

## 下载哪一个？

| 使用目的 | 获取方式 | 所需环境 |
|---|---|---|
| 在自己的 UE 地图中加入 WISEYE | [v1.1.0 Release](https://github.com/Ws-3/WISEYE-Studio/releases/tag/v1.1.0) 的 `WISEYE-Plugin-v1.1.0-UE5.8-Win64.zip` | Windows x64、UE 5.8 C++ 工程、VS 2022、Python；无需 City Sample |
| 修改仿真端、训练端和插件源码 | 克隆本仓库，再按[安装说明](docs/INSTALLATION.md)准备依赖 | UE、C++ 工具链与 Python；城市示例另需合法取得 City Sample |
| 直接使用完整软件 | 本地已构建 `WISEYE-Full-20261110.zip`，约 27.3 GiB | Windows x64、DX12/SM6 显卡驱动与 VC++ 运行库；无需 UE 编辑器、VS 或 Python |

**本次 GitHub Release 上传源码插件 ZIP 和 SHA256，不包含大型完整运行包。** GitHub 自动生成的 Source code ZIP 是源码，不可双击运行；完整运行包尚无公开下载地址。完整包包含小城市和大城市试验场景。运行与构建见[发布说明](docs/releases/v1.1.0.md)及[打包指南](docs/RELEASE_BUILD.md)。

## 插件接入自己的场景

解压 Release 插件 ZIP，保存并关闭宿主工程，在插件包目录执行：

```powershell
python .\install.py --project 'D:\MyScene\MyScene.uproject' --map /Game/Maps/MyMap
python .\install.py --project 'D:\MyScene\MyScene.uproject' --map /Game/Maps/MyMap --apply
```

先预检，再安装；编译宿主 Editor，打开指定地图，按[插件接入指南](docs/PLUGIN_DISTRIBUTION.md)初始化设备并连接桌面端。当前包保留 `/Script/test` 和历史资产路径，安装器会同时放置 Plugins 与宿主资源；不是仅复制一个裸插件目录。宿主已有 `test` 模块或冲突资产时会拒绝写入。SDK 不包含桌面 Python 环境，桌面端使用完整源码仓库。

感谢YZE、ZWT的大力支持！

## 当前功能

- 场景编排、模型放置预览、设备实时增删/修改与单独保存初始设置；大小城市分别加载。
- Mavic、Avata 多旋翼；80 cm 固定翼与 JSBSim 六自由度参考模型；手动飞行、航线、云台跟随/保持。
- 独立光心可见光 1920×1080 / 红外 640×512；云台与机载航拍、双光并排、各传感器独立启停。
- 可见光模糊、噪声、对比、对焦/光圈与景深；红外建筑、天空、道路及无人机局部热外观。
- LiDAR 点云、帧驱动事件相机、PointCloud2 / EventCD 格式转换；可编辑 RTSP 等接口。
- 云台角度、视场角、目标距离、自定义仿真地理基准及坐标指向。
- 快速预览与标注采集分开；训练端数据源切换、人工标框、负样本审核和按 run 隔离的数据集导出。
- 中英文界面、性能诊断、时间/雾/雨等环境设置、UE 窗口显隐与退出清理；打开桌面不自动启动 UE。

红外是热外观近似，未做辐射温度定标；事件和点云不是厂商硬件等效模型；固定翼参数未实机辨识。云台同 Tick 双光不等于像素配准，航拍当前需人工标注，不能当自动 GT。设置帧率不等于实测吞吐。具体边界见[传感器说明](docs/SENSOR_UPGRADE_20261109.md)。

## 日常运行与开发

完整包全部解压后运行 `WISEYE/WISEYE.exe`；训练端为 `WISEYE/Training/WISEYE-Training.exe`。源码环境使用根目录 `Start-WISEYE-Studio.vbs` 或 `scripts/Start-Desktop.ps1`，再在界面启动仿真。配置与输出由 UserData/显式数据目录管理。完整操作见[使用指南](docs/USER_GUIDE.md)。

UE 唯一源码为 `ue5/WISEYE/Source/test`，默认工程为 `ue5/WISEYE/test.uproject`。不再要求外部 `WISEYE-IR-Work` 或 `ProjectAirSim-Evaluation` 工作副本；可重建依赖置于仓库 builds。城市原始资产仍为可选本地依赖，详[目录与依赖](docs/PROJECT_DEPENDENCIES.md)。

```powershell
# 在已配置开发环境中生成两种交付物
.\scripts\Build-Distribution.ps1 -Kind Plugin
.\scripts\Build-Distribution.ps1 -Kind Full -Configuration Shipping -IncludeBigCity
```

## 验证与已知问题

v1.1.0 发布前 171 项核心与安装回归全部通过；此前 39 项分发专项也已通过。独立无城市宿主通过 Editor 双光/飞行实跑与 Shipping 编译；完整包大小城市通过取图、云台、点云、起飞/手动爬升/降落，冻结仿真端和训练端界面启动通过。验证证据见[本版发行说明](docs/releases/v1.1.0.md)。

尚未完成干净 Windows、其他 GPU、自定义宿主完整 Cook 和长时间/全城/多机压力验收。城市完整包采用 DX12/SM6；第三方人物头部材质存在 Cook 回退告警。当前没有在线更新器或签名安装器。

## 文档

- [安装](docs/INSTALLATION.md) · [使用](docs/USER_GUIDE.md) · [插件](docs/PLUGIN_DISTRIBUTION.md) · [UE 源码](ue5/README.md)
- [训练与数据集](training_client/README.md) · [协议](docs/PROTOCOL.md) · [云台接口](docs/GIMBAL_INTERFACE.md)
- [打包与更新](docs/RELEASE_BUILD.md) · [依赖结构](docs/PROJECT_DEPENDENCIES.md) · [版本变化](CHANGELOG.md)
- [开发交接](docs/AI_HANDOFF.md) · [本轮实施与验收](docs/DISTRIBUTION_IMPLEMENTATION_20261110.md)

v1.0.0 是 2026 年 11 月 3 日作者生日纪念版，保留[历史发行说明](docs/releases/v1.0.0.md)。第三方许可证见 LICENSE 和 third_party/notices；城市与模型资产适用各自授权，代码许可证不替代资产许可。
