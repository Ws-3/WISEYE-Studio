# 中英文界面与固定翼巡航

最新更新：固定翼已接入 JSBSim 六自由度（参考参数未标定）；事件相机默认启动即采样；可见光新增模糊、噪声、对比和饱和度。重启桌面及UE使用，旧运行包未更新。详 [JSBSIM_CAMERA_20261105.md](JSBSIM_CAMERA_20261105.md)。下方早期运动学说明为历史记录。

后续更新优先：[实时设备编辑、机头轴修复与事件默认开启](LIVE_DEVICES_20261105.md)。旧版下文重载和尺寸轴说明已被覆盖：现在机长80cm、翼展约62.05cm，机头+Y；设备实时编辑不需重载。

当前源码目录：`E:\Projects\WISEYE`。此前的 `WISEYE-PortableBuild` 已改名；F 盘迁移仍暂缓。双击根目录 `Start-WISEYE-Studio.vbs` 打开当前源码界面，再在界面中启动仿真。旧独立包不会自动获得本批功能，本次没有重新打包或推送。

## 中英文切换

仿真端进入 **资源设置 → 窗口与语言 → 界面语言**，选择 `简体中文` 或 `English`。训练端右上方也提供相同选择。

切换立即应用并保存，下次启动恢复；同一电脑上已打开的另一端会自动同步。保留场景、连接、驾驶对象、传感器参数和窗口实例，不为切换语言重建界面或发控制命令。界面标签、按钮、参数、状态、提示及点云绘制共用 `configs/locales/en_US.json`。未知技术诊断保留服务端原文，用户输入、名称、地址、ID、协议和保存数据不翻译。便携包通过原有 QtSettings 目录保存偏好，源码版通过 QSettings 本机偏好保存。

实现为 `core/localization.py` 和 `apps/desktop_app/language.py`。高频文本在 setter 写入时翻译，定期刷新负责动态创建的菜单、标签、树和跨进程偏好同步。切换时阻断 Qt 展示控件信号，业务依然依赖 currentData / device_id；新增控件不应靠翻译后的文字判断动作。可编辑文字不参与翻译。

## 使用固定翼

1. 在设备管理中新增无人机，或编辑已有无人机的型号，选择 **固定翼（80 cm）**。
2. 调整初始位置与朝向，在已连接场景开启实时应用即可生效，无需重载；跨类型切换只需被编辑的无人机停止，保存初始配置可单独操作。
3. 在工作台选择该无人机作为驾驶对象，点击 **开始巡航**。它会从初始位置上方 30 m 进行空中初始化，以 12 m/s 开始巡航；请选开阔空域并留出建筑高度。
4. 默认盘旋半径约 80 m。点击 **接管手动驾驶** 后，W/S 临时调节速度，A/D 或 Q/E 转向，R/F 爬升下降。松手恢复中性输入，飞机仍向前飞，不悬停；输入超过 0.4 s 未更新也回到中性。
5. **盘旋等待**切回持续盘旋；航线编辑器支持上传再执行，速度 5–15 m/s，默认航点跨度 200 m，转弯与爬升受限。不要用四旋翼 5 m 小方框作为固定翼航线。
6. **停止巡航**停止运动预览并保持当前位置，状态回到待开始巡航；不执行物理降落。关闭本程序时由原有所属进程清理流程停止预览。

日常 Fleet 的型号、设备数量和位置保持原样；新增固定翼需按上述操作保存。本次实跑使用独立测试数据，不把测试的高空起点和第二架 Avata 写入日常场景。

## 模型、尺寸和接口

原始 FBX：`Models/FixedwingUAV_gray.fbx`，贴图在同名 `.fbm` 目录。引擎资产位于 `/Game/WISEYE/DroneModels/Fixedwing/`；幂等导入脚本 `ue5/scripts/import_fixedwing.py` 不覆盖 Mavic/Avata。

用户指定机长 80 cm。UE 原始包围尺寸约 155.12 × 199.99 × 33.38 cm（X 翼展、Y 机长，机头+Y），整体等比缩放并居中，保留机身/机翼比例。尺寸配置位于 `ue5/WISEYE/Config/WISEYE/device_dimensions.json` 的 fixedwing：`length_cm` 与 `uniform_scale_multiplier`；已存在 UserData 配置优先，修改后重启仿真。翼展、高度不是独立真实测量数据。

`model_id=fixedwing`，`physics=kinematic_fixedwing`。原生 `WiseEyeFixedwing.cpp` 独立计算姿态和位置；Project AirSim World 不为它生成四旋翼物理体。既有 50052 控制服务通过 FixedwingController 转发 `flight.fixedwing` 到 50051，按 device_id 与 run_id 隔离。多旋翼保持原有 FastPhysics / SimpleFlight。

原始原生命令 `flight.fixedwing` 需要 device_id、当前 run_id、action，可用 start/stop/loiter/mode/input/pause/resume/reset/route/state；普通应用优先沿用 50052 的 flight.takeoff/hover/land、flight.set_mode/input、sim.pause/resume/reset、route.upload/start/stop。固定翼对这些命令提供对应巡航语义。设备清单 fixedwing 字段包含实际长度、翼展、巡航速度、姿态、航线进度及错误。

VIS/IR、独立光心、云台跟踪、放置预览和训练 GT 复用现有采集链；导出型号与文件命名包含 Fixedwing。Cook 已覆盖 DroneModels，但要发布新软件仍需重新 Cook 与冻结两端。

## 范围与限制

这是用于成像、跟踪和采集的受约束运动学预览。不是固定翼空气动力学或飞控验证，不模拟失速、风场、舵面、真实发动机、地面起飞或降落；螺旋桨目前为 FBX 静态几何，不伪造四电机 RPM。

转弯由约 30° 滚转角限制约束，爬升上限 2 m/s；异常长帧限制推进步长。前进线段做遮挡检测，遇障碍停止并报告，不做自动绕障，也不构成整机体积碰撞认证。窄航点或急转航线可能无法按预想经过；需要大间距航线。大城市、多固定翼和长时飞行未做完整性能验收。

## 验证记录

- Editor Development 编译通过，固定翼独立资产真实导入，本轮修正后实际机长约 80.00 cm、翼展约 62.05 cm。
- 117 核心测试、28 项相关 Qt 检查通过；界面切换可逆，数据 ID、输入和连接保留。
- 已完成纯固定翼与固定翼 + Avata 的城市实跑：巡航、手动转向/爬升、航线上传执行、云台跟踪、VIS/IR、双路 fixedwing GT 和保存、观察跟随、停止静止、旧 run 拒绝及关闭清理。
- 混用时 Avata 实际起飞降落并待命；运行中切换英文保持连接。
- 最终证据在 docs/evidence/language-fixedwing/，源码开发工具与实机场景仍使用 E 盘本地依赖。
