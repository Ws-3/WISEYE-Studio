# 本机控制协议 v1

## 2026-11-02 环境诊断

environment新增rain_active_particles（现有本地体积中Rain组件活动粒子总数）、night_amount[0,1]和day_sky_meshes。rain_supported只表资源能力，不代表粒子已产生；雨量为视觉强度，不是毫米降水量。night_amount是当前艺术性太阳路径的夜间响应系数，不是日照/辐射标定。可见光曝光不套用于红外；光学相机显示缩放仅桌面视图，不改变FOV或GT。见[实现与验证](WORKBENCH_WEATHER_20261102.md)。

## 2026-10-31传感器停用与预览质量

相机停用时sim.get_state仍返回规格width/height，是否采集由sensors.<sensor>.enabled表示。旧版明确停用时0×0状态兼容，不能用0×0冒充任意正常状态。camera.stream_frame对停用通道仍返回sensor_disabled，不影响控制或OBS。共享JPEG缓存实际quality=90（请求quality仍仅兼容校验，不逐请求重编码）。environment新增rain_unavailable_reason；正常为空。稳定AGC与点云视角说明见[SENSOR_STABILITY_FIXES.md](SENSOR_STABILITY_FIXES.md)。

## 2026-10-31 大城市试验流送状态

50052飞控状态现从物理引擎actual_pose推送读取position_ned_m与yaw_deg，telemetry_source标记actual_pose_topic（初始单次种子为initial_kinematics_rpc）；新增telemetry_valid与telemetry_age_s。超过2秒标记connected/telemetry_valid=false并保留最后坐标。状态查询不再同步访问旧场景的NNG服务，避免切图期间阻塞重连；机器人控制和物理权威不变。源码Native runtime_hardware还新增asset_compile_jobs，大城市启动等待后台资源编译队列清空。

`sim.get_state` 新增 `world_streaming_enabled`（原生查询分区流送是否启用）、`world_streaming_ready`（设备流送源当前是否完成加载）、`device_streaming_sources`（显式设备流送源数，不含PlayerController观察视角源）；大城市 `city_large` 另有 `streaming_radius_m=250`。只在大城市安装跟随云台和无人机的流送源并限制观察源形状，小城市不增加设备源。飞控初始化要求大城市的enabled、ready均严格为true；该标志不代表整城已加载、不保证任意远处都有碰撞，也不替代自动避障。地图接入及验收见 [BIG_CITY_INTEGRATION.md](BIG_CITY_INTEGRATION.md)。

## 2026-10-30 坐标指向

新增gimbal.point_at：payload包含device_id、当前scene_id/run_id、sensor(visible/infrared)、position_cm三个UE世界厘米坐标；按实际独立光心求解，非法/过期/超限拒绝且保留原姿态。成功保持新朝向并退出真值跟踪，回传coordinate_pointing光轴误差与斜距。state新增gimbal_geometry、coordinate_pointing_supported，各相机新增vertical_fov_deg/width_px/height_px。WGS84仿真基准转换由SDK/GUI完成，不是原生经纬接口。详见[GIMBAL_COORDINATES.md](GIMBAL_COORDINATES.md)。

## 2026-10-29 GT速率配置

camera.gt_configure新增max_fps，可选，严格数字有限0.1–20，默认2；与其他GT策略全部校验后原子生效。双路/单路各传感器请求间隔由1/max_fps决定。sim.get_state包含gt_max_fps_supported=20（协议上限，不是实测性能）和当前gt_max_fps，标注元数据新增gt_annotation_cpu_ms。新工作台请求max_fps10，默认预览5/保存1；本机双路实测约4–5组/s。详见GT_RATE_AND_UNIFIED_PREVIEW.md。

## 2026-10-29 运行中设备放置

能力live_placement_supported=true；50051新增placement.validate/apply，50052对无人机新增placement.apply。必填device_id、当前scene_id/run_id、request_token（1–64字符）、position_cm三维有限坐标（每轴±1e7cm）、yaw_deg（±180°）。UE确认placement_applied包含device_id/request_token；预览placement包含yaw_deg，devices含placement_yaw_deg。无人机仅落地/无动作/电机停止可改，由50052先设置物理位姿（SetPose包含frame_id并reset_kinematics=True），再由50051校验物理位置/偏航并更新起始原点。云台可直接50051更新完整装配。当前运行应用不写磁盘，保存初始布置另行进行。详见LIVE_PLACEMENT.md，数据网关不开放这些控制命令。

