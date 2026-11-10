# WISEYE 工作规则

## v1.1.0 已发布（2026-11-10）

v1.1.0 已公开发布为 GitHub 最新发行版：https://github.com/Ws-3/WISEYE-Studio/releases/tag/v1.1.0 。源码及主要 README/安装/使用/训练/打包/依赖文档已推送 main；插件 ZIP 554789718 字节（约529 MiB）与 SHA256 附件均上传成功，GitHub 服务端 ZIP digest 与本地 SHA256 一致，公开校验文件下载读回通过。标签指向 119e8272b8f3fa44911ffe4e5d540e70bf11a0ad；后续 main 只补文档和发布证据，不移动已发布标签。发布前171项回归通过。完整城市包本地保留，未上传；未发表论文保留本地。发布记录 docs/evidence/distribution-20261110/github-v1.1.0.json。下方日期记录中的“未上传”仅为当时状态。

## 2026-11-10：插件与完整包交付完成

源码插件与完整 Shipping 运行包均已完成。39 项回归通过；独立无城市宿主 Editor 实跑与 Shipping 编译通过；主项目及冻结运行包大小城市均通过双光、云台、点云和起降验证；仿真/训练冻结界面启动通过。完整目录 releases/20261110-164135-City-Shipping（约27.34 GiB），传输包 builds/distributions/WISEYE-Full-20261110.zip；源码 SDK 为 builds/distributions/WISEYE-Plugin-20261110.zip。完整包采用 DX12/SM6。第三方 M_Crowd_Head_v2 Cook 有 SRV 超限材质回退，干净电脑和自定义宿主完整打包未验收；未上传 GitHub。唯一源码/UE工程在 E:/Projects/WISEYE；旧外部工程已移至 builds/legacy-* 隔离，未物理清空。Scene/CitySample 仍供城市源码编译使用，完整运行包不依赖它。详 docs/DISTRIBUTION_IMPLEMENTATION_20261110.md。

## 2026-11-09 最新：传感器、景深与后台窗口验收

源码E:/Projects/WISEYE、预览E:/Projects/WISEYE-IR-Work已同步。云台/每机可见光有auto/manual/infinity/off、对焦距离m、光圈、实际焦点与薄透镜景深估计，默认PSF .95px；航拍独立vis_blur_px。修正MID不能以MID为父材质，使用根UMaterial；最终实跑模糊/景深均改变源画面且材质编译/运行错误0。人车热标签改16/17，与无人机>=32分离，不套无人机提亮曲线；车辆IR近景人工确认可见且不再全白描边，非温度/发动机物理模型。航拍双光左右网格，UE默认隐藏、右上单按钮sim.window.set_visible可显隐，放置自动显示；保持后台渲染，非零GPU。

完整扫描sensor.lidar.get_scan新增真实扫描时刻/序号/无回波-1，点云仍理想矩形角网格首碰撞回波；core/sensor_formats.py转换PointCloud2（Y反号）和EventCD（极性0/1），不等于厂商驱动/RAW编码。事件仍约15Hz帧驱动插值，不是微秒硬件时序。35 Python/Qt与原生热像/事件不变量、Editor通过；最终builds/imaging-realism/sensors-20261109-final实际起飞、昼夜8图、航拍PSF/云台DOF、隐藏持续渲染、576点测距一致、4000事件转换、降落退出通过。证据docs/evidence/sensors-20261109，详docs/SENSOR_UPGRADE_20261109.md。先前verified等目录有MID父材质问题已撤销整体通过，最终只认final；车辆IR单独帧保留来源，不当GT。已有Mass CustomData ensure未修；未大城/Shipping/打包/推送。LoS可选碰撞射线不是像素可见性，早期近景被楼遮挡不作为车辆可见证据。


## 2026-11-07 最新：双光成像改进已实跑

源码E:/Projects/WISEYE，预览E:/Projects/WISEYE-IR-Work已同步并Editor重编译。道路Facade热代理增加世界坐标固定/材质差异、降低统一热值，航拍独立昼夜背景曲线；云台原曲线及目标/天空不变。可见光去固定灰底、改弱读出噪声及夜间增益，原有参数保留；独立双镜头不退回RGB转灰度。21Python+原生热数学通过；最终builds/imaging-realism/verified小城真实起飞/悬停昼夜8图/降落/所属进程退出通过，材质回退0。道路日间190→178、std .57→4.36；夜37→166、std1.03→9.14，单机位显示域非物理定标。docs/evidence/imaging-realism-20261107含原图/报告。先读[docs/IMAGING_REALISM_20261107.md](docs/IMAGING_REALISM_20261107.md)。中间after/final曾因HLSL fixed宏导致可见光默认材质，已修正fixedPattern并撤销中间验收，不能复用其图。既有Mass CustomData ensure仍见，未修；未大城/Shipping/推送，旧独立包未更新。

