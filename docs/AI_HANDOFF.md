# WISEYE 当前交接（2026-10-19）

## 2026-10-19：跨电脑安装与 GitHub 发布

- 当前工作目录已从 GitHub ZIP 安全接回 `origin/main` 历史，可正常 `git pull` / `git push`。仓库完整安装入口为 `docs/INSTALLATION.md`，目录职责和不应提交的本机产物见 `docs/FILE_STRUCTURE.md`。
- 新电脑必须先创建仓库内 `.venv`、安装 FFmpeg/MediaMTX，再运行 `scripts/Setup-ProjectAirSim.ps1`。`test.uproject` 已启用 ProjectAirSim/Drone 插件，直接打开而未完成插件安装会提示缺模块。
- Git 中保留 WISEYE 源码、地图、外部 Actor、Avata/Mavic/PTZ 模型与资产、插件描述文件和 Project AirSim 固定补丁。Project AirSim 源码/构建产物、MediaMTX、UE 缓存、日志和本机环境均由脚本重建，不上传。
- 推荐完整启动顺序：`Start-ProjectAirSim.cmd`，等待 UE 自动进入 Play 和无人机起飞，再运行 `Start-Desktop.cmd` 并连接 UE。

## 2026-10-19：统一实时传感器查看与云台工作传感器

- 桌面中心区现在统一选择 CH1 可见光、CH2 红外和 LIDAR 激光点云。CH1/CH2 继续走 RTSP/H.264，LIDAR 使用 50051 有界实时点云预览；切到点云会停止当前 RTSP 解码，切回图像会恢复所选通道。
- “当前查看的数据源”和“光电云台工作传感器”是两个独立状态。新命令 `sensor.set_active` 支持 visible、infrared、lidar；状态新增 `active_sensor` 与 `available_sensors`。保存按钮会按工作传感器导出 PNG 或 PLY。
- 无人机型号仍可在 Mavic 3 / Avata 间切换，只有外观改变，Project AirSim 继续拥有唯一动力学与位姿控制权。
- 深度相机、事件相机和雷达仍未生成真实数据；界面只说明扩展顺序，不提供伪通道。新增传感器时先扩充 UE 生产端和状态列表，再由桌面动态接入。
- 验证完成：UE `testEditor` Development 编译成功，协议 4 项和桌面结构检查通过；真实 UE/AirSim/RTSP/桌面自动联调 14 项通过，包含 CH1、CH2、LIDAR 实时显示、三种工作传感器选择与 PLY 导出、Mavic 3/Avata 往返切换。摘要证据在 `docs/evidence/realtime_multisensor_validation.json`，本机完整状态在 `runtime/desktop_live_validation.json`。
- 后续流畅度修复：UE 编辑器后台节流已关闭（原约 3 FPS）；`WiseEyeStreaming` 使用异步 GPU readback 和多帧 JPEG 编码流水线；RTSP 网关为每通道保持 UE 长连接。输出标准为 CH1 30 FPS、CH2 25 FPS，实测 6 秒解码 181/151 帧。当前场景两路同时运行约 20 FPS 独立新渲染帧，达到完全独立 1080p30 需后续 GPU H.264 硬件编码。验证证据为 `docs/evidence/realtime_streaming_and_manual_control.json`。
- 桌面手动控制新增 W/S 前后、A/D 左右、R/F 升降、Q/E 转向，也保留按住式按钮。必须先选择“手动飞行”；松键发送零输入。`Start-ProjectAirSim.ps1` 会清理仅属于 WISEYE 的旧 runner，避免 UE 重启后 50052 返回 `Object closed`。

## 2026-10-17：CH1/CH2 RTSP、AirSim 操作按钮与无人机外观切换

