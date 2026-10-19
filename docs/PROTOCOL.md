# 本机控制协议 v1

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
| camera.stream_frame | channel: CH1 / CH2，quality: [25,95]；返回 JPEG Base64、帧号和仿真时间，专供本机 RTSP 网关 |
| sensor.lidar.set_enabled | enabled: boolean |
| sensor.lidar.capture | 空对象；立即扫描并导出传感器局部坐标、米制 PLY |
| sensor.lidar.get_points | 空对象；返回最近扫描的 `lidar_points_m` 和完整命中数 `lidar_point_count`，预览最多 768 点 |

状态包括仿真时间（秒）、位置（UE 世界坐标厘米）、云台角（度）、转速（RPM）、模式、分辨率、调色板、FOV、跟踪来源及最后导出路径。`active_sensor` 表示云台工作传感器，`available_sensors` 是本构建真实可用的传感器列表；当前为 visible、infrared、lidar。AirSim 接入后还包括 `flight_backend`、`dynamics_connected`、`dynamics_actor`、`lidar_enabled`、`lidar_hits`、`lidar_rays`、`lidar_nearest_m` 和 `lidar_last_export_path`。Project AirSim 后端拥有唯一飞行控制权，`flight.set_input` 会返回 `invalid_argument` 并提示使用 AirSim runner。跟踪来源是 UE ground truth；模拟热强度不等于物理温度。

地图扩展：状态新增 `scene_id` 与 `pending_scene`。`sim.load_scene` 校验 Config/WISEYE/Scenes/<id>.json 的版本、参数、地图存在性和 prepared 标记，返回当前状态及 pending_scene；0.75 秒后执行 OpenLevel。接受不等于加载完成；客户端必须重连并验证新的 scene_id。桌面清除旧截图并重试连接最多 90 秒，未知/非法 ID 不切换。运行时读取配置仅允许当前地图对应项，避免把其他地图的实验坐标应用到当前地图。

每客户端请求上限 64 KiB，图像响应上限 16 MiB；最多 8 个客户端（包含 CH1、CH2 持久网关连接），每 tick 每客户端读取最多 8192 字节、处理最多 8 条消息。控制网络操作非阻塞；`camera.stream_frame` 返回异步 GPU 缓存帧，只应由有界频率的本机网关调用。手动输入超过 350 ms 未更新归零。

Project AirSim runner 另在 `127.0.0.1:50052` 提供同版本 JSON Lines 飞控服务。状态应用名为 `WISEYE AirSim Control`，包括 `paused`、`flight_mode`、`position_ned_m`、`route_loops`、`velocity_mps`、`command_active` 和 `last_error`。命令包括 `flight.takeoff`、`flight.hover`、`flight.land`、`flight.set_mode` 和 `flight.set_input`。手动输入使用机体系归一化前/右/上/偏航量；桌面按住方向按钮时每 120 ms 更新。AirSim 引擎时钟不支持全局 SimPause，因此 `sim.pause` 表示取消当前航线并悬停保持。

按需 PNG 依然保留；持续图像通过 CH1/CH2 RTSP/H.264 发布，详见 `docs/RTSP.md`。当前 JPEG 桥接的帧号和仿真时间已提供，但 RTSP 与点云/AirSim 的精确统一时钟仍待实现。