## 2026-10-28 双相机外参与楼顶默认布局

`sensors.visible/infrared.extrinsics_supported=true`时，`sensor.configure`在原有必填字段之外可单独设置`mount_x_cm/mount_y_cm/mount_z_cm`（每轴±100cm）、`boresight_pitch_deg/boresight_yaw_deg/boresight_roll_deg`（±15°）。均严格有限数值，不接受布尔/字符串；全部参数验证后原子生效。不提供则保留。参考为共同机械头部，X前/Y右/Z上，厘米不受导入模型缩放；旋转为局部pitch/yaw/roll复合。仅本次运行有效。

状态按传感器回读六设置值及世界`camera_position_cm`、`camera_rotation_pitch_yaw_roll_deg`。GT单路/同刻双路样本仍使用捕获时刻各自相机位姿与内参；不共享像素框。同刻采集不代表同光心或图像已配准。PNG导出使用指定模态相机当前位姿，保留最近完成图像的时间限制说明。

当前示例VIS位置(0,-6,0)、IR(0,6,0)cm，IR视轴(0.1,0.2,0)°，未由实机测量。城市默认仅ptz-01/uav-01，同一楼顶；旧ptz-02不再存在。训练默认设备已相应调整。详见[DUAL_CAMERA_ROOFTOP](DUAL_CAMERA_ROOFTOP.md)。

## 2026-10-28 同帧训练样本接口

2026-10-29采集上下文：每个GT样本新增environment（采集Tick的环境参数快照）、scenario_models（该场景已配置无人机机型，包含不可见目标）及context_source=capture_tick。用于负样本命名和分组；不改变objects只包含符合策略可见目标的规则，也不提高2次/s限制。新训练端不再保存pairs文件，按samples/<共享组ID>保存双路图像与各自标签/元数据；详见训练接口说明最新节。

双路更新：能力 `paired_training_samples_supported=true`，`camera.sample_pair_request` 接受 device_id、返回 sample_token；`camera.sample_pair_frame` 接受 device_id/sample_token，返回 pair_id/run_id/simulation_time_s 和 samples.visible/infrared。两路强制同 Tick 捕获，未同时完成返回 frame_unavailable，任一路禁用返回 sensor_disabled。各自保留独立帧号，不能要求帧号相等。数据服务随仿真启动，训练端仅 Start-Training.vbs；无需手动启动网关。

新能力 `training_samples_supported=true`。新增按云台 `camera.gt_configure`、`camera.sample_request`、`camera.sample_frame`；接收端通过 sample_token 获取同帧 JPEG、可见 GT、相机参数与负样本标志。部分遮挡/出画分别可配，完整空标注可训练；计算失败或策略排除可见目标不能混作普通负样本。GT 不绘制到仿真图像。默认按需低频采样，UE 仍只监听本机；跨电脑通过新增 `training_client.gateway` 的数据端口。字段、限制与命令见 [训练接口说明](TRAINING_DATA_INTERFACE.md) 和 [独立训练端](../training_client/README.md)。

## 2026-10-28 红外探测器控制与同帧回放（源码预览）

`sensors.infrared.detector_controls_available=true` 表示包含新版 Facade 资产及读出支持。`sensor.configure` 指定 `device_id` 与 `sensor:"infrared"`，可编辑：

| 字段 | 范围/语义 |
|---|---|
| gain_mode | auto / locked / manual；locked保持当前实际窗口 |
| stable_agc | 严格布尔，仅auto时启用背景统计与限速 |
| manual_low / manual_high | 0–1有限数值，high-low至少0.01；不是温度 |
| brightness | -0.3–0.3有限数值，在极性反转前施加 |
| sky_denoise | 0–1有限数值，仅facade天空掩码空间滤波 |
| noise_seed | 0–2147483647整数，噪声由种子/帧序号/像素决定 |

新参数与旧参数一起验证后原子生效。`agc_enabled`旧调用保留：true映射auto，false映射manual（初始0–1或已设手动范围）。同时提交新模式与旧布尔须一致：仅auto对应true。新能力不存在时不要发送新字段。legacy/enhanced仍可保存参数但不使用读出增益/滤波。`agc_low/high`为已处理帧实际窗口，不等于手动草稿；新增`sky_pixels`为下采样后天空计数。锁定窗口跨红外停用/恢复保留；重启程序不持久化。

