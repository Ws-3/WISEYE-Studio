# 云台外部控制接口

2026-10-30新增：gimbal.point_at按VIS/IR实际光心指向UE世界厘米目标，严格scene_id/run_id与俯仰限位；SDK新增point_at_world、point_at_geodetic、coordinates(ref)。设备面板显示角度、FOV、米制距离和自定义仿真经纬高。详见[GIMBAL_COORDINATES.md](GIMBAL_COORDINATES.md)，旧独立包不支持；不是实机GNSS或真实地图配准。

标准库 SDK：`integrations/gimbal_client.py`；示例：`python -m examples.gimbal_control --device ptz-02`。当前 UE 服务仅监听本机 `127.0.0.1:50051`，传输为 TCP UTF-8 JSON Lines，version=1。每条命令必须带 request_id，payload.device_id 指向云台实例。无需另开端口或安装 Python 依赖。

```python
from integrations.gimbal_client import GimbalClient

ptz = GimbalClient('ptz-02')
print(ptz.capabilities())
ptz.take_control()                 # 明确把全局输入模式切为云台
ptz.set_angles(yaw_deg=20, pitch_deg=5)
ptz.track('uav-01')                # 仿真真值跟踪
ptz.hold()                        # 关闭跟踪、保持方向
```

速度控制：`set_velocity(yaw_deg_s=10, pitch_deg_s=0)`，应每 100–200 ms 发送一次，结束必须在 finally 中调用 `stop()`。最后一条非零输入超过 300 ms 自动失效。SDK 是同步调用，GUI/算法应放在自己的工作线程，不能阻塞界面。

| 命令 | payload / 行为 |
|---|---|
| gimbal.get_capabilities | 返回 gimbal_capabilities：角度单位 degree、yaw ±180、该实例 pitch_min/pitch_max、yaw_rate 30°/s、pitch_rate 20°/s、watchdog 300 ms |
| gimbal.set_angles | yaw_deg、pitch_deg；相对于设备底座转轴，正俯仰朝上；越界拒绝，自动退出跟踪 |
| gimbal.set_input | yaw、pitch 为 [-1,1] 比例；需要 input.set_mode(mode=gimbal)，有非零输入时退出跟踪 |
| gimbal.set_target | drone_id；只修改此云台的跟踪目标 |
| gimbal.set_tracking | enabled 布尔；启用为真值指向，尚非图像算法闭环 |
| sim.get_state | 当前云台状态、传感器设置和设备清单 |

外部视觉算法以后可消费 RTSP 检测目标，再通过 SDK 提交角度/速度。硬件串口、厂商 SDK、网络鉴权和多控制端独占仲裁尚未实现；此接口当前控制仿真云台。不要让桌面摇杆和外部程序同时持续发送速度输入。

## 2026-10-21 接口核查

已核对 UE 命令分发、按 device_id 路由、客户端请求封包、SDK 与桌面输入清理：角度控制、比例速度、目标选择、跟踪开关、状态/能力查询均有实现。桌面新增“停止并保持方向”：先清理摇杆/键盘并发送零速度，再关闭跟踪。SDK stop() 只归零速度，hold() 还会关闭跟踪；不要把 stop() 当作关闭跟踪。

数据与接口页新增文档、SDK、示例入口。SDK 当前速度换算与服务端固定30/20度每秒一致；未来不同型号能力变化时应同步改为能力查询驱动。全局输入模式仍共享，不提供多客户端独占控制。

本轮39项单元测试通过，新增4项SDK协议测试覆盖实例路由、回执ID不匹配、服务端拒绝、保持命令顺序；Qt按钮接线检查通过。UE 50051/飞控50052未监听，仅8554监听，未进行本轮实际转动、限位和300ms超时实机联调。上述超时行为本轮为源码核查，历史运行证据见RUNTIME_OPTIMIZATION.md。