## 2026-11-07 最新：红外真实/仿真基准初版

源码仍E:/Projects/WISEYE；F盘已重新可读，用户数据F:/DATASET_UAV_BICE/YOLO_UAV_BICE只读取样，不修改。新增官方HIT-UAV昼夜各16帧+本机Halmstad/CESE各16帧，固定树/文件哈希、手工铺装ROI、显示灰度/截断/框对比/JSON/CSV/联系表。共66图（另含Nov7航拍与Oct31历史云台各1），仿真路面中位191/标准差0.57，对所选真实日间171.5/18.28；无近白截断，偏亮且过于平坦，非温度定标/真实性评分。12回归通过；未启动UE、未修改渲染/打包/推送。当前云台目标、夜间仿真及完整夜间地面实拍仍未补齐，Anti-UAV410/DroneVehicle仅已查官方入口，示意图不计评测。先读[docs/INFRARED_REAL_SIM_BASELINE.md](docs/INFRARED_REAL_SIM_BASELINE.md)，脚本scripts/infrared_reference_data.py、infrared_baseline.py，配置configs/infrared_real_sim_baseline.json。外部/本机原图及联系表保留忽略builds目录，不冒充许可已核实或完整论文测试集。

## 2026-11-07 最新：航拍红外、采集与数据集管理

用户选择本轮完善采集/标注/数据集管理，目标含地面与其他无人机，不接训练启动。每机独立640×512 AERIAL_IR/HDR热读回/6cm基线+局部0.2°视轴差、IR电源/独立采样/FOV/极性/模糊/噪声，按需分配/空闲释放；VIS保持1920×1080，工作台VIS/IR/双光切换。JPEG绑定捕获tick姿态/环境历史；运行时Mass模板车辆与已知Crowd VAT人群整组件热代理，非温度/发动机热模型。训练发现设备、切换来源，云台保留同刻GT；航拍schema4原图pending_manual、不伪造GT/同步对/空负标签，数据集校验/人工拖框0无人机1行人2车辆/明确负样本、独立run防泄漏导出、后台可取消。138核心/29Qt/最终32训练检查/Editor/隔离小城实际飞行双光采集-审核-切回GT-降落通过，源进程退出；Mass出现非致命CustomData ensure未声称修复，见详单。源码E:/Projects/WISEYE，预览E:/Projects/WISEYE-IR-Work；未大城/重包推送。详[docs/AERIAL_IR_TRAINING_20261107.md](docs/AERIAL_IR_TRAINING_20261107.md)。

## 2026-11-05 最新：预载、被动实例与轻量加载界面

启动/换图新增真实阶段2D加载覆盖层，可后台加载/查看失败；300×8局部光带80ms，隐藏即停，无额外3D视角、无假百分比；等待首帧及3个独立稳定样本。原生异步预载并保留实体配置、预构建模板，直接覆盖Crowd/Traffic显示模板高/中LOD为实例，关闭保留低精度Actor，首次更新分散、人群实例可见600m。纠正先前仅全局LOD不能阻止近处完整人物的问题。Shader编译计数纳入就绪。31相关Qt/指标回归+Editor通过；隔离小城300行驶/300停放/600行人实际生成和移动、航拍扫视通过，14样本FPS中位29.99/最低14.55，仍有瞬时停顿，非A/B或稳定30保证。所属进程退出，未起飞；大城未重测。中间超时已定位头发/完整动画临时载入并修正模板，不作通过证据。详 [docs/LOADING_POPULATION_20261105.md](docs/LOADING_POPULATION_20261105.md)。需重启桌面/UE，未重包推送，原始城市资产不写盘。

## 2026-11-05 最新：方向键、窗口及人群首轮优化

观测隐藏相机、航拍方向键有界持续/松键失焦停；正式入口最大化，场景设置/F11全屏。固定翼中心线改模型盒扫掠，保护停止后明确返回起点，不是假恢复；编译通过但未主动撞墙，非完整接触/坠机物理。被动行人近处取消骨骼Actor改原VAT实例，容量增600行驶/600停放/1200行人；车辆首次载入卡顿未完全解决。22Qt及隔离小城60/60/120预算、机载取图/朝向通过，单次快照28.7/30FPS非A/B保证，所属进程退出。红外本轮只答复可行性，机载IR尚未实现。详 [docs/KEYBOARD_COLLISION_POPULATION_20261105.md](docs/KEYBOARD_COLLISION_POPULATION_20261105.md)，未重包推送。

## 2026-11-05 最新：任务式工作台UI