显式诊断接口（按云台隔离，默认关闭）：

- `camera.signal_recording`：`{device_id, enabled: bool}`。开启须红外已启用且使用reference/classified/facade读出、具有新版资产；关闭清空可读记录。
- `camera.signal_frame`：`{device_id}`。开启记录并等待新帧后，返回640×512、`frame_number`、`encoding:"f32_le"`、`signal_base64`（float32 little-endian归一化代理）、`sky_mask_base64`和`target_mask_base64`（每像素uint8，0/1）。信号已由FP16读取/下采样，位于天空滤波/PSF/噪声/AGC之前，不是相机原始ADC或温度。
- 未开启记录、未有记录或红外停止时返回`frame_unavailable`。关闭采集清记录，重新开启记录后须等新帧；只返回最近记录，不阻塞等待采集。2×输出仍640×512，任一子像素目标即保护，四子像素全天空才标天空。

诊断每帧保留约1.88MiB数据（加临时复制/Base64响应），关闭后不再复制，容器容量可保留复用。该接口不替代JPEG/RTSP，不应轮询作为实时预览；用完显式关闭。固定种子不保证UE体积云/完整模拟确定性；以相同原始信号与掩码回放验证处理差异。复现实验及限制见 [INFRARED_DETECTOR_PILOT](INFRARED_DETECTOR_PILOT.md)。

## 2026-10-28 云层与采集开关（源码预览）

`sensor.set_enabled`：`{device_id:"ptz-02",sensor:"visible"|"infrared"|"lidar",enabled:true|false}`。只修改该传感器运行启用状态，不提交其他参数，严格布尔校验，要求云台设备。能力`state.sensor_power_supported`；旧版无此能力时UI禁用快捷开关，仍保留原sensor.configure。停用图像通道清空缓存并使旧读回任务失效；camera.stream_frame返回sensor_disabled，恢复后仅返回新采集帧。状态VIS/IR增加capture_sequence，雷达增加scan_sequence，停止后不增长；completed_frames仍累计。热读出诊断停用时清空，采集需等待恢复新帧。

`environment.configure`可选`clouds`严格数值[0,1]，缺省保留当前值，0移除WISEYE新增云层；environment增加clouds_supported/clouds/cloud_layer_active/cloud_atmosphere_created。实际体积云为全局环境，云量是工程控制量，并非测得天空覆盖率。缺少大气组件时运行时补建，关闭云层后删除补建项并恢复太阳光标志。environment.reset也清理新增云层。红外楼宇模式修复有限远深度的天空判定（当前10km阈值），并过滤空自定义深度的假热目标，以及实际天空亮度/色度云层外观代理，非云温度/辐射标定。详见[CLOUDS_AND_SENSOR_POWER](CLOUDS_AND_SENSOR_POWER.md)。

## 2026-10-27 楼宇热像增量（源码试验）

`thermal_profile=facade` 需 `sensors.infrared.facade_available=true`，缺资产时原子拒绝。沿用classified的FP16/AGC/PSF、极性、细节与诊断计数；GBuffer材质线索只用于外观，不改变类别计数含义，也不提供温度。默认仍reference。详见[楼宇试验](INFRARED_FACADE_PILOT.md)，旧Shipping不含此能力。

## 2026-10-27 材料热像增量（源码试验）

`sensor.configure` 的 `thermal_profile` 增加 `classified`，需要 `sensors.infrared.classified_available=true`。参考读出功能（AGC、1/2×、PSF）同时适用于 reference/classified；缺新资产时拒绝新模式。能力表示代码/材质存在，不保证当前地图有标签。

新模式以离线写入的组件类别使用昼夜信号预设；全局 `environment.configure` 的 time_override/hour 决定预设混合，未覆盖时间时用日间。环境时间仍不是物理温度或城市热传导。

`class_pixels` 是7项计数，按未知/天空/目标、道路、砌体、玻璃、植被、金属、水体排列；当前帧已覆盖比例为后6项之和除以全部计数，不能当分类准确率。1×总数640×512，2×用每个输出像素首个子样本标签。`target_pixels`为目标可见掩码面积，`motor_region_pixels`为当前所选Avata投影电机区域通过机身和深度约束的像素数，不是已识别电机数量。均来自PSF之前的GPU标签通道，只在新鲜classified/facade帧中有效；其他模式可保留上次统计。

