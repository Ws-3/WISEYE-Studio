# 本机控制协议 v1

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

状态 `placement`：active、has_result、device_id、request_token、sequence、position_cm、surface_cm、error。任务由全局根实例管理，查询任意云台状态均返回同一取点任务。`position_cm`仅has_result=true时有效；surface_cm在交互取点时是悬停射线命中点。sequence随新请求/完成/超时递增，在新run_id中重置。消费者必须同时匹配run_id、scene_id、device_id和request_token，不能应用旧会话、旧设备或旧请求的结果。地面查询接受WorldStatic与City Sample的FastGeoSurrogateActor，排除其他动态对象及所有自身设备；云台按所选实例底座最低点补偿。

交互取点自动切到独立自由相机和 observer 输入；左键完成、右键取消，45 秒超时。只有 WorldStatic 碰撞且法线 Z≥0.25 的表面有效；忽略整套云台、无人机、动力学代理。云台 position_cm 的 Z 以当前 PTZRecovered 外壳最低点校正到表面，另加 clearance_cm；无人机为表面高度 + clearance_cm，物理接触高度仍由 AirSim 决定。标记由 HUD 绘制，不加入 SceneCapture 图像。取消、未命中或非法参数不会把坐标写入桌面草稿。

命名预设保存在 Config/WISEYE/Layouts/Presets/<scene>/<preset_id>.json，包含基础布局字段及 name、preset_id。preset_id 为安全 ASCII ID，name 可中文；无远程文件上传接口。读取命名预设与更新命名预设都不替换当前生效的 <scene>.json，需显式保存初始布置并重载。