- 桌面相机页已由按需快照升级为 RTSP 实时显示：CH1=`visible` 1920×1080，CH2=`infrared` 640×512。两路同时发布，界面切换不改变 UE 传感器状态。快照功能保留。
- 链路为 UE `camera.stream_frame` JPEG + `integrations/rtsp/rtsp_gateway.py` + FFmpeg H.264 + MediaMTX 8554 + 桌面 FFmpeg 解码线程。`scripts/Setup-RTSP.ps1` 下载并校验 MediaMTX 1.21.2；二进制被 gitignore。`Start-ProjectAirSim.ps1` 自动启动 RTSP。
- 当前两路目标为各 2 FPS，已真实解码验证 CH1 H.264 1920×1080 与 CH2 H.264 640×512，桌面两通道都收到 960×540 适配帧。限制是同步 GPU readback；下一步用异步 GPU readback 达到 CH1 15 FPS/CH2 25 FPS。
- AirSim 50052 新增 `flight.takeoff` / `flight.hover` / `flight.land`，桌面有独立按钮；原手动九键和自动航线保留。三个命令单元测试通过，真实服务悬停/恢复通过。
- 无人机外观可在 Mavic 3 与 Avata 之间切换。Avata FBX 已导入 `/Game/WISEYE/DroneModels/Avata/Avata_black`；切换只更换可见外观，不改变 AirSim 位姿与动力学。跨电脑可用 `scripts/Import-DroneModels.ps1` 从 `Models/Avata_black.fbx` 重建。
- 完整产品/流程设计在 `docs/SYSTEM_UX_DESIGN.md`，RTSP 运行与算法接口在 `docs/RTSP.md`。
- 验证：UE `testEditor` Development 编译成功；AirSim 3 项测试、协议 4 项、场景 7 项通过；真实 UE/AirSim/RTSP/UI 端到端通过。证据为 `runtime/rtsp_integration_validation.json`、`runtime/desktop_rtsp_validation.json` 和 `runtime/desktop_rtsp_preview.png`（runtime 仅本地）。

## 2026-10-17：Project AirSim 已进入 WISEYE（最新优先级）

- 用户要求 AirSim 负责无人机空气动力学，并在地面光电云台增加激光传感器。已实现并完成真实 UE 联调，不再只是独立评估。
- `AWiseEyeGameMode` 继承 `AProjectAirSimGameMode`；Project AirSim 在 WISEYE 地图内启动 8989/8990 服务。`AWiseEyeDemo` 默认 `FlightBackend=ProjectAirSim`，自动寻找 `Drone1`，现有无人机整机关闭碰撞后跟随 AirSim 位姿，避免双后端写姿态和重复碰撞。旧 Kinematic 后端保留。
- 云台 `LidarMount` 挂在 Camera/PitchPivot 层级下，默认 48×12、10 Hz、30°×8°、300 m；`sensor.lidar.capture` 输出局部米制 PLY。bottom2/camera/ptz 原轴向逻辑未改变。
- 本地插件入口在 `ue5/WISEYE/Plugins/{ProjectAirSim,Drone}`；Source/SimLibs/Content 是本机目录联接，不上传。另一台电脑必须先运行 `scripts/Setup-ProjectAirSim.ps1`，再用 `Start-ProjectAirSim.cmd`。详见 `docs/PROJECTAIRSIM_INTEGRATION.md`。
- 为嵌入自定义 GameMode，Project AirSim 补丁增加 GameMode 头文件解耦、外部插件着色器真实路径解析、UnrealSimLoader 场景 Actor 指针初始化和 GIS Actor 安全清理；补丁文件已包含此前飞行完成修复及本轮适配。未初始化的 `GISRenderer` 曾在 DefaultScene 热重载时造成访问冲突，修复后连续两次重载通过。不要只应用旧五文件补丁描述。
- 真实验证：testEditor 构建成功；AirSim 起飞和一圈路径完成；WISEYE 返回 `dynamics_connected=true`、576 条激光射线/8 命中并导出 PLY。100 个遥测样本 X/Y/Z 跨度 1183.852/760.774/733.216 cm。证据 `docs/evidence/projectairsim_wiseye_integration.json`。
- 桌面飞控桥接已完成：runner 在 50052 提供单一 AirSim 控制面，支持自动/手动、机体系速度输入、悬停暂停、继续和按物理航迹复位；桌面有九键按住控制、自动重连和 AirSim 状态。UE 50051 仍拒绝 AirSim 模式下的旧 `flight.set_input`，避免双控制源。
- 桌面新增“激光点云”实时俯视页，50051 的 `sensor.lidar.get_points` 返回最近局部米制点，预览上限 768。向下扫描实测 576/576 点；UE 增量构建、原 11 项测试、新 2 项飞控测试和 UI 启动检查通过。
- `Start-ProjectAirSim` 改为自动进入 Play。不要改回 `-ExecutePythonScript`，该参数执行完会触发 `QUIT_EDITOR`；当前使用 `-ExecCmds="py ..."`。场景服务等待为 60 秒，避免 UE 刚开放端口时加载超时。
- 下一步优先给相机、点云、飞行状态加入统一仿真时间戳和帧编号，再实现持续图像通道与任务航线编辑。AirSim 引擎时钟不支持全局 SimPause，桌面“暂停”实际是 SimpleFlight 悬停保持。