PNG记录 `thermal_profile=classified`，仍为显示灰度图；类别、原始信号和物理温度不作为PNG导出。规则和资产需在构建副本准备，见[材料热像试验](INFRARED_MATERIAL_PILOT.md)。

## 2026-10-27 实拍参考红外（源码试验）

`sensor.configure` 的 infrared 继续要求 enabled、fov_deg、palette、noise，另可选：

| 字段 | 类型 / 范围 |
| --- | --- |
| thermal_profile | legacy / enhanced / reference；按材质能力拒绝不可用模式 |
| blur_px / contrast / background_detail | JSON number，分别 [0,2] / [0.3,3] / [0,1] |
| agc_enabled | JSON boolean；数字或字符串不代替布尔 |
| agc_response_s | JSON number，[0.1,10] 秒 |
| sampling_scale | JSON number，只允许整数 1 或 2；最终仍输出640×512 |

全部校验后原子应用；省略可选字段保留原值。客户端仅在 `reference_available=true` 时发送 AGC/采样字段；旧运行时不支持这些控件。UI 草稿仍按 device_id 隔离，新参数仅本次运行有效。

`sensors.infrared` 回显以上参数及 `enhanced_available`、`reference_available`，另有 `agc_low/high`（归一化信号范围）、`readout_ms`（最近参考帧的 CPU PSF/增益/灰度处理耗时，非 GPU/JPEG/网络/端到端耗时）、`readout_sequence`。切回旧模式后这些参考读出统计可能保留最后值，不能据此计算旧模式处理耗时。`signal_model` 明确这是 FP16 归一化热信号代理，不是测温或已标定辐射数据。

状态 `thermal_target` 含 motor_warmth、battery_warmth、power_proxy、body_signal、motor_signal、units，按所查询装配对应的无人机拥有者读取；投影参考热斑按当前 tracking_target 选取。电机热部件分类首轮沿用 Mavic 网格；Avata 尚未细分电机区域。`rotors.sync_state` 仍只能提交真实转速，禁止为“变热”伪造动力学遥测。

红外 PNG 元数据新增 thermal_profile、agc_enabled、agc_response_s、sampling_scale、blur_px、contrast、noise，表示保存时当前配置。PNG/JPEG 是显示图像，未提供原始 FP16 辐射导出；时序仍不是硬同步。详见[试验说明](INFRARED_REFERENCE_PILOT.md)。现有 Shipping 包需重新 Cook 才能包含这些源码改动。

## 2026-10-21 新增接口和运行状态

- `gimbal.get_capabilities`：payload.device_id；返回角度范围、30/20°/s速度和300ms输入看门狗，标准库SDK见 [GIMBAL_INTERFACE.md](GIMBAL_INTERFACE.md)。
- `sim.set_performance_profile`：profile为quality/balanced/economy，全局生效。状态增加 performance_profile、visible_capture_hz、infrared_capture_hz、observer_capture_hz。数值为上限；传感器原始输出分辨率保持不变。
- 状态 `tick_seq` 每个UE Tick递增，与飞行是否暂停无关；`streams.CH1/CH2.cache_age_ms`为源读回排队以来的UE单调时钟年龄，不能代替端到端延迟。
- `motor_rpm` 顺序FL/FR/RL/RR；rotor_source=airsim_rad_s或kinematic；rotor_telemetry_fresh按新Native时间戳和本机时效判断。rotor_rpm为均值。AirSim状态增加 motor_rpm、rotor_sample_age_s。
- 内部 `rotors.sync_state`：device_id、rpm四个有限[0,30000]数、fresh布尔。仅供动力学桥提交实际转速；AirSim下rotors.set_enabled不能覆盖持续实际遥测，应用应使用飞控起降。运动学模式保留动画启停。
- camera.stream_frame缓存超过2s返回无新帧；网络连接和旧视频不代表仿真继续推进。详细参数与采样见 [RUNTIME_OPTIMIZATION.md](RUNTIME_OPTIMIZATION.md)。

## 多实例寻址（2026-10-21）

