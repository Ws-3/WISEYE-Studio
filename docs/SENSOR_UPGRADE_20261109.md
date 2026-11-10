# 可见光、航拍热像、传感器接口与后台窗口改进

日期：2026-11-09。唯一源码 `E:\Projects\WISEYE`，预览构建 `E:\Projects\WISEYE-IR-Work`。这次更新源码预览和项目材质，不重打旧独立运行包、不推送GitHub。

## 可见光与景深

云台和每架无人机航拍均支持以下运行参数：

| 字段 | 范围/含义 |
|---|---|
| `focus_mode` | `auto` 自动、`manual` 指定距离、`infinity` 无穷远、`off` 关闭景深 |
| `focus_distance_m` | 0.2–10000m，手动模式使用 |
| `aperture_f` | f/1–f/22，越小通常景深越浅 |
| `actual_focus_distance_m` | 实际对焦距离，只读，自动模式由场景测量 |
| `dof_near_m` / `dof_far_m` | 薄透镜近/远景深估计，远界为-1表示无穷远 |
| `sensor_width_mm` | 参考传感器宽13.2mm，只读；非实机测量 |
| `dof_estimate` | 使用两个输出像素弥散圆的工程估计，不是实机标定结果 |

云台设置在“传感器→可见光”，航拍设置在右侧“航拍相机”。修改后点击应用，无需重载地图。手动距离仅在手动模式可编辑。自动对焦在云台跟踪时使用目标轴向距离，其他情况取画面中心碰撞射线；每0.15秒更新、平滑模拟镜头执行器。射线可能受玻璃碰撞和碰撞LOD影响，并非基于真实图像的对比度/相位自动对焦。

