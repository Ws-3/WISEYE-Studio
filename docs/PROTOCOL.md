# 本机控制协议 v1

UE 的 AWiseEyeDemo 在 BeginPlay 监听 `127.0.0.1:50051`，EndPlay 关闭连接。UTF-8 JSON Lines，每条消息以换行结束；TCP 分段和多条合并均支持。请求示例：

```json
{"version":1,"request_id":"demo-1","command":"camera.set_mode","payload":{"mode":"infrared"}}
```

响应包含 `version`、同一 `request_id`、`status` 和 `payload`；成功 status 为 `ok`，失败为 `error`，另带 error 对象（code、message）。错误码包括 bad_request、invalid_payload、invalid_argument、unknown_command、capture_failed。多数成功响应 payload 为当前状态；capture 另带 frame_path。

| command | payload |
|---|---|
| sim.ping / sim.get_state / sim.pause / sim.resume / sim.reset | 空对象 |
| gimbal.set_tracking / rotors.set_enabled | enabled: boolean |
| gimbal.set_angles | yaw_deg: [-180,180]，pitch_deg: 关卡配置的俯仰范围；执行后保持方向 |
| flight.set_mode | mode: auto / manual |
| flight.set_input | forward、right、up、yaw: [-1,1]，仅手动模式 |
| camera.set_mode | mode: visible / infrared |
| camera.set_palette | palette: white_hot / black_hot |
| camera.set_fov | fov_deg: [5,120]，水平视场角 |
| camera.capture | 空对象；导出当前模式原生 PNG |

状态包括仿真时间（秒）、位置（UE 世界坐标厘米）、云台角（度）、转速（RPM）、模式、分辨率、调色板、FOV、跟踪来源及最后导出路径。跟踪来源是 UE ground truth；模拟热强度不等于物理温度。

每客户端消息上限 64 KiB、待发送上限 256 KiB；最多 4 个客户端，每 tick 每客户端读取最多 8192 字节、处理最多 8 条消息。网络操作非阻塞，UE 对象操作在游戏线程执行。手动输入超过 350 ms 未更新归零。桌面轮询 500 ms、请求超时 5 s、最多 32 条等待响应；断连清除陈旧状态。

图像通过同机文件路径读取并校验工程 Saved/WISEYE 范围及原生尺寸，未实现图像二进制传输、跨机文件服务或实时流。PNG 为最后完成渲染帧，状态时间为请求时刻，精确帧时间同步待实现。