UE 50051 的 payload 可带 `device_id`：云台/相机/传感器命令用 ptz-XX，无人机模型/旋翼/飞行状态命令用 uav-XX；未知 ID 或类型不匹配拒绝。sim.get_state/ping 返回对应实例的兼容状态，同时含完整 `devices` 清单。未带 ID 保留默认实例行为；场景/观察/输入模式仍为全局操作。sim.pause/resume/reset 在显式寻址时属于无人机控制。

状态 devices 项含 id、kind、model_id、name、position_cm、initial_position_cm、dynamics_name、tracking_target、initial_yaw_deg；顶层 drone_id/gimbal_id 标识所返回装配，单独的驾驶对象以飞控 drone_id 为准。内部复用装配不代表云台必须与同序号无人机配对。

新增：`gimbal.set_target {device_id:"ptz-02",drone_id:"uav-01"}`；`input.select_drone {drone_id:"uav-02"}`；`input.select_gimbal {gimbal_id:"ptz-02"}`。后两项选择 UE 本地键盘与 follow/gimbal 视角目标，不自动起飞或改变飞行模式。

AirSim 50052 全部飞行与航线请求可带 device_id=uav-XX，各机有独立控制器。响应保持所选无人机的原字段，增加 `fleet` 数组（每机完整状态）；省略 ID 默认 uav-01。上传/执行/暂停等不广播到其他无人机。当前没有编队广播或避碰。

camera.stream_frame 返回 device_id、sensor_id；额外云台 RTSP 路径 `<ptz-id>/CH1|CH2`，默认云台继续使用旧 CH1/CH2。OBS 为全局 observer/view。PNG/PLY 伴随 JSON 含 device_id/sensor_id/scene_id/run_id，源分辨率和坐标系仍与旧协议一致。各模态尚未硬件同步，旧 simulation_time_s 不应当作跨设备硬同步时间戳。

## 2026-10-21 扩展

同日保存接口精简：camera.capture 可选 payload.sensor=visible/infrared（省略保留旧行为），直接导出目标传感器，不切换 ActiveSensor/InfraredMode。响应新增 frame_sensor、frame_width、frame_height，导出 PNG 与伴随元数据使用对应模态、分辨率及 FOV；顶层 width/height 仍表示当前 UE 模态，客户端应以 frame_width/height 校验导出。停用目标仍拒绝保存。

UE 50051 新命令均返回完整状态：

| command | payload / 行为 |
| --- | --- |
| gimbal.set_input | yaw、pitch 均 [-1,1]；需 input_mode=gimbal，零输入可随时停止；30°/s 水平、20°/s 俯仰，300 ms 超时归零，非零输入退出跟踪 |
| observer.set_input | forward/right/up [-1,1]、yaw_deg/pitch_deg 单次增量 [-90,90]；需 observer 输入模式与 free 视角；6 m/s，300 ms 超时停止；不驱动无人机 |
| sensor.configure | sensor=visible/infrared/lidar，enabled 布尔。visible 必填 fov_deg [5,120]；infrared 另必填 palette=white_hot/black_hot、noise [0,1]（UI 限 0–0.1）；lidar 必填 horizontal_fov_deg、vertical_fov_deg [0.1,60]，range_m [1,1000]，scan_rate_hz [0.05,10]。完整校验后原子应用，仅影响该传感器 |

状态 `sensors` 是以 visible/infrared/lidar 为键的实际参数映射；原有顶层字段保留兼容。camera.set_fov 只改变当前相机模态的 FOV。sensor.set_active 不再隐式启用雷达。停用相机的 capture/stream_frame 返回错误，点云预览为空。camera.stream_frame 增加 channel=OBS；960×540，modality=observer；原协议质量参数仍仅校验，当前编码质量固定 60。

AirSim 50052 新增 route.upload（payload 为下列完整 JSON）、route.start 和 route.stop（空 payload）。upload 不启动、不改变执行快照；start 要求已起飞且手动起飞/悬停动作已结束；stop 制动悬停。sim.pause / sim.resume 保留下一未完成航点；逐点飞行、拐点减速，无自动避障。成功响应含 route 草稿快照、active_route_name、route_status、route_next_waypoint（1 起）、route_loops；单次完成转为 manual+paused。运行时配置随 PIE 会话失效，持久化需保存 JSON。

```json
{"version":1,"scene_id":"original","name":"演示航线","frame":"ue_world_m","speed_mps":2,"repeat":false,"waypoints":[[80,14,3],[85,14,3],[85,18,3]]}
```

