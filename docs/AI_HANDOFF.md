# WISEYE 当前交接（2026-10-28）

## v1.1.0 发布整理（2026-11-10）

用户已明确授权将插件上传 GitHub 为下一版本，并更新 README 与重要文档。目标版本 v1.1.0，发布源码插件与 SHA256；完整城市包本地保留，不作为本轮附件。插件描述符/清单使用 1.1.0，README 保留远端标题与 YZE、ZWT 致谢。下方“未上传”是先前验收快照，最终发布状态以 docs/releases/v1.1.0.md 与 GitHub Release 为准。

## 2026-11-10：插件与完整包交付完成

源码插件与完整 Shipping 运行包均已完成。39 项回归通过；独立无城市宿主 Editor 实跑与 Shipping 编译通过；主项目及冻结运行包大小城市均通过双光、云台、点云和起降验证；仿真/训练冻结界面启动通过。完整目录 releases/20261110-164135-City-Shipping（约27.34 GiB），传输包 builds/distributions/WISEYE-Full-20261110.zip；源码 SDK 为 builds/distributions/WISEYE-Plugin-20261110.zip。完整包采用 DX12/SM6。第三方 M_Crowd_Head_v2 Cook 有 SRV 超限材质回退，干净电脑和自定义宿主完整打包未验收；未上传 GitHub。唯一源码/UE工程在 E:/Projects/WISEYE；旧外部工程已移至 builds/legacy-* 隔离，未物理清空。Scene/CitySample 仍供城市源码编译使用，完整运行包不依赖它。详 docs/DISTRIBUTION_IMPLEMENTATION_20261110.md。

## 2026-11-10：清理项目父目录临时 Python 脚本

核查并删除 E:/Projects 根目录 13 个一次性开发/证据整理脚本，共 26362 字节，均写死旧 F:/WISEYE-Studio 路径；当前项目未检出文件名引用，无匹配活动 Python 进程。根目录 *.py 已为 0，删除前路径/大小/SHA256 和原因见 [cleanup-20261110.json](cleanup-20261110.json)。仅删审查清单中的直接子文件，未递归删除；正式源码、测试、UE 工具、依赖、论文和历史实验证据均保留。计算路径的批量删除命令被策略拒绝且未执行，改用明确列出全部字面路径的 PowerShell 原生删除成功，已逐项确认不存在。无应用代码改动，未启动 UE/训练或重跑应用测试。

## 2026-11-09：论文配图版

当前 paper/main.tex 与 body.tex 原位加入 6 组图：四组 TikZ 示意（系统架构、双相机几何、双光成像、采集标注）及 12 张既有原始仿真采集图组成的昼夜/光学控制两组面板。图注区分示意、顺序采集和严格实验，不冒充实拍、配准或同刻对照；图源及哈希见 paper/figures/provenance.json。paper/add_figures.py 可重建，build.py 已接入防止图丢失。桌面内置 compile_latex_document 编译成功；未单独导出 PDF、未逐页视觉验收或压缩至投稿页数，当前编辑器预览即配图版本。未运行仿真/训练或补造实验。

## 2026-11-09：英文论文初稿

新增 [论文目录与中文说明](../paper/README_ZH.md)、[英文主稿](../paper/manuscript.md)及可阅读 HTML、ICCV 2025 官方样式 LaTeX 源稿、4 条已核入口参考文献与重建脚本。约 4000 英文词，完整写入已有双相机/成像/云台/飞行/采集与标注工作流；四张实验表全留空。主线按当前已实现的框架描述，未实现自动校准不冒充方法。引用覆盖、创新核查、实验、图表与 2027 模板复核尚待补齐。Pandoc HTML/TeX 生成及引用键/空表检查通过；无本地 TeX 编译器，未 PDF 编译或页数验收。未运行仿真/训练、未改功能、未推送。

## 2026-11-09：ICCV 论文选题与结构草案

新增 [ICCV_PAPER_PLAN_20261109.md](ICCV_PAPER_PLAN_20261109.md)。建议主线为地面云台视角的小目标无人机检测、传感器感知仿真校准及真实迁移评测；候选创新均待文献检索、实现和真实测试，不把 UI/系统集成作为充分贡献，不声称物理温度定标或已有 AP 收益。先完成相关工作差异表、来源/序列/许可审计与冻结划分、等预算训练基线；已用于成像调参的实拍不能作为未见最终测试。ICCV 为顶会、CCF A 类，主会与 Workshop 区分；2027 官方日期页本次未列投稿截止日期。本轮只新增论文规划与交接，未训练、改渲染、编译、打包或推送。

## 2026-11-09 最新：传感器、景深与后台窗口验收

源码E:/Projects/WISEYE、预览E:/Projects/WISEYE-IR-Work已同步。云台/每机可见光有auto/manual/infinity/off、对焦距离m、光圈、实际焦点与薄透镜景深估计，默认PSF .95px；航拍独立vis_blur_px。修正MID不能以MID为父材质，使用根UMaterial；最终实跑模糊/景深均改变源画面且材质编译/运行错误0。人车热标签改16/17，与无人机>=32分离，不套无人机提亮曲线；车辆IR近景人工确认可见且不再全白描边，非温度/发动机物理模型。航拍双光左右网格，UE默认隐藏、右上单按钮sim.window.set_visible可显隐，放置自动显示；保持后台渲染，非零GPU。

完整扫描sensor.lidar.get_scan新增真实扫描时刻/序号/无回波-1，点云仍理想矩形角网格首碰撞回波；core/sensor_formats.py转换PointCloud2（Y反号）和EventCD（极性0/1），不等于厂商驱动/RAW编码。事件仍约15Hz帧驱动插值，不是微秒硬件时序。35 Python/Qt与原生热像/事件不变量、Editor通过；最终builds/imaging-realism/sensors-20261109-final实际起飞、昼夜8图、航拍PSF/云台DOF、隐藏持续渲染、576点测距一致、4000事件转换、降落退出通过。证据docs/evidence/sensors-20261109，详docs/SENSOR_UPGRADE_20261109.md。先前verified等目录有MID父材质问题已撤销整体通过，最终只认final；车辆IR单独帧保留来源，不当GT。已有Mass CustomData ensure未修；未大城/Shipping/打包/推送。LoS可选碰撞射线不是像素可见性，早期近景被楼遮挡不作为车辆可见证据。


## 2026-11-07 最新：双光源成像改进完成

详[IMAGING_REALISM_20261107.md](IMAGING_REALISM_20261107.md)。Facade路面世界固定缓变热场/材质差异；航拍独立昼夜背景曲线，保留云台/天空/目标；可见光改保黑端点对比和低照度噪声，VIS/IR物理镜头仍独立。源码/预览二资产SHA一致，Editor/21Python/原生热数学通过；最终builds/imaging-realism/verified小城实际起飞悬停、昼夜两视角8图、降落/退出，项目材质回退0。道路日190→178、std.57→4.36；夜37→166、std1.03→9.14，前后位置约6.2cm差。文档证据含原图；此前after/final可见光fixed变量触发UE宏回退，已改fixedPattern并撤销中间报告通过，禁止使用其对照图。最终运行日志检查加入验收，不能只信材质生成脚本返回0。Aerial分配时新增可选AGC/类别覆盖诊断。世界位置节点要重建M_IR_Facade，可见光也需重建M_VisibleCamera；已同步到E:/Projects/WISEYE-IR-Work，主源仍E:/Projects/WISEYE。既有Mass CustomData ensure未修，无大城/Shipping/推送或标定达标承诺。

## 2026-11-07 最新：真实/仿真红外外观基准

新增[基准说明](INFRARED_REAL_SIM_BASELINE.md)、两份配置、下载/本机只读采样和测量脚本及12回归（通过）。共66图：官方HIT昼夜各16、本机F:/DATASET_UAV_BICE/YOLO_UAV_BICE的Halmstad/CESE各16，Nov7航拍及Oct31历史云台各1；官方训练子集不用测试集调参。铺装手工ROI仿真中位191/标准差0.57，真实白天帧间中位171.5/18.28，近白0%，当前首先是平坦路面层次不足。原图/本地联系表在忽略builds/research-data及builds/infrared-real-sim-baseline，可提交数值/许可明确HIT比较图在docs/evidence/infrared-real-sim-20261107。未启动UE或改渲染，不声称当前云台目标/夜间仿真已评估；完整Anti-UAV410夜间设备序列与DroneVehicle未取得。继续按文档矩阵补当前受控采集，再改航拍材质热分布；保持已认可云台风格，不全图压暗或用噪声伪造纹理。主源码仍E:/Projects/WISEYE，未打包推送。

## 2026-11-07 最新：航拍红外、采集与数据集管理

用户选择本轮完善采集/标注/数据集管理，目标含地面与其他无人机，不接训练启动。每机独立640×512 AERIAL_IR/HDR热读回/6cm基线+局部0.2°视轴差、IR电源/独立采样/FOV/极性/模糊/噪声，按需分配/空闲释放；VIS保持1920×1080，工作台VIS/IR/双光切换。JPEG绑定捕获tick姿态/环境历史；运行时Mass模板车辆与已知Crowd VAT人群整组件热代理，非温度/发动机热模型。训练发现设备、切换来源，云台保留同刻GT；航拍schema4原图pending_manual、不伪造GT/同步对/空负标签，数据集校验/人工拖框0无人机1行人2车辆/明确负样本、独立run防泄漏导出、后台可取消。138核心/29Qt/最终32训练检查/Editor/隔离小城实际飞行双光采集-审核-切回GT-降落通过，源进程退出；Mass出现非致命CustomData ensure未声称修复，见详单。源码E:/Projects/WISEYE，预览E:/Projects/WISEYE-IR-Work；未大城/重包推送。详[docs/AERIAL_IR_TRAINING_20261107.md](docs/AERIAL_IR_TRAINING_20261107.md)。

## 2026-11-05 最新：预载、被动实例与轻量加载界面

启动/换图新增真实阶段2D加载覆盖层，可后台加载/查看失败；300×8局部光带80ms，隐藏即停，无额外3D视角、无假百分比；等待首帧及3个独立稳定样本。原生异步预载并保留实体配置、预构建模板，直接覆盖Crowd/Traffic显示模板高/中LOD为实例，关闭保留低精度Actor，首次更新分散、人群实例可见600m。纠正先前仅全局LOD不能阻止近处完整人物的问题。Shader编译计数纳入就绪。31相关Qt/指标回归+Editor通过；隔离小城300行驶/300停放/600行人实际生成和移动、航拍扫视通过，14样本FPS中位29.99/最低14.55，仍有瞬时停顿，非A/B或稳定30保证。所属进程退出，未起飞；大城未重测。中间超时已定位头发/完整动画临时载入并修正模板，不作通过证据。详 [LOADING_POPULATION_20261105.md](LOADING_POPULATION_20261105.md)。需重启桌面/UE，未重包推送，原始城市资产不写盘。

## 2026-11-05 最新：方向键、窗口及人群首轮优化

观测隐藏相机、航拍方向键有界持续/松键失焦停；正式入口最大化，场景设置/F11全屏。固定翼中心线改模型盒扫掠，保护停止后明确返回起点，不是假恢复；编译通过但未主动撞墙，非完整接触/坠机物理。被动行人近处取消骨骼Actor改原VAT实例，容量增600行驶/600停放/1200行人；车辆首次载入卡顿未完全解决。22Qt及隔离小城60/60/120预算、机载取图/朝向通过，单次快照28.7/30FPS非A/B保证，所属进程退出。红外本轮只答复可行性，机载IR尚未实现。详 [KEYBOARD_COLLISION_POPULATION_20261105.md](KEYBOARD_COLLISION_POPULATION_20261105.md)，未重包推送。

## 2026-11-05 最新：任务式工作台UI

工作台新增云台观测/无人机航拍入口，航拍编辑器嵌入右侧，主画面默认单航拍、设备栏自动收起，可选场景参考；切回恢复原观测布局，临时航拍不覆盖持久化观测源。起降与明确接管常驻，驾驶/相机分别标ID；参数折叠，场景设置统一天气/人车/画质/诊断，航拍隐藏无关云台参数，删重复入口。21Qt界面+4原预览最终通过，隔离UE实际连续转向/俯仰/图像变化/驾驶不切换通过，所属会话退出，未起飞；1600/1100布局回放检查。一次组合进程中断及较早预览时序失败不作通过证据，最终日志已归档。只改桌面，无需编译UE，重启桌面；训练端不改、未重包/推送。详 [MISSION_UI_20261105.md](MISSION_UI_20261105.md)。

## 2026-11-05 最新：人群骨骼设置与实时航拍朝向

DefaultEngine.ini补齐CitySample要求的16位骨骼索引、无限骨骼影响、SkinCache默认0、ExperimentalChunking=1，源码/预览同步，实际UE日志读入，首次重建缓存。运行评估与告警共用资源准备状态，加载中不累计持续低帧率，完成后仍如实评估。航拍新增可长按四方向按钮及默认实时朝向应用，80ms合并、一个在途+最新待发，旧ACK保护草稿、关闭/断连/换机取消发送。20项相关测试及隔离小城uav-02实际俯仰−30→−75/长按偏航10°/图像变化/驾驶不切换通过，所属会话退出，未起飞。资源就绪/增加15Hz航拍单次快照25.4/18.1FPS，不能宣称性能升到30。详 [AERIAL_AIM_PERFORMANCE_20261105.md](AERIAL_AIM_PERFORMANCE_20261105.md)；未重包/推送。

## 2026-11-05 最新：机载航拍与自动人车

仿真端新增每机独立AERIAL可见光相机（前/斜/下视、稳定/刚性、FOV/采样率、按需释放、原始PNG），场景菜单及设备树入口；航拍注册Mass观察者。原生CitySample交通与人群按启用/密度实时管理，默认25%，预算上限300行驶+300停放+600行人，轿车预设，不逐个操纵。新增prepare_observation_population.py恢复WISEYE大小城副本生成器、ZoneGraph与对应停车/路口资产；原始CitySample不改。场景默认独立保存Observation/<scene>.json，训练端与地面2D GT尚未接入。129核心/23Qt和Editor通过；小城实际起降/三视角/密度切换及独立第二相机、空闲释放通过，修复大城缺生成配置后，大城人车移动/取图→小城密度与相机默认恢复通过，所属进程已退出。源码E:/Projects/WISEYE，预览构建E:/Projects/WISEYE-IR-Work；未重包/推送。详 [AERIAL_POPULATION_20261105.md](AERIAL_POPULATION_20261105.md)。

## 2026-11-05 最新：JSBSim、事件启动与可见光参数

覆盖下方固定翼运动学记录。用户本轮选择JSBSim参考参数路线；已接入官方1.2.4固定提交原生核心，项目C ABI DLL/各机独立六自由度120Hz，键盘为增稳目标、惯性油门/舵机响应；质量/惯量/气动与推力参考值未标定、空中初始化，不是实际起降，风/天气/地理未耦合。未替换ProjectAirSim现有库。修复EventEnabled默认true但根/子云台未创建采集与启用流通道；启动即15Hz，未知设备草稿也默认开启。可见光GPU材质新增独立blur/noise/contrast/saturation，默认.55/.006/.96/.88，中性0/0/1/1，不混IR/事件。129核心（7真实DLL）/最终16Qt/Editor与隔离实城双云台默认事件、源图模糊、Qt固定翼驾驶/回平/爬升/调速/暂停恢复通过，所属测试退出。详情 [docs/JSBSIM_CAMERA_20261105.md](docs/JSBSIM_CAMERA_20261105.md)。源码E:/Projects/WISEYE，E:/Projects/WISEYE-IR-Work同步编译，未重包/推送；上一轮关机请求已完成，本轮未要求关机。

## 2026-11-05 优先：实时设备编辑、固定翼机头轴与事件默认开启

覆盖下方“新增/跨类型必须重载、事件默认关闭、固定翼+X/翼展103cm”的旧记录。设备页实时应用与保存初始独立，fleet.apply/patch字段差异+run/revision校验，云台与无人机热增删/更改不重载地图；只要求受影响的飞机停止后移动/跨类/删除。4个着陆隐藏飞控槽位供热领用，无额外相机；放置租约临时关闭该停机槽位碰撞并恢复/5秒到期，飞行碰撞不关闭。固定翼经实际几何确认机头+Y、机长80/翼展62.05cm；修复UI接管、暂停恢复与零输入，界面真实按键验证。事件默认开15Hz，默认5画面、保留自定义布局，两云台开/关均约30FPS。122核心/28Qt/Editor及同run实城热增删、Mavic保持悬停、Fixed按键、Avata热新增起降与类型切换通过，测试已退出。源码 E:/Projects/WISEYE，未重包/推送，用户要求完成后关机。详 [LIVE_DEVICES_20261105.md](LIVE_DEVICES_20261105.md)。

## 2026-11-05 当前：双语与固定翼巡航

源码工作目录已改名为 E:/Projects/WISEYE（覆盖下方历史 PortableBuild 路径），F 迁移暂缓。仿真资源设置→窗口与语言和训练端支持中/英即时切换及持久化，不翻译协议/输入；语言目录configs/locales。用户 FixedwingUAV_gray.fbx 按机长80cm等比导入，fixedwing/kinematic_fixedwing 独立原生巡航与控制代理，不创建四旋翼物理体；空中初始化+30m，巡航/盘旋/手动/航线/停止，不是物理起降。模型动态跨类切换须保存Fleet并重载，日常Fleet未改。117核心/28Qt和纯固定翼、固定翼+Avata城市实跑通过，VIS/IR固定翼GT、Avata起降、英文不中断、停止/退出已验证；最终手动速度边界复测见证据。Editor已编译，无重包/推送。详 [LANGUAGE_FIXEDWING.md](LANGUAGE_FIXEDWING.md)。

## 2026-11-03 发布优先状态

当前唯一开发工作副本 E:/Projects/WISEYE-PortableBuild，F 迁移暂缓；覆盖下方历史“F唯一源码”。v1.0.0 为作者 11 月 3 日生日纪念、首个功能较完整阶段版本。GitHub 发行提供源码和说明，不附大型运行包。发布前111核心测试通过；成品实测沿用11月2日记录，本次未重跑UE全量验收。迁移副本遗漏559项历史已跟踪资源已从Git恢复，避免误删；旧场景入口保持移除。详 [发行说明](releases/v1.0.0.md)。

## 2026-11-02当前优先：内部盘便携打包，F迁移因USB故障暂缓

用户先授权修盘/搬迁/打包，随后明确“先在内置盘打包，F盘稍后处理”。修盘MFT/卷位图已更正、Dirty一度清除，复制再次I/O重试/UASPStor重置，已停止写负载。F不可作为已完成迁移，五个小路径编辑状态亦未复核；不要删E。不可变安全备份6019文件/1.54GB，E:/Projects/_WISEYE-MigrationSafety-20261102-181223/source，初始逐文件SHA匹配F。当前便携新代码在本E:/Projects/WISEYE-PortableBuild工作副本，F尚未同步，未推送。