工作台新增云台观测/无人机航拍入口，航拍编辑器嵌入右侧，主画面默认单航拍、设备栏自动收起，可选场景参考；切回恢复原观测布局，临时航拍不覆盖持久化观测源。起降与明确接管常驻，驾驶/相机分别标ID；参数折叠，场景设置统一天气/人车/画质/诊断，航拍隐藏无关云台参数，删重复入口。21Qt界面+4原预览最终通过，隔离UE实际连续转向/俯仰/图像变化/驾驶不切换通过，所属会话退出，未起飞；1600/1100布局回放检查。一次组合进程中断及较早预览时序失败不作通过证据，最终日志已归档。只改桌面，无需编译UE，重启桌面；训练端不改、未重包/推送。详 [docs/MISSION_UI_20261105.md](docs/MISSION_UI_20261105.md)。

## 2026-11-05 最新：人群骨骼设置与实时航拍朝向

DefaultEngine.ini补齐CitySample要求的16位骨骼索引、无限骨骼影响、SkinCache默认0、ExperimentalChunking=1，源码/预览同步，实际UE日志读入，首次重建缓存。运行评估与告警共用资源准备状态，加载中不累计持续低帧率，完成后仍如实评估。航拍新增可长按四方向按钮及默认实时朝向应用，80ms合并、一个在途+最新待发，旧ACK保护草稿、关闭/断连/换机取消发送。20项相关测试及隔离小城uav-02实际俯仰−30→−75/长按偏航10°/图像变化/驾驶不切换通过，所属会话退出，未起飞。资源就绪/增加15Hz航拍单次快照25.4/18.1FPS，不能宣称性能升到30。详 [docs/AERIAL_AIM_PERFORMANCE_20261105.md](docs/AERIAL_AIM_PERFORMANCE_20261105.md)；未重包/推送。

## 2026-11-05 最新：机载航拍与自动人车

仿真端新增每机独立AERIAL可见光相机（前/斜/下视、稳定/刚性、FOV/采样率、按需释放、原始PNG），场景菜单及设备树入口；航拍注册Mass观察者。原生CitySample交通与人群按启用/密度实时管理，默认25%，预算上限300行驶+300停放+600行人，轿车预设，不逐个操纵。新增prepare_observation_population.py恢复WISEYE大小城副本生成器、ZoneGraph与对应停车/路口资产；原始CitySample不改。场景默认独立保存Observation/<scene>.json，训练端与地面2D GT尚未接入。129核心/23Qt和Editor通过；小城实际起降/三视角/密度切换及独立第二相机、空闲释放通过，修复大城缺生成配置后，大城人车移动/取图→小城密度与相机默认恢复通过，所属进程已退出。源码E:/Projects/WISEYE，预览构建E:/Projects/WISEYE-IR-Work；未重包/推送。详 [docs/AERIAL_POPULATION_20261105.md](docs/AERIAL_POPULATION_20261105.md)。

## 2026-11-05 最新：JSBSim、事件启动与可见光参数

覆盖下方固定翼运动学记录。用户本轮选择JSBSim参考参数路线；已接入官方1.2.4固定提交原生核心，项目C ABI DLL/各机独立六自由度120Hz，键盘为增稳目标、惯性油门/舵机响应；质量/惯量/气动与推力参考值未标定、空中初始化，不是实际起降，风/天气/地理未耦合。未替换ProjectAirSim现有库。修复EventEnabled默认true但根/子云台未创建采集与启用流通道；启动即15Hz，未知设备草稿也默认开启。可见光GPU材质新增独立blur/noise/contrast/saturation，默认.55/.006/.96/.88，中性0/0/1/1，不混IR/事件。129核心（7真实DLL）/最终16Qt/Editor与隔离实城双云台默认事件、源图模糊、Qt固定翼驾驶/回平/爬升/调速/暂停恢复通过，所属测试退出。详情 [docs/JSBSIM_CAMERA_20261105.md](docs/JSBSIM_CAMERA_20261105.md)。源码E:/Projects/WISEYE，E:/Projects/WISEYE-IR-Work同步编译，未重包/推送；上一轮关机请求已完成，本轮未要求关机。

## 2026-11-05 优先：实时设备编辑、固定翼机头轴与事件默认开启

覆盖下方“新增/跨类型必须重载、事件默认关闭、固定翼+X/翼展103cm”的旧记录。设备页实时应用与保存初始独立，fleet.apply/patch字段差异+run/revision校验，云台与无人机热增删/更改不重载地图；只要求受影响的飞机停止后移动/跨类/删除。4个着陆隐藏飞控槽位供热领用，无额外相机；放置租约临时关闭该停机槽位碰撞并恢复/5秒到期，飞行碰撞不关闭。固定翼经实际几何确认机头+Y、机长80/翼展62.05cm；修复UI接管、暂停恢复与零输入，界面真实按键验证。事件默认开15Hz，默认5画面、保留自定义布局，两云台开/关均约30FPS。122核心/28Qt/Editor及同run实城热增删、Mavic保持悬停、Fixed按键、Avata热新增起降与类型切换通过，测试已退出。源码 E:/Projects/WISEYE，未重包/推送，用户要求完成后关机。详 [docs/LIVE_DEVICES_20261105.md](docs/LIVE_DEVICES_20261105.md)。