航线约束：2–128 点；每点三个有限米制坐标，绝对值≤100000；相邻间距≥0.05 m；速度 0.2–15 m/s；scene_id 必须匹配运行场景；frame 只接受 UE 世界米制 Z 向上。飞控内部转换 NED [X,Y,-Z]。示例坐标仅示意，不保证适合当前地形。

UE 的 AWiseEyeDemo 在 BeginPlay 监听 `127.0.0.1:50051`，EndPlay 关闭连接。UTF-8 JSON Lines，每条消息以换行结束；TCP 分段和多条合并均支持。请求示例：

```json
{"version":1,"request_id":"demo-1","command":"camera.set_mode","payload":{"mode":"infrared"}}
```

响应包含 `version`、同一 `request_id`、`status` 和 `payload`；成功 status 为 `ok`，失败为 `error`，另带 error 对象（code、message）。错误码包括 bad_request、invalid_payload、invalid_argument、unknown_command、capture_failed。多数成功响应 payload 为当前状态；capture 另带 frame_path。

| command | payload |
|---|---|
| sim.ping / sim.get_state / sim.pause / sim.resume / sim.reset | 空对象 |
| sim.load_scene | scene_id: 已安装且 prepared=true 的场景 ID；接受响应后关卡重载，连接断开 |
| gimbal.set_tracking / rotors.set_enabled | enabled: boolean |
| gimbal.set_angles | yaw_deg: [-180,180]，pitch_deg: 关卡配置的俯仰范围；执行后保持方向 |
| flight.set_mode | mode: auto / manual |
| flight.set_input | forward、right、up、yaw: [-1,1]，仅手动模式 |
| drone.set_model | model: mavic3 / avata；仅切换可见外观，不改变 AirSim 动力学 |
| sensor.set_active | sensor: visible / infrared / lidar；选择云台当前工作的传感器，与桌面当前查看通道相互独立 |
| camera.set_mode | mode: visible / infrared |
| camera.set_palette | palette: white_hot / black_hot |
| camera.set_fov | fov_deg: [5,120]，水平视场角 |
| camera.capture | 空对象；导出当前模式原生 PNG |
| camera.stream_frame | channel: CH1 / CH2 / OBS，quality: [25,95]；返回原尺寸JPEG Base64、frame_number和simulation_time_s；本机RTSP网关及工作台最新帧预览使用，云台源传device_id |
| sensor.lidar.set_enabled | enabled: boolean |
| sensor.lidar.capture | 空对象；立即扫描并导出传感器局部坐标、米制 PLY |
| sensor.lidar.get_points | 空对象；返回最近扫描的 `lidar_points_m` 和完整命中数 `lidar_point_count`，预览最多 768 点 |

点云是单帧传感器局部米制坐标：X 向前、Y 向右、Z 向上；响应新增 `lidar_coordinate_frame`、`lidar_units`、水平/垂直采样数和 FOV。坐标变换只包含扫描原点与旋转，不包含云台外形缩放；PLY 与预览使用同一坐标系。2026-10-19 修正此前模型缩放混入米制坐标的问题，旧版本导出的 PLY 应重新采集，历史文件不自动改写。

当前默认 48×12、30°×8°、10 Hz，是有限视场单帧射线扫描，朝向天空或小目标落在射线间隙时可为零回波；不代表完整场景建图。无回波时导出返回 capture_failed。当前可见无人机使用仅查询碰撞供激光测距，隐藏型号和 AirSim 物理代理不参与激光回波；AirSim 仍独占动力学。

状态包括仿真时间（秒）、位置（UE 世界坐标厘米）、云台角（度）、转速（RPM）、模式、分辨率、调色板、FOV、跟踪来源及最后导出路径。`active_sensor` 表示云台工作传感器，`available_sensors` 是本构建真实可用的传感器列表；当前为 visible、infrared、lidar。AirSim 接入后还包括 `flight_backend`、`dynamics_connected`、`dynamics_actor`、`lidar_enabled`、`lidar_hits`、`lidar_rays`、`lidar_nearest_m` 和 `lidar_last_export_path`。Project AirSim 后端拥有唯一飞行控制权，`flight.set_input` 会返回 `invalid_argument` 并提示使用 AirSim runner。跟踪来源是 UE ground truth；模拟热强度不等于物理温度。

