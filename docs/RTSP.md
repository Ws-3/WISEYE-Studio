# WISEYE 实时图像通道

## 通道约定

| 通道 | 传感器 | RTSP 地址 | 当前源分辨率 |
| --- | --- | --- | --- |
| CH1 | 可见光 | `rtsp://127.0.0.1:8554/CH1` | 1920×1080 |
| CH2 | 红外 | `rtsp://127.0.0.1:8554/CH2` | 640×512 |

通道名、端口、帧率和 JPEG 桥接质量在 `configs/app.json` 中配置。界面切换 CH1/CH2 只切换显示源；两路依然同时发布，也不会修改 UE 的传感器当前模式。

## 首次安装与启动

1. 确保 `ffmpeg -version` 可以运行。
2. 运行 `scripts/Setup-RTSP.ps1`。脚本下载锁定的 MediaMTX 1.21.2 并核对官方 SHA256；二进制文件不提交 Git。
3. 双击 `Start-ProjectAirSim.cmd`。它会启动 MediaMTX、双通道网关、UE 和 AirSim。
4. 运行 `Start-Desktop.cmd`，连接 UE，然后选择 CH1 或 CH2。

也可单独运行 `scripts/Start-RTSP.ps1`。网关在 UE 未就绪时会等待并自动重试。

## 后续算法接口

视频流是 H.264/RTSP，检测、录像和远程显示可以独立订阅。UE 桥接还有专供本机网关使用的 `camera.stream_frame`，返回通道、帧号、仿真时间、尺寸和 JPEG。算法不应绕过 RTSP 高频调用该命令。

## 当前性能边界

当前使用异步 GPU readback、多帧编码流水线和每通道持久 UE 连接。RTSP 输出帧率为 CH1 可见光 30 FPS、CH2 红外 25 FPS；2026-10-19 实测 6 秒分别解码 181/151 帧。当前复杂场景在本机同时生成两路时约有 20 FPS 独立新渲染帧，其余输出帧沿用最近缓存帧，因此协议帧率正确且控制台明显更流畅，但若要求每一帧都是独立渲染的 1080p 新帧，下一步需要 UE 达到稳定 30 FPS，并改用 GPU H.264 硬件编码以移除 JPEG/Base64 中间层。

UE 编辑器默认在控制台位于前台时降低后台 PIE 帧率。本项目在 `AWiseEyeDemo::BeginPlay` 注册编辑器节流豁免，否则实测会被限制到约 3 FPS。