## 2026-11-05 当前：双语与固定翼巡航

源码工作目录已改名为 E:/Projects/WISEYE（覆盖下方历史 PortableBuild 路径），F 迁移暂缓。仿真资源设置→窗口与语言和训练端支持中/英即时切换及持久化，不翻译协议/输入；语言目录configs/locales。用户 FixedwingUAV_gray.fbx 按机长80cm等比导入，fixedwing/kinematic_fixedwing 独立原生巡航与控制代理，不创建四旋翼物理体；空中初始化+30m，巡航/盘旋/手动/航线/停止，不是物理起降。模型动态跨类切换须保存Fleet并重载，日常Fleet未改。117核心/28Qt和纯固定翼、固定翼+Avata城市实跑通过，VIS/IR固定翼GT、Avata起降、英文不中断、停止/退出已验证；最终手动速度边界复测见证据。Editor已编译，无重包/推送。详 [docs/LANGUAGE_FIXEDWING.md](docs/LANGUAGE_FIXEDWING.md)。

## 2026-11-03 发布优先状态

当前唯一开发工作副本 E:/Projects/WISEYE-PortableBuild，F 迁移暂缓；覆盖下方历史“F唯一源码”。v1.0.0 为作者 11 月 3 日生日纪念、首个功能较完整阶段版本。GitHub 发行提供源码和说明，不附大型运行包。发布前111核心测试通过；成品实测沿用11月2日记录，本次未重跑UE全量验收。迁移副本遗漏559项历史已跟踪资源已从Git恢复，避免误删；旧场景入口保持移除。详 [发行说明](docs/releases/v1.0.0.md)。

2026-11-02再后续最新：实时遥测新增所选无人机→所选云台底座三维距/水平距/高差，几何真值非激光回波，断连清除；光心斜距仍在设备数值页。夜灯保留尺寸/闪烁，以18–20/4–6时过渡增强工程强度6→24和深夜Bloom .09（覆盖下方一律.015历史），非照度/曝光标定。robot_wiseye_fastphysics simple-flight-api-settings.parameters.MPC_LAND_SPEED=.8，替代底层默认.2，大小城/机型共用配置重启生效；仍原生接地确认后disarm，未引入分段下降。Editor/110核心/20Qt及隔离小城实际起飞爬升/距离/夜灯/降落通过，中位.817m/s约10.43m落差全流程14.20s，ready/4RPM<1，所属进程退出；日常11JSON SHA相同。雨评估保留空间雨线、干镜头默认去大滴，近处虚焦与镜头沾水应区分，未恢复旧滴/未加湿镜头功能。详docs/DISTANCE_NIGHT_LANDING_20261102.md与evidence/distance-night-landing-20261102/verified；早期遮挡/严格色阈值失败不能当最终通过证据，未重包推送。

2026-11-02后续最新：夜间雾散射颜色随Night降低，修复天空仍灰蓝；新增项目M_RainStreaks与WiseEyeRain世界网格细雨线，空间遮挡/距离衰减/近镜头排除，旧粒子仅资源缺失回退；天气UI与验收须兼容rain_active_streaks。新增云台独立640×480 HDR帧驱动event传感器，默认关闭，独立光心/阈值/不应期/采样上限，关闭释放组件/目标/CPU缓冲。原始sensor.event.get_packet每客户端独立游标，world_time插值微秒非硬件精度，65536环形/20000回复及每采样/8次每像素上限，蓄水池保留全图，必须报告skipped/truncated/dropped；不提供假RTSP。桌面第四参数页/独立电源/最多6预览（默认仍4），新增JSONL示例。Editor/数学/110核心/38Qt、真实city→city_large→city及最终新版小城市复测通过；发现并修复退出线程向已销毁QObject发信号；最终所属进程退出、11正常JSON SHA不变，不起飞/不重包推送。大城市事件转动存在截断和缓冲跳过，非无损。详docs/EVENT_CAMERA_WEATHER_20261102.md与evidence/event-weather-20261102/final、smoke。