## 2026-10-16：Project AirSim 独立评估（最新优先级）

- 用户当前要求先测试 AirSim；若需要改上游源码，先评估商量。不要直接替换 WISEYE 的现有飞行/云台后端。
- 独立目录 D:/Projects/ProjectAirSim-Evaluation，上游 iamaisim/ProjectAirSim commit 62229cd7c77ad31da7bc8aba8dd6303c564d8ba2；自己的 Python .venv。用户已同意修复独立副本，分支 `wiseye/flight-completion-fix` 有五个 staged 源码修改；因仓库未配置作者身份，没有伪造身份提交。
- 本机 UE 5.8.3 实测 Release 仿真库 188/188、BlocksEditor 47/47 编译通过。BlocksMap 可运行，客户端连接及 RGB/深度消息接收通过。无需已知的 UE 5.8 编译适配。
- 已修复 MoveOnPath 完成判定和成功 Land 后的 SimpleFlight 状态同步。最终严格回归连续两次通过；最新结果：悬停漂移 0.00905 m、三米航点误差 0.49276 m、短航点/超时/恢复/指令替换/降落状态均符合预期，RGB/深度 872/871 条。Release C++ 单元测试 391/391 通过。
- 脚本 scripts/Test-ProjectAirSimBuild.ps1 与 Test-ProjectAirSimFlight.py；完整复现和限制见 docs/PROJECTAIRSIM_EVALUATION.md。补丁 third_party/patches/projectairsim-simpleflight-completion.patch；证据 docs/evidence/projectairsim_flight_fixed.json。
- 下一步：设计 WISEYE 可切换的 AirSim 运动后端和坐标/时钟适配，先接现有 Blocks 验证位姿驱动云台，再考虑把插件放入 WISEYE 工程。PX4、雷达/激光雷达输出、多地图飞行尚未验证。本轮没有上传 GitHub。

## 2026-10-15：多地图与设备装配修复（历史工作副本）

- 当时当前工作目录 D:/Projects/WISEYE-Studio 是 GitHub ZIP 解压目录；该状态已由本文顶部的 2026-10-19 发布记录取代。UE D:/Projects/UE_5.8（5.8.3）。不要再使用旧 Repository 或 Scene 路径。
- 已建立本机 .venv（Python 3.13.9 / PySide6 6.11.0），main.py 提前加载系统 ICU 以处理 conda 同名 DLL 冲突；用户确认桌面可运行。未修改 conda WISEYE 训练环境。
- 用户要求多地图、标准包导入、通过 UE 接入 Fab/社区资源；已新增 core/scenes.py、scene_dialog.py、桌面选择/自动重连、WiseEyeScenes.cpp 和 UE 场景准备/导出脚本。使用方法与边界见 SCENES.md。当前预置 original 和 test_range。
- 原地图没有重建；standard_rig.json 提取标准装配，新地图安装相同设备。共享控制/双模态代码继续使用；后续修改装配需迁移已生成地图。
- **用户发现新地图云台分离，已定位并修复：UE Python Rotator 的位置参数是 roll/pitch/yaw，原脚本误按 C++ pitch/yaw/roll 传入。** ue_transform 现在使用命名参数；所有子 Actor 和网格由标定局部变换恢复。不要再写 Rotator(*[pitch,yaw,roll])。
- 新地图设备增加锁定的整体选择组；保持组选取开启。test_range 已修复保存，保留用户将云台根移动到 Z=53.0585 cm 的位置，并同步场景配置。修复前地图备份位于 Saved/WISEYE/Backups，仅本地保留。
- 修复入口 repair_scene_assembly.repair_current_scene() 只接受生成场景；不能用于原始 WISEYE-test。完整编辑器内 verify_scene_assembly.verify() 验证局部装配、整机平移旋转、轴向及选择单个零件选中全组。已保存地图与全新临时地图均通过，证据 assembly_validation.json / new_assembly_validation.json。
- 较早相机截图曾被误提取的 /Engine/EditorMeshes/MatineeCam_SM 辅助网格遮挡；提取器已排除编辑器网格，测试地图中误生成的辅助网格已移除。
- C++ 构建通过；真实切换/自动重连/双模态截图结果见 docs/evidence/scenes_validation.json。这些只证明已验证项，不代表物理成像或视觉闭环已完成。
- 最终验证：11 项 Python 单元测试通过；真实 original→test_range→original→test_range 切换及 8 张双模态快照通过，已目视确认修复后测试场图像能看到无人机。标准包 UE 导出、163 个共享依赖校验、隔离目录导入和逐文件哈希一致性通过，见 scene_pack_validation.json。已修复地图与全新临时生成装配均通过完整编辑器回归。
- 标准 ZIP v1 支持普通地图自身命名空间资产 + 带 SHA256 的已安装共享依赖；不执行代码、不覆盖同 ID。World Partition 和插件复杂地图走 UE 完整迁移 + install_current_scene，不宣称任意 Fab ZIP 一键可用；第三方大地图尚未实测。
- 下一步：针对用户选定的真实社区场景验证接入、安装位置与遮挡，再推进持续图像通道和算法闭环。此轮功能是编辑器工作流，未实现独立打包程序热加载地图。

