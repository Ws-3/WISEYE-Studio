# WISEYE 工作规则

2026-10-27运行状态/环境：工作台RuntimePanel读取运行主机CPU/RAM、实际RHI显卡/专用容量/UE使用与预算、Windows PDH本UE最忙GPU引擎、实测Tick FPS，未知不填0、持续3个新样本才提示。environment.configure/reset为全局运行参数，独立太阳光路/天空强度、指数高度雾、复用AirSim雨效并覆盖云台/观察相机；可恢复场景默认，非天文/天气动力学/红外温度模型。Editor构建、真实city图像/接口及53核心+15Qt通过，见ENVIRONMENT_AND_PERFORMANCE与evidence/environment-20261027。新入口Start-SimulationPreview.ps1复用红外预览流程；旧ZIP尚未重Cook，F源码/E临时构建，用户Fleet不改。

2026-10-26红外试验：已新增独立M_IR_Experimental（原Minimal保留），增强/原始A/B、模糊/对比/背景层次与逐帧噪声，协议和按云台UI已接。内置E构建Editor成功、真实city ptz02对照通过，51核心+13Qt通过；不是新的Shipping包，旧ZIP不含本改动。试用scripts/Start-InfraredPreview.ps1，详见docs/INFRARED_EXPERIMENT.md。未做整城温度材质/AGC/真实数据校准/GPU耗时或新飞行验收。用户Fleet未改，F主源码/E临时构建，勿将旧打包或试验观感当成物理红外已完成。

2026-10-23最新：Shipping独立运行内测包已生成并回传F，ZIP约16.864GiB，F盘SHA256复核通过；三个场景起降/原尺寸图像/云台/点云和city中文路径验收通过，47核心+9Qt通过。源码主目录F:\WISEYE-Studio，用户授权内置盘临时构建在E:\Projects\WISEYE-BuildWorkspace，E旧工程保留。先读AI_HANDOFF最新节、docs/RELEASE_BUILD.md；不要重复从P0迁移。Shipping启动靠WiseEyeScene模块清单选图，勿退回仅位置URL；运行写用户目录，保留AirSim cooked-game补丁及原GC/碰撞/RPM补丁。在线更新/安装器/干净Windows/30分钟/4+4仍未完成，不能宣称已交付。

2026-10-22最新打包：当前工作目录F:\WISEYE-Studio，E原工程保留；Game Development已通过，完整Cook/发布包尚未完成。F盘在高负载时出现disk153/UASPStor129与读取阻塞，已停止构建，待用户处理连接或选择内置盘暂存。先读docs/RELEASE_BUILD.md和AI_HANDOFF最新节；不要把中断的builds/desktop当成成品，不在异常存储上盲目重启高负载。新增发布路径层和AirSim cooked-game补丁，详细限制见交接。

2026-10-22最新：建筑粘墙已修复，独立projectairsim-wall-contact.patch保留碰撞当轮预测速度/姿态并加1mm间隙，Setup脚本幂等应用，需重建SimLibs和UE插件。原生19+核心44及真实三轮建筑碰撞脱离/返航降落、稳定四RPM=0通过；Fleet按用户当前1机2云台保留，见COLLISION_RECOVERY与AI_HANDOFF首节。

2026-10-22当前最新：city用户配置为1机2云台，数量/位置以现有文件为准。全部实例坐标、俯视图和表面取点按Fleet动态刷新，UI保存合并改过位置；UE按FindDevice查询、全局placement状态对所有云台一致、FastGeo道路可取点。无人机在系统和UE均为R上升/F下降，观察QE和云台箭头保留。构建及44核心/5新Qt/4预览回归、真实取点/RF映射通过，见AI_HANDOFF首节；Qt测试tests.verify_multi_placement用桌面环境。

2026-10-22 最新：传感器显示延迟已修复，工作台用UEPreviewClient直连最新原尺寸JPEG缓存；RTSP保留外部接口、源帧去重与禁补帧，勿退回桌面H264往返。单窗口120秒VIS中位206/P95271ms；点云100ms有界查询。44核心+4项Qt预览回归通过，后者用桌面环境 `python -m unittest tests.verify_video_preview`，与AirSim核心环境分开。详见docs/SENSOR_LATENCY_REPORT.md和AI_HANDOFF首节；外部RTSP延迟未最终验收。