2026-11-02最新：顶部收敛为启动/关闭仿真与状态/连接/断开两个会话按钮，独立断连不停止UE；只关闭所属RuntimeManager进程。退出先获取换图后的当前run_id再安全降落。键盘归属移右侧，预览/传感器树不自动开参数；工作台放大旁有弹窗图标，ImageView支持1–16x指针锚点缩放/左拖/双击复位，不改FOV/源帧/GT。PerformanceRating按3–8新样本和档位上限给良好/一般/较差，5s数据过期，GPU高占用不单独判差。Native显式设置RainDensity和激活，关闭WeatherActor跟随Tick并限制密度，雨粒子不混IR；夜间隐藏识别的日景天幕、EV下限3/偏置-0.5/导航灯64→6/Bloom .015，保留暗部，非物理月光或低照标定。110核心/34Qt/Editor及真实city→city_large→city、启停/断连重连/雨粒子/雾/夜间/关闭按钮通过，13配置SHA不变、所属进程退出；本轮不起飞，未重包推送。F/E插件201文件SHA相同，E的ProjectAirSim与Drone Content联接已改指F，51处工作区联接无Evaluation目标；其20KB完整本地源码差异归档F builds/dependencies/evaluation-source-handoff-20261102，Setup默认源码checkout进builds/dependencies/ProjectAirSimSource。Evaluation日常依赖已解除但未删；IR-Work36GiB与Scene209GiB仍有必需地图/用户数据/共享资产，不能删。详docs/WORKBENCH_WEATHER_20261102.md和PROJECT_DEPENDENCIES.md。

2026-10-31传感器稳定性最新：大小城市共用修复已编译并实测。采集关闭时Native保留相机规格，桌面严格兼容旧0×0停用回复，不再断开整机控制；天气Collection资产/实例改UPROPERTY强引用，失效2s重试。稳定AGC排除天空/目标，背景不足保持，0.025/s限速及0.10–0.36归一化参考区间，非温度；保留现有灰度曲线/热斑/光学模糊。点云默认雷达原点透视、按实际FOV且保持比例，保留3D旋转/俯视；JPEG缓存60→90、返回真实quality=90。108核心/31Qt/原生数学通过，真实city→city_large→city启停/全关保持UE与OBS推进/雨效启停/全天空增益保持/锁定转角通过，最终所属进程退出；13配置SHA不变。本轮无飞行/全城LOD/长时GC/训练帧率验收，未重包推送。重开桌面及源码仿真使用；详docs/SENSOR_STABILITY_FIXES.md和evidence/sensor-stability-20261031。

2026-10-31最新：大城市city_large已作为独立试验场景接入并通过真实起降、90秒飞行采样、2.65m手动移动和切回小城市验收；小城市city仍默认，根VBS只开GUI。1机1云台/经济画质/250m设备与观察流送源，约30FPS、UE内存11.38GiB、显存4.05GiB；切回city约35.13s，最终四RPM0、所属进程全退出。F唯一代码源；新地图和约10万外部Actor在E衍生工程，依赖原始CitySample联接，未向有读取错误的F批量复制。正常E preview-data仅新增city_large Scene/Fleet，用户city Fleet及原始Big地图SHA保持。修复actual_pose缓存和Python3.14服务关闭顺序死锁，107核心/11相关Qt通过。未全城/多机/长时/Shipping验证、未重包推送；旧测试/沙漠二进制删除受审批限制仍在。详docs/BIG_CITY_INTEGRATION.md与evidence/big-city-20261031/final/report.json。此条覆盖下方历史“仅city、Big尚未接入”状态。
2026-10-31当前：仅city入口。已删F/E/preview-data旧original/test_range场景/Fleet/Layout配置及旧AirSim JSONC，启动与发布仅City；102核心/65Qt通过。UE只读312包无外部引用，但物理umap/Actor删除被自动审批拒绝，文件仍在，勿称清理完毕，见docs/BIG_CITY_ASSESSMENT.md准确路径。Big City原始资源存在/E联接可注册，未接入/未加载实测/未重包；32GB内存，建议局部流送。F Building/CH/C/Kit_Bldg_CHC_L1_A/Mesh枚举报损坏，未修复；不要删共享目录/原始CitySample。此条覆盖历史“保留original/test_range源码”要求；仍保留通用模块与测试、用户city Fleet与不自动UE。

2026-10-30当前：用户放弃边缘盒子，选择自定义仿真地理基准。新增云台数值与坐标弹窗、core/georeference WGS84 ECEF/ENU/UE转换（默认未设置、椭球高、simulation_anchor）、SDK坐标导出/指向和JSONL示例。Native gimbal.point_at严格scene/run/sensor/worldcm、实际独立光心解算、越界拒绝恢复，成功直接位置设置非完整伺服；state新增几何/垂直FOV/输出规格。Editor/102核心/65Qt及实城双光心20m/非法保姿/实际起飞悬停10次坐标指向通过，最终ready/4RPM0/测试退出。测试基准仅隔离目录，不代表真实地理，未改Fleet/日常基准，旧高位Land限制仍在。详GIMBAL_COORDINATES与AI_HANDOFF；F唯一源/E构建，未重包推送，默认不自动UE。

2026-10-30最新：用户要求节省整行，workbench_v3顶部modes行已删；连接/推进异常合并右上、诊断左下，天气/画质进画面工具栏“场景”菜单，键盘唯一控件在原归属条；不要恢复重复状态卡。NavigationButton固定几何绘制，设备网格/接口双箭头等五种图标不重复。62Qt/原生100/150与菜单检查，无自动UE，compact-toolbar证据。RK3576不适合当前完整UE城市（可作为待移植网关/推理），建议GPU x86远程承载；当前控制/飞控只loopback，未实现完整远控或开放端口。说明COMPACT_WORKBENCH_EDGE_DEPLOYMENT，未UE联调/重包推送，保留其他P1缺项。