## 2026-10-14 的历史交接

先读根 README、AGENTS 和长期计划，检查 git status。工程为本仓库 ue5/WISEYE/test.uproject，地图 /Game/WISEYE-test，唯一 UE 源码 ue5/WISEYE/Source/test；桌面源码 apps/desktop_app 与 core。保留 test 模块和 testEditor 目标。

## 已完成与运行

- 本机成功运行昨天完整工程；UE 5.8.3、VS 2022/MSVC 14.44.35229、SDK 10.0.26100.0、Intel Arc B580。经用户授权升级 VC++ x64 至 14.50.35719，安装提示重启，未自动重启，实际运行通过。
- 无人机跨度 60 cm、云台高 40 cm；自动航线/键盘手动飞行、四组旋翼、云台跟踪/保持。bottom 固定、bottom2 水平转、camera 与 ptz 共用俯仰。
- 可见光 1920×1080、IR 640×512，双 Capture/Render Target，共光心/水平 FOV、不同垂直 FOV。IR 以部件模拟热强度生成，有白热/黑热及遮挡。
- PySide6 桌面主窗口、本机 JSON Lines TCP 控制桥、状态轮询、暂停/继续/复位、飞行模式、跟踪、旋翼、模态/调色板/FOV、原生 PNG 快照显示。
- 开始时 pull --ff-only，双击 Start-WISEYE.cmd，UE 点击播放，再 Start-Desktop.cmd 连接 127.0.0.1:50051。完整配置见 DESKTOP.md；协议见 PROTOCOL.md；人工上传下载见 GIT_WORKFLOW.md。

本机仓库 E:/Projects/WISEYE-Studio，UE E:/Programs/UE_5.8；机器路径在忽略的 scripts/engine-root.local.txt。桌面 .venv 复用已安装 PySide6 6.11.0 的 Python 3.14.6；未更改既有 conda WISEYE 训练环境。新机器自行创建 venv 并安装 requirements。

## 验收与证据

C++ 构建成功，真实 PIE 40 秒/79 样本验证通过；14 项控制检查及保存关闭重开后的布局验证通过。双模态尺寸、灰度、不透明 alpha、参数响应、白黑反转、遮挡通过；测试遮挡物已清理并保存。
桌面真实 UE 集成 10 项通过，包括连接/轮询、时间暂停恢复、跟踪/旋翼、两种原生快照/FOV、TCP 分段合并及错误、断开重连、超时期间 GUI 保持响应；协议单元测试 4 项通过。证据在 docs/evidence，原始实验输出保留于 ue5/WISEYE/Saved/WISEYE。

## 边界与后续

2026-10-14 当时是真值指向和运动学演示，无 YOLO、动力学/碰撞、物理红外测温或打包程序。当时桌面图像仅为按需快照；这一限制已被本文顶部的 CH1/CH2 RTSP 更新取代。
下一步优先做持续图像通道与帧时间/性能监测，再接单帧视觉检测和闭环。保留已确认场景；旧 setup_scene.py/restore_ptz.py 恢复旧尺度，不要直接运行覆盖当前布局。

World Partition 外部 Actor/对象必须与源码一起提交，不上传 Saved/logs/runtime/.venv 或凭据。用户 papers 保持原状。今天已明确授权整理、上传 GitHub 和删除不必要备份日志；具体上传和清理结果见 WORKLOG_2026-10-14.md。历史阶段状态以本文件当前描述为准。

功能提交 a221349 已上传并核对远端，正式桌面启动入口通过。清理被自动审批检查拒绝，临时文件尚未删除；已提供人工 Clean-Temporary.ps1，详见今日工作记录。