地图扩展：状态新增 `scene_id` 与 `pending_scene`。`sim.load_scene` 校验 Config/WISEYE/Scenes/<id>.json 的版本、参数、地图存在性和 prepared 标记，返回当前状态及 pending_scene；0.75 秒后执行 OpenLevel。接受不等于加载完成；客户端必须重连并验证新的 scene_id。桌面清除旧截图并重试连接最多 90 秒，未知/非法 ID 不切换。运行时读取配置仅允许当前地图对应项，避免把其他地图的实验坐标应用到当前地图。

每客户端请求上限 64 KiB，图像响应上限 16 MiB；当前实现最多24个客户端（包含各路持久网关和预览连接），每 tick 每客户端读取最多8192字节、处理最多8条消息。控制网络操作非阻塞；`camera.stream_frame` 返回异步GPU缓存帧，本机预览每源20Hz上限、最多一个在途请求，重复帧号/仿真时间不刷新显示新鲜度；源缓存超2秒拒绝返回。仿真时间是采集时的仿真时钟，不能直接与本机墙钟相减当作绝对延迟。手动输入超过350ms未更新归零。

Project AirSim runner 另在 `127.0.0.1:50052` 提供同版本 JSON Lines 飞控服务。状态应用名为 `WISEYE AirSim Control`，包括 `paused`、`flight_mode`、`position_ned_m`、`route_loops`、`velocity_mps`、`command_active` 和 `last_error`。命令包括 `flight.takeoff`、`flight.hover`、`flight.land`、`flight.set_mode` 和 `flight.set_input`。手动输入使用机体系归一化前/右/上/偏航量；桌面按住方向按钮时每 120 ms 更新。AirSim 引擎时钟不支持全局 SimPause，因此 `sim.pause` 表示取消当前航线并悬停保持。

按需 PNG 依然保留；持续图像通过 CH1/CH2 RTSP/H.264 发布，详见 `docs/RTSP.md`。当前 JPEG 桥接的帧号和仿真时间已提供，但 RTSP 与点云/AirSim 的精确统一时钟仍待实现。

## UE 本地键盘与飞控会话

runner 每 100 ms 查询内部 `flight.get_local_control`，读取有界一次性命令队列、按住/松开的机体系输入及 play_session_id。UE 的 M/空格/Home 分别生成模式、暂停和复位请求，WASD/↑↓/Q/E 提供按住输入。桌面和 UE 都由同一个 runner 驱动 AirSim；runner 以 `flight.sync_state`（mode、paused）回写显示状态，避免双控制源。桌面不再提前向 UE 乐观写入飞控状态。

50052 状态新增 yaw_deg、manual_command_count、last_manual_input，供操控验证。零输入先执行 0.6 秒零速度制动，再使用 Hover 定点保持（旧制动不能抢占新运动），暂停拒绝新运动指令；模式切换可恢复手动操控。检测 UE listener 关闭或 Play 会话更换后重建飞控；临时渲染阻塞且 listener 仍在时等待恢复，避免误重载世界。场景配置按 UE 当前 scene_id 选择。

## V2 增量接口（2026-10-19）

继续使用 version=1；旧命令兼容，当前实际单架。新状态含 `run_id`、`drone_id=uav-01`、`gimbal_id=ptz-01`，飞控状态同样带 `run_id`；客户端不能使用旧会话的飞控状态。

| command | payload / 行为 |
|---|---|
| observer.set_mode | mode: overview / free / gimbal / follow；只改变 UE 观察相机，不修改光电传感器输出 |
| input.set_mode | mode: observer / drone / gimbal；切换清零 UE 旧输入；桌面切换同时向飞控清零 |
| sensor.lidar.set_parameters | 全部提供 horizontal_fov_deg、vertical_fov_deg（0.1–60）、range_m（1–1000）、scan_rate_hz（0.05–10）；全部校验通过后一次应用 |

状态回显 `observer_mode`、`input_mode`、`observer_position_cm`（自由相机创建后）、`initial_drone_position_cm`、`gimbal_position_cm`、`pitch_min_deg/max_deg` 与 `lidar_horizontal_fov_deg/vertical_fov_deg/range_m/scan_rate_hz`。

