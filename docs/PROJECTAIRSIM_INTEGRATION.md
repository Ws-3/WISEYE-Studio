# WISEYE × Project AirSim 运行说明

WISEYE 现在可把 Project AirSim 作为无人机唯一动力学与位姿来源。Project AirSim 的 Fast Physics、SimpleFlight、旋翼执行器、IMU、GPS、气压计和磁力计运行在 WISEYE 自己的 UE 地图中；WISEYE 原无人机模型关闭碰撞后作为整机外观跟随 `Drone1`，云台、相机和实验流程继续使用现有代码。

地面光电云台新增激光扫描器。扫描原点挂在 `Camera` 下，因此继承 `bottom2` 的水平转动以及 `camera/ptz` 的水平和俯仰转动。默认每秒 10 帧、每帧 48×12 条射线、水平 30°、垂直 8°、最大 300 m。点云以传感器局部坐标、米为单位导出为 PLY。

## 首次配置

Project AirSim 固定使用 `iamaisim/ProjectAirSim` commit `62229cd7c77ad31da7bc8aba8dd6303c564d8ba2`。它体积较大，不直接复制进 WISEYE Git；脚本会克隆、应用 WISEYE 的 UE 5.8/飞行完成补丁、构建仿真库，并为 WISEYE 创建本地插件入口和目录联接。

```powershell
cd D:\Projects\WISEYE-Studio
.\scripts\Setup-ProjectAirSim.ps1 `
  -EngineRoot D:\Projects\UE_5.8 `
  -VisualStudioRoot 'D:\programs\Microsoft\Visual Studio\2022\Community'
```

插件源码默认位于 WISEYE 同级的 `ProjectAirSim-Evaluation`。本机生成的 `.venv`、插件目录联接、二进制和中间文件不上传。可复现修改保存在 `third_party/patches/projectairsim-simpleflight-completion.patch`。

## 启动演示

双击 `Start-ProjectAirSim.cmd`。脚本编译并打开 UE，自动进入播放并启动飞控服务；无需再点击绿色“播放”。默认在 `original` 场景持续飞行，按 Ctrl+C 停止客户端。随后双击 `Start-Desktop.cmd`，连接后即可控制飞行。

也可以从 PowerShell选择测试场或只飞一圈：

```powershell
.\scripts\Start-ProjectAirSim.ps1 -Scene test_range
.\scripts\Start-ProjectAirSim.ps1 -Scene original -Loops 1
```

直接运行客户端时，UE 必须已经处于 Play：

```powershell
D:\Projects\ProjectAirSim-Evaluation\.venv\Scripts\python.exe `
  .\integrations\ProjectAirSim\run_wiseye_flight.py --scene original --loops 1
```

## 接口与输出

`sim.get_state` 增加：

- `flight_backend=projectairsim`
- `dynamics_connected` 与 `dynamics_actor`
- `lidar_enabled`、`lidar_hits`、`lidar_rays`、`lidar_nearest_m`
- `lidar_last_export_path`

激光命令：

- `sensor.lidar.set_enabled`，载荷 `{ "enabled": true }`
- `sensor.lidar.capture`，导出 PLY 并返回 `point_cloud_path`
- `sensor.lidar.get_points`，返回最近扫描的局部米制点，桌面每秒刷新 5 次俯视点云

AirSim 飞控服务监听 `127.0.0.1:50052`，使用相同 JSON Lines 包格式。支持 `sim.ping/get_state`、`sim.pause/resume/reset`、`flight.set_mode` 和 `flight.set_input`。桌面在 AirSim 后端自动连接该端口。暂停执行 SimpleFlight 悬停保持，物理引擎继续运行；复位按物理航迹返回起飞后的航线原点，不瞬移。

输出仍在 `ue5/WISEYE/Saved/WISEYE/日期_时间/`。AirSim 模式下 `flight.set_input` 会明确拒绝，因为位姿和飞控必须由 Project AirSim 客户端控制，避免两个后端同时写入无人机。

## 已验证与限制

2026-10-17 在 UE 5.8.3 实测联合编译成功。原始地图完成一次起飞和路径飞行，WISEYE 成功绑定 `Drone1`；100 个遥测样本的 X/Y/Z 运动跨度约为 11.84/7.61/7.33 m。云台激光每帧 576 条射线，接口报告 8 次命中并成功导出 PLY。修复上游未初始化场景 Actor 指针后，连续两次场景热重载均通过；持续演示进程保持响应且重复相机捕获警告为 0。证据见 `docs/evidence/projectairsim_wiseye_integration.json`。

桌面已实测转发自动/手动、悬停暂停、继续和物理复位，提供九键手动控制与实时点云页。一次联调中手动前飞产生 0.23 m 位移，向下扫描返回 576/576 个预览点；13 项 Python 测试、桌面 UI 启动检查和 UE 增量构建通过。激光仍是 WISEYE 地面光电云台的 UE 射线扫描模型，Project AirSim 自带的机载 LiDAR 尚未接入桌面数据流。下一步加入统一时间戳、持续图像通道和飞行任务编辑。