2026-10-30最新优先：用户指出V4与示例差距，整套P1仍未逐项完成，见UI_V4_GAP_REVIEW。根VBS改只开桌面，用户点“启动仿真”才启动UE；不要恢复默认自动UE。保留E现有preview-data（参数/env可覆盖），无UE也能开GUI。补device_catalog实例详情、workbench_polish固定安全动作/诊断/归属、训练紧凑工具、五组设置与接口分区。高级内嵌折叠150%切窗AV改独立小窗、关闭清零。94核心/62Qt/原生DPI/实根入口无UE无端口通过，refinement证据；本轮未UE联调，旧verified属上一轮。尚有明确P1缺项，不能统称P2或宣称全部完工；未重包推送、不改Fleet/IR/UE。

2026-10-30界面最新：用户批准V4已实施P0/P1主体，原生Qt/shared灰蓝theme、shell_v4五页左导航/参数Dock、arrangement_v4复用单OBS、设备草稿保护、training_client/layout_v4双主画面/融合缩略/顶部保存条；保留实际命令/独立相机/统一GT/存储/RPM/关闭保护。94核心/59Qt、真实7组/4.68FPS、ready/四RPM<0.01后全退出；证据ui-v4-20261030/verified。高位直接Land60秒NNG超时尚未修，最终先下降再降落；1440×900/150%未完整适配，P2样本浏览/UE三维航线/完整性能对照未做。本轮未重跑全部空中退出，勿冒称完成。见docs/UI_V4_IMPLEMENTATION.md及AI_HANDOFF；F唯一源/E构建，未改本轮IR/Fleet/UE，未重包推送。

2026-10-30关闭保护验收：根预览Job/桌面RuntimeManager/训练子Job拥有进程；主窗异步退出、仅所属树清理，手动连接外部UE不杀。修复降落2秒ACK超时导致提前退出：ACK8s，状态错误总30s内重试，run_id核验、所有drone_id降落。94核心/54Qt、真实空中关主窗13.21s（确认ready）、直接关UE3.79s均无所属PID残留，测试全部退出、未开额外预览。源码/说明见docs/SHUTDOWN_PROTECTION.md与evidence/shutdown-final-20261030；不回退后续统一训练UI/GT速率，红外/Fleet/模型不改，未重包推送。

2026-10-29无人机灯光最新：Mavic/Avata默认夜间左红右绿交替双闪（1.6秒周期），四灯随真实姿态；18–06时间覆盖或原场景太阳朝向判断，白天关闭。仅VIS自发光小灯，无投射光；所有IR相机隐藏灯珠、热分类跳过，IR深度继承隐藏列表。近似安装点/灯语，非原厂标定。Editor/93核心/真实起降、型号往返切换、图像红绿亮灭像素及双GT通过，最终ready/4RPM0，自有进程退出，未重包推送。见docs/DRONE_NAVIGATION_LIGHTS.md及evidence/navigation-lights-20261029/final。新增模型先读docs/DRONE_MODEL_INTEGRATION.md（含可直接交AI的任务模板）；当前自动导入仅FBX静态网格，运行用uasset，不能只添下拉选项或复制Avata UUID。保留当前Fleet与红外效果。

2026-10-29训练最新：用户授权测试提高GT并合并界面。原限2为保护门，现gt_configure.max_fps可0.1–20（默认2/兼容旧客户端），新UI请求10、默认预览5/保存1、UI各0.1–10。实机B580/14600KF双路GT设置2/5/10/20实得1.84/3.86/4.63/4.74，缩短轮询后10约4.84；统一GUI实际4.51FPS、仿真30Tick，不承诺10/20。已移除视频/样本模式与双视频线程；始终同帧图像+GT，单“预览GT框”仅叠框，隐藏仍保存GT/融合。图像解码复用、最新单槽不积压，修复源预览驱动时重复限流丢帧。93核心/52Qt/Editor/3次实际起降/运动GT+隐藏框保存+在线设置通过，最终ready/4RPM0、隔离测试全退出。见docs/GT_RATE_AND_UNIFIED_PREVIEW.md与evidence/gt-rate-20261029，未重包推送；勿恢复双模式/固定2上限或声称20实帧。