Shipping双城市成品E:/Projects/WISEYE-PortableBuild/releases/20261102-191254-City-Shipping，portable.flag→旁边UserData，两个冻结EXE含训练端、随包FFmpeg/MediaMTX。111核心、24Qt、实际小城起降/控制/点云/原尺寸图像、city→city_large→city天气/事件、RTSP自定义19554路径实际解码、训练启动关闭均通过，所属进程退出；无干净机/长时/全城/多机认证。最终ZIP/哈希见releases。详细状态和临时E资源联接依赖见 [PORTABLE_RELEASE_20261102.md](PORTABLE_RELEASE_20261102.md)，优先于下方历史F唯一码源/旧包未更新记录。

## 2026-11-02再后续：距离、夜灯与加快降落

工作台实时遥测新增所选无人机到所选云台**底座**的三维距离/水平/高差，断连清除，不能称激光测距；光心斜距原设备页保留。Native StepNavigationLights工程强度6→24随深夜渐变，Visible Bloom深夜.09，覆盖后文旧.015；灯珠尺寸/闪烁不变、IR仍隐藏灯；非物理曝光标定。项目robot_wiseye_fastphysics SimpleFlight parameters.MPC_LAND_SPEED=.8替代底层默认.2，复用原生Land接地确认和disarm，不是新分段飞控，需重启。

Editor/110核心/20Qt、隔离实城爬升/距离/黄昏深夜图像与实际降落通过，中位.817m/s、约10.43m下降全流程14.20秒、ready/4RPM<1；进程退出、11日常JSON SHA一致。早期低悬停有屋顶遮挡、严格颜色阈值曾失败，最终证据必须读evidence/distance-night-landing-20261102/verified。雨效本轮是评估，保留空间雨线、默认干镜头不恢复大水滴；“近滴虚焦”和“保护玻璃沾水”是不同条件，后者尚未新增。未大城/多型号实飞、未重包推送。详 [本轮说明](DISTANCE_NIGHT_LANDING_20261102.md)。

## 2026-11-02后续：夜空、世界雨线、独立事件相机

最新实现与验收见 [EVENT_CAMERA_WEATHER_20261102.md](EVENT_CAMERA_WEATHER_20261102.md)。此条覆盖下方“只检查rain_active_particles”和只有三传感器的历史状态。事件默认关闭，未启用不创建GPU采集目标；独立HDR640×480，原始RPC事件不是RTSP，时间UE world time帧间插值，不能宣称硬件微秒响应或无损录制。默认4个画面不自动加event，允许最多6个本地订阅。大城市事件转动确有截断/缓冲跳过，须保留每包skipped/truncated/dropped及sensor_state；最终蓄水池限流已数学和小城市复测，大小城市天气及生命周期此前往返验证通过。修复预览worker关闭/销毁时仍发信号；最终smoke无该异常。Editor、110核心、38Qt与原生数学通过，最终所属进程退出、11日常JSON SHA相同，未起飞/重包/推送。

修改入口：Native WiseEyeEventMath/EventCamera/Streaming/Sensors/Bridge/Rain/Environment/Demo，desktop event_preview_client/sensor_forms/sensor_power/sensor_workspace/device_manager/source_registry/interface_settings/runtime_panel/main_window/workbench_v3，examples/event_camera_stream.py。新雨材质M_RainStreaks已同SHA存F和E，生成脚本ue5/scripts/prepare_rain_streaks.py，Sensors目录原已AlwaysCook。夜空修复雾自身散射亮度，不再次压黑楼宇来遮盖天空问题。正常目录与默认不自动启动UE保持。

## 2026-11-02最新：交互、天气与依赖归位

2026-11-02最新：顶部收敛为启动/关闭仿真与状态/连接/断开两个会话按钮，独立断连不停止UE；只关闭所属RuntimeManager进程。退出先获取换图后的当前run_id再安全降落。键盘归属移右侧，预览/传感器树不自动开参数；工作台放大旁有弹窗图标，ImageView支持1–16x指针锚点缩放/左拖/双击复位，不改FOV/源帧/GT。PerformanceRating按3–8新样本和档位上限给良好/一般/较差，5s数据过期，GPU高占用不单独判差。Native显式设置RainDensity和激活，关闭WeatherActor跟随Tick并限制密度，雨粒子不混IR；夜间隐藏识别的日景天幕、EV下限3/偏置-0.5/导航灯64→6/Bloom .015，保留暗部，非物理月光或低照标定。110核心/34Qt/Editor及真实city→city_large→city、启停/断连重连/雨粒子/雾/夜间/关闭按钮通过，13配置SHA不变、所属进程退出；本轮不起飞，未重包推送。F/E插件201文件SHA相同，E的ProjectAirSim与Drone Content联接已改指F，51处工作区联接无Evaluation目标；其20KB完整本地源码差异归档F builds/dependencies/evaluation-source-handoff-20261102，Setup默认源码checkout进builds/dependencies/ProjectAirSimSource。Evaluation日常依赖已解除但未删；IR-Work36GiB与Scene209GiB仍有必需地图/用户数据/共享资产，不能删。详docs/WORKBENCH_WEATHER_20261102.md和PROJECT_DEPENDENCIES.md。

修改入口：image_view.py、workbench_v3/workbench_polish/main_window/runtime_manager/startup_status、runtime_metrics/runtime_panel、sensor_workspace/icons；Native WiseEyeEnvironment/Demo/Sensors。不把顶部按钮改回连接后禁用、重复三按钮；不要恢复点预览开参数。雨资源可用不等于下雨，须检查rain_active_particles和实际图像。IR-Work的两处插件Content已通过Use-LocalPluginContent.ps1改为F实体副本，不得指回Evaluation。日常正常目录仍E preview-data，未迁入F，不得因Evaluation可清理而删IR-Work或Scene。最终证据workbench-weather-20261102/final，summary在父目录。夜间首版过暗结果只作历史，最终目标灰度142→29/81→33；雾近景不是远景验收，GT仍几何标注。当前部分用户视角有近景遮挡，未挪用户设备；本轮不保证空中夜航轮廓、全天候感知或多机。

## 2026-10-31最新：大小城市传感器／天气／增益稳定性

2026-10-31传感器稳定性最新：大小城市共用修复已编译并实测。采集关闭时Native保留相机规格，桌面严格兼容旧0×0停用回复，不再断开整机控制；天气Collection资产/实例改UPROPERTY强引用，失效2s重试。稳定AGC排除天空/目标，背景不足保持，0.025/s限速及0.10–0.36归一化参考区间，非温度；保留现有灰度曲线/热斑/光学模糊。点云默认雷达原点透视、按实际FOV且保持比例，保留3D旋转/俯视；JPEG缓存60→90、返回真实quality=90。108核心/31Qt/原生数学通过，真实city→city_large→city启停/全关保持UE与OBS推进/雨效启停/全天空增益保持/锁定转角通过，最终所属进程退出；13配置SHA不变。本轮无飞行/全城LOD/长时GC/训练帧率验收，未重包推送。重开桌面及源码仿真使用；详docs/SENSOR_STABILITY_FIXES.md和evidence/sensor-stability-20261031。

F原生修改同步并编译到E:\Projects\WISEYE-IR-Work，测试隔离目录sensor-stability-test-data；正常preview-data及F的Scene/Fleet/Layout不改。新UE state雨效失败原因字段rain_unavailable_reason。不要把MPC改回局部变量+实例弱引用，也不要把停用相机当坏连接。新点云云台视角是透视角度图：规则射线网格为真实扫描采样，不补造点；用户可切自由三维看形状，不能冒充相机配准。camera.stream_frame的quality参数仍兼容校验，缓存实际统一90，不宣称逐请求可调编码。

## 2026-10-31最新：大城市独立试验接入完成

2026-10-31最新：大城市city_large已作为独立试验场景接入并通过真实起降、90秒飞行采样、2.65m手动移动和切回小城市验收；小城市city仍默认，根VBS只开GUI。1机1云台/经济画质/250m设备与观察流送源，约30FPS、UE内存11.38GiB、显存4.05GiB；切回city约35.13s，最终四RPM0、所属进程全退出。F唯一代码源；新地图和约10万外部Actor在E衍生工程，依赖原始CitySample联接，未向有读取错误的F批量复制。正常E preview-data仅新增city_large Scene/Fleet，用户city Fleet及原始Big地图SHA保持。修复actual_pose缓存和Python3.14服务关闭顺序死锁，107核心/11相关Qt通过。未全城/多机/长时/Shipping验证、未重包推送；旧测试/沙漠二进制删除受审批限制仍在。详docs/BIG_CITY_INTEGRATION.md与evidence/big-city-20261031/final/report.json。此条覆盖下方历史“仅city、Big尚未接入”状态。

启动入口：场景编排选择“City Sample · 大城市（试验）”，再点击“启动仿真”；已有UE时落地后加载所选场景。首次源码启动最后一轮138.22s，更冷的缓存曾约430s；大城市启动/切入允许900s，切回小城市90s。Native新增asset_compile_jobs等待初始缓存完成。实际地面高度用runtime placement.snap/FastGeo核对，不用编辑器简单Visibility覆盖已验证布局。云台/无人机为地面道路旁布局，用户city楼顶布局不动。

