# 夜空、雨效与事件相机

源码位于 `F:\WISEYE-Studio`，源码预览构建位于 `E:\Projects\WISEYE-IR-Work`。这次改变需要重开桌面和源码仿真；旧版运行包不会自动更新。

## 使用

场景画面工具栏的“场景”菜单可设置时间、雨雾及云量。夜间额外压低雾的自发散射亮度，避免天空仍呈白天灰蓝色；保留城市暗部、窗灯。雨使用世界空间网格中的细雨线，有距离衰减和深度遮挡，避免近镜头大水滴。雨量为零时销毁雨体积；缺少新材质时兼容旧粒子，状态会说明实际模型。

云台传感器新增“事件相机”标签页和独立采集开关，默认停用。开启后，通过工作台“添加画面”选择 `ptz-01 · 事件相机`；正事件青色，负事件红色。支持水平视场、采样上限、正负对数阈值、像素不应期及独立光心/视轴偏移。可见光与红外均关闭时仍可独立工作；关闭事件相机释放其采集组件、渲染目标和CPU缓冲。

640×480 独立 HDR 场景采集 → 对数亮度阈值穿越 → `(x,y,t_us,p)` 事件。默认30Hz采样上限，受UE实际帧率、GPU读回负载影响；120Hz是设置上限，不保证实际达到。微秒时间戳由相邻帧插值，**不是硬件微秒响应**。当前没有加入硬件带宽、漏电噪声、阈值不一致或真实传感器标定；不以普通视频帧差冒充物理事件传感器。

预览只显示近期事件极性，优先最新数据，允许跳过；“保存最近事件窗口”保存有界JSON快照，不是连续无损录制。连续导出示例：

```powershell
cd F:\WISEYE-Studio
& .\builds\python-env\Scripts\python.exe -m examples.event_camera_stream --output E:\events.jsonl --seconds 10
```

先在界面启用事件相机。输出文件必须不存在；示例不改传感器开关，遇到停用或换图会停止并报错。

## 原始接口

本机 JSON Lines RPC，控制端口默认50051，每个订阅者维护自己的游标：

```json
{"version":1,"request_id":"evt-1","command":"sensor.event.get_packet","payload":{"device_id":"ptz-01","after_sequence":0,"max_events":5000,"latest":false}}
```

回复 `payload.events` 每行 `[x,y,t_us,p]`，`p` 为±1；`next_cursor`用于下一次请求。时间原点是当前UE运行的world time，单位微秒，与悬停时可能不推进的旧 `simulation_time_s` 不同。保留 `run_id`、`generation`、`world_time_s` 做会话与配置边界识别；切图重置游标，不混合会话。无事件也是正常结果。

每相机环形缓冲65536事件，每回复最多20000事件，每像素每采样最多8次阈值穿越、每采样最多20000事件。达到单帧上限采用确定性蓄水池采样保留全图事件，避免只保留图像顶部；仍有损。`skipped_events`表示读取游标落后/最新预览跳过，`truncated_events`表示生成上限丢弃，`dropped_sample_frames`表示读回缺帧；三者不同，采集方都应记录。后两者同时包含在状态和原始包中；包的`sensor_state`保留当时采集参数。参数变化会清空基线、缓冲并增加generation。当前接口仅本机，不提供伪造RTSP事件流。

`sensor.set_enabled`接受 `sensor:"event"`；`sensor.configure`须提供 `enabled,fov_deg,sample_hz,positive_threshold,negative_threshold,refractory_us`，安装偏移可选。`sensor.event.capture`保存最新窗口并返回 `event_last_export_path`。

## 边界

雨目前是视觉近似，深度遮挡不等于完整雨滴碰撞、室内降雨阻挡、积水或气象物理；不含镜头附着水滴。夜间是工程光照控制，尚无月光、真实照度与相机低照标定。本轮实测结果在完成后记入下方。

## 验证

Editor原生编译、事件数学测试、110核心、38项Qt检查通过。原生测试覆盖阈值累积、正负极性、时间排序、不应期、非有限信号保持、截断与全图采样；Qt包含停止时RPC返回、QObject已销毁的退出回归。

真实 `city → city_large → city` 完成：夜间天空/上方区域灰度均值，小城市152.20→0.002，大城市101.78→11.86（后者区域包含楼宇，不是纯天空）；同视角截图人工检查确认天空变暗、窗灯与楼宇暗部仍保留。雨量0.7时约6296/6299条细雨线、旧粒子0，关雨后体积0；未做雨滴碰撞/全城降雨物理验收。

两地图均验证：VIS/IR关闭时事件独立采样约30Hz，产生合法有序事件并保存JSON/JSONL，两个游标独立，非法阈值不生效，关事件后capture_active=false且sample_frames停止增加，控制连接保留。大城市转动阶段存在明显事件截断和环形缓冲跳过；不能以该结果宣称连续无损或真实硬件精度。

证据 `docs/evidence/event-weather-20261102/final/report.json` 及对应截图。该轮发现退出线程向已销毁QObject发信号，已修复；后续新增蓄水池限流及每包参数/丢弃计数，经再次Editor编译、数学测试和全新小城市实测通过，证据 `smoke/report.json`；smoke日志无线程异常。最终测试所属进程退出，正常preview-data 11份JSON前后SHA256一致，未修改日常设备放置。未起飞、未测多设备/硬件对标/长期运行，未重打包或推送GitHub。