2026-10-29输入最新：桌面飞控每设备最多1个在途flight.set_input+1个最新待发，松键零输入覆盖旧队列，降落/悬停/模式切换丢弃待发移动；后端手动速度用AirSim SingleTaskCall替换，取消每Tick同步CancelLastTask/UE状态同步和重复遥测读取。UE放置点按原步长，按住.3s后10Hz连续、松键停、不卡顿补步。训练连接中策略/目录可改（版本快照，旧策略在途样本丢弃），VIS/IR自动异步重订阅，主机端口云台点应用连接设置；不再禁用这些控件。Editor/91核心/51Qt/真实60s输入493ACK、首末16.87/16.82ms、零输入6ms、长按D1s70cm后停、训练在线改设置/换源通过。自有测试ready/4RPM0后全退出，用户Fleet不改。见docs/INPUT_AND_ONLINE_SETTINGS.md及evidence/input-online-20261029，非端到端画面时延/多电脑长期保证；未重包推送。

2026-10-29最新放置：按用户要求WASD沿设备朝向移动、QE转向、RF升降，10cm/1°，Shift1cm/0.1°；禁止恢复箭头/PgUpDn。桌面放置确认/编辑坐标与新增朝向字段默认实时应用，无需重载；保存仅保留下次初始值。云台移动完整装配，机由50052先SetPose(reset_kinematics=True，必须frame_id)再50051确认物理实际位置/更新原点，拒绝空中/旧run；UI异步去抖/设备隔离/断连清理。E Editor及90核心/47Qt/真实键盘、GUI直接改两设备、同run移位后起降通过，最终ready/4RPM0、自有测试全部退出；用户Fleet未改。见docs/LIVE_PLACEMENT.md和evidence/live-placement-20261029。未重包/推送。

2026-10-29当前优先：红外固定用户认可的当前效果，UI旧成像版本选择和两个预设已删（core仅保留字段常量）；旧底层协议/内部材质兼容保留。最终灰度背景轻微低通，目标及邻域不混；Mavic与Avata实际电机轴心/电池后向近似区域热斑，随RPM升温冷却。修复天空窄视场AGC统一压白：目标显示混合原始归一化热信号保留局部差别，非测温。Editor/Facade回传F、73核心/40Qt/原生数学、两型号真实起降双GT均通过；最终Mavic/ready/四RPM0且测试退出。训练默认1FPS/UE限2每路，6组短测1.83组/s，本轮不调高GT上限。见docs/IR_CURRENT_MODEL.md及evidence/infrared-current-20261029。未重包/推送。

2026-10-28当前优先修复：Python Fleet rotation_deg为pitch/yaw/roll，检查0、2轴，允许yaw90；此前[:2]误拒导致桌面设备空/全0/放置禁用。73核心+36Qt+实城桌面点击放置/第一次确认草稿/训练按钮自动接收/复用窗口通过。Facade改屋顶/墙体层次和AGC后平滑背景曲线，目标显示×0.82；不再用0.72背景信号缩放（仅历史回放保留）。新Facade资产E→F已同步；真实Mavic起降双GT通过，测试最终ready/4RPM0并退出。新入口为主界面右上打开训练端，pythonw无console；旧包无Training可执行需明确提示，未重包/推送。见[本轮修复](docs/PLACEMENT_TONE_TRAINING_FIX.md)。

2026-10-28最新：启动/角位/楼宇灰度/模型预览完成。F唯一源/E衍生构建已同步；Editor-game取消全源扫描，初始化实测42.23/30.72/29.93s（非冷缓存承诺）。1机1云台保留，云台(-27066.5527,-2092.688,4059.1168)，双边各1m；机(-27400,-2600,4080)，勿恢复旧远处起点。默认facade/contrast1.1/稳定增益，背景显示幅度0.72，非物理LWIR。放置青绿半透明完整模型/同尺寸姿态/仅草稿/右键取消，VIS/IR/训练隐藏，Nanite预览回退不改源资产。Editor/72核心/35Qt/原生数学/实际三模型放置和Mavic角位起降双GT通过，最终ready/4RPM0并退出自有进程。详见[本轮说明](docs/STARTUP_PLACEMENT_IR_TUNING.md)，未重包/推送。

2026-10-28双相机/楼顶最新：VIS/IR同级独立相机，12cm示例基线、IR0.1/0.2°视轴偏差，厘米不随导入缩放；各自6外参字段/API。IR热区与导出坐标用实际相机。用户明确授权城市改为1机1云台同楼顶，云台距边1.07m；F Fleet/Layout/Scene与E已更新，勿恢复旧ptz-02。训练默认ptz-01；双路同刻但有视差，未配准拒绝融合，原图/GT保留。Editor/68核心/35Qt/真实几何、采集、接收及Mavic楼顶起降通过，4RPM0并退出自有进程。详见AI_HANDOFF与DUAL_CAMERA_ROOFTOP，非实机标定/LWIR物理化，未重包/推送。

2026-10-28入口整理：根目录仅Start-WISEYE-Studio.vbs，已改为完整E城市预览+飞控+桌面（不是旧的仅桌面）。五个旧CMD/VBS已删；已有UE只重开桌面运行scripts/Start-Desktop.ps1 -Connect，解释器先builds/python-env再.venv。训练端入口保留。旧历史入口引用不可照抄；详见当前USER_GUIDE及CLEANUP_REPORT。VBS桩/PS语法/路径通过，未完整启动UE/重包/推送。