原生UE景深作用于源相机渲染，不是桌面截图模糊。光圈、视场/焦距及对焦距离共同决定景深，不能任意指定一对互不相容的清晰远近界。广角、远距离和小光圈下，真实相机本身也可能大部分清晰。[Epic景深说明](https://dev.epicgames.com/documentation/unreal-engine/cinematic-depth-of-field-in-unreal-engine)。

默认光学模糊从0.55px提高到0.95px，避免过于锋利的合成边缘；可见光原有噪声、对比和饱和度仍可调。保留已保存的用户值，旧版UE不支持对焦时界面禁用新增控件。航拍增加独立`vis_blur_px`（0–3px）及独立对焦状态，不修改云台焦点；红外继续使用独立镜头和自己的PSF，不套用可见光景深。航拍“保存默认”会保存新增镜头参数；云台可见光参数保持原有的本次运行设置范围。

## 车辆热红外

原实现将人群/车辆整组件编码为180/235，落入无人机的热目标编码范围。车辆会错误使用无人机提亮曲线，并在原始信号PSF后按硬目标掩模切换曲线，形成不合理的整车高亮及边缘反差。

现在车辆/行人使用独立16/17标签，无人机继续使用≥32编码。车辆按有界材质、粗糙度、法线差异生成热代理；行人采用单独的衣着/表面代理。人车不再套用无人机的目标提亮，边缘与背景通过共同显示曲线，保留原始信号光学PSF。

真实热像中，远处小目标、强增益或饱和可能呈白块；但“任何车辆整车均匀白热”不是合理通用默认。当前也不是发动机/轮胎/玻璃真实温度求解，尚未接车辆动力和停车冷却历史，不能声称已完成车辆热物理模型。

## 双光左右并排

“无人机航拍→双光并排”固定可见光在左、红外在右，不再进入自定义布局的主画面/缩略窗上下分割。启用场景参考时参考窗放在下一行；放大和弹出仍按单画面工作，退出航拍恢复原观测布局。修复窗口尺寸变化时航拍设备栏意外重新展开的问题。

## 激光雷达核查

| 项目 | 当前结论 |
|---|---|
| 测距/坐标 | UE碰撞射线首回波，米制，传感器局部坐标；适合几何和接口试验 |
| 扫描方式 | 矩形角度网格的一次快照；不是旋转雷达逐束时序扫描 |
| 点云显示 | 空间点的可视化，颜色不代表真实反射强度或热像 |
| 已有缩略接口 | `sensor.lidar.get_points`，最多768点，不能冒充完整扫描 |
| 新完整接口 | `sensor.lidar.get_scan`，最多128×64束，包含有效点及按束排序距离，未命中为-1 |
| 新时间字段 | `lidar_capture_time_s`为最后一次扫描时刻，而不是请求/导出时刻；附`lidar_scan_sequence` |
| 未模拟 | 真实强度、反射率/材料响应、光束发散、测距噪声、多回波、雨雾回波、厂商UDP协议 |

`lidar_points_m`为命中点，坐标轴为X前/Y右/Z上（UE左手系）。`lidar_ranges_m`按pitch从负半视场到正半视场逐行、yaw从负半视场到正半视场逐列排列，不把无回波写成原点点云。输出`lidar_downsampled`和模型说明。

`core.sensor_formats.pointcloud2(packet)`提供ROS PointCloud2字段和值，其中`data`为小端float32 XYZ字节，Y反号转为X前/Y左/Z上。头部使用采集时间，返回头部为普通字典；实际发布需要ROS消息构造、ROS2节点、仿真`/clock`和正确TF，不是已经安装或运行的ROS驱动。[ROS2官方消息定义](https://github.com/ros2/common_interfaces/blob/rolling/sensor_msgs/msg/PointCloud2.msg)。禁止直接将UE左手系旋转四元数当ROS变换使用。

## 事件相机核查

真实事件相机输出每像素亮度变化的坐标、时间和极性，红/蓝点图只是一定时间窗口的可视化，不是原始RGB视频。[Prophesee事件概念](https://docs.prophesee.ai/stable/concepts.html)。

当前模型有独立HDR相机、对数亮度阈值、不应期、阈值累计、事件排序和有界缓冲；输出`columns=x,y,t_us,p`，原点左上、X右/Y下，极性-1/OFF和+1/ON。时间以UE本次运行微秒计，**由相邻渲染帧线性插值**；微秒单位不代表达到真实微秒响应。

包中新明确`hardware_timing=false`、极性编码、像素原点和时间单位，保留generation、游标、丢采样帧、截断/跳过事件指标。主接口仍为` sensor.event.get_packet`，支持`after_sequence`、`max_events`（≤20000）、`latest`。恒定静态场景零事件是正常现象。

`core.sensor_formats.metavision_events(packet)`转换为Metavision EventCD风格NumPy结构（x/y为uint16，p为0/1，t为int64微秒，16字节对齐）。这是数据结构适配，不是EVT2/EVT3 RAW编码、真实硬件SDK驱动或硬件时钟同步。仍缺少实机阈值差异、背景活动噪声、完整光电带宽/延迟和微秒运动细节，不能当论文中的真实事件传感器等效模型。

## UE窗口

正常内置启动和`Start-SimulationPreview`均默认隐藏UE窗口，仍保留GPU渲染和仿真，不能使用`-nullrhi`。右上角一个“UE 窗口”切换按钮，通过`sim.window.set_visible {visible:bool}`显示/收起；回读`ue_window_visible`、`ue_window_control_supported`。窗口控制仅匹配UE自身进程的UnrealWindow，不修改其他进程。

原生隐藏标志`-WiseEyeHiddenWindow`、初始隐藏窗口信息及离屏初始位置共同避免启动抢前台；设置`t.IdleWhenNotForeground 0`避免仅因后台而主动空转休眠。这不是减少到零GPU占用；最小化/隐藏窗口也不等于关闭仿真。进入“到UE预览放置”会主动显示UE窗口，避免看不见放置模型。

## 验证及证据

源码与预览资产同步，UE5.8 Editor编译通过。35项Python/Qt检查通过，原生热像标签/曲线及事件阈值、极性、时间、不应期、截断测试通过。隔离小城实跑完成起飞悬停、隐藏窗口双光昼夜8帧、显示/隐藏窗口、景深渲染、自动对焦、无效焦点参数拒绝且不改变FOV、完整雷达点/距离一致性、事件EventCD转换、降落和所属进程退出；项目材质编译回退0。

实跑记录见`docs/evidence/sensors-20261109`。其中界面图是本轮实采图像的离线UI回放，不是额外实时会话。雷达本轮得到576个点；事件包取得4000个事件，实际渲染采样约15Hz。航拍光学模糊0/2.5px对照的细节方差约622→31，验证每机模糊确实生效；近焦失焦测试为建筑画面：拉普拉斯方差约186→1.94，证明景深渲染改变了画面，不将这个比值称作“真实度”。

已有Mass CustomData非致命ensure仍有出现，未声称本轮修复。大城、多设备性能、Shipping/Cook和真实设备标定尚未重验。每束雷达和每个事件的真实性限制必须随数据说明一起保留。

## 复现

项目根目录：

```powershell
& .\Tools\Python\python.exe -X utf8 -m unittest tests.test_sensor_upgrade_ui tests.test_sensor_formats tests.verify_infrared_settings tests.verify_mission_workspace tests.verify_observation_ui tests.verify_event_sensor_ui tests.test_localization -v
& .\Tools\Python\python.exe -X utf8 -m tests.verify_imaging_realism_live --tag sensors-check --sensor-upgrade
```

实跑脚本只在端口空闲时启动自己拥有的UE/飞控，写隔离builds目录并最终降落退出；先关闭正在运行的用户仿真再执行。脚本使用本机scripts/engine-root.local.txt和preview-project.local.txt，也支持显式路径。重建材质需运行`ue5/scripts/configure_imaging_realism.py`并同步两份源资产，不能只复制HLSL。

`population.get_agents`另提供可选`from_camera=<无人机ID>`碰撞射线诊断，用于过滤明显被建筑挡住的候选；`los_clear`不是像素级可见性、同帧目标框或训练GT。车辆近景采样须人工确认目标确实可见，不能只看到实体坐标就断言图中有车。