变更入口：Prepare-BigCity.ps1（Build/Duplicate/Inspect/Surface/Assemble/Place/Thermal）、ue5/scripts/*big_city*.py、Scene/Fleet city_large、AirSim JSONC、原生流送源与状态、桌面/预览启动监督器。复制器没有-Rename，不能删共享文件夹重来；F只维护代码与配置，新地图二进制在E。正常数据仅复制新场景两JSON，禁止用隔离目录覆盖用户日常配置。flight状态只读actual_pose缓存，2s过期；close_control_server先关客户端再wait_closed，不能恢复async-with server提前等待。107核心与11相关Qt实际执行通过，其余既有Qt此前66项通过，勿混报本轮执行数量。
## 2026-10-31最新：大城市评估／旧场景清理未完全物理删除

用户要求评估Big City、删除通用测试/沙漠。F主源码、E衍生Config、E preview-data的original/test_range配置和旧Fleet/Layout已移除，两个AirSim场景JSONC已删；PS启动/CLI/组包仅city，默认路径改CitySample，FlightController默认city、相关隔离测试夹具同步。102核心/65Qt通过，PS语法与SceneStore检查见证据。未动Native/用户city Fleet，未自动UE/重包/推送。

NullRHI Python commandlet只读引用审计312旧包、无外部referencers，Big原始地图可注册但未接WISEYE。Big外部Actor101981文件/9329717379字节，不等于完整体积/打包增量；本机32GB低于Epic64GB推荐，建议局部流送试验，不能宣称大城市不卡或已测。E大量联接原始CitySample，严禁删共享目录。F的Building/CH/C/Kit_Bldg_CHC_L1_A/Mesh两次枚举损坏错误，E对应可读，未修复磁盘。详BIG_CITY_ASSESSMENT。

重要：批量递归删除及逐项umap删除被自动审批拒绝（blocked by policy），未绕过。二进制旧地图/Actor仍在F、E各约32.78MiB，系统入口已移除。准确四项手动删除清单在BIG_CITY_ASSESSMENT；不要写成已完成物理删除或腾出大量城市资源。原始下载和旧发行包不改。单元测试虚构ID与历史原场景验收脚本可保留，后者不能用于当前city冒称验收。

## 2026-10-30最新：云台数值／坐标指向与自定义仿真基准

用户明确放弃边缘盒子；不要继续做部署。用户选择“暂无真实基准，先支持自定义仿真基准”。新增core/georeference WGS84 ECEF/ENU双精度转换，按场景GeoReferenceStore默认未设置，purpose固定simulation_anchor/椭球高，北向定义UE+X相对北顺时针。DATA_ROOT/configs/georeferences文件用户需自己配置，未替用户把测试地点写到日常目录。

Native WiseEyeBridge state新增gimbal_geometry/coordinate_pointing_supported、双镜头vertical_fov_deg/width_px/height_px；gimbal.point_at要求device_id、sensor、scene_id/run_id、position_cm（世界厘米），按实际独立光心/视轴/旋转底座迭代求解；非法、旧会话、<1cm、超限/不收敛恢复原姿态，成功清远程输入/退出真值跟踪/保持新姿态。此为直接位置设置，未模拟完整伺服响应；原pointing_error_deg仍是GT目标误差，新误差读coordinate_pointing.error_deg。SDK新增point_at_world/geodetic/coordinates(ref)，经纬转换在Python不在UE原生API，不自动给训练样本加geo。

GUI云台“设备数值与坐标…”新增gimbal_device三页：实时角度/FOV/光心距离/XYZ/仿真LLH；单次指向；仿真基准设置。断连清空、回包按请求/设备，保存本次数据目录，原传感器草稿owner不变。examples/gimbal_coordinate_tracking从stdin有序JSONL提交新坐标，EOF保持；非GPS硬件适配或滤波/时钟/高速跟踪验收。

F仅WiseEyeBridge.cpp同步E并Editor成功。102核心/65Qt；真实run5CFCFED442F678E9CA8FBA995694D4C4双光心20m、FOV回读、地理往返指向、非法/旧run/超限原姿态、实际起飞升高悬停10次坐标回读→LLH→VIS指向通过；ready/四RPM0、恢复角度/tracking、自有进程全退出。证据gimbal-geometry-20261030/final，30N/120E/100m仅isolated-config测试，不是城市真实地点，用户Fleet未动。新字段bearing/入口微调后仅Qt复测，不冒称高速端到端精度。高位Land仍先下降再降落。详GIMBAL_COORDINATES；未Cook/打包/提交推送，默认仍不自动启动UE。

## 2026-10-30最新：删除顶部冗余行、导航对齐与RK3576评估

workbench_v3不再构建顶部modes行，active_scene/health_label/performance_profile保持兼容owner；health移诊断、连接/推进异常合并右上badge，冻结检测清零保持。workbench_polish将唯一input_mode放原ownership条；scene_tools菜单在已有画面工具栏，打开原天气对话框或跳资源设置画质，诊断只留左下（侧栏隐藏可从设置进入）。NavigationButton固定68×68/24图标/文字框绘制；devices网格/data双箭头，不再复用settings。62Qt、原生100/150及菜单无自动UE/图标区别几何检查通过，未连接截图compact-toolbar；未启动UE/改C++/重包推送。小屏限制与其余P1缺项保留。

用户询问RK3576承载UE以释放主机：已核对官方Rockchip/Epic，当前完整城市不适合该SoC，NPU非渲染GPU，Win64包不可直接ARM运行；推荐GPU x86节点跑仿真、本机仅控制显示，RK可网关/轻量推理但需独立移植。当前50051及50052仅loopback，不能宣称改IP就完整远控，50100可LAN仅数据；本轮未开放端口。见COMPACT_WORKBENCH_EDGE_DEPLOYMENT.md，未进行硬件移植/板上实测。

## 2026-10-30最新：用户指出示例差距，补齐继续；默认不启动UE

根VBS现调Start-Desktop.ps1，不传Connect、不自动UE；右上统一手动“启动仿真”走RuntimeManager。Start-Desktop沿用存在的E预览数据，显式DataDirectory/env优先，不依赖UE也能开GUI。实际VBS新增两层pythonw可见主窗，无UE/飞控/50051/50052/50100监听，测试后关闭。显式Start-SimulationPreview仍可全预览，旧根入口说明已过时。

新增device_catalog为实例表＋详情，旧DeviceManager隐藏表仍唯一草稿owner；名称修改不截断坐标，新增复制删除ID/保存原逻辑保留。workbench_polish固定安全动作、归属条、左栏机器摘要与诊断；高级控制内嵌折叠在150%切窗复现native AV，隔离改AdvancedControl独立小窗后100/125/150通过，关闭清零/随主窗关闭（未证明Qt底层根因）。训练工具与元信息同栏、真实组身份、策略折叠；资源五组、DATA_ROOT打开输出修正、GT/飞控分区状态不伪造。

94核心/62Qt（V4八项）及原生布局、实入口通过；本轮不自动启动UE测试、未重跑起降采集，之前verified只属于上一轮。证据ui-v4-20261030/refinement，layout为未连接截图、diagnostic为隔离记录。整套P1尚未逐项完成，不再泛称“主体完成”等同交付；剩余IR主布局/融合偏好/窄屏抽屉/日志计数/接口整合/编排叠加/航点详情见UI_V4_GAP_REVIEW.md。未重包提交推送，不改Fleet/IR/UE。

## 2026-10-30：V4 原生界面最新

用户已批准V4方案并授权实施。本轮P0/P1界面主体完成：shell_v4左侧五页导航（内部保留0编排/1工作台/2接口/3设置/4设备索引）、上下文与参数Dock；arrangement_v4复用同一OBS来源、左设备右位姿；设备常驻页有重读/退出草稿确认，DeviceManager.saved_snapshot按编辑器规范化值比较避免浮点假dirty。workbench_v3保留命令归属，属性选择不接管。sensor_forms原字段移动到折叠组，草稿/请求身份不变。training_client/layout_v4双路主画面+融合缩略/放大+集中保存动作，仍原Receiver/GT/存储、单槽解码；_theme为独立部署副本并测一致。

94核心/59Qt通过；真实run F1D5974F424BEF5B47E44EA89C0AFFFC参数FOV修改/回读/恢复、编排单OBS、GT关框仍有标签、停止保存保留接收器、融合弹窗及起降，7秒7组/约4.68FPS，ready/四RPM约0.0056后全部自有进程退出。证据以docs/evidence/ui-v4-20261030/verified为准，其它同目录final/owned-final/accepted/final-pass为中间或失败测试。DPI1920在100/125/150与1440在100/125可用；1440/150钳制到960×640逻辑最小窗口，不能宣称该物理屏适配。

发现高位直接Land触发AirSim60秒NNG超时/飞控重连，尚未修复；最终先手动下降到起点附近2m再降落，不代表高位关闭保护通过。前两轮恢复脚本又有缺完整sensor.configure字段的问题，最终使用真实表单完整快照恢复，未改协议。空中关主窗/直接关UE完整生命周期仍引用上一轮，不能冒称本轮重测。P2样本浏览、UE真实三维航线、进一步拖拽、完整性能基准未做。未改本轮UE/C++/IR/Fleet/模型，未重包/提交/推送。操作/代码映射/限制见UI_V4_IMPLEMENTATION.md；使用同一根VBS，重开源码GUI看新UI，旧包不更新。

## 2026-10-30：关闭保护最终验收（保留后续统一训练预览）

源码根VBS→preview_session Job管理UE/飞控/桌面及后代，桌面启动仿真由RuntimeManager管理，训练端独立子Job；主窗口异步退出，先停止本次训练并等待保存，UE已退出时清理所属GUI/后台；手动连接外部UE不结束对方。先挂起创建再入Job，避免venv子Python逃逸；不按进程名称全局杀。未提交传感器草稿原有确认保留。会话kill兜底不保证最后组在强杀/断电时完整。

发现真实session.log降落ACK超过原2秒后提前结束会话。本轮local_rpc支持有总时限的timeout，降落ACK等8秒；ACK超时继续看状态，短暂轮询错误在总30秒内重试，先核对原生/飞控run_id并按drone_id降落。没有ready不能声称落地。未改UE/C++/IR/Fleet/模型/后续统一训练UI。

94核心、54Qt通过。真实city run1760FAB04F33E18255BDC4A534282192空中关主窗口：9秒内确认降落，13.21秒整套清理、所属PID无残留；run36A337114440A13E557A16AEF7725E0A直接关UE：3.79秒整套清理、所属PID无残留。测试前无用户实例，结束全退出，不恢复额外预览。证据evidence/shutdown-final-20261030，操作与架构见SHUTDOWN_PROTECTION.md；未重包/提交/推送。

注意：最初分离快速视频/GT方案的历史实测在session-video-20261029（约9视频FPS、12组保存），后来用户要求统一预览已被GT_RATE_AND_UNIFIED_PREVIEW取代。当前仍为统一同帧图像+GT、默认显示5/保存1、实际约4.5FPS；不恢复旧双模式或固定2上限，不冒称30FPS已完成。


## 2026-10-29：无人机夜间灯光与新模型接入规范（当前最新）

Mavic 3 / Avata 增加4个自发光灯珠，左红右绿交替双闪，1.6s周期；时间覆盖18–06自动启用，未覆盖时依据主太阳朝向。待机可闪，运动暂停不冻结提示灯；day关闭。机体坐标电机/护圈外缘安装点近似（首次埋入电机不够可见，最终已外移），直径0.9/0.6cm、自发光参数64，非原厂灯语/光度学标定。StepNavigationLights每帧更新姿态，组件只创建一次；切型号复用4灯，不添加投射光。DeviceInventory新增navigation_lights状态。所有IR相机隐藏灯珠，热分类跳过；IR GT深度沿用隐藏列表，VIS灯实体可参与GT，Bloom不算实体轮廓。

新增build_navigation_lights.py生成Common/M_NavigationLamp，已接import_drone_models；E生成uasset回传F，既有Cook目录覆盖。F源4文件最小同步E，Editor构建成功。93核心回归通过；最终run EFFFB81F4471492DFD81DBADB7DFAE7E实际城市起降、Mavic→Avata→Mavic、白天/夜间3相位、始终4灯、两型号双路正GT通过。可见光中心区域色灯像素峰值Mavic红110绿71、Avata红43绿44，两者熄灭最低均0；状态与JPEG有缓存错位，测试另外按实际图像抓取actual_red/green，不能按查询状态标注缓存相位。结束恢复原型号、环境、相机及tracking，最终ready/四RPM0，自有测试进程全退出。证据docs/evidence/navigation-lights-20261029/final/report.json与validation.json。首轮证据保留，final为最终亮度版本。未验收多机长期/远距子像素灯珠/夜IR物理真实性，未Cook/重包/提交推送。

用户要以后AI一次完成接入：新增docs/DRONE_MODEL_INTEGRATION.md，列出当前FBX静态导入、uasset运行和其他格式需另做转换；尺寸/朝向/电机轴/旋翼转向/灯位/电池热区输入、Python与UE硬编码注册点、放置/训练保存/Cook/真实起降验收及可复制任务文字。只换外观默认shared_quadrotor，不等于新机性能。后续新增型号必须先读此规范，保留Fleet和现有红外。

## 2026-10-29：GT高频实测与统一预览（当前最新）

用户授权测试更高GT并取消双模式。UE gt_configure新增max_fps数字0.1–20、严格/原子校验，默认2兼容旧客户端；state返回gt_max_fps_supported=20和当前gt_max_fps，GT新增gt_annotation_cpu_ms。新UI请求max_fps10，预览默认5/保存1，UI各0.1–10（是上限）。14600KF/B580实采正样本2/5/10/20档各15秒为1.84/3.86/4.63/4.74组/s，仿真30Tick；短轮询后5/10为4.19/4.84。不能把20当可达实帧率。

训练UI已移除video/sample模式与VideoPreview线程/视频FPS，始终用同帧GT包，单“预览GT框”仅控制叠框；隐藏后标签/融合仍在，保存原图不带框。默认5预览最终GUI4.51FPS、保存9组、运动中控制请求1.49ms中位。Receiver解码缓存复用，最新单槽33ms轮询，legacy frame信号兼容普通包。发现源/显示重复限速按arrival抖动丢帧至2.8，已改预览驱动源时显示每个新样本，最终4.51；保存独立限速、不补帧。旧双模式live测试由verify_unified_preview_live替代，其他模式引用已调整。

Editor、93核心/52Qt通过，F/E GT h/cpp/Bridge SHA一致。runFCE5768E462AF7B4B78B748C61078485，两轮起飞悬停阶梯、最终运动GUI+GT开关不换帧/隐藏仍存正标签、在线修改/换源、非法速率原子拒绝均通过。docs/GT_RATE_AND_UNIFIED_PREVIEW.md和evidence/gt-rate-20261029；最终GUI报告位于final/，根下unified-live是修复前限速问题报告。测试前无用户UE，独立E gt-rate-data；结束恢复云台和后端默认2、ready/4RPM0，自有进程退出，用户Fleet/资产/IR未改；未重包提交推送。视频/样本双模式不再是当前产品行为，旧档案仅历史。

## 2026-10-29：长按延迟、连续放置与训练在线操作（当前最新）

AirSimClient每设备1在途set_input+1最新待发，松键0覆盖旧值，动作/断连/错误清待发；不积累历史按键。后台高频输入使用现有SingleTaskCall替换，避免每次同步CancelLastTask及flight.sync_state；Fleet复用当前state而非重复SDK读取。其他动作保持原取消。注意Fleet复用必须dict(result)再加fleet，直接把result放进自己的fleet会循环JSON，已单测覆盖。

UE放置保留点按，新增每键独立计时：.3s后10Hz连发，不追赶卡顿漏步，松键停，映射WASD/QE/RF和Shift细调不改。训练端移除连接时禁用策略/目录/数据源；Receiver锁+revision快照热更新，设置改变丢弃在途旧策略样本；VIS/IR自动异步重订阅，主机端口云台编辑后点“应用连接设置”，无需手动断开。视频线程stop后wait(0)+Qt定时器收尾，不阻塞UI。GT/融合仍需sample视图，不能把旧GT叠到快速视频。

Editor build-input-online通过，F/E Demo.h/Placement SHA一致；91核心/51Qt通过。真实run986B530847DB75951659FFB049B9EBFD，60秒持续输入493ACK，首末10秒中位16.87/16.82ms、零输入6ms确认、每设备最多1在途；随后实际落地4RPM0。不是物理制动/画面端到端时延保证。UE实际长按D1s70cm、松键不再动与原点按/Shift通过；训练GUI在线政策/目录保存、双路改单路清旧图、应用连接保留选项通过。见INPUT_AND_ONLINE_SETTINGS.md、evidence/input-online-20261029。独立E input-online-data，结束恢复云台角度/跟踪、ready/4RPM0且自有进程全退出；无用户UE被关闭、Fleet/资产未改、未重包提交推送。

## 2026-10-29：WASD/QE/RF 与运行中实时放置（当前最新）

用户纠正上轮放置体验；已将箭头/PgUpDn改为WASD按设备朝向移动、QE转向、RF升降，10cm/1°、Shift1cm/0.1°，Home同时复原转角，确认结果携带yaw_deg。编排新增每设备朝向输入，默认实时应用；放置确认或坐标编辑400ms去抖后异步提交，无需场景重载，保存只负责下次初始布置。新增headings_deg可选预设字段，旧预设兼容；Fleet合并仅编辑设备的位置/偏航。

UE live_placement_supported、placement.validate/apply带scene/run/token，云台更新完整装配；无人机由50052先SetPose重置物理位姿/速度（必须frame_id！初测漏该字段实际RPC报Unknown exception，已修复并重测），50051再校验DynamicsSource位置/朝向并更新原点。ready/无未完动作/四RPM0才允许，空中与旧run拒绝；普通失败恢复物理位姿/原点。Qt单请求+设备队列、回包按token/device/run匹配、断连/换场景清理，其他驾驶对象的placement确认不污染遥测。训练网关不开放控制。

Editor构建通过，F/E Demo.h/Placement/Fleet/Bridge SHA一致，E manifest现回到UnrealEditor-test.dll。90核心/47Qt、真实city云台/无人机同run位置+偏航、移位后2秒无弹回、移位后实际起飞/降落与拒绝空中放置、真实UE W/E/R/Shift-F/Enter及实际GUI两设备自动应用/保存全部通过。run5D44BD2C4849FEE678E0A991B6043C5A，证据evidence/live-placement-20261029。测试前无用户UE，使用E独立live-placement-data，保存配置按字节恢复；用户Fleet/红外/模型不改。结束恢复位姿、ready/4RPM0，自有进程全退出，未重启常规预览。详见LIVE_PLACEMENT.md；未重包/提交/推送。

## 2026-10-29：启动阶段、放置微调、VIS响应与固定目录追加（当前最新）

见[本轮说明](STARTUP_PLACEMENT_VISIBLE_STORAGE.md)。用户纠正保存架构：新双路及单路使用所选根下visible/IR各自images/labels/annotations，直接追加，无samples逐组/无pairs。schema3保存counterpart_directory/image，原命名/负样本/过滤逻辑保留；训练兼容schema2组目录及旧单路。普通写入/发布异常回滚本次新增；固定两模态目录无法沿用整目录原子提交，强杀/断电坏组由完整性检查拒绝。历史数据不动。

preview_session每次独立状态文件→桌面StartupStatus非阻塞轮询，UE加载/飞控初始化/ready自动连接/失败提示；飞控必须同新run。失败桌面保留直到用户关闭。UE放置新增空格锁定、方向键XY/PgUpDnZ=10cm、Shift=1cm、Home清零、锁定Enter确认，首次微调自动锁定；Z不低于表面，120秒超时；仍只草稿，保存加载生效。可见光Capture源PP饱和.88/对比.96/Gamma1.03/Bloom.08/暗角.08/颗粒.04，红外不改，无几何变换；只属实拍风格基础近似，未实机标定。

86核心/43Qt通过；3组此前真实JPEG/GT重导出新结构通过，非新VIS实时验收。E Editor带后缀模块构建通过，F/E Demo.h/Placement/Sensors/Bridge SHA一致；E UnrealEditor.modules当前映射UnrealEditor-test-1029.dll，下次启动会加载新模块。常规用户UE PID1848运行preview-data，本轮从未关闭/控制/采样该会话，也未新起测试UE；新UE微调按键、VIS实际观感及完整根入口启动仍待现场验收。证据evidence/startup-placement-visible-storage-20261029。请勿将旧运行实例当已加载本轮代码；用户正常退出整套后根VBS重开。未重包/提交/推送。

## 2026-10-29：采集上下文命名与整组直接保存（当前最新）

用户要求以传感器/机型/气候命名、不要额外pairs文件，并询问FPS。新storage.py使用VIS/IR_机型_天气_场景_设备_s会话8位_共享组ID24位.jpg；多机型组合、负样本仍用场景机型。GT快照新增environment、scenario_models、context_source=capture_tick，环境/型号在同次采集读取，不用稍后sim.get_state冒充。天气是仿真配置标签，clouds/rain/fog非零组合，零为Clear；显式hour覆盖按6–18标Day否则Night，精确参数仍留JSON。旧后端缺上下文明确Unknown。

双路保存改为samples/<组ID>/{images,labels,annotations}：同一images目录中两张原图除VIS/IR前缀外同名后缀，各有同名YOLO与JSON，不再生成pairs文件。先暂存完整六文件、整目录提交，写失败不发布半组；任一路被策略排除则整组跳过，合法双路负样本保存两图和空标签。暂存清理只限已验证位于本数据目录的自有临时路径。原单路入口保持images/labels/annotations，可读命名。历史文件不改名/删除。train.py递归支持新/旧目录，--sensor默认infrared选择模态；配对读取检查另一图/标签/JSON、ID、时间、互指及SHA，防混模态和坏组。

未改变FPS限制：实时无GT视频默认轮询20、上限30（不保证新帧率）；GT显示/保存默认各1、范围0.1–2，每秒一组双路是2张原图。未勾保存时不落盘。此次隔离city run_id A0E91D454AF73E94E3DC1CB7311AC7D4源VIS/IR短测9.89/10.38新帧/s，六组GT1.76组/s，非双机长期性能承诺。

Editor build-dataset-context通过，GT h/cpp F/E SHA一致；82核心/36相关Qt通过；晴天白昼、雾天夜间命名及采集Tick元数据、真实负样本机型/双空标签、无pairs、递归IR读取通过，模拟写满磁盘无半组与旧目录兼容单测通过。证据docs/evidence/dataset-storage-20261029，含3组完整实采示例。仅增GT元数据与训练保存/读取逻辑；相机、红外材质、FPS限流、用户Fleet/配置未改。测试运行前查无用户UE；自有测试最终ready/4RPM0且退出，不重启常规用户预览。未重包/提交/推送。

## 2026-10-29：单一红外、轮廓柔化与局部热区（当前优先）

用户认可上一版作为基础。已移除成像版本选择及清晰/实拍两个预设按钮和PRESETS数据；固定facade，白热/黑热/增益/采样/FOV等参数保留。内部单项隐藏字段维持请求兼容，不提供旧模式；旧后端无facade能力不提交新profile。修改对应Qt回归，禁止恢复旧预设。

最终灰度加入低强度背景光学低通，目标及紧邻像素保护；灰度基础曲线不改。共享原生函数/回放同步，单位测试验证轮廓极值下降和微小目标不变。Mavic新增4个真实Rotors轴心投影，Avata路径保留；电池本机后向偏置，Mavic热点半径电机1.6cm/电池4cm，Avata1.5/3cm。仅目标可见像素近深度叠加，不是每零件真实辐射/自遮挡；热量由真实RPM派生功率、快慢热惯性控制。

查到另一根因：FOV很窄且背景全是天空时，背景AGC会把整架机压到同样高亮。目标显示现混合AGC结果与归一化热信号平滑映射，保留局部差别，末尾再反转黑热；源热信号/GT不改。勿退回只做目标×0.82再硬夹1的旧实现。背景仍为上一版tanh曲线。

最终Editor与Facade生成成功且资产E→F回传；73核心/40Qt/原生数学/回放编译通过。实际run1108EEDA4557A2903C3AEA82329521DB，Mavic/Avata各20秒悬停升温、双路GT、落地ready/4RPM0/恢复Mavic通过。Mavic目标原信号P25/P99 .344/.469，灰度P25/P95约164/193；Avata .362/.435、168/185，掩码/JPEG临近采集非精确同帧零件测温。最终测试已退出，已通过根目录VBS重新打开常规preview-data供用户使用；不要误结束该常规预览。

数据50100短测6组约1.83组/s，源码限每设备每传感器0.5秒，UI默认显示/保存各1FPS/最大2；已加产品解释，没有冒然提升限流。下一步快速视频与同步GT采样分离，不能把旧GT贴到新视频。最初用户预览处于暂停、降落等待未完成且飞控曾报连接超时，未当成降落通过；本轮正式验收另在正常推进的隔离实例完成。

见[当前说明](IR_CURRENT_MODEL.md)，证据evidence/infrared-current-20261029；未重包/提交/推送。

## 2026-10-28：修复桌面读取/预览、楼宇对比与训练启动（当前优先）

详见[本轮修复](PLACEMENT_TONE_TRAINING_FIX.md)。用户实测暴露上轮遗漏：core/devices.py误将[pitch,yaw,roll]的yaw90判为倾斜。现检查0、2轴，保留用户90°朝向；核心与Qt新增真正覆盖非零坐标/设备列表/按钮可用/请求的测试。上一轮原生预览通过并不能覆盖桌面加载。

楼宇HLSL明确屋顶/墙体，增强材质/法线层次；CPU改AGC后的背景tanh中间调展开+目标×0.82、最后反转黑热，其他模式不变。旧0.72函数仅供历史回放，flag1旧/flag2新。实际同机位背景P5–P95 133–147→71–169，中位144→131；重点是对比层次，非整幅提亮。云时间与重启前后无人机位置不同，不能当同目标像素A/B；新悬停目标中位168/P95172/>235为0。用户参考未入库，非温度/实机校准。

全局右上“打开训练端”由training_launcher.py启动pythonw，无console，传主机/选定云台/50100；已连接时自动连。已有窗口复用，独立运行不随桌面关闭。发布包无Training/WISEYE-Training.exe时提示缺失，不谎报可用；本轮源码验证，未新打包。 验收后已用根目录VBS恢复常规preview-data预览供用户使用，UE仍正常运行；不要把它误当未清理测试实例。

E Editor与Facade生成成功并回传F，73核心+36Qt+原生数学/回放编译通过。run2C45EBCE4E2B09152A6177AC2AF2B6B5实际桌面读取、预览、第一次左键确认且仅草稿、按钮启动训练自动双路与复用窗口、Mavic起降双GT通过，最终ready/4RPM0且自有测试退出。证据evidence/placement-tone-training-20261028；未提交/推送。

## 2026-10-28：启动优化、角位与模型放置预览（当前优先）

详见[完整说明](STARTUP_PLACEMENT_IR_TUNING.md)，证据`evidence/startup-corner-tone-20261028`。Editor-game取消AssetRegistry启动全量扫描，真实初始化42.23/30.72/29.93秒；正常Editor/Cook不改。显示名WISEYE，内部test模块不改；文字HUD移除，屏幕光追警告单独关闭，日志保留。

F Fleet/Layout/Scene与E三处配置同步：PTZ(-27066.552734375,-2092.68798828125,4059.1168165)，z4055楼面，两碰撞楼边各内缩100cm；Mavic(-27400,-2600,4080)，同楼顶±100cm九点同高。旧远处起点被屋顶结构遮挡，候选(-28200,-3000)为平台顶，均未采用。角位真实起降与双路GT最终通过，证据报告passed=true；碰撞/遮挡保留。

默认facade/contrast1.1/StableAGC，降低墙体基值、保留屋顶变化，AGC后背景幅度0.72（天空/目标不改），Facade资产已由E回传F。旧机位同参数手动增益对照中位灰度193→111，非物理测温或实拍标定，不将新机位和旧机位直接比较。

模型放置创建独立无碰撞/阴影/自定义深度的设备副本，保留尺寸姿态、随鼠标命中更新，未命中隐藏；与确认共用PlacementAnchor，左键仅草稿、右键/45秒取消。Nanite副本bDisallowNanite，原资产不改；M_PlacementPreview.uasset已回传F，configure_placement_preview.py可重建，曝光补偿青绿色。每路VIS/IR HiddenActors排除副本，训练深度沿用对应隐藏表；OBS展示副本。UI改“到UE预览放置”、显示悬停坐标。尚无旋转操纵器/占地冲突验证。

Editor编译、72核心、35Qt、原生数学通过；UI最后改动后取点5Qt再过，回放工具编译过。真实PTZ/Mavic/Avata鼠标移动/左键坐标/离窗隐藏/右键取消通过。Mavic角位飞行run AB3F783249EA9AF0F2035E917A6E9B50双路GT通过；最终颜色预览run FA431E364FD3C90E22FAD5A9D18F9320，恢复Mavic/ready/4RPM0并退出自有进程。下方其他AI的训练融合增强保留，未重包/提交/推送。

## 2026-10-28：双光心融合对照、时差/中心差、缩放与独立FPS（当前最新）

用户要求恢复VIS/IR融合以观察差异，并增加放大、显示/保存帧率。仅修改training_client与相应测试/说明，UE、相机默认值和用户楼顶Fleet未改；入口仍Start-Training.vbs。融合新增raw（默认，只统一FOV尺度，保留视轴/基线差）和rotation（按UE实际相机旋转矩阵投影到IR网格，补偿旋转不补基线深度视差）。原同光心拒绝检查保留mode='strict'，旧dual-camera live测试已显式使用strict。

融合下方显示仿真采集时差ms、整对样本请求返回耗时ms、基线cm和共同目标GT中心差Δx/Δy/距离px；pairs清单保存时间差/取帧耗时。采集同Tick时Δt=0不代表零传输延迟；中心差受模态可见范围影响，不是配准准确率。raw/rotation均为观察叠加，不是学习融合/深度配准。

新增view.py：三路滚轮缩放、拖动、适应、实际像素1:1、独立实时放大窗口/双击打开，百分比按实际显示像素计算，断连联动清屏。rates.py独立单调时钟调度，显示/保存各0.1–2FPS在线可调，源采样跟随较高者，不补帧；记录可在线开关，显示实测更新/保存频率。GT接口上限仍2FPS；配置时间不计入取帧周期，2FPS正常限流可取消退避重试。低显示FPS按周期判断过期。

72核心与31项相关Qt通过；真实city run_id 785B6501479A746720D27B9A3612EF75、12cm基线/FOV5°静态目标：仿真采集Δt0ms，GT中心差raw105.10px、rotation78.75px。7秒阶段显示2/保存0.5实际收到13/显示11/保存4；下一阶段显示0.5/保存2收到12/显示3/保存12，实测显示0.45/保存1.79FPS（设置是上限）。放大窗口307%截图及实时跟随通过。证据docs/evidence/training-inspection-20261028；结束ready/四RPM0，自有UE/飞控/数据服务退出，未飞行。未新编译UE（本轮无UE改动），未重包/提交/推送。

限制：本机静态验证，无双物理电脑/运动目标配准精度/高FPS承诺；基线需要深度相关配准才能消除视差。不要因能叠加就称为像素已对齐。其他聊天/既有变更仍保留，包括DefaultEngine.ini末尾空行提示，未擅自清理。

## 2026-10-28：独立双相机与楼边1机1云台（当前最新）

用户要求两相机有视轴差，并将云台/无人机放同一楼顶、云台靠边。原本双Capture独立渲染但同光心；现共同OpticalMount下两个同级相机，世界物理厘米偏置不随模型缩放，默认VIS(0,-6,0)/IR(0,6,0)cm，IR pitch/yaw偏差0.1/0.2°（仿真假设非实机标定）。传感器页各自6安装/视轴字段，sensor.configure严格有限数值/原子提交、旧后端能力门控，本次运行有效。热区投影与PNG导出改用实际IR/被导出相机，GT按各自位姿。IR不读VIS RenderTarget，但背景仍有外观代理，非物理LWIR。

城市F Fleet/Layout/Scene已按本次授权更新为uav-01+ptz-01；云台(-33000,-2075,4104.1168)，底面z4100、距碰撞楼边1.07m；无人机(-33800,-2900,4125)，同屋顶内侧约11.5m。各自9点碰撞平面核实。E Config与隔离数据同步，日常preview-data当时尚不存在，下次从F创建。旧模型/城市资产不改，多设备功能保留。训练默认ptz-01；无配准的双路保留显示/采集/独立GT但拒绝直接融合，后续需深度/内外参配准。基准manifest v2，不与旧地面v1直接比较。

E Editor build-dual-camera-final通过，68核心+35Qt；最终city run_id 1257AD154F9416E54CA522918D3273D1几何三姿态12cm、独立参数/启停、4非法请求、同刻独立位姿、PNG元数据、50100双路/不同FOV/负样本/恢复通过。Mavic楼顶真实起降，z4119.27→4268.87→4119.27，最终ready/四RPM0；悬停两路各有GT。自有进程已退出。F唯一源/E构建，说明DUAL_CAMERA_ROOFTOP及evidence/dual-camera-rooftop-20261028；未重包/推送。

## 2026-10-28：根目录唯一启动入口与冗余清理（最新）

用户要求清理根目录冗余入口。现仅保留Start-WISEYE-Studio.vbs，语义从“仅桌面”改为隐藏启动Start-SimulationPreview.ps1（当前E城市预览+飞控+桌面），加载后用户点连接；不自动同步/编译。旧CitySample.vbs、Desktop.cmd、ProjectAirSim.cmd/vbs、WISEYE.cmd实际删除，开发PS保留。Start-Desktop.ps1先找F builds/python-env再.venv，已有UE只需该脚本-Connect，勿再次启动主入口。训练端Start-Training.vbs保留。

实际另删根目录运行log及8目录86个pyc；总移除文件原大小约0.96MiB。README/用户指南/文件结构/开发引用与Setup提示已更新，历史证据旧名保留。VBS含空格路径无副作用桩执行、StartPS AST和桌面解释器/参数校验通过；非完整UE启动验收。详见CLEANUP_REPORT最新节及entry-cleanup-20261028.json；未推送/重包。

## 2026-10-28：训练端单入口、仿真主题、双路同刻与融合（当前最新）

按用户要求移除 training_client/Start-Preview.cmd、Start-Gateway.cmd，仅保留 Start-Training.vbs；已真实cscript启动可见训练窗口并正常关闭。数据服务由 integrations.ProjectAirSim.run_wiseye_flight 主进程自动启动/收尾，监听0.0.0.0:50100，仅数据/策略命令；端口占用记录错误并让仿真继续，不接管/结束其他进程。训练电脑只需填写仿真IP；源码普通AirSim入口自动生效，旧Shipping未重包。

新工作台位于 training_client/workbench.py，直接复用apps.desktop_app.ui.theme；目录单独复制时使用相同_theme快照（测试校验一致）。品牌/深色侧栏/多源卡片沿用仿真风格。默认VIS+IR同时接收，三视图（可见光/红外/融合），亦可单路；GT显示和红外权重即时调整。Worker接收/保存，错误/过期清三路及关联；原图、标注分visible/infrared存储，pairs清单关联，不把融合预览当训练原图。

UE新增paired_training_samples_supported、camera.sample_pair_request/frame，共享UUID，在两路可排队时强制同Tick捕获，同simulation_time_s；独立frame_number不要求相等。融合根据共同光心/姿态及FOV在IR像素网格对齐VIS，只在共同视场透明度叠加，额外IR视场保留原图，避免16:9拉伸至5:4；不同光心/姿态拒绝融合但继续显示原图。未使用学习融合或跨光心深度配准。

E Editor build-training-pair通过，三处UE源F/E SHA一致；68核心、20既有Qt+6新增融合Qt测试通过，独立目录隔离导入通过。实际city run_id 96F72B7D4C0EBB30D552D7A805C0A00F：自动服务（无单独网关进程）、同刻双路GT/不同FOV融合、停IR拒绝旧对/恢复新对、双路负样本、单路兼容、真实Receiver线程三视图截图通过。证据 docs/evidence/training-fusion-20261028；本机未起飞，结束ready/四RPM0，全部自有UE/飞控退出且50100无监听，用户Fleet/城市资产未改。

仅低频按需采样原型，UI约1Hz，未做双物理电脑/长时多源/运动目标精度/真实训练/新版Shipping。单源建议一个采集客户端；服务无认证TLS。手动训练按模态目录运行；尚无自动训练/模型上线。说明docs/TRAINING_DATA_INTERFACE.md、training_client/README.md已更新；未提交/推送。

## 2026-10-28：独立训练端与同帧 GT 数据出口（当前最新）

用户要求仿真与训练分离，局域网另一电脑接收图像/GT；部分遮挡和部分出画按配置保留，完整空标注作负样本，仿真端不显示 GT 框。新增 WiseEyeGroundTruth 独立场景/实例深度采集，与同阶段传感器图像一起 GPU 读回并缓存；camera.gt_configure/sample_request/sample_frame 和 training_samples_supported。UUID token 关联单次请求，frame_id 带 run_id/设备/模态/帧号。可见像素 bbox、可见比例与裁切标志；不改现有热成像 stencil 或地图资产。策略过滤仍可见目标记录 ignored_objects，暂不作为普通负样本训练；完全遮挡/出画的成功空标注可训练，失败不得训练。

新增 training_client 独立目录：标准库数据网关默认本机50100（--bind 0.0.0.0供可信LAN）、PySide6接收/GT叠加/保存原图+JSON+YOLO标签/空负标签、手动train.py入口（独立验证会话与校验）。无仿真模块依赖；仿真保持原有RTSP，训练使用成套样本。启动/接口详见 docs/TRAINING_DATA_INTERFACE.md、training_client/README.md。入口 training_client/Start-Gateway.cmd、Start-Preview.cmd；新版UE源码预览用scripts/Start-SimulationPreview.ps1。

F唯一源码，E:/Projects/WISEYE-IR-Work Editor最终构建通过，8个相关源文件F/E SHA一致；67核心+20相关Qt+1原生GT自动化通过，接收GUI实际线程与GT截图通过。最终真实city run_id ADB6EFE4490AFB9B5C9F5D8ACE39C4CF，IR640×512/VIS1920×1080同帧GT、部分遮挡保留/过滤、部分出画保留/过滤、另一云台遮挡空标注、负样本落盘、停用错误/非法配置原子拒绝/设备隔离/网关拒绝飞控通过。短时观测不采样29.998Tick/9.890IRHz，1Hz采样29.983Tick/10.214IRHz，仅单机短测，不是无开销结论。证据 docs/evidence/training-interface-20261028，包含完整接口报告、原生摘要和独立界面/带框图。使用隔离gt-test-data；未改Fleet/城市资产，未起飞，结束ready/四RPM0，自有UE/飞控/数据网关均退出。

限制：默认UI约1Hz、接口最多2Hz/传感器、每源一采集客户端、只保留最近样本；额外深度捕获与复用资源有成本。部分出画为目标光栅触边，非精确完整网格比例；透明/LOD/抗锯齿/子像素/运动目标仍需专项验收。仅drone类；没有多物理电脑、长期网络、实际YOLO训练/效果、自动增量/模型上线验收。手动训练依赖需在算法电脑安装；无认证/TLS。旧Shipping不含新接口，未重包/提交/推送。后续先双机数据链路和动态目标对齐，再采集独立验证集跑模型训练。

## 2026-10-28：红外P0/P1探测器优化完成（当前优先）

新增同帧原始信号回放、天空掩码空间滤波、稳定AGC、自动/锁定/手动窗口、亮度及种子，UI两预设仅填草稿并保留FOV；能力门控、旧agc_enabled兼容、按云台隔离。目标排除天空平均，2×任意目标子像素保护；光学PSF仍影响目标。未加入时域滤波/物理辐射/夜间标定。camera.signal_recording显式开启后camera.signal_frame取归一化float32及掩码，默认不录，非测温数据/实时通道。

E build-detector-replay Editor通过、60核心/27Qt/原生数学通过。最终run_id 30E31CB642A66C6E310B27A03183E13E同原始云帧天空高频指标0.522→0.382（下降26.7%）、重复回放逐字节一致；连续实时云截图受UE随机采样干扰，不据此宣称收益。8非法请求原子拒绝、手动/亮度/锁定跨转向和停启/2×掩码/设备隔离通过。Avata真实起降冷却回归通过，最终恢复Mavic3、4RPM0。1×云视角短测IR9.95→9.93Hz，CPU6.26→8.74ms，缓存年龄P50 97→131ms；不是端到端/长期验收，不能声称零延迟开销。

F唯一源码/E最小构建；Facade新天空标识资产已回传F，Fleet/Minimal/Reference/Classified SHA不变。说明INFRARED_DETECTOR_PILOT，证据evidence/infrared-detector-20261028（含单云原始帧）。未重包、未推送，旧ZIP不含改动。下一步真实数据统计标定、远距1–3像素目标、独立云辐射与夜间，再长期性能/Cook。

## 2026-10-28：云层红外和传感器快捷启停完成（当前优先）

新增按云台sensor.set_enabled严格布尔接口，sensor_power_supported能力；传感器页顶部三快捷按钮即时启停VIS/IR/雷达，不提交其他参数草稿，按请求ID/设备确认、旧UE禁用新按钮。原参数页应用方式保留。停用取消后续SceneCapture/射线扫描，清JPEG和热统计并推进读回版本，旧GPU任务只收尾不发布；UE主视图IR后处理权重归零、HUD不再画停用缓存。capture_sequence/scan_sequence用于实际停采检查。桌面沿用enabled停订阅；RTSP收到sensor_disabled后释放对应FFmpeg，恢复新帧再建，低频探测保留。少量配置/RT/view-state内存、热状态与基础UE/其他设备/观察视角仍运行，不能说整体零GPU/零显存。

环境增加clouds[0,1]、晴朗/多云预设与能力回读；默认0，非0创建同场景实际UE体积云。当前静态city没有SkyAtmosphere，运行时补建必要大气和太阳光标志；关云后移除补建项并恢复，不保存地图。独立M_Cloud_Runtime实例让引擎云父材质/纹理成为Cook依赖。M_IR_Facade新增实际天空亮度/色度云灰度代理。关键修复：采集远背景是有限深度，旧100km阈值漏掉天空，空CustomDepth/Stencil造成仰拍247k像素误当热目标；楼宇模式按10km远背景判天空，分类分支排除>=10km的空自定义深度。曾尝试法线/材质标识未解决，最终代码不含这些试探。10km之外地形/目标不属于当前城市模型，需要另做天空掩码和长距方案；不是实测云温度、LWIR辐射传输或夜间标定。

E最小衍生Editor build-cloud-acceptance成功，F唯一源码；60核心/23Qt通过。最终同run_id 2C2D0F634D18A9E40265C49FC3986437真实city：VIS云开关平均差22.83灰度、IR10.52、纯天空ROI P95-P5=44、天空误热目标0；VIS-only/双光/IR-only/全停、采集序号和输出停止、另一云台继续、快速开关恢复、非法请求原子拒绝通过。旧RTSP编码器生命周期是Mock回归，未新做外部RTSP长期负载。另跑原材料/Avata真实起飞悬停降落冷却回归通过，恢复型号/环境/传感器/云台，最终flight_status ready、4RPM=0。参数页实际停IR与雷达截图后已恢复。F Fleet和旧Minimal/Reference/Classified资产SHA保持；Facade更新、新Cloud资产均回传F并匹配E。本轮自有UE/飞控进程已退出。

说明docs/CLOUDS_AND_SENSOR_POWER.md，证据docs/evidence/clouds-sensor-power-20261028，含云开关对照、真实VIS、快捷开关截图和target-regression。入口仍Start-InfraredPreview；云量建议白天12点、多云65–75%、楼宇热像1×/detail0.8。云有额外GPU开销与低采样颗粒，近楼可能偏白；未做云层端到端/长期多设备性能或新Shipping。原有SunSky/过时CVar/光追几何预算等日志仍有，不能声称全部告警修复。未推送、未重包。下一步云信号独立通道/夜间、颗粒与曝光调优、长距地形、最终Cook/多设备长测。


## 2026-10-27：楼宇热像外观试验通过（当前优先）

用户以实拍拼图b为参考，新增独立M_IR_Facade及facade模式（UI“楼宇热像 · 试验版”、能力facade_available）。沿用classified类别/目标/FP16/AGC/PSF，增加deferred GBuffer BaseColor/Roughness/法线的有限立面纹理和低信号天空；未知竖直表面是启发式，非语义/温度测量，不解决透明玻璃真实反射和LWIR光学。保留旧四模式、资产回退与默认reference；背景细节参数控制新纹理。原M_IR_Classified/Reference/Minimal和F城市Fleet哈希不变，只新增自有材质，不改城市或原始共享材质。

F唯一源码，E最小衍生工程Editor编译成功；58核心+18Qt通过，真实city两固定方向对比/640×512灰度/极性/细节/原三模式检查通过并恢复环境传感器云台。新版上部楼宇窗格从单色中显出，仍有墙面粗糙、玻璃未标定等限制，不能声称达到实拍/Anti-UAV分布。初轮约30Tick/9.95IR Hz，重复短测28.5–28.6Tick/9.34–9.90IR Hz，缓存P50 207–224ms；classified对照29.5–29.8Tick/9.55–10.02IR Hz/P50约198–199ms，CPU约10–12.5ms。不是端到端延迟测试，也不声称没有开销。无新飞行测试；此轮仅楼宇背景。

说明docs/INFRARED_FACADE_PILOT.md，证据docs/evidence/infrared-facade-20261027（不含用户实拍拼图）。Start-InfraredPreview运行后手动选择楼宇热像，1×/FOV50/blur0.8/contrast1.15/detail0.8。Prepare-ThermalCity -Apply增加Facade资产生成，新机仍需准备标签并重新Cook。旧Shipping未更新、未推送。自有验证进程已结束。后续：真实同步视频拟合、混合/透明材质、降墙面纹理与性能/端到端。


## 2026-10-27：材料热像与Avata局部区域完成（当前优先）

新增独立M_IR_Classified与classified模式，原三个模式在新材质内保留，默认仍reference。背景组件按名称保守分类，混合/未知跳过；范围为初始设备周围120m，FastGeo保留低位1–6分类Stencil，32以上热目标；实际视角道路/砌体/植被/金属进入GPU，玻璃/水体当前无可见覆盖证据。昼夜是environment时间混合的工程信号预设，不是温度/发射率/热惯性求解。Avata当前跟踪目标4Socket局部投影、机身/深度遮挡、随所属实际RPM热状态变化，非网格热分割；其他Avata未同时投影。柔和高亮保留部分局部灰度。

修复相机继承模型缩放导致热斑投影单位错误：InverseTransformPositionNoScale统一世界厘米，GPU motor_region_pixels实际冷26/悬停25/落地热25，修复前该计数0，已完整重测。诊断G/B通道归一化，最终PNG/JPEG仅用R热信号灰度。新class_pixels显示视角材料覆盖率，非准确率；UI补首次回读仍显示未确认的状态文字。

F唯一源码与旧城市/用户Fleet保持，M_IR_Reference/Minimal哈希不变。只在E:\Projects\WISEYE-IR-Work城市副本保存组件标签；6295标签/15051组件，5710Actor描述。保存严格限已修改城市Actor包，保护非自有深度标签；规则版本/保留ID/信号范围检查，重跑可清除不再匹配的自有标签。Prepare-ThermalCity.ps1默认审计，WinPS5.1真实审计通过；底层Apply重跑/选择性保存通过，city.json与city_audit.json分开。仅标签/材质准备脚本在Git，第三方城市Actor包不入Git。新电脑/重建副本/重新Cook前须在构建副本重做标签。旧标签副本应使用新材质内的对照模式，完整回退旧二进制/资产需使用未标记城市副本，避免低位Stencil被旧公式当热目标。

最终Editor build-material-acceptance.log成功；58核心+17Qt+原生数学通过。真实city 1UAV2PTZ ptz02全流程：640×512分类像素sum327680，72.2%已标记，昼夜/极性、Avata实际起降RPM4928.59/可见局部区域/落地RPM0/冷却/型号云台环境参数恢复；旧原始/增强/噪声/4非法请求兼容通过。最终材料1× IR9.96Hz/UE30Hz、cache P50/P95133.1/133.5ms、CPU10.03ms；对照参考99.6/100.8ms，不能当端到端差值。报告、对照、目标裁剪和prepare报告在docs/evidence/infrared-materials-20261027。自有测试进程已停，无未降落飞机；旧ZIP未Cook更新、未推送。

入口仍Start-InfraredPreview.ps1，手动选择材料热像，保持1×；环境开启时间控制比较12点/0点。完整说明INFRARED_MATERIAL_PILOT.md。已观察VSM512页池溢出日志，未修复，不声称零告警/长期稳定。后续优先处理玻璃与混合材质、背景过平和规则误归类、实际距离/视频/真实校准、多目标局部区域与完整端到端/打包验收。

## 2026-10-27：实拍参考红外源码试验（当前优先）

用户授权参考实拍图改进并测试。新增M_IR_Reference/HLSL与原生WiseEyeThermalMath：FP16归一化信号、可选1/2×采集后回640×512、CPU后台Gaussian PSF/百分位平滑AGC、同一处理结果用于JPEG/PNG/HUD/UE光学视图；默认1×。按云台能力/请求ID保留草稿与严格参数校验。热状态由所属无人机实际新鲜RPM驱动电机/电池RC升温冷却，机身投影电池斑是近似；Mavic沿用部件名，Avata未细分电机。环境仍是结构/弱RGB代理，不是整城温度/发射率或物理测温，未校准Anti-UAV，用户实拍拼图未入库。

唯一主源码F:\WISEYE-Studio。用户此前自行删除的E:\Projects\WISEYE-Studio、E:\Projects\WISEYE-BuildWorkspace已确认不存在；本轮最小衍生构建E:\Projects\WISEYE-IR-Work重编Editor，不是第二开发源。其城市/插件大内容联接E:\Projects\Scene\CitySample，少量自有资产实体复制，SimLibs仍引用已有安装；不可直接复制此工作区发布。F首次扫描重现disk153/UASPStor129后已停止负载并改用内部资源。新E城市复制/装配后，将6个自动系统Actor保存为EditorOnly，避免它们后台启动。用户F模型、城市/Fleet位置不改。

最终Editor构建成功 build-validation.log；54核心+16Qt+原生数学通过。真实city ptz02完整检查：640×512灰度/VIS1920×1080、三模式、白黑热、AGC开关、1/2×、5非法请求原子拒绝、PNG/JPEG一致、FOV角尺寸、真实起飞RPM升温/降落归零冷却及恢复通过。最终1×约9.96Hz、cache P50/P95134/181ms、CPU10.36/15.22ms；2×约8.52Hz、231/302ms。另一次同二进制短测1×166/200ms，不能将单轮缓存年龄当端到端延迟。报告/原图见docs/evidence/infrared-reference-20261027；用户随后正常关窗，守护退出，当前无UE/飞控运行。

新源码入口scripts/Start-InfraredPreview.ps1或Start-SimulationPreview.ps1默认E:\Projects\WISEYE-IR-Work，桌面/飞控解释器用F构建环境，运行数据E工作区preview-data；首次城市索引数分钟。新资产已回传F。脚本PS语法检查通过；实际UE/AirSim由隔离测试启动器运行，未重新验收完整新版桌面启动链。旧Shipping ZIP仍为20261027增强IR版，未Cook/重包/推送本轮。原M_IR_Minimal和city Fleet哈希保持。

使用/实测/限制/后续见docs/INFRARED_REFERENCE_PILOT.md。优先做不同背景、实际距离/运动视频与目标局部热斑，补Avata分类，建立少量城市热材料类别；必要时将PSF/AGC迁GPU降低读出成本，再完整端到端/多设备和Shipping验收。原有清理修改是本轮开始前已存在的未提交工作，勿覆盖或当作本轮完成删除。

2026-10-27清理补充：用户要求仅留最新主项目并保留20261027最新ZIP。旧E工程64.361GiB/临时E构建316.561GiB及F旧包/缓存已审计；1010个Git文件与E副本逐字节一致，Content39860文件对应长度一致，Git fsck通过。自动执行删除被blocked by policy拒绝（含用户再次授权后的固定单文件），实际删除0字节，用户改为自行删除，不能写成已清理或假定E目录已不存在。F Python环境两处__pycache__报1392，不强删/不做磁盘修复。清单见CLEANUP_REPORT最新节与evidence/cleanup-20261027；Clean-LegacyProjects仅语法检查，未执行。原启动入口仍引用E临时构建，用户删后源码需重新构建/指定BuildWorkspace，完整ZIP可直接运行。

## 2026-10-27：城市专用Shipping与GitHub同步（最新）

用户要求打包当前全部功能并更新上传代码/文档，过程中明确系统自带场景只用城市。最终版本20261027-171140-City-Shipping：Content City完整Cook、仅city的发布清单与场景资源，保留源码original/test_range不删除。发布版SceneStore过滤旧数据目录中不在release.json的场景；原配置文件保留。GameDefaultMap为city，EditorStartupMap仍保留原始场景。默认Build-Release Content改City，Stage Cook先编译Editor确保反射类与Game一致。

打包实测补了两处发布版问题：雨效Blueprint类原为弱引用，AirSim GC后雨效不可用，改为UPROPERTY TObjectPtr持有；Shipping关闭STATS导致RHI显存快照不可用，按实际D3D12设备Adapter LUID查询DXGI进程本地显存及预算，不枚举第一张卡。Win64新增dxgi.lib，原pdh.lib保留。Game Shipping与Editor重新编译、City重新全Cook；冻结桌面也因SceneStore变化重打包。

54核心+15Qt通过。最终City包真实验收：场景/冻结飞控run_id一致，VIS1920×1080/IR640×512/OBS960×540，云台角速度、576点回波、起飞/电机RPM、稳定手动升高约0.962m、降落四电机归零及持续Tick；IR增强/原始/极性/噪声与4非法请求，时间/雾/雨与3非法请求、DXGI显存读数；冻结RTSP worker使用自定义19554/acceptance/thermal，随包FFmpeg实际解码640×512。冻结桌面清空开发PATH启动与中文GUI通过，模拟旧三场景配置只显示city且保留旧文件，Qt偏好测试后恢复。安装目录无新增文件，Fleet city hash仍bc48982ddb6043eca0fb6dbf7a4d61a249e8b15918590e8df2188b9587fb2fa6。证据docs/evidence/standalone-release-20261027。

源码唯一主目录F:\WISEYE-Studio，构建E:\Projects\WISEYE-BuildWorkspace，旧E工程未改。完整城市资产/生成城市副本、Python环境、builds/releases、自动TLS私钥与本地论文PDF排除Git；自有模型/代码/补丁/文档已纳入。代码提交3a3d99b、e3045af、0be8144；后续交付文档提交与远端验证见RELEASE_BUILD。ZIP、体积、SHA及F盘回传结果以发布说明和delivery校验报告为准；旧20261023包保留回滚，不把旧桌面增量包当作新完整包。

剩余：干净Windows机器、30分钟/4+4负载、外部RTSP端到端延迟、安装器与签名在线更新器尚未完成。增强IR仍外观近似、环境非物理天气/温度模型；未修改虚拟阴影页池预算。不能称为生产稳定或Anti-UAV保真度已达标。

## 2026-10-27：Windows PowerShell 5.1预览启动修复

用户实际用powershell.exe -ExecutionPolicy Bypass运行，启动器Get-Content未指定编码导致无BOM UTF-8中文JSON被按ANSI解码、ConvertFrom-Json报错。已在Start-InfraredPreview.ps1读取manifest处显式-Encoding UTF8，通用别名自动继承，源场景/已复制预览JSON都用Python核实完好，无需重复制或覆盖用户配置。实际Windows PowerShell5.1.22621.2506跑完整入口（Start-Process模拟、不启动程序）通过：中文名保持、city URL正确、game/flight/desktop三项调用均生成，配置hash不变。证据preview-powershell51-20261027.json；F/E启动脚本同步，文档命令改为本进程Bypass，不改变全局策略。此轮未重新启动UE或飞行，也没有Git提交。

## 2026-10-27：运行主机状态与环境控制（当前最新）

用户要求显卡/显存等状态与低性能提示，及时间/雾/雨环境调整。新增WiseEyeRuntimeStatus.cpp每秒采样RHI显卡、专用容量、UE显存UsedLocal/BudgetLocal、系统CPU/RAM、UE RAM与墙钟Tick FPS；Windows PDH英文GPU Engine计数器取本UE进程最忙引擎，pdh.lib仅Win64。UI runtime_panel工作台常驻，未知未提供/断连清空；core/runtime_metrics要求3个不同样本持续预算90%/RAM90%/FPS<20才提示，不自动改画质，不用品牌推断机器性能。

新增WiseEyeEnvironment.cpp与全局environment.configure/reset，State带环境能力/参数。独立太阳路径+光强/天空光，不依赖SunSky；雾恢复原始密度/距离/衰减/颜色/可见性，开启时调整近景范围；雨复用已存在AirSim WeatherActor/MPC，在各云台和ObserverCapture附近创建随视角移动体积。UI非模态窗口、有草稿/预设/按ID确认/等待锁定/重置/断连能力检查，仅本次运行有效，不改关卡/Fleet。不是天文计算、真实照度、风力/地面积水或红外天气模型。

E Editor Development构建成功，真实city ptz02图像验证：昼夜差44.54、雾差12.39、雨差5.68灰度级（仅差异，不是保真度分数），恢复默认差3.89（动态场景/自动曝光非逐像素同帧）；3种非法请求拒绝且状态不变，参数finally恢复，自有游戏退出，未起飞。实际读到i5-14600KF、ArcB580，驱动专用总量11.83GiB，采样UE约4.23GiB/预算11.08GiB，~30FPS、UE GPU引擎峰值87.7%，只是该次采样。53核心+15Qt通过；界面用实测样本回放截图明确命名sample，不当作在线截图。证据environment-20261027/report.json+visual-review.json+comparison；雨可见滴落折射，雾为基础可视雾。日志仍有城市经济档VSM页池溢出警告，未调全局阴影预算、未做GPU时间/长期/4+4/新飞行验收。

入口F:\WISEYE-Studio\scripts\Start-SimulationPreview.ps1别名调用现有Start-InfraredPreview，使用E已编译工程与源码GUI/后台飞控、隔离preview-data。组合启动的完整飞行未重新验收；旧Shipping/桌面ZIP不含新C++，本轮未Cook打包、未Git提交。F为主源码，修改同步E；city Fleet hashbc48982d...不变。细节ENVIRONMENT_AND_PERFORMANCE.md。核心原碰撞/GC/RPM/红外与其他未提交改动保留。

## 2026-10-26：红外外观第一版试验（当前最新）

用户授权开始试改红外。F主源码新增独立M_IR_Experimental与可复现generator/HLSL，原Minimal未动；优先加载试验材质，支持legacy/enhanced同视角切换、5点模糊、固定对比、背景法线/弱亮度代理、距离衰减近似、帧间/固定图案噪声。WiseEyeDemo/Bridge/Sensors接参数与能力回读，严格验证后才写状态；sensor_forms按云台控制/草稿/确认隔离并兼容旧UE。无新增CPU整帧处理，无地图/用户配置修改。不是材质温度/物理辐射模型，无AGC和热源升降温。

E临时构建Editor Development成功（同时补编译城市Editor依赖），材质commandlet生成成功，无该材质shader编译错误。真实city ptz02同视角接口/图像验收通过：IR640×512灰度/VIS1920×1080，模式差24.90、极性互补误差0.86、噪声差1.89，四种非法请求拒绝且状态不变，最后恢复参数并退出自有游戏。仅地面场景，无本轮飞行/实时延迟/GPU耗时/Shipping验收。51核心+13Qt通过。原Minimal hash675a01fd...；city Fleet bc48982d...未变。证据docs/evidence/infrared-city-20261026；观察仍偏灰平，下一步热材质分类，不要称已达到Anti-UAV或辐射精度。

源修改同步E，生成的新uasset已回F。入口F:\WISEYE-Studio\scripts\Start-InfraredPreview.ps1，用E构建运行游戏+源码GUI+后台飞控，独立preview-data，游戏关闭后清理自有飞控；脚本解析通过，组合入口未做新的完整飞行验收。旧完整包/桌面更新ZIP未修改，不包含本次UE改动，需后续Game/Cook/发布。细节docs/INFRARED_EXPERIMENT.md。修复WiseEyeDemo.cpp首头文件顺序以通过Editor IWYU；未升级UE/装插件/Git提交。

## 2026-10-23：Shipping独立包已交付F盘（最新）

成品F:\WISEYE-Studio\releases\WISEYE-20261023-Windows-x64.zip，18108112700B=约16.864GiB；F盘复制后SHA256复核通过（5a74e3d33b7bef3102ca8219d050b85f58c46c25eaf4ef1bacb845a82e15a20f）。完整目录18107757190B/1438文件。用户明确允许改内置盘临时构建，临时目录E:\Projects\WISEYE-BuildWorkspace；源码主目录F，E旧工程不覆盖。F异常连接下重试又报disk153/UASP129，因此未继续F构建；单文件限速传输和复核成功，不代表硬件问题已治愈。

Development与Shipping Game均实际构建，完整原始/测试场/真实城市Cook+IoStore归档通过。最终20261023-001704-All-Shipping在original/test_range/city三个场景均真实通过：正确场景/run、冻结飞控worker、原尺寸VIS/IR/OBS、实际云台、点云、真实起飞/RPM、稳定悬停后手动升高、降落四RPM0和tick推进；升高分别0.795/0.796/0.923m。city为用户当前1机2云台，中文空格安装和数据路径通过，安装目录无运行新增文件。最终冻结GUI清开发PATH后正常显示，47核心/路径/Job+9Qt通过。证据standalone_release_20261023.json及city/desktop图。

关键发布修复：Source/test/test.cpp用WiseEyeScene读取清单设置默认地图（Shipping忽略位置地图URL）；EngineSettings依赖；C++WiseEyeDataDir与可写配置/输出；RuntimeManager严格run握手、Job与后台进程、CWD用户日志目录；冻结入口flight/rtsp显式角色；构建sitecustomize预加载系统ICU防Qt钩子漏收平台插件；AirSim monolithic shader启动、CustomDepth避免重复回调、Weather运行资源与空指针保护、Unicode simlogdir；CitySample主模块改支持模块；关闭MediaMTX闲置接口。原碰撞/GC/RPM修复保留，AirSim新改动在projectairsim-cooked-game.patch与Setup中可重放，已反向检查。

没有在线更新器/正式安装器/GPU共享，没有干净Windows、30分钟/4+4或完整外部RTSP延迟验收。运行ZIP先完整解压本机SSD，再WISEYE.exe→启动仿真；缺运行库用随包vc_redist.x64.exe。详细docs/RELEASE_BUILD.md。打包源件保留用于后续复现；未Git提交/推送。以下旧记录是过程，不代表当前仍然阻塞。

## 2026-10-22：F盘实际打包执行（最新，存储异常待恢复）

用户授权开始打包且全部项目文件放F:\WISEYE-Studio。源码43.334GiB/40939文件迁移无失败，六处插件联接实体化；后续改动仅在F，E保留。Game Development实际构建成功test.exe399874560B；修复AirSim monolithic GetModuleFilename和Cooked shader初始化（新projectairsim-cooked-game.patch、Setup脚本幂等应用），CitySample主模块宏改为支持模块并更新依赖安装器。实现runtime_paths、UE WiseEyeDataDir、发布RuntimeManager/Job、packaging/entry.py多角色EXE、Build/Verify-Release.ps1和assemble.py。46核心路径、9Qt、1Job测试通过；早期EXE清空开发PATH诊断通过。

最终Desktop重打包COLLECT及基础Cook在F盘USB I/O异常时被停止。Cook已关闭Zen输出存储，进度约987/1008，尚未Cook/Stage成功；没有完整可用release或城市/Shipping包。Windows22:21–22:23实际disk153重试、UASPStor129重置，F读取长时间阻塞；已停止本轮Cook/ShaderCompileWorker/PyInstaller，无修复/格式化。已向用户询问更换USB连接或允许内置盘临时构建，等待答复，不能把停工说成打包完成。早期desktop目录后被重建中断，不能当交付成品。详见docs/RELEASE_BUILD.md，包括启动管理未联调、Cook用旧Editor工具引导和原E飞控端口占用等限制。全部新改动尚未提交。

## 2026-10-22：下一位AI打包实施任务书

新增 docs/PACKAGING_IMPLEMENTATION_HANDOFF.md，给出P0基线/Game构建、P1独立端到端基础包、P2城市Cook/Shipping与实测、P3本地安装/离线分发、P4在线更新路线。列明现有代码入口、路径协议建议、启动状态机、依赖闭包、验收与建议产物。所有新脚本/参数均明确为待实现；当前未实际打包。首包保留UE Stage目录结构，外置content必须验证挂载。移动盘仅为传输，默认用户数据在本机目录。下一位AI从P0开始，不重写界面、不先做更新UI、不覆盖Fleet；注意现有开发脚本进程终止和斜杠匹配逻辑不可直接照搬发布版。本轮仅文档更新与diff检查。

## 2026-10-22：分发方式澄清与打包可行性复评（最新）

用户明确硬盘主要方便传输，以后可直接下载。主方案调整为同一版本发布物通过硬盘或网络获取，安装到目标电脑本地SSD运行；不强制便携Data随盘。默认本机用户目录，跨机数据显式导入导出；F卷问题不阻塞E盘构建/网络发布。已更新PACKAGING_AND_UPDATES_PLAN的复评、风险和验收门槛，以及PORTABLE_F_DRIVE_PLAN的范围说明。技术可行但尚未Game/Cook/Shipping验收；优先验证AirSim/City插件Game构建、城市动态资产Cook和Anaconda依赖闭包，再做安装器和在线升级。25–60GiB仍仅预算。此次只改文档，未构建、未写F盘、未修改运行配置或上传GitHub。

## 2026-10-22：F盘移动SSD便携版评估（未部署）

用户希望插移动盘到其他电脑直接运行。只读检查F卷Ws3为NTFS、USB致态Ti6001TB SSD，总931.51GiB、空606.43GiB；容量足够。物理Disk Healthy，但卷Health Warning/OperationalStatus Spot Fix Needed，fsutil dirty query F:确认Dirty。USB/CIM详细可靠性计数不可读，未测协商速率或读写性能，不能推断硬件损坏。未修复/格式化/写F盘，建议先备份重要文件并处理卷问题再部署；用户尚未授权磁盘修复，本轮仅评估。

新增docs/PORTABLE_F_DRIVE_PLAN.md与evidence/portable_f_drive_assessment_20261022.json，总方案增加链接。建议E盘构建Cook再校验复制至F:\WISEYE-Portable；相对根路径允许换盘符，Data设备/航线随盘，机器缓存留LocalAppData，完整自带Qt/Python/飞控/视频依赖。另一台需兼容Windows/DX12显卡驱动及必要VC运行库，非任何电脑绝对即插即用；不需另装UE编辑器或Python。移动盘不减少实际包体，不自动改善GPU/预览性能。便携在线更新暂存同卷、退出后切换、保留旧版回滚，安全退出全部进程后再弹出。下一步为F卷问题处理与真正Game独立基础包；当前仅完成评估，未打包、未部署、未上传GitHub。

## 2026-10-22：包体盘点与独立运行/在线更新方案（规划，未实施打包）

用户要求评估城市与UE包体并制定可在线更新的运行方案。本轮只读统计磁盘与代码依赖，新增 docs/PACKAGING_AND_UPDATES_PLAN.md，未停止仿真、未Cook/构建Game或Shipping、未制作安装器或上线更新服务。实测CitySample源工程104.702GiB（Content71.186、DDC22.698）；迁入城市26854文件逐个stat仍44963092255B=41.875GiB；WISEYE Content42.941、工程63.580（不含6个目录联接目标）、DDC11.412、Intermediate2.684；UE安装30.573GiB，绝不能当作发布包大小。城市副本外部Actor目录12412文件0.912GiB，文件数不是运行时Actor数。证据 packaging_size_inventory_20261022.json 和 city_migrated_size_20261022.json。

桌面.venv仅11MiB因借用Anaconda系统包，PySide6包约30MiB，Qt DLL另约283MiB，不能直接拷贝.venv交付；当前Python3.14.6/Qt6.11.0，未改变环境。独立UE实际包体未知；方案仅作容量预算：城市Cooked20–50GiB、全套25–60GiB，首包需替换为实测，不承诺压缩率或范围。建议独立UE Game+Qt standalone+飞控/RTSP workers，统一可写数据根并去编辑器启动/绝对路径依赖，基础/城市分包。在线更新为签名清单+HTTPS可恢复下载+兼容组件组合+退出仿真后切换+回滚；首版按变更组件/容器替换、未变内容复用，后续再做资产差分。IoStore容器集不能拆配。GitHub代码，小包Releases（单文件<2GiB），大城市对象存储/CDN；离线安装器可分卷。先基础独立包，再城市Cook实测，再干净Windows安装验收，最后在线更新。未写生产代码、未上传GitHub。

## 2026-10-22：建筑碰撞粘墙修复（最新优先）

真实现场 UE/飞控仍响应但 UAV 在 FastGeo 建筑接触点位置不变，反向控制不能脱离。FastPhysics 碰撞响应沿用旧速度并清零加速度/冻结姿态，覆盖当前轮飞控响应；新增独立 third_party/patches/projectairsim-wall-contact.patch，StepPhysicsBody 将预测状态传入响应，保留本轮线/角速度及姿态，并增加与着陆相同的1mm接触间隙。未禁用碰撞、未自动瞬移。Setup-ProjectAirSim.ps1 在基础及GC补丁后幂等应用；必须重建SimLibs并重链UE插件，不能只更新Python。

实际SimLibs及testEditor构建成功，原生FastPhysics*19项（含新回归）和44核心Python测试通过，Setup -SkipBuild重复安装及反向补丁检查成功。最终同一真实城市建筑连续三轮54/53/51次接触后，按远离墙面的世界方向换算机体输入，分别脱离约6.80/6.74/6.60m，仿真时间/控制正常；随后经临时航点返回、真实降落disarm，稳定后四电机遥测均0。该回归航点在末端0.85m内主动悬停，不等同自动航线自然完成；早期测试因脚本参数、接近高度/朝向变化或到达判断失败，最终报告只记录成功轮次。详见 docs/COLLISION_RECOVERY.md、docs/evidence/collision_recovery_live_20261022.json。

新增 tests/verify_collision_live.py 需显式 --allow-flight --editor-log <当前日志>，限定原始起飞点的单机city、已落地，失败尝试悬停。最终实际飞行用同逻辑runtime脚本，仓库版本额外增加预条件及opt-in。用户当前city1机2云台和Fleet哈希保持（ptz-02是用户本轮修改后的实际位置，禁止恢复旧值）。操作前确认无脏资产，正常关闭UE后重开加载新插件；启动时曾因路径斜杠不同重复启动一个全新编辑器，已清除仅此重复进程。当前仅保留8232编辑器、城市PIE，正式飞控在已落地后重启以清除临时内存航线；桌面自动连接。日志 collision_editor_20261022.log、collision_runner_final_*、collision_*build*。并非所有模型/高速碰撞/多机/长期稳定验收；碰撞仍有转向、高度变化。未提交上传。

## 2026-10-22：全部实例表面取点与RF统一（最新优先）

当前city用户文件为1 UAV+2 PTZ，保持其位置/型号/数量，不按历史恢复。ArrangementPage的坐标表、俯视图、取点列表改为DeviceStore当前场景全部实例；DeviceManager保存或运行inventory变化后刷新。改过的坐标按ID合并最新Fleet，保留其他位置/型号/旋转/跟踪；旧两设备预设不清除额外实例，新增设备未加载时提示先加载。取点回包匹配run/scene/device/token，移除/换设备取消旧请求，重复刷新隐藏待删除控件避免视觉残影。

UE Begin/Snap支持FindDevice实际清单，底座补偿取目标云台，根实例共享placement状态回传给所有云台查询。额外修复City FastGeo道路是WorldDynamic查询对象：TraceMulti白名单允许WorldStatic或FastGeoSurrogateActor，忽略其他动态对象及全体设备，避免落到隐藏Z=0平面。实际无人机附近surfaceZ约73cm、ptz-02处70cm，取点只改草稿。两处UE无人机输入和HUD均改R/F升降，与系统一致；观察QE、云台箭头保留。

testEditor实际增量构建成功 logs/placement_rf_build_20261022.log；44核心单元、5项新Qt回归及原4项预览回归通过。真实UE RPC+Windows按键验证R=up+1/F=-1、箭头up=0，在落地disarm状态测输入映射，没有起飞运动测试；ptz-02/uav取点及额外云台begin/cancel、子云台查询共享结果、Fleet哈希不变通过。额外真实Qt在选中ptz-02时snap回填仅其草稿通过。证据multi_placement_rf_live_20261022.json、multi_placement_rf_ui_20261022.json/.png。

为加载C++曾确认无脏地图/资产、停止PIE并正常关闭重开城市；当前新DLL已加载、正式AirSim在地面待命。说明已更新；本轮没有新增画面延迟优化/测量，打包UE仅可能减少编辑器开销，不能消除GPU读回/JPEG/网络/Qt或低采集频率；上次约0.2秒为历史1+1条件，非本轮1+2性能保证。未提交推送。

## 2026-10-22：城市硬件光追额外负载处理（最新）

用户截图83.198MiB/400MiB的警告实际为常驻RT几何超过池预算20%提醒线；已核对本机UE5.8 RayTracingGeometryManager.cpp，不是全GPU显存超限。硬件为Intel Arc B580；原节能档仅关Lumen效果/传感器RT，却保留全局r.RayTracing.Enable=1及r.Lumen.HardwareRayTracing=1。现DefaultEngine.ini的SystemSettings设EnableOnDemand=1、r.RayTracing.Enable=0、r.Lumen.HardwareRayTracing=0，并向当前city编辑器执行后两项，读回均0。保留项目RT编译支持、模型/采集尺寸，画质档也不会自动打开硬件RT。处理时PIE已停止，未擅自重启播放、未做FPS改善承诺；证据city_raytracing_disabled_20261022.json。无需C++构建；用户下一次Play仍需检验实际卡顿，尤其区分节能10/10/8Hz与旧帧延迟。使用说明已补充，未提交推送。

## 2026-10-22：已实施预览延迟修复（本节优先）

用户“修复”授权后，工作台改用UEPreviewClient直连UE已有最新JPEG缓存，保留VIS1920×1080/IR640×512/OBS960×540；每源20Hz轮询上限、一个在途请求，帧号+仿真时间去重、单帧邮箱覆盖、2秒无新源帧提示过期、换源代际隔离、stop中断读。源身份仍固定到设备，不跟随属性/控制选择。RTSP继续外部输出，网关去重、墙钟时间戳、passthrough禁补帧及单线程颜色转换；RTSP旧客户端修正失败后的重连状态。点云显示查询独立100ms定时器，每设备一个在途请求，隐藏不查询。不改UE C++、资产、尺寸或飞控任务。

正式单窗口40秒：VIS内容年龄中位205/P95269/最大311ms，IR184/251/286ms，OBS187/271/341ms。120秒2382次/每路CRC全通过：VIS206/271/330ms，IR189/251/293ms，OBS188/268/323ms；约9.64/9.97/7.97独立Hz。对应旧基线VIS843/1923/2685ms；同口径，未降分辨率。120秒EO/IR绝对源时间差中位0/P95101/最大140ms，仍无硬同步。证据sensor_existing_window_latency_20261022_native_after_40s.json、_native_after_120s.json。

最终额外仪表窗口40秒：新帧到paint VIS142/P95183ms、IR125/168、OBS124/176；点云54次位移中位160/P95248/最大532ms，366更新。证据sensor_end_to_end_latency_20261022.json内native_final_points_40s。此口径与持续内容年龄不能混用；原桌面运输负载也变化，不能把点云改善全部归因于100ms轮询。RTSP各解码3秒31/32/25帧、H264原尺寸通过（rtsp_after_preview_fix_20261022.json），外部RTSP完整延迟未最终验收，不能套用新预览数据。

44核心单元通过；桌面环境 `python -m unittest tests.verify_video_preview -v` 4项Qt新鲜度/队列/换源/恢复通过，150%离线界面4组通过，compileall/diff-check通过。使用说明/RTSP/协议/延迟报告已同步。本机工作台及网关已重开新版本，UE城市PIE和AirSim保持；不自动降落，不恢复历史设备数量。69个测试Actor清理且测试桥关闭。未提交推送，4+4/高画质/30分钟稳定及跨机RTSP未验收。

## 2026-10-22：传感器延迟检查与使用说明更新（修复前历史）

已用UE场景内像素时间码测到当前较大延迟，并非只测ping或RTSP合成输入。单个已有1600×1000工作台，城市节能档40秒/794次有效窗口采样：可见光内容年龄中位842.6ms/P951922.5ms/最大2684.5ms；IR385.6/535.4/663.5ms；观察450.9/601.7/724.3ms。单窗口为PrintWindow每50ms观测，含约11ms捕获开销，不等于首次paint/显示器扫描。EO相对IR源时间中位落后407ms，绝对时间差P951596ms，当前不能视为同步双模态。

另做额外MainWindow60秒小幅云台运动和40秒分段诊断。直接UE可见光JPEG中位142.1/P95204.4ms；同轮RTSP到Qt可见光640.6/P951281.7ms，IR262.1/334.7ms，观察347.8/459ms。点云实际查询靶位移到LidarView绘制54次，中位310.1/P95494.3/最大806.5ms。点云保持原生产扫描与200ms轮询；直接JPEG224采样包含预热，不是逐帧配对分解。额外窗口与单窗口负载不同，不能相减当作精确分段成本。源JPEG较新而视频慢，后续编码/RTSP/解码/客户端有额外积压，具体主导队列尚待定位。本轮没有实施链路修复，不能声称已达到低延迟。

证据 docs/evidence/sensor_existing_window_latency_20261022.json 与 sensor_end_to_end_latency_20261022.json；方法/误差/复测步骤 docs/SENSOR_LATENCY_REPORT.md。新增tests/benchmark_sensor_live.py、benchmark_sensor_existing_window.py和PIE专用fixture/白名单start-stop桥；69个临时Actor均清理，不保存地图、不改设备配置，测试桥可按文档选择加载。未用起降测延迟，结束飞行状态以用户实际操作为准。

新增统一操作说明docs/USER_GUIDE.md，README/DESKTOP改为引导到当前指南；INSTALLATION补齐当前CitySampleSupport源码安装顺序、5.8.4版本和资源阶段。说明强调“新帧Hz”为源缓存计数、“接收于0秒前”不是采集年龄；整理启动、四页操作、独立设备/参数、自由观察、航线、保存与故障排查。保留1920×1080/640×512，本轮不改生产采集/码流/界面，不上传GitHub。


<!-- CITY_SAMPLE_20261022_BEGIN -->
## 2026-10-22：真实 City Sample 已接入（最新状态）

用户已下载并授权接入 E:/Projects/Scene/CitySample。26854个文件/约44.96GB依赖和Small City的12102个城市外部Actor已迁移；WISEYE副本 /Game/WISEYE/Scenes/city/CitySample 安装相同标定设备。城市 prepared=true、integration_status=ready。原城市地图、original Fleet和尺寸配置哈希保持。实际磁盘原配置当前1 UAV + 1 PTZ，以它克隆city，不按旧交接3+2/2+2恢复数量。

完整流式加载的人行道Z约73cm，不能采用编辑器未加载街区时的Z=0下层碰撞块。已保存云台根Z78.1169cm、无人机初始中心Z98cm，总览在街道上方12m；实际AirSim落地中心约Z92.27cm。仅整机平移，云台总高80cm和轴向层级不变。副本移除五个人群/车流生成器及依赖原GameState的BP_nightmode，首轮为静态白天城市。详情与手动恢复见 docs/CITY_SAMPLE_SETUP.md。

本机引擎目录现5.8.4，CompatibleChangelist55116800；不是本轮主动升级。构建版本变化触发399项重编，logs/city_final_build.log成功。更早5.8.3记录属历史。44项Python单元通过；隔离临时目录验证Git仅带插件描述时可安装缺失源码，重复安装保留源码。Windows PowerShell5启动配置显式UTF8，避免中文场景名导致JSON读取失败。

实际UE/AirSim/Qt端到端5组通过：正确城市/人行道/物理起点；云台角度/速度/停止/跟踪；起飞、真实RPM和手动上升；1920×1080 EO、640×512 IR、960×540观察RTSP、非空点云、仿真推进；降落disarm。12秒357次Tick为短测，非长期FPS承诺。证据 docs/evidence/city_runtime_20261022.json、city_workbench_20261022.png。保存移除昼夜控制器后，再以正式Start-ProjectAirSim脚本重播通过：city_reload_20261022.json；渲染配置/无昼夜Actor：city_render_configuration_20261022.json。编辑器装配完整回归先前通过，之后仅整体平移。

修复AirSim冷启动等UE确认起点、拥塞超时误判退出、物理场景创建后观察视角恢复需确认；可见光/观察LDR输出Gamma2.2、观察Capture保留渲染历史，IR强度映射不改。补齐插件链接依赖、虚拟纹理/材质层、表面类型、GameplayTags两个表、WorldAudio Mass、FastGeo异步碰撞。原资源十个旧车辆/玻璃引用自身缺文件，审计单独列出。AirSim仍报告未使用的Vulkan/PixelStreaming旧CVar和无SunSky提示；不宣称零告警。更早预热阶段有Renderer访问冲突，重编后本次验收未复现，不宣称30分钟稳定。

视频缓冲优化独立测量真实JPEG→H264→MediaMTX→Qt：640×512中位135.3ms降至94.6ms，P95143.9降至102.2ms；1080p优化后中位121.8ms/P95134.3ms，无1080p旧基线。不含UE采集/渲染，不代表完整运动到画面延迟。见 docs/RTSP.md、evidence/video_transport_latency_20261022.json。

当前UE城市正在Play、正式飞控/RTSP/桌面已启动，无人机落地待命。下次关闭现有UE后双击Start-CitySample.vbs（隐藏命令行），再Start-Desktop.cmd连接；也可 Start-ProjectAirSim.cmd -Scene city -SkipBuild。两台电脑仍需分别合法获取同版城市源资源，按Setup-CitySample.ps1安装本地依赖；原资源/插件源码不上传，地图及外部Actor不能单独漏掉。未提交推送。Big City、动态人车、避障、打包、多机/30分钟稳定未验收。
<!-- CITY_SAMPLE_20261022_END -->


## 2026-10-21 剩余页面与云台接口检查

数据与接口、资源与设置迁至 secondary_pages.py，统一卡片、数据源表格、连接状态、资源/布局分区；新增云台接口文档/SDK/示例入口。设备管理表格和航线网格视觉同步。云台面板新增停止并保持按钮，清零速度并退出跟踪。接口核查细节见 GIMBAL_INTERFACE.md；硬件驱动、鉴权、多客户端独占仲裁仍未实现。

本轮39单元通过（新增4 SDK协议契约测试）、150%离线Qt4组通过；两个页面宽窄窗、文档按钮、停止保持接线检查通过；compileall通过。截图 interfaces_polish_20261021.png / settings_polish_20261021.png。UE控制与飞控端口未监听，未进行本轮真实转动/飞行；未改UE/模型/场景配置，未提交推送。


## 2026-10-21 场景编排视觉优化

场景编排改为环境、默认设备位置、预设与表面取点三个卡片区；固定底部读取/保存/加载栏。新增两默认设备草稿 XY 俯视示意，自动缩放，不代表地形、其他实例或碰撞。小于1150逻辑像素切换单列；全部实例管理入口独立。保留现有保存、加载及取点协议，不写场景配置。

验证：实际Qt 1600×960双列、1000×720单列、坐标编辑后重新读取、固定操作栏均通过；150%离线回归4组通过，compileall通过。截图 evidence/arrangement_polish_20261021.png 与 arrangement_polish_narrow_20261021.png。本轮未执行UE取点/场景加载，未提交推送。重开桌面程序查看“场景编排”。


## 2026-10-21 第二轮视觉精修

用户要求直接继续优化外观。已调整中性深灰层次、蓝色品牌标识、带矢量图标的主导航、传感器 SCENE/EO/IR/LIDAR 通道标签及紧凑画面工具；飞行面板分为任务、手动操控、实时遥测，方向按钮与普通操作区分；参数页与固定提交栏背景统一。源身份、参数回执、控制目标、视频分辨率与飞控协议保持原实现。

本轮验证：125%/150% 离线 Qt 各4组检查通过，桌面模块 compileall 通过；截图 docs/evidence/ui_polish_20261021.png。尝试真实联调时 50051/50052/8554 未监听，脚本在前置连接阶段退出，未运行本轮真实飞行/视频回归；下方旧版9组真实联调不代表本次验证。未启动或重载 UE、未修改用户场景配置，未推送 GitHub。


## V3 界面已按用户指令实施（2026-10-21，本节优先）

- 用户“按照方案开始修改”已授权实施，不再沿用下方设计阶段的未批准限制。专业深灰/蓝色强调、场景主导已实现；主界面入口 workbench_v3.py，主题与输入组件在 ui/，旧 workbench.py/sensor_settings.py/view_gallery.py 为兼容导入。
- SensorWorkspace 固定 device/sensor 身份、跨云台混排、四路上限、拖入替换/标题换位、布局和场景/缩略比例保存、放大/弹窗/1:1；每源一个原尺寸解码器。隐藏工作台时释放无弹窗引用的本地解码，不停止外部发布。
- 设备树只选属性，显式选择驾驶/云台才切控制对象。传感器表单可编辑非控制云台；UEClient 额外本地详细回执信号带 request_id/提交 payload，不修改线协议。多设备草稿、晚回包、提交后继续编辑、失败/断线保留、退出丢弃提示已接；参数仍仅会话有效。
- RPM 是只读遥测；保留物理起降、disarm、进度保护、非阻塞队列和隐藏命令行。修复短任务使按住飞行按钮被轮询禁用的问题。航线模式只打开编辑器，上传/执行分开，执行需上传确认且已起飞、动作结束。
- 35单元通过；verify_ui_redesign_live.py 9组真实UI联调、verify_ui_redesign_offline.py 125%/150%各4组、verify_ui_flight_live.py 5组实际Qt飞行、verify_runtime_live.py 6组两型号/SDK/健康/尺寸回归均通过。证据 ui_redesign_* 与 runtime_controls_ui_v3_20261021。用户3+2配置字节保持，不修改UE源/资产。
- 说明见 docs/UI_REDESIGN_IMPLEMENTATION.md。P1/P2/P3与P4主要交互已交付，完整P4/P5长时性能未完成，TASK-023仍进行中；不声称GPU下降或30分钟稳定。任意停靠、航线撤销重做/任务库、参数场景持久化、连续录制/回放、批量集群与城市场景仍待后续。未提交/推送GitHub。

## 界面改版设计交接（2026-10-21，未实施）

用户要求优化全套 UI/UX 方案交给下一位 AI，而非本轮直接改程序。新增 `docs/WISEYE_UI_REDESIGN_V3.md`、`docs/AI_UI_REDESIGN_HANDOFF.md` 和 `docs/ui/wiseye-v3-review.html` 离线布局示意。重点为紧凑工作台、固定身份多源画面、对象上下文控制、独立参数草稿与确认、统一视觉组件、分期实施及验收。用户随后已确认专业深灰 + 蓝色强调，以及场景大画面 + 传感器缩略窗；这两项为后续实现默认，不必重复询问。其余详细方案仍待评审。生产代码与用户配置未修改，未重跑运行测试；V3 不得标记已实施。下方为既有运行基线。

## 转速、卡顿检测与性能（2026-10-21，本节优先）

- 用户新增六项任务；城市场景随后明确选 City Sample，并要求本轮稍后下载、先完成其他功能。未下载城市；已建 city 未准备入口并阻止生成替代街区，见 docs/CITY_SAMPLE_SETUP.md。
- 当前实际 Fleets/original.json 为用户已有 3 UAV + 2 PTZ，保持原字节布局，不恢复历史 2+2。三机地面待命。
- AirSim rotor_info 四电机 rad/s 转 RPM，UE 按电机实际速度积分，Avata 按轴心映射。高转速保留模糊盘；桌面电机显示只读，O 不再伪造 AirSim 电机启动。原模型仍共享 FastPhysics 参数，并非厂家实机动力学标定。
- 修复 landing 成功后仍 armed 约3504 RPM：成功且任务代次匹配后 disarm，再进入 ready。两型号悬停实测约4931 RPM，落地0；真实联调证据 runtime_controls_20261021.json/png。
- UE tick_seq + 桌面进度/缓存年龄看门狗（约3s）；GPU读回每通道最多2项、超时3s、场景退出取消；缓存超过2s不再发布。未证明消除所有偶发冻结，未做长时压力验收。
- 默认均衡45 FPS上限，VIS/IR/OBS捕获20/15/10Hz；画质60与30/25/15；节能30与10/10/8。尺寸保持1920×1080和640×512。降低捕获、阴影/反射并关闭未使用原生AirSim相机；节能还关闭动态间接光，会改变光照观感。
- Arc B580当前3+2短采样：画质GPU92.8%/Tick20.1Hz；均衡89.7%/Tick34.8Hz；节能70.6%/Tick30.0Hz。新帧实测与目标不同，见 docs/RUNTIME_OPTIMIZATION.md / runtime_performance_20261021.json，不宣传稳定1080p30或端到端延迟。
- FFmpeg编解码、界面启动/场景准备隐藏命令行；新增 Start-ProjectAirSim.vbs、Start-WISEYE-Studio.vbs。保留cmd诊断入口。避免重复启动同一UE。
- 云台标准库 SDK integrations/gimbal_client.py + examples/gimbal_control.py，get_capabilities/角度/速度/跟踪/保持/停止；loopback JSON Lines端口50051，速度300ms看门狗。见 docs/GIMBAL_INTERFACE.md；没有硬件驱动或多端仲裁。
- UE5.8.3构建成功：logs/runtime_performance_build.log；35单元+6真实联调+3项真实UE快捷键通过，另有3档WindowsGPU采样及最终Qt/VBS启动检查。GUI停滞使用注入旧推进时间，未人为卡住真实UE。TASK-023仍IN_PROGRESS。

## 多设备首轮：真实双机、双云台（优先于下方旧单机限制）

- 用户明确“开始多设备功能实现”。`core/devices.py` 注册 mavic3/avata/eo80 模板，校验实例身份、类型、姿态、数量与跟踪引用；`Config/WISEYE/Fleets/<scene>.json` 持久化。当前原始场景已保存 2 架 UAV + 2 套 PTZ；各类最多 4 个，默认 uav-01/ptz-01 保留。无文件时兼容原布局。
- `WiseEyeFleet.cpp` 运行时复制校准装配，不编辑 Content/模型；保留 Mavic/Avata 旋翼、底座/偏航/俯仰结构。每实例独立纹理、热成像、点云、导出目录和动态目标；修正 deferred spawn 重复应用位置偏移。gimbal.set_target 可跨云台选择任意 UAV。内部复用装配但 drone/gimbal 数量独立。
- UE 命令 payload.device_id 路由到实例，错类型/未知 ID 拒绝；状态带 devices 清单。AirSim runner 根据清单创建 Drone1/Drone2 等真正的机器人，各自 FlightController/航线/任务/状态，服务响应增加 fleet 数组。保留单机无 ID 兼容入口；当前源实际独立模型物理参数仍共享四旋翼，不能宣称 Avata 独立动力学已标定。
- 桌面新增 device_manager.py：新增/复制/删除草稿、名称/型号/位置/偏航/默认跟踪目标、保存重载。驾驶对象和云台对象分别选，切换清旧输入、过滤旧实例状态/回执、隔离传感器草稿。航线绑定驾驶对象；当前总览显示所选云台，全云台视频接口同时发布，暂没有跨云台混排。UE follow/gimbal 视角以及 O/T/I/缩放/P 操作按当前实例选择。
- 网关动态发现额外云台，默认 CH1/CH2 保留，新增 ptz-02/CH1、ptz-02/CH2 等；OBS 全局。媒体路径正则、24 个有界 UE 客户端。每图像源响应校验 device_id；PNG/PLY 伴随 JSON 增 device_id/sensor_id/scene_id/run_id。时钟尚未硬同步，旧 simulation_time_s 不应视为跨实例同步时钟。
- 首次双机加载暴露 Project AirSim GC 同步 bug：GLastGCFrame 在 GC 开始时更新，原代码提前创建新机器人会触发 UE AsyncLoading2 断言。新增 third_party/patches/projectairsim-ue58-gc-completion.patch，在游戏线程 core ticker 完成同步 CollectGarbage 后才唤醒服务线程；本地依赖已应用并重编译。Setup-ProjectAirSim.ps1 幂等安装该附加补丁，原基础补丁及用户依赖修改均保留。不要只同步本机二进制而漏补丁。
- 本轮验证：testEditor 与 ProjectAirSim 模块编译成功；31 单元、10 项真实双机/双云台联调（含双机不同航线同时完成、手动隔离、参数/目标/视频/PNG身份、重载恢复）。另 3 项数量组合/恢复检查（1 UAV+2 PTZ、2 UAV+1 PTZ、原始2+2字节级恢复），3 项真实 UE 键盘 O/T/I 选择隔离。几何读取确认两套零俯仰外壳参考高度 80.0 cm、实际位置与配置相差 <0.1 cm。证据 evidence/fleet_20261021.json/png、fleet_shapes_20261021.json、fleet_hotkeys_20261021.json、fleet_geometry_20261021.json；脚本 tests/verify_fleet*.py。
- 运行仍 Start-ProjectAirSim.cmd + Start-Desktop.cmd；新电脑先关 UE，Setup-ProjectAirSim.ps1 应用 GC 补丁再构建。多设备新增/删除及初始配置保存后重载，不是运行中热插拔；当前已恢复2+2地面待命。旧编排页/命名位置预设只编辑默认实例，完整配置以 Fleets 为准。运行时参数尚未持久化；4+4性能、长时稳定、避碰/队形、任意型号导入与独立安装包未验收。TASK-023 保持 IN_PROGRESS；本轮未提交/推送，既有大量未提交地图/模型与 papers 保留。

## 同日：保存入口精简、比例摇杆与设备结构澄清

- 用户追问保存下拉意义、摇杆、可扩展传感器及整体型号/多实例。已删桌面工作传感器下拉，子页/总览直接按传感器保存，顶部按当前传感器子页；camera.capture 增可选 sensor 与独立 frame_sensor/width/height，避免为保存改变观察模态。UE P 键旧入口保留。
- 新 gimbal_joystick.py 比例回中摇杆、8% 中心死区、归一化限幅，复用 100 ms 输入与 UE 300 ms watchdog；松手/失焦/隐藏/禁用/切模式清零；键盘方向键保留。未修改任何模型、地图或物理配置。
- docs/DEVICE_COMPOSITION.md 明确现状：固定 Drone1/uav-01 与 ptz-01，型号外观切换共用物理，不是通用多实例平台。记录模板 model_id → 实例 device_id → 挂载 sensor_id 的改造顺序与 ID 分流验收要求，本轮没有实现多机。
- 本轮 testEditor 构建成功，28 单元测试、6 项新增真实桌面/UE 联调通过；比例运动、松手/失焦停止、模式禁用、两种原生 PNG 尺寸和元数据、保存不改变当前模态均验证。证据 evidence/joystick_capture_20261021.json/png，脚本 tests/verify_joystick_capture_live.py。新版桌面已重启，原有 AirSim helper 自动恢复会话，保持待命；未提交/推送。

## 2026-10-21：用户五项工作台改进

- 桌面 eventFilter 接云台方向键，数值/文本/表格/组合框焦点隔离；长按按钮、松键、失焦、切模式清零；UE gimbal.set_input 300 ms watchdog。底座/模型尺寸未改。
- core/routes.py 统一航线 schema；route_editor.py 航点表与等比例 XY 拖动、增删排序、当前位置替换、速度、单次/循环、JSON 存取。飞控 route.upload/start/stop；上传与正在执行的快照隔离，逐点运动、暂停保留下一未完成点，单次结束悬停；先起飞后任务。仅单架，无避障。
- sensor_settings.py 独立可见光/红外/雷达子页，启停与实际参数确认、保留草稿。UE sensor.configure 原子校验和 per-sensor 状态；可见/红外 FOV 分离，IR palette/noise；禁用停止采集输出，查看/选择不隐式启用。
- view_gallery.py 默认四缩略图（OBS/CH1/CH2/LIDAR）、勾选一/两列并排、放大复用解码器。OBS 运行时场景捕获 960×540/15 FPS 目标，经第三 RTSP 发布回传；桌面右键转向+WASD/QE 移动独立自由相机，松右键/失焦/隐藏停止；UE observer.set_input watchdog。当前卡片勾选布局，无拖放持久化。OBS 不含 HUD/编辑器 UI，表面放置仍用独立 UE。
- 实测证据：2026-10-21 testEditor 构建成功；28 单元测试、11 项真实 Qt/UE/AirSim/RTSP 联调，见 evidence/workbench_v3_live_20261021.json、workbench_v3_20261021.png。自定义路线转换世界坐标后到达末点并降落，循环/暂停/继续/停止已验证。原始 VIS1920×1080/IR640×512 保留。最终进程默认地面待命。
- 运行：Start-ProjectAirSim.cmd + Start-Desktop.cmd；已有视频服务需重启 MediaMTX/rtsp_gateway 读入 OBS。C++ 源需关闭编辑器后重建；本机已完成。未推送 GitHub。前序大量未提交模型/地图变更和 papers 均保留。
- 限制：参数本次只会话内生效；路线需人工存文件后 Git 同步。未测三路独立渲染 FPS、端到端延迟、30 分钟稳定；仍软件 H.264。UE/AirSim 初始化日志出现 FAppTime 非游戏线程 ensure 和无 SunSky 提示，随后仿真联调通过，来源尚未定位。最终免装 UE 安装包、硬编、多架、姿态编辑仍未完成。TASK-023 保持 IN_PROGRESS。

## 2026-10-19：阶段 A 续作——表面放置、底座贴合与命名预设

- 按用户“继续”推进已批准方案。新增 UE 鼠标点选向上表面、当前 X/Y 垂直贴合、云台底座高度补偿、命名预设另存/读取/更新。未改模型尺寸/基础地图/飞行物理。所有此前未提交变更与 papers 保留，当前仍未提交/推送 GitHub。
- UE 新 WiseEyePlacement.cpp：placement.begin/snap/cancel，设备 uav-01 / ptz-01，scene_id + request_token 校验。点选采用独立自由相机和 observer 输入，左键确认、右键取消、45 秒超时；忽略整套云台/无人机/AirSim 代理，只命中 WorldStatic 且法线 Z≥0.25 的表面。垂直查询是输入 Z±100000 cm；屋顶/平台也可选，没有碰撞不能命中，不宣称地形语义识别。
- 取点返回 surface_cm、position_cm 等状态，不移动任何 Actor、不自动写文件。标记绘制在 HUD，不生成进入 SceneCapture 的调试几何。云台根据 PTZRecovered 外壳最低点计算 demo anchor 高度，保留整体尺寸与安装关系；无人机默认留 25 cm 初始余量，最终接触高度由 AirSim 决定。
- 桌面新 placement_controls.py 组合到 arrangement.py，增加命名库与设备/高度/选点/贴合/取消控件，编排页可滚动。待处理结果按 run_id/scene_id/token 匹配，断连、换场景、编辑草稿时丢弃旧结果。断连后重连可显式取消遗留 UE 取点；关闭窗口会 flush 本窗口取消请求。取点时驾驶控件停用，取消后保持 observer，需要显式切回驾驶。
- core/layouts.py 扩展命名库 Config/WISEYE/Layouts/Presets/<scene>/<preset_id>.json：安全自动 ID、中文 name、原子写入、同场景名称去重、更新要求已存在的选中 ID。读取/另存/更新不替换当前生效的 Layouts/<scene>.json；必须“保存初始布置”再“加载场景”才激活。损坏单个预设不隐藏其他合法预设；没有自动覆盖基础地图或删除预设动作。
- 修复坐标编辑相关输入问题：移除绕过编辑焦点检查的 MainWindow.keyPressEvent 兜底，键盘驾驶统一经过全局 eventFilter。数值框忽略的 R/F 等字符不再冒泡触发驾驶；按键释放仍能清除旧飞行输入。
- 验证：testEditor 最终构建成功；23 单元、8 项真实放置联调、15 原桌面联调通过。实际鼠标在 UE 选表面后回传草稿；拒绝非法设备/坐标/无表面/场景不匹配，过期 token 无法取消新请求；断连恢复取消有效；命名预设另存/读取/更新隔离当前布局；贴合保存后实际 AirSim 与云台重载一致。
- 真实几何校验 ue5/scripts/validate_surface_placement.py：平面 z=0、云台最低点 -0.0168165 cm（UI 1 mm 坐标舍入所致）、零俯仰参考高度 80.0 cm，anchor z=4.1 cm。不是重标定模型，也不宣称所有倾斜姿态包围盒总高固定 80。几何检查只读 PIE，依赖 runtime/placement_expected.json；不运行 calibrate_current_scene。
- 本轮观察键鼠回归：相机移动 590.56 cm，无人机漂移 0.00493 m，云台方向键变化 11.78°。八方向有符号飞行/鼠标按住/失焦停止通过，新增数值编辑不触发飞行检查；最终悬停样本漂移 0.0541 m。旧桌面测试修为等待 flight.set_mode 确认及制动完成再发 W，观察回归修为测量实际稳定悬停而非固定睡 2 秒，不放宽阈值掩盖残余运动。
- 证据 docs/evidence/placement_presets_20261019.json/png。1080×740、正式微软雅黑 UI 10 字号编排页已渲染检查。测试命名文件和临时生效布局均已清理/恢复；原始场景待命供用户使用。运行与流程见 docs/DESKTOP.md，新增协议 docs/PROTOCOL.md。冷启动既有 FAppTime 非致命 ensure 仍保留，不宣称零引擎告警。
- 复验：AirSim 环境 unittest discover -s tests -p test_*.py；桌面 python -m tests.verify_placement_live（需要 UE 文件桥、真实鼠标焦点，临时保存并恢复布局/测试预设）及 verify_desktop_live / verify_observer_live / verify_manual_controls_live。placement.begin 只创建草稿，尚无三轴拖拽操纵杆、初始姿态编辑/法线对齐；A 尚未整体完成。后续 B 实时数据/硬编、C 多架、D 内嵌/免装 UE 的独立成品仍按计划推进。

## 2026-10-19：V2 已批准，阶段 A 首轮工作台已实现并验证

- 用户明确“按照你的方案计划，开始完善优化修改”，覆盖下方旧的等待审批状态。方向为仿真平台 + 开放数据/控制接口，默认场景主导，A/B/C/D 分阶段；用户还确认最终用户免装 UE 编辑器/VS/开发 Python。此次完成 A 首轮，不宣称完整 V2 或安装包交付。此前所有未提交模型/地图/代码及 papers 保留，未提交或推送 GitHub。
- 桌面布局移到 apps/desktop_app/workbench.py：场景编排、仿真工作台、数据与接口、资源与设置。设备树与无人机/云台/传感器属性分开，选对象不接管飞行；输入模式互斥。主窗继续复用已有非阻塞 UE/AirSim 客户端。新增 CH1+CH2 双画面、参数实际回显、云台目标角、雷达视场/量程/扫描频率；工作传感器与观看通道独立，导出原始源尺寸。
- UE WiseEyeObserver.cpp 新增独立运行时自由相机（不修改 Overview 或传感器）：observer.set_mode overview/free/gimbal/follow；input.set_mode observer/drone/gimbal。C 切输入、Tab 切视角；观察按住右键+WASD，Q/E 升降，Shift 加速；UE 驾驶 WASD/上下箭头/QE，云台箭头。旋翼改 O、复位 Home 避免键冲突。失焦/切模式清零本地速度；桌面切模式、松键、失焦同步飞控零输入。
- core/layouts.py 与 arrangement.py 原子保存 Config/WISEYE/Layouts/<scene>.json，version=1、scene_id、flight_origin_cm/gimbal_location_cm。UI 用米、UE 世界 Z 向上；UE 场景加载先解析基础配置再叠加布局。runner ConfiguredWorld 在 AirSim 创建真实 robot 前转换 [X/100,Y/100,-Z/100]。位置改动不写基础地图，也不在飞行中强行 teleport。当前无拖拽、地形吸附、命名多预设或初始姿态编辑；高处未解锁无人机受重力下降。测试临时布局已恢复，当前无测试预设残留。
- 日常 loops=0 启动地面 ready，不自动 arm/takeoff/执行航线；界面点击起飞，再选手动或自动。成功起飞重建空中航线，成功降落回 ready。--loops N 保留自动起飞回归。ready 时拒绝自动航线/非零手动输入，不因本地无效热键重启会话。flight_status active 不是完整飞行阶段遥测。
- 场景重载修复两个实际问题：同场景名称不能代表重载完成，必须 run_id 改变；UE/AirSim 状态携带同一会话号，旧飞控连接被关闭并丢弃。销毁旧世界后直接关闭旧 transport/接收线程，不对不存在的 robot 发送 cancel/disable/unsubscribe RPC，保持正常起飞/降落的长任务超时。两次连续原地 reload 自动恢复已通过，最终日志没有新增 Object closed 栈。
- 视频预览改为 GUI 定时取最新 QImage 邮箱，每路至多一帧；generation 隔离过期帧/状态/解码进程。接收 FPS 用滚动窗口平滑，显示输出目标、适配 960×540 与源分辨率。断流/断连清除有效画面。UE streams.CH1/CH2 增加 frame_seq/completed_frames/readback_queued_ue_monotonic_s/cache_age_ms，统计不复制 JPEG；队列时刻不是曝光时刻或端到端延迟。
- 验证：最终 testEditor 构建成功；20 单元、15 真实桌面、8 个有方向的手动键 + 按住按钮/失焦/稳定悬停、7 个 V2 真实联调全部通过。真实键鼠观察移动 590.25 cm，无人机漂移 0.0070 m，FOV/指向不变；云台箭头变化 11.75°。V2 检查包括待命/起降、布局落到真实 AirSim robot、同场景重载、双画面/故意 GUI 卡顿队列≤1、雷达参数原子校验、编辑值跨轮询保持、切输入清零。
- 最后 8 秒双画面样本：CH1/CH2 完成新帧均约 20.50 FPS，UE JSON 控制往返 P95 57.49 ms；不声称达到独立 30/25 FPS、视频 P95 或 30 分钟稳定目标。证据 docs/evidence/workbench_v2_20261019.json/png。冷启动 FAppTime 非致命 ensure 为既有限制，未宣称零 UE 告警。
- 运行仍用 Start-ProjectAirSim.cmd → Start-Desktop.cmd，详细新流程 docs/DESKTOP.md；协议 docs/PROTOCOL.md。测试：AirSim 环境 unittest discover tests/test_*.py；桌面环境 python -m tests.verify_workbench_live / verify_observer_live / verify_manual_controls_live / verify_desktop_live（真实 UE/runner/RTSP 已开，observer 会恢复并聚焦 UE；workbench 要求起始地面 ready，会暂改并恢复布局）。
- 下一步：完成 A 的可视化放置/地形吸附、命名预设与体验验收；B 硬编 PoC/去 JPEG/统一时钟/原始录制，C 真正 2→4 架，D 内嵌兼容验证与干净电脑独立安装。h264_qsv 仍只枚举，尚未启用或通过性能验收。主 UI 当前中心为传感器，三维观察仍为独立 UE 窗口。

## 2026-10-19：仿真平台系统设计讨论（方案待审批）

- 用户要求主系统聚焦仿真、留好 RTSP/参数等数据与控制接口，数据处理由扩展应用完成；要求先提交系统设计方案，审批后再完善。**本轮没有实现新运行功能、修改 UE 资源、重启服务或调整参数。未经用户后续批准，不开始 V2 重构。**
- 新方案 docs/WISEYE_SIMULATION_PLATFORM_DESIGN_V2.md，涵盖四页信息架构、场景/传感器两种工作区布局、参数实际生效反馈、单架/多架、独立自由观察、可视化初始布置、预设/会话/个人布局分离、接口/控制权/时间戳和 RTSP 优化路线。
- 拟定阶段 A 单架工作台（含独立 UE 自由观察）→ B 数据面与硬编 → C 2→4 架 → D 统一交互视口/交付。ID 和性能指标从 A 引入。内嵌视口先做硬件/输入/延迟兼容性验证，不承诺立即嵌入 UE 编辑器。
- 本机事实：runner 硬编码 Drone1；机型切换不是多架；RTSP 仍有 JPEG/Base64/libx264 中间层、GOP=1；桌面解码固定适配 960×540。历史 30/25 FPS 是输出率，约 20 FPS 独立新帧，本轮没有重测性能。本轮只读确认 FFmpeg 编码器列表含 h264_qsv，不能认作 Arc 硬编码已验收。
- 可点击讨论原型保存在本线程可视化目录 wiseye-workbench-design.html，内含场景主导/传感器主导两种布局；所有对象/数据均为示例、不连接真实后端。已用 Edge/Playwright 检查位姿修改、参数面板、飞行接管/组操作、接口页与 1024/736/360/320 宽度，无 JS 异常或横向溢出。runtime 中是本机预览/验证文件，不入 Git。
- docs/SYSTEM_UX_DESIGN.md 的旧算法闭环定位保留为历史，新增待审批方案提示；计划新增设计完成/实现待审批状态。下一步等待用户对范围、默认布局、独立自由观察窗口、阶段顺序与性能目标的审批。

## 2026-10-19：旋翼速度与激光点云修复（前序实现记录）

- 用户反馈旋翼慢、点云奇怪，已修复并完成本机验收，尚未提交/推送。此前所有修改、原始模型、papers 和历史实验输出保留。
- 默认视觉转速由 600 改为 6000 RPM，同步两图与 standard_rig。>=1200 RPM 使用半透明扫掠圆盘，停止后恢复原桨叶，规避帧率采样造成慢转/倒转。Mavic 从深层桨叶几何计算扫掠半径，直径约 24.37–24.43 cm；Avata 四盘约 6.97 cm。圆盘无碰撞，不是实时电机遥测或物理曝光仿真。材质 M_RotorBlur 与生成脚本 build_rotor_blur.py 随项目保存，标准导入入口可重建。
- 点云异常的实际原因：传感器局部坐标逆变换包含云台外形缩放，约 13.6 m 回波曾显示到约 82 m；旧 UI 丢弃 Z 并独立拉伸 X/Y；扫描还主动忽略无人机。现扫描姿态固定为单位缩放，扫描原点/米制 PLY/预览一致；忽略自身云台和隐藏 AirSim 代理，当前无人机仅参与 Visibility 查询，不参与物理碰撞。切型号同步查询几何。AirSim 场景加载会重设分割 stencil，增加热特征哨兵恢复，保留红外分类。
- 新 apps/desktop_app/lidar_view.py：三维默认、正视 Y/Z、俯视 Y/X；拖动旋转、滚轮缩放、双击复位，等比例、距离配色/轴/比例尺，过滤非法坐标，明确单帧与零回波。仍为 48×12、30°×8°、10 Hz，最多 768 预览点；不是完整建图，小无人机可能落在射线间隙，地面平面/条带属于真实有限采样。
- 验证：最终 UE 构建成功，17 单元、15 桌面联调、三视图渲染检查通过；查询碰撞调整后的八方向、按住按钮、失焦停止通过，悬停漂移约 0.008 m（单次观测）。两型号高速盘/停止恢复/再启动、盘尺寸与热标记通过。协议实测 10 m 测试平面表面 x=9.95 m，576 命中；独立 PLY 回归用 1 m 参考平面，全部 x=0.95 m，不受 0.172975 云台缩放影响。Avata 机身实际射线命中、无动力学碰撞通过。
- UE 专项脚本：validate_rotor_blur.py（分别选两种型号后运行）、validate_lidar_metric.py（PIE 临时借用空 Actor，finally 恢复；Rotator 必须 .copy() 备份）、validate_avata_rotors.py；桌面 python -m tests.verify_lidar_view。完整桌面导出测试现先朝向地面，不能依赖对天空/小目标必然有回波。旧不正确米制 PLY 必须重新采集，未改写历史文件。
- 摘要 docs/evidence/rotor_lidar_fix_20261019.json；截图 lidar_3d_fixed_20261019.png、fast_rotors_{avata,mavic3}_20261019.png 已检查。冷启动已有 FAppTime 非致命 ensure 仍会出现，不声称零告警。运行方式不变：Start-ProjectAirSim.cmd → Start-Desktop.cmd；点云查看在数据源下拉框选择 LIDAR。
- 下一步按用户实际反馈决定是否提高角分辨率、做世界坐标点云累积、接各电机转速。当前改动不宣称完成这些功能。
- 交付时检测到 UE 已停止 Play（2026-10-19 16:29:55 日志），编辑器和桌面仍开着，runner 等待重连；没有强制重启用户窗口。点击 UE 播放即可恢复服务。

## 2026-10-19：Avata 自身四旋翼动态化（前序记录）

- 用户要求 Avata 自身桨叶由静态改为动态，已完成。本机修改尚未提交/上传，保留此前按键/尺寸修复及 papers。
- 从原始 FBX 的前后两对桨叶中按左右拆分为四个独立网格，按圆形轮毂确定真实轴心。新资产位于 /Game/WISEYE/DroneModels/Avata/Animated：AvataBody + AvataRotor0..3。机身剔除全部原静态桨叶；300385 机身三角形 + 4×8307 旋翼三角形 = 原始 333613，无丢失/重复。原 FBX、一体网格、材质和 UV 保留。
- AvataBody 的 Rotor0..3 sockets 存轴心，C++ 将旋翼作为 Drone 所属组件挂在机身下旋转，相邻反向、对角同向。共用 RotorsRunning/RotorRPM/RotorPhase，UE F 与桌面旋翼按钮同时生效；切换型号时递归隐藏整套外观，红外使用 RotorHeat。旋翼为视觉动画，尚未读取 AirSim 各电机实时 RPM。
- 尺寸继续以原完整网格标定 18×18×8 cm，实机测量通过；可见 Mavic 网格为零，四轴局部位置固定。8 阶段验证通过：持续旋转、配对方向、关停保持、重新开启；近景截图已检查。UE testEditor 构建成功，17 单元 + 15 桌面真实联调通过。
- 复现：正常 Start-ProjectAirSim.cmd → Start-Desktop.cmd；选择 Avata，UE 进入 Play 后 F 开关旋翼（桌面 F 仍是下降）。预生成资产随 Git 同步，不需要每次导入。重建用 scripts/Import-DroneModels.ps1，缺资产时调用 ue5/scripts/build_avata_rotors.py；仅构建过程启用引擎自带 GeometryScripting，无新增运行时插件依赖。
- 专项验证脚本 ue5/scripts/validate_avata_rotors.py 在已选 Avata 的 PIE 中执行；验证时临时用 137 RPM 避免采样谐波，结束恢复原 600 RPM。证据 docs/evidence/avata_rotors_20261019.json、avata_rotors_running_20261019.png。当前保持 Avata、旋翼开启、手动悬停。
- 后续若需要物理一致的电机转速/高速旋转模糊，应接 AirSim 电机遥测并独立验收；本轮没有修改空气动力学参数。

## 2026-10-19：按键、Avata 外观及实物尺寸修复（前序记录）

- 用户报告 UE 与桌面按键无效，Avata 桨叶穿模；要求 Mavic/Avata 实际大小，云台高 80 cm。本轮已实现并完成最终实机验证，当前修改保存在本机，尚未提交/推送。
- UE 旧飞行按键仅改运动学字段；现在用有界本地意图队列和 runner 单一 AirSim 控制面。输入绑定采用独立完成标记，显式设置 InputComponent.Priority 并重新入栈，解决上游 T/Tab consuming 动作抢键。UE M、W、空格、T 的真实 Windows 按键通过；最新 W 位移约 2.29 m。
- 桌面采用窗口内事件过滤，子按钮/下拉框聚焦仍支持 W/S/A/D、R/F、Q/E；文字/数值编辑保留输入用途。松键、失焦、断连、暂停清理输入。选择手动模式退出悬停暂停，飞控确认后再回写 UE 状态。
- AirSim 原生 Hover 在前速度命令后可能过早完成并保留速度目标；现先零速度制动 0.6 秒再 Hover，以命令代数防止旧制动回调抢占新输入。严格八方向实机回归、鼠标按住、失焦归零通过；稳定后 0.7 秒悬停漂移约 0.0145 m（本次观测，不是性能保证）。
- runner 检测 UE PlaySessionId 和 listener 生命周期，重播后自动重建世界，按 UE scene_id 选择配置。真实停止/重播恢复后再次手动位移约 1.29 m。临时 UE 渲染阻塞且 listener 仍开时不会误重载。
- 设备按 Config/WISEYE/device_dimensions.json 校准：Mavic 3 展开机身不含桨叶 34.75×28.3×10.77 cm；初代 Avata 含护圈 18×18×8 cm；光电云台总高 80 cm。原始与 test_range 两张地图已保存、重开测量通过，并更新标准装配、场景配置和标定。原网格不改，不代表质量/惯量/光学内参完成实物标定。
- Avata 叠加的是未被隐藏的 Mavic 深层桨叶。改为递归收集并隐藏 Mavic 网格；Avata 动态组件归属 Drone，避免把地面云台识别成无人机附属 Actor。运行时尺寸、旧桨叶零可见和近景目视通过。Avata 保留一体静态网格，自身桨叶尚无独立动画，不复用 Mavic 桨叶。
- 最终 UE 构建成功，17 单元 + 15 完整桌面集成检查通过；八方向实机、UE 实体按键、重播恢复与双地图重开尺寸另有专门验证。证据 controls_dimensions_fix_20261019.json、avata_dimensions_fixed_20261019.png。此前 second_pc_run 中仅按“有位移”断言的手动测试不够充分，以本轮有方向回归为准。
- 运行仍为 Start-ProjectAirSim.cmd → Start-Desktop.cmd。当前保持手动/悬停供用户试键；UE 中先点击游戏画面。尚未提交/上传。papers 和其他既有本机变更保留。旧 configure_controls.py 不能用于新尺寸。


## 2026-10-19：E 盘第二台电脑拉取与完整验证（本机最新）

- 已从 cbdb7ef 快进到 GitHub origin/main 的 667b8a3；原有 papers/ 保留未跟踪，无其他开工前本机修改。
- 本机 E:/Projects/WISEYE-Studio，UE E:/Programs/UE_5.8（5.8.3）；独立 AirSim 在 E:/Projects/ProjectAirSim-Evaluation，固定 62229cd。使用原有 VS 2022、Python 3.14.6，新建 AirSim 自己的 .venv，不改原训练环境。
- MediaMTX 1.21.2 与 FFmpeg 9.0.2 Windows essentials 已安装并核验下载 SHA256。FFmpeg 位于 E:/Environments/ffmpeg-wiseye/ffmpeg-9.0.2-essentials_build/bin，已加入用户 PATH 并广播环境更新。若旧终端找不到，关闭后重开终端。
- 修复 Setup-ProjectAirSim.ps1 的三处首次安装兼容性：Windows PowerShell 对预期失败的 stderr 探测、CRLF 补丁匹配、首次生成 SimLibs 后再建联接。原生库 188/188 和 UE testEditor 53/53 构建成功；重复运行 setup -SkipBuild 通过。
- 14 项 Python 单元测试、15 项真实 UE/AirSim/RTSP/桌面集成测试通过；ffprobe 三秒分别解码 CH1 91 帧（1920×1080 H.264 30/1）、CH2 76 帧（640×512 H.264 25/1）。这验证输出帧率，不代表全部帧独立渲染。
- 首次冷启动记录了非致命 IsInGameThread/FAppTime 上下文 ensure；没有崩溃，后续飞行和全部集成检查通过。不要声称本机零告警；保留日志便于后续定位。
- 证据 docs/evidence/second_pc_run_20261019.json，窗口截图 second_pc_desktop_20261019.png；日志 logs/build-20261019.log、desktop-validation-20261019.log、airsim-20261019*.log。UE/桌面/飞控与视频服务保持运行。当前为自动航线，可直接使用。
- 日常先 Start-ProjectAirSim.cmd，再 Start-Desktop.cmd 连接。若当前仍有 UE 在运行，不要重复启动第二个编辑器；先正常停止并关闭再重开。
- 本轮按用户要求拉取并验证；修正和验收记录留在本机，尚未提交或上传。


## 2026-10-19：跨电脑安装与 GitHub 发布

- 功能提交 `375e31b` 已上传到 GitHub `main`，远端包含本轮 105 个代码、模型、UE 资源、场景、测试和文档变更。上传后已核对远端引用与本地提交一致。
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
# 2026-10-26：传感器接口编辑与体积/红外评估（最新）

用户要求可编辑RTSP等传感器接口、删除冗余、研究Anti-UAV式红外。已修改F主源码：AppConfig兼容旧配置、验证路径冲突/主机/端口、原子保存；统一stream_path/stream_url支持ptz01～04与scene/observer覆盖。数据页全局按钮与逐源编辑、设置页入口；连接中或RuntimeManager运行中禁止保存，不飞行中重启。客户端/源目录/订阅文本同步配置。gateway新增设备用同一路径函数，OBS可改；独立启动与开发Start-RTSP按可写配置启动MediaMTX，本机/远程RTSP发布分开。内置UE/飞控监听仍固定50051/50052，编辑控制端口用于连接已有服务，独立启动明确校验；点云/云台/JPEG共用UE通道，没有伪造点云RTSP。

51核心+11Qt回归通过；真实MediaMTX+FFmpeg自定义19554/custom/camera2/thermal发布/解码3帧640×512合成信号通过，证据rtsp-endpoint-20261026.json。不是UE新实时飞行或红外画质验收。F修改已同步E内置构建目录，桌面补丁构建/产物以本节后续交付记录为准；原20261023完整ZIP不可说已包含新功能。

清理只完成盘点：F候选5.821GiB、E构建目录候选107.542GiB；批量及固定路径递归删除被自动审批审查拒绝，**本轮没有删除/释放空间**，勿换工具绕过。docs/CLEANUP_REPORT.md与evidence/cleanup-20261026.json记录候选。保留最终Shipping目录/ZIP、源资产、ExternalActors、模型数据、Fleet、有效E Cooked/DDC及构建环境。清缓存不改变分发包16.864GiB。

红外方案docs/INFRARED_REALISM_PLAN.md：当前Stencil近似；建议先热材质分类+运行热源+PSF/噪声/FPN/平滑AGC+真实片段统计校准。CST Anti-UAV规格不能混称原Anti-UAV。ThermoForge仅温度场/游戏近似，Infinite Studio为商用辐射方案候选，均未安装/采购/确认UE5.8.4、IntelArc与Shipping授权兼容。本轮未改UE红外材质或重Cook，无Git提交推送。

# 2026-10-26桌面更新交付记录

已生成并回传F:\WISEYE-Studio\releases\WISEYE-Desktop-Update-20261026.zip（330377510B，约315MiB），F读回SHA256 758bb24fceb444a52a3a583ea975a557e0391b505689eafab6e495f9a180aaa3通过。只覆盖原001704完整包的桌面/文档/release.json/checksums；不含Simulation，不能单独运行，不覆盖LOCALAPPDATA配置。原完整ZIP保留。E最终桌面构建位于dist/WISEYE（第二轮直接spec构建默认输出），不是较早builds/desktop；已检查最终PYZ包含QCheckBox新版编辑模块。冻结诊断/GUI冒烟及源代码真实编辑对话框交互通过（保存mock防改用户配置），截图/报告docs/evidence/interface-*。复现脚本packaging/desktop_patch.py。仍未清理、未升级红外渲染、未Git提交推送。