2026-10-28当前优先：红外P0/P1完成，同帧云信号回放下降26.7%高频指标、重复一致；不可用随机实时云截图归因。新增天空空间滤波/稳定AGC/锁定与手动/亮度/种子及两草稿预设，保护2×子像素目标。Editor/60核心/27Qt/原生数学和实际Avata起降恢复通过，4RPM0。IR仍约10Hz，CPU+2.48ms、缓存年龄多一Tick，非端到端验收。F源/E构建，Facade回传F、Fleet旧资产不变；详见AI_HANDOFF/INFRARED_DETECTOR_PILOT。未重包/推送，下一步真实数据与远距目标标定。

2026-10-28优先：实际场景体积云与楼宇IR云灰度、按云台VIS/IR/雷达快捷启停已验收。60核心/23Qt/Editor及真实云图、停采计数、多设备隔离、Avata起降冷却恢复通过；最终4RPM0、自有进程退出。F唯一源码/E最小构建，Fleet旧资产保留，Facade更新+M_Cloud_Runtime新增。远背景有限深度旧阈值误判天空热目标247k→0，当前10km限制；云灰度是白天外观代理，非物理温度/夜间校准。详见AI_HANDOFF与CLOUDS_AND_SENSOR_POWER，未重包/推送。

2026-10-27当前优先：楼宇热像facade试验通过，独立M_IR_Facade，GBuffer纹理/粗糙度/法线代理，保留classified与原三模式和资产、默认reference。Editor/58核心/18Qt/真实城市两机位及恢复通过；F Fleet哈希不变，源F构建E，未重包/推送。不是物理温度/透明玻璃/Anti-UAV校准，短测增加少量开销，详见AI_HANDOFF与INFRARED_FACADE_PILOT。

2026-10-27当前优先：材料热像classified与Avata局部热区试验通过。E衍生城市6295组件低位1–6材料标签，目标32以上；F正式城市/Fleet不改。新M_IR_Classified内保留三种对照，默认reference，手动选材料模式。实际GPU分类覆盖72.2%，电机区域约25像素；相机投影必须InverseTransformPositionNoScale保持世界厘米，不可退回除模型缩放的投影。58核心/17Qt/原生数学/Editor及真实起降材料图像/旧模式兼容通过。Prepare-ThermalCity默认审计，新机须在构建副本标记后Cook；仅保存自有Actor包，保护他用深度。玻璃/混合材质/真实温度/多目标/端到端/新Shipping未完成，VSM告警未修；未推送。先读AI_HANDOFF和INFRARED_MATERIAL_PILOT最新节。

2026-10-27当前红外：实拍参考源码试验完成，独立M_IR_Reference、FP16/CPU PSF/平滑AGC、RPM热状态、每云台参数，默认1×；2×明显增加开销。最终Editor/54核心/16Qt/原生数学和city真实起降/热状态/图像接口通过，证据infrared-reference-20261027，说明INFRARED_REFERENCE_PILOT。唯一主源码F:\WISEYE-Studio；旧两个E工程已用户自行删除，新最小衍生构建E:\Projects\WISEYE-IR-Work复用E原始CitySample资源，不是第二开发源。旧Shipping包未更新，未推送；不宣称物理测温/Anti-UAV校准/整城热材质/Avata电机细分已完成。用户Fleet哈希不变，实拍拼图不上传。先读AI_HANDOFF最新节。

2026-10-27最新发布：用户要求系统只自带城市。Shipping交付版本20261027-171140-City-Shipping，City专用完整Cook，默认Build-Release Content=City；release.json与资源清单仅city，SceneStore在发布版过滤旧用户目录中未随包发布的场景，不删除用户配置。保留源码original/test_range；GameDefaultMap改为city。54核心+15Qt、最终City真实起降/RPM归零/三路原尺寸图像/云台/点云、增强IR/天气/自定义19554 RTSP解码、冻结GUI与旧配置兼容通过。修复雨效UClass需UPROPERTY强引用、Shipping无RHI STATS时按实际D3D12 Adapter LUID查询DXGI显存预算。Cook阶段先编译Editor，避免反射布局与Game不一致。F主源码/E临时构建，原Fleet hash不变；交付SHA与GitHub状态以RELEASE_BUILD和evidence/standalone-release-20261027为准。安装器/在线更新/干净机器/长期4+4仍待做。

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
- 自有原始/测试场的World Partition Content/__ExternalActors__、__ExternalObjects__必须提交；完整CitySample第三方城市副本及其外部Actor按.gitignore保留本地，通过Setup-CitySample重建，不强制上传整城。编辑器修改对象要modify并保存，不能仅改内存。
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
