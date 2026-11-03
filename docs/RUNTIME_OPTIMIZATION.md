# 运行、转速与性能更新（2026-10-21）

2026-10-28：本机日常统一双击根目录 **`Start-WISEYE-Studio.vbs`**，一次启动当前城市预览、飞控和桌面。下方保留的分步 PowerShell 命令面向开发；在仓库 PowerShell 执行，遇执行策略限制加 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File`。已启动UE时仅重开桌面用 `scripts/Start-Desktop.ps1 -Connect`。详见[当前使用指南](USER_GUIDE.md)。

## 启动与操作

- 日常双击根目录 `Start-WISEYE-Studio.vbs`，一次启动城市预览、飞控与桌面，后台命令行隐藏。开发分步入口在 `scripts`；根目录旧五个CMD/VBS已删除。已有UE时仅运行 `scripts/Start-Desktop.ps1 -Connect` 重开桌面。
- 界面启动 UE、场景准备、FFmpeg 编解码和 RTSP 服务均使用隐藏后台进程。已打开同工程 UE 时复用，避免重复编辑器；如果当前没有播放，仍需在 UE 点击播放。
- 顶部选择画质优先、均衡、节能；默认每次 PIE 均衡，本轮保持均衡待命。原始场景当前实际配置为用户已有的 **3 UAV + 2 PTZ**，没有删除第三架或改写 Fleets 布局。

## 实际仿真电机转速

AirSim `robot_info.rotor_info` 主题中的四个电机 speed 单位 rad/s，转换 `RPM = abs(speed) × 60 / (2π)`，按 FL/FR/RL/RR 路由。UE 每个电机独立积分相位 `RPM × 6 × dt`；Mavic 校准转轴和 Avata 按轴心位置映射，保留相邻反转和高速模糊盘，减少显示采样混叠。

遥测超过 1–1.5 秒失效后不继续伪造转速。AirSim 模式的电机启停由起飞、降落控制，桌面原旋翼开关改成只读四电机 RPM；O 不再伪造电机动作。运动学模式保留动画开关。旋翼视觉不是通过几乎不可见的“慢转”冒充实际速度。

发现原飞控完成降落后仍解锁、怠速约 3504 RPM；现在只在真实 land 任务成功且没有被新任务替代后 disarm，解除成功才标记地面待命。本轮 Mavic 和 Avata 悬停约 4931 RPM，降落后四电机均为 0。它们依旧共享当前四旋翼动力学配置（max-rpm 6396.667），**并非大疆实机电机/桨叶参数标定**。

## 卡顿识别与限制

UE 状态增加 `tick_seq`；桌面分别监视网络响应、Tick 是否推进、启用传感器缓存年龄。持续约 3 秒无进展时显示异常、清空持续操控并拦截新的起飞/航线开始/非零移动输入。暂停飞行是物理悬停，Tick 仍正常推进，不按无人机是否位移判断卡死。

JPEG 缓存超过 2 秒拒绝作为新图像源；异步 GPU 读回最多每通道 2 项，等待超过 3 秒退出，场景退出时取消，防止无限等待积累。读回本身不在游戏线程阻塞。连接成功和 RTSP 正在收帧不再单独作为仿真健康依据。

这次处理了已定位的额外捕获、读回无界等待和缺少进度检测。**没有复现并证明排除所有偶发 UE 卡死原因，也没有完成长时间压力验收。** 真正失去响应时不会强制杀编辑器或自动重建在飞场景；需要保留现场日志再排查。

## 捕获预算与实测

关闭 WISEYE 不使用的原生 AirSim Chase/Down 相机（采用独立 robot_wiseye_fastphysics.jsonc，不修改原评估机器人）。云台从每个 UE 帧捕获改成定时主动 CaptureScene；VIS 始终输出 1920×1080、IR 始终 640×512，OBS 960×540。

| 档位 | UE 帧率上限 | VIS / IR / OBS 捕获上限 Hz | 画面取舍 |
|---|---:|---:|---|
| 画质优先 | 60 | 30 / 25 / 15 | 完整动态间接光、反射，允许捕获光追 |
| 均衡（默认） | 45 | 20 / 15 / 10 | 降低阴影和反射开销，传感器使用屏幕空间反射 |
| 节能 | 30 | 10 / 10 / 8 | 再降低阴影并关闭动态间接光，光照观感会变化 |

以下为 Intel Arc B580、原始沙漠场景、3 UAV + 2 PTZ、编辑器 PIE 的短时采样。每档预热 4 秒，再读取 8 次间隔 1 秒的 UE 3D 引擎计数器；帧率来自实际 Tick 和新 JPEG 完成计数，不是重复帧的 RTSP 输出帧率。

| 档位 | GPU 3D 中位数 | UE Tick Hz | CH1 / CH2 新帧 Hz |
|---|---:|---:|---:|
| 画质优先 | 92.8% | 20.1 | 7.4 / 7.8 |
| 均衡 | 89.7% | 34.8 | 12.5 / 13.0 |
| 节能 | 70.6% | 30.0 | 10.0 / 9.9 |

改动前同机基线 3D 中位数约 93.8%。编辑器窗口、视角、飞行、光照和场景都影响占用，这些是短时参考，不能当作严格固定负载 A/B、帧率保证或整机 GPU 总占用。GPU 接近满载在实时渲染中可能正常；低负载需求可切节能。帧率档位是上限，负载高时达不到。

RTSP 为保持通道时间节奏可能重复最新图像；客户端短时接收/解码 FPS 也可能受缓冲影响。源新帧率、缓存年龄与网络连接必须分别判断。GPU 硬编码、端到端 P95 延迟、多设备长时稳定和城市性能仍待验收。

## 证据与复现

- `scripts/Start-WISEYE.ps1 -BuildOnly`：UE 5.8.3 testEditor 构建成功，日志 `logs/runtime_performance_build.log`。
- AirSim Python 环境执行 `python -m unittest discover -s tests -p "test_*.py" -q`：35 项通过。
- 桌面 Python 环境执行 `python -m tests.verify_runtime_live`：6 项真实联调通过，含两型号分别起降、遥测驱动视觉、SDK/看门狗、双云台原始分辨率和桌面停滞提示/拦截。GUI 停滞通过注入旧 Tick 时间验证，没有人为卡死真实 UE。
- `python -m tests.benchmark_runtime`：三个档位的 GPU/Tick/新帧短采样；结束恢复原档位。
- `python -m tests.verify_fleet_hotkeys_live`：新版O行为及T/I按实例路由共3项真实按键验证通过。隐藏VBS桌面入口及最终Qt三机待命/三路画面检查通过，证据 runtime_ui_final_20261021.json、runtime_controls_final_20261021.png。
- 原始证据 `docs/evidence/runtime_controls_20261021.json/png`、`runtime_performance_20261021.json`、`gpu_baseline_20261021.json`。

云台接口见 [GIMBAL_INTERFACE.md](GIMBAL_INTERFACE.md)。City Sample 已选定，按用户要求稍后下载，详见 [CITY_SAMPLE_SETUP.md](CITY_SAMPLE_SETUP.md)。