2026-10-22 优先状态：真实 Small City 已接入，prepared=true；构建、44单元、5组城市实时验收及保存重播通过，见 docs/CITY_SAMPLE_SETUP.md。当前磁盘 original Fleet 核查为1机1云台；设备数量始终以用户现有文件为准，禁止依据下方历史数量覆盖。引擎目录现为5.8.4，本轮未执行升级。

先读 `docs/AI_HANDOFF.md` 和 `WISEYE_ProjectPlan.md`，检查 git status，按用户当前需求工作。

- 唯一 UE 源码在 `ue5/WISEYE/Source/`。不要编辑旧电脑外部 Scene 工程或创建重复源码副本。
- 使用 `scripts/Start-WISEYE.ps1 -EngineRoot <实际UE目录>`。UE 5.8.3 已验证，首次构建需要 VS 2022 C++ 工具链。历史 D 盘路径不是新电脑依赖。
- 保留模块 test、构建目标 testEditor 和 `/Script/test` 类路径，不擅自升级引擎。
- bottom 固定；bottom2 只水平转；camera 和 ptz 一起水平及俯仰转；光学组件跟随 PitchPivot。
- 导入模型使用独立目录，避免覆盖通用 Mesh 名称。恢复云台在 `/Game/WISEYE/PTZRecovered`。
- World Partition 的 Content/__ExternalActors__、__ExternalObjects__ 必须提交。编辑器修改对象要 modify 并保存，不能仅改内存。
- 不覆盖未提交变更、不删除用户模型/权重/实验数据；不上传凭据、Saved 日志或缓存。
- 操作 UE 前确认工程与关卡，不强制结束有未保存数据的编辑器。
- 只报告实际执行的验证，历史测试不代表新电脑测试通过；真值跟随不等于视觉闭环。
- 完成任务后更新交接与计划，记录修改、运行方式、验证、限制及下一步。

- 桌面源码在 apps/desktop_app 和 core；运行先读 docs/INSTALLATION.md 与 docs/DESKTOP.md，控制协议见 docs/PROTOCOL.md。网络/GUI 应保持非阻塞，断连不能保留有效状态。CH1/CH2 已接入 RTSP 实时流，LIDAR 使用有界点云预览；帧率与限制以 docs/RTSP.md 的实测结果为准。

- 设备外形尺寸以 Config/WISEYE/device_dimensions.json 为准：Mavic 3 机身不含桨叶，Avata 含护圈，云台总高 80 cm。不要再执行旧 configure_controls.py 将其改回 60/40 cm。修改预置地图后同步 standard_rig.json；验证按键必须从稳定悬停测有方向的实际运动，不能把自动航线残余位移算为手动成功。

- 多实例配置在 Config/WISEYE/Fleets；运行时复制装配，不往原地图重复添加 Actor。控制/状态/记录必须按 device_id/sensor_id 隔离；驾驶对象与云台对象分开。当前原始场景2机2云台，默认实例保留；实例变更保存重载后生效，每类最多4，4+4性能未验收。
- ProjectAirSim 必须应用基础补丁和 projectairsim-ue58-gc-completion.patch（Setup-ProjectAirSim.ps1 自动处理）。只等 GLastGCFrame 变化会在 GC 开始时过早创建第二架，导致 UE 断言。验证多机用 tests/verify_fleet_live.py、verify_fleet_shapes_live.py、verify_fleet_hotkeys_live.py 和 verify_fleet_geometry_live.py；真实双机完毕后降落并恢复配置。

- 旋翼现在按 AirSim rotor_info 实际四电机转速驱动；O 在 AirSim 下不伪造启停，起降后真实 disarm。不要回退成固定RPM。当前 Fleets 是用户3机2云台，测试不能擅自恢复历史2+2。新回归 tests/verify_runtime_live.py 与 benchmark_runtime.py，详见 docs/RUNTIME_OPTIMIZATION.md。City Sample 已选定但用户明确稍后下载；prepared=false，禁止生成方块替代城市场景。
- V3 桌面入口 workbench_v3.py，画面由 sensor_workspace.py 按固定设备/传感器管理；选择属性不接管驾驶，切控制对象不换画面。参数 sensor_forms.py 按设备+请求ID确认；不得退回按命令名清空全部待确认参数。航线上传和执行分开。新检查 verify_ui_redesign_live.py、verify_ui_redesign_offline.py、verify_ui_flight_live.py，详情 docs/UI_REDESIGN_IMPLEMENTATION.md；旧GUI测试的CH1字典键/控件索引不适用于新工作区。