`streams.CH1/CH2` 含 `frame_seq`、`completed_frames`（成功发布到缓存的新捕获帧数）、`readback_queued_ue_monotonic_s` 与 `cache_age_ms`。最后两者是 UE 进程时钟下的 readback 排队时间/年龄，不是硬件曝光时间、跨进程统一时钟或端到端延迟；新会话计数重置。不能将 RTSP 重复输出帧计作 UE 新帧。

飞控 `flight_status=ready/active`：日常启动为 ready，拒绝自动航线/非零手动速度，需先 flight.takeoff；active 表示离开待命，不能替代真实着陆/飞行阶段遥测。起飞成功重新建立航线，降落成功返回 ready。`--loops N` 自动回归启动保留。

初始布置 JSON：version=1、scene_id、gimbal_location_cm、flight_origin_cm。路径为 Config/WISEYE/Layouts/<scene>.json，UE 世界坐标厘米，Z 向上；AirSim 加载前转换为 NED 米 [X/100,Y/100,-Z/100]。布局在场景加载时生效，当前不支持通过远程控制端上传布局；桌面保存的是本机文件。

## 表面放置接口与命名预设（2026-10-19）

以下命令仍在 50051，返回完整状态；只查询初始位置草稿，不移动 Actor、不写配置文件。

| command | payload |
|---|---|
| placement.begin | scene_id: 当前场景；device_id: 运行清单中任意无人机/云台ID；request_token: 非空字符串≤64 字符；clearance_cm: 0–1000 |
| placement.snap | 同 begin，并提供 position_cm: 有限三元数组、每轴绝对值≤1e7；按该 X/Y 在 Z±100000 cm 范围垂直查询 |
| placement.cancel | scene_id、request_token；token 必须匹配当前请求，否则拒绝 |

状态 `placement`：active、has_result、preview_supported、preview_visible、preview_position_cm、preview_size_cm（仅预览可见时）、device_id、request_token、sequence、position_cm、surface_cm、error。任务由全局根实例管理，查询任意云台状态均返回同一取点任务。`position_cm`仅has_result=true时有效；surface_cm在交互取点时是悬停射线命中点。sequence随新请求/完成/超时递增，在新run_id中重置。消费者必须同时匹配run_id、scene_id、device_id和request_token，不能应用旧会话、旧设备或旧请求的结果。地面查询接受WorldStatic与City Sample的FastGeoSurrogateActor，排除其他动态对象及所有自身设备；云台按所选实例底座最低点补偿。

交互取点自动切到独立自由相机和 observer 输入；左键完成、右键取消，45 秒超时。只有 WorldStatic 碰撞且法线 Z≥0.25 的表面有效；忽略整套云台、无人机、动力学代理。云台 position_cm 的 Z 以当前 PTZRecovered 外壳最低点校正到表面，另加 clearance_cm；无人机为表面高度 + clearance_cm，物理接触高度仍由 AirSim 决定。预览使用实际设备网格副本（当前尺寸/姿态），坐标与确认共用底座/高度校正，preview_position_cm仅preview_visible时有效，preview_size_cm是当前世界包围盒，不是名义标定尺寸。副本无碰撞/阴影/自定义深度，纳入VIS/IR HiddenActors，因此对应训练深度/GT也排除；操作观察OBS可见模型。未命中有效表面或鼠标离开视口则隐藏，确认/取消销毁。旧后端可能无预览字段。取消、未命中或非法参数不会把坐标写入桌面草稿。

命名预设保存在 Config/WISEYE/Layouts/Presets/<scene>/<preset_id>.json，包含基础布局字段及 name、preset_id。preset_id 为安全 ASCII ID，name 可中文；无远程文件上传接口。读取命名预设与更新命名预设都不替换当前生效的 <scene>.json，需显式保存初始布置并重载。
# 2026-11-02 增补：事件相机

云台 `sensors.event` 为独立640×480 HDR事件采样，默认停用。`sensor.set_enabled`、`sensor.configure`新增`event`；`sensor.event.get_packet`按每订阅者游标返回`[x,y,t_us,p]`原始数据，`sensor.event.capture`保存最新有界窗口。时间为UE world time插值，非硬件微秒精度。参数、完整报文、缓冲上限、丢弃计数及会话处理见 [事件相机与天气说明](EVENT_CAMERA_WEATHER_20261102.md)。天气新增`rain_active_streaks`、`rain_model`，不能再仅用旧`rain_active_particles>0`判断下雨。
