# WISEYE UE 工程与源码插件 · v1.1.0

本目录的 `WISEYE/test.uproject` 是默认城市工程；唯一原生源码在 `WISEYE/Source/test`，按桥接、设备、云台、成像、飞行、人车和窗口等职责拆分。模块名 `test` 与 `/Script/test` 是现有资产兼容路径，不要直接改名。

## 两种开发方式

- 使用本仓库城市：先按[安装说明](../docs/INSTALLATION.md)准备 UE 5.8.4、VS、Project AirSim、JSBSim 和合法获取的 City Sample。小城市地图 `/Game/WISEYE/Scenes/city/CitySample`，大城市 `/Game/WISEYE/Scenes/city_large/BigCity`。源码仓库不含完整城市及其生成副本。
- 使用自己的场景：下载 [v1.1.0 插件包](https://github.com/Ws-3/WISEYE-Studio/releases/tag/v1.1.0)，按[插件指南](../docs/PLUGIN_DISTRIBUTION.md)预检、安装、编译并初始化；不要求 City Sample。无 Traffic 插件时城市人车适配不可用，核心设备与双光仍可运行。

生成 SDK 的 `Source/test` 是构建产物，不作为第二套开发源码。普通运行包用户无需打开此工程。

## 设备和传感器

云台高 80 cm；固定底座 bottom、水平 YawPivot/bottom2、俯仰 PitchPivot/camera/ptz。实际设备尺寸由 `WISEYE/Config/WISEYE/device_dimensions.json` 管理；固定翼机长 80 cm、参考气动参数未标定。Mavic/Avata 旋翼跟随模拟电机 RPM，不能用固定动画速度替代起降。

可见光 1920×1080 和红外 640×512 使用独立光心及可配置安装偏差；不再描述为共用相机或单纯 RGB 灰度化。云台支持同 Tick 双光采集，但不等于像素已配准；机载双光独立采样。可见光包含光学模糊/景深近似，红外为热外观而非温度定标。事件为帧驱动近似，LiDAR 为理想射线扫描，详[传感器边界](../docs/SENSOR_UPGRADE_20261109.md)。

多旋翼采用 Project AirSim，固定翼采用项目原生 JSBSim 适配。设备 ID、驾驶对象、云台对象与画面来源独立；当前运行修改与保存初始配置分开。不要运行历史 setup_scene/configure_controls/restore_ptz 等脚本覆盖现有装配。

## 操作和构建

推荐从桌面启动仿真；仅需编辑时运行 `scripts/Start-WISEYE.ps1`。键盘驾驶 WASD、R 上升/F 下降、Q/E 转向；自由观察采用右键导航，与驾驶归属分开。云台通过右侧遥杆或已分配的键盘模式控制。完整按键与起降操作见[使用指南](../docs/USER_GUIDE.md)，不沿用历史 M/F/R 旋翼动画快捷键。

```powershell
# 在仓库根目录，依赖准备完毕后
.\scripts\Build-Distribution.ps1 -Kind Plugin
.\scripts\Build-Distribution.ps1 -Kind Full -Configuration Shipping -IncludeBigCity
```

插件安装器会布置宿主资源并保留 `/Game` 路径；第三方依赖和 JSBSim 运行资源包含在 SDK。完整城市 Shipping 采用 DX12/SM6。自定义宿主已通过 Editor 实跑与 Shipping 编译，完整宿主 Cook 尚未验收。已知城市人物头部材质回退及完整构建证据见[实施记录](../docs/DISTRIBUTION_IMPLEMENTATION_20261110.md)。
