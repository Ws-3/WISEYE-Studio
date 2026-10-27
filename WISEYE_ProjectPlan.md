# WISEYE Studio（智瞳）：项目计划与持续交接文档

## 2026-10-27：当前功能打包，运行版仅自带城市

最终20261027-171140-City-Shipping完成全Cook，包含可编辑RTSP、增强IR、硬件性能栏和时间/雾/雨；按用户要求仅city随包，源码原始/测试场保留。发布版过滤旧配置中的未发布场景且不删配置，默认构建Content City。修复Shipping雨效类GC回收和无RHI STATS显存读数，Cook前编译Editor保证反射一致。54核心+15Qt、最终城市真实起降/云台/点云/三路原尺寸画面、IR/天气、自定义RTSP、冻结桌面与旧数据兼容通过；用户Fleet未改。源码F/E临时构建，交付路径、SHA及GitHub提交见RELEASE_BUILD，证据standalone-release-20261027。下一步为干净Windows验收、长期/多设备性能、正式安装器和签名在线更新；这些尚未交付。

2026-10-27启动兼容修复：预览脚本显式UTF-8读取场景JSON，解决Windows PowerShell5.1中文乱码引起的ConvertFrom-Json错误。5.1真实入口模拟进程启动验证通过，原用户配置不变；文档提供单进程ExecutionPolicy Bypass命令。

## 2026-10-27：运行状态与环境控制试验完成

工作台常驻显示运行主机显卡/显存/预算、CPU/RAM、GPU引擎峰值、实际FPS，持续低性能给出非弹窗提示；环境窗口可调视觉时间、雾、基础雨效并恢复默认。Editor构建、真实City参数/图像与53核心+15Qt通过，用户Fleet不变。启动Start-SimulationPreview.ps1，说明ENVIRONMENT_AND_PERFORMANCE.md。当前源代码试验版，旧ZIP未更新；物理天气/红外温度联动、阴影预算优化、长期/多设备与新飞行验收仍待做。

## 2026-10-23：独立Shipping包完成并回传F盘

Windows x64版本20261023-001704-All-Shipping已生成，含original/test_range/真实city；ZIP18108112700B约16.864GiB，F:\WISEYE-Studio\releases\WISEYE-20261023-Windows-x64.zip复制后SHA256一致。目录展开18107757190B/1438文件。用户批准内置盘临时构建，实际E:\Projects\WISEYE-BuildWorkspace，F保留源码与成品。三场景冻结worker/三路原尺寸图像/云台/点云/起飞手动升高降落RPM0、city中文空格路径与安装目录无新增文件通过，47核心+9Qt通过。完整问题修复/源码入口见AI_HANDOFF最新节、RELEASE_BUILD与evidence/standalone_release_20261023.json。下一阶段为干净Windows安装验收、长期/多设备性能和正式安装器/在线更新；不能把这些未来项宣称已完成。未上传GitHub。

## 2026-10-22：执行F盘打包，Game通过、Cook待存储恢复

项目已按用户要求迁至F:\WISEYE-Studio（源文件43.334GiB，六处插件联接转实体，E原工程保留）。Game Development编译链接成功；新增发布路径/启动/worker/Job与构建装配脚本，46核心路径+9Qt+1Job测试通过，早期桌面EXE独立依赖诊断通过。基础Cook关闭Zen后约987/1008资源，最终Desktop重打包COLLECT中断；尚无完整交付包。F盘Windows实际I/O重试disk153和UASPStor129端口重置，停止本轮负载，等待用户更换连接或选择内置盘暂存。恢复后重建Desktop→基础Cook/Stage/运行→城市All→Shipping/安装验收；详见docs/RELEASE_BUILD.md。未上传。

## 2026-10-22：打包实施技术交接

新增 docs/PACKAGING_IMPLEMENTATION_HANDOFF.md 作为下一位AI可执行任务书。按P0构建基线→P1基础独立包→P2城市Cook/Shipping和实际体积→P3安装与干净Windows验收→P4在线更新推进；含真实代码入口、路径/启动契约设计、依赖处理和验收。尚未开始打包，新增接口与脚本只是建议。保持本地SSD安装、硬盘/下载同一发布物的方向；不改现有仿真配置和用户资产。

## 2026-10-22：交付方式修订与可行性复评

用户澄清移动盘用于传输，后续支持下载。采用同一发布物经硬盘/网络分发，目标电脑本地SSD安装运行；直接移动盘运行降为可选扩展，默认配置保存在本机可写用户目录。F卷问题不阻塞E盘构建或网络分发。更新docs/PACKAGING_AND_UPDATES_PLAN.md复评与docs/PORTABLE_F_DRIVE_PLAN.md范围说明。技术路线可行但尚未实际Game/Cook/Shipping验证；先打通基础独立包，再城市Cook实测、干净Windows离线安装验收，随后在线更新。重点风险为运行插件、动态资产Cook、Python/Qt依赖及发布路径改造。完整25–60GiB仍仅容量预算；本轮只改方案文档，未构建或部署。

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

## 2026-10-22：多设备表面取点与统一RF完成（最新）

全部实例坐标/俯视图/取点列表按当前场景Fleet刷新；新建复制删除保存后更新，按设备ID保存改过的位置，旧预设保留额外实例，未加载设备提示先重载。UE放开默认两ID限制、按目标云台底座补偿、全局任务通过任意云台状态回传，并匹配device/token防错填。FastGeo道路加入静态表面白名单，忽略其它动态物和所有设备，实际命中73/70cm道路而非隐藏0cm平面。系统/UE无人机统一R上升F下降，观察QE和云台箭头不变。

增量构建成功；44核心、5新Qt回归、4预览回归通过；真实额外云台/无人机取点、取消、子实例状态、Windows RF/箭头映射、Qt选ptz-02后仅回填该草稿均通过。Fleet文件哈希不变，当前用户city1+2不调整；未进行起飞运动测试、未新增延迟测量。打包不能替代采集/编码/显示优化，指南已说明。证据multi_placement_rf_*_20261022，未提交上传。

## 2026-10-22：城市光追负载处理（最新）

针对用户常驻RT几何20%预算告警与卡顿，确认并关闭当前编辑器运行时硬件光追，同时保存DefaultEngine.ini默认r.RayTracing.Enable=0和r.Lumen.HardwareRayTracing=0，EnableOnDemand=1；保留项目编译支持/原尺寸。83MiB/400MiB不是GPU显存耗尽。编辑器city正确、开关读回0，证据city_raytracing_disabled_20261022.json；当时PIE已停，不宣称FPS已改善或卡顿完全修复。下一次运行需复测帧耗时，画质档不自动启用硬件RT。说明/交接已更新，未提交推送。

## 2026-10-22：预览延迟修复已完成（最新优先）

工作台通过原生UE最新JPEG缓存预览，避免本机H264/RTSP往返；外部RTSP接口保持，网关源帧去重、实际时间戳、禁止补帧。每来源保留原始尺寸、独立连接、单在途请求、单帧显示邮箱、源停滞提示及换设备旧响应隔离；点云显示查询改为100ms有界定时器。

正式单窗口40秒VIS内容年龄由843/P951923ms降为205/269ms；120秒VIS206/P95271/最大330ms，IR189/251/293ms，OBS188/268/323ms，2382次/每源全部CRC有效。最终额外仪表窗口40秒：VIS新帧paint142/P95183ms，点云54次真实靶位移160/P95248/最大532ms（旧310/494/807ms）。独立Hz符合节能源约10/10/8，无降分辨率；双模态仍非硬同步。证据和口径见docs/SENSOR_LATENCY_REPORT.md及evidence新native_after/points记录。

44核心单元、4项Qt预览回归、150%离线UI4组、三路RTSP3秒原尺寸H264解码通过。工作台与网关已重启应用，不重启UE/AirSim，不改地图/设备/飞控任务；69临时Actor清理、测试桥关闭。新预览延迟不代表外部RTSP低延迟保证，跨机/4+4/画质档/30分钟稳定仍待测。未提交上传GitHub。

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


更新（2026-10-21，V3界面实施）：用户明确要求按方案开始修改。已交付专业深灰蓝色主题、紧凑四页工作台、场景主导/双模态/跨设备多源布局、共享解码与原比例/1:1显示、固定身份与拖动布局、独立属性/控制选择、按请求确认的多设备参数草稿、固定应用栏、只读RPM、上传/执行分离航线、数据源接口表。35单元、9组真实UI、125%/150%各4组离线Qt、5组真实Qt飞行、6组两型号/SDK/健康回归通过；3机2云台配置字节不变。P1/P2/P3与P4主要交互完成，P4全量/P5长时性能尚未完成，TASK-023保持IN_PROGRESS。详见 docs/UI_REDESIGN_IMPLEMENTATION.md；未提交或推送。

更新（2026-10-21，界面设计交接）：用户要求整理完整 UI/UX 优化方案供下一位 AI 修改。新增 V3 界面规格、AI 实施交接与离线可点击布局示意，覆盖画面布局、视觉组件、参数事务、多设备控制、航线/编排/接口及分期验收。本次仅设计，未改生产程序、未重新运行 UE 测试，整体方案尚待评审；用户已确认专业深灰 + 蓝色强调、场景大画面 + 传感器缩略窗作为默认。详见 `docs/WISEYE_UI_REDESIGN_V3.md` 与 `docs/AI_UI_REDESIGN_HANDOFF.md`。

更新（2026-10-21）：旋翼接四电机实际AirSim遥测；降落成功后解除解锁，防止怠速被假停止动画掩盖。新增UE推进/渲染卡顿检测与运动指令拦截、读回超时取消、隐藏命令行、三档捕获/渲染性能设置、云台标准库SDK。35单元与6真实联调通过；两型号悬停约4931RPM、降落0，B580均衡/节能短采样GPU中位数89.7%/70.6%。当前用户原布局3机2云台保持不变。City Sample已选定，用户明确稍后下载，暂未导入；入口prepared=false。详见 docs/RUNTIME_OPTIMIZATION.md、GIMBAL_INTERFACE.md、CITY_SAMPLE_SETUP.md。偶发冻结未宣称全部排除，长时压力/城市性能/硬编与最终安装包仍未验收。

> **2026-10-21 多设备首轮已验证：** 已实现型号注册与实例配置、整套装配运行时复制、驾驶/云台独立选择、每机真实 AirSim Robot/独立航线、云台独立目标与传感器、分设备 RTSP 和原始记录身份。当前原始场景2机2云台待命；新增/复制/删除/位置编辑保存重载后生效。31单元、10双机联调、3组合恢复、3真实UE快捷键及双云台80cm/位置检查通过。补充可迁移 AirSim UE5.8 GC 完成同步补丁并接安装脚本。详见 docs/DEVICE_COMPOSITION.md、docs/DESKTOP.md 与交接顶部。每类上限4，4+4性能未验收；仍无避碰、队形、热插拔或任意型号导入，不把阶段 C 或 TASK-023 标为整体完成。

> **同日交互精简：** 移除工作传感器保存下拉，改子页/画面直接保存对应源；云台换比例回中摇杆，保留方向键。新增 docs/DEVICE_COMPOSITION.md，明确当前固定单机单云台以及后续模板/实例/挂载结构；本轮不宣称已实现整体型号注册或多实例新增。

> **2026-10-21 用户五项改进：** 已接桌面方向键云台、单架航点编辑/上传/单次循环/暂停续飞停止、独立传感器子页与启停、可选并排四画面缩略图与放大、系统内 UE 运行时观察流与自由相机控制。testEditor 构建成功，28 单元与 11 项真实 Qt/UE/AirSim/RTSP 联调通过，证据在 docs/evidence/workbench_v3_live_20261021.json。当前为逐点航线、拐点减速且不避障；OBS 是场景流，表面放置仍在 UE 独立窗口。参数会话内生效；最终独立安装包、多架、硬编、端到端视频性能验收仍待完成，TASK-023 保持 IN_PROGRESS。操作见 docs/DESKTOP.md 顶部更新。

> **2026-10-19 V2 实施更新：** 用户已批准仿真平台方案，已交付阶段 A 首轮工作台与性能基线，并继续实现表面放置、底座贴合和命名预设；启动为待命后由用户起飞。最终用户免装 UE/VS/开发 Python 是阶段 D 明确验收条件。

> **2026-10-19 前序状态：** 桌面统一实时显示 CH1 可见光、CH2 红外和 LIDAR 点云；CH1/CH2 已采用异步 GPU readback、编码流水线和持久连接，RTSP 输出为 30/25 FPS。两路同时运行在当前场景约产生 20 FPS 独立新渲染帧，完全独立 1080p30 仍需 GPU H.264。手动 AirSim 飞行支持界面按键和 W/S/A/D、R/F、Q/E 键盘。下一任务为硬件编码与统一传感器时间戳。

> **2026-10-16 AirSim 评估更新：** 固定提交 62229cd7c77ad31da7bc8aba8dd6303c564d8ba2 在 UE 5.8.3 编译运行。用户批准后已在独立分支修复 MoveOnPath 完成判定和 SimpleFlight 落地状态同步；严格飞行回归连续两次通过，Release C++ 单元测试 391/391 通过。可迁移补丁、证据和复现方法见 `docs/PROJECTAIRSIM_EVALUATION.md`。当时尚未修改 WISEYE 运行后端，也未验证 PX4、额外传感器和多地图飞行。

> **2026-10-14 迁移更新（优先于下方旧路径记录）：** 仓库现已包含完整 `ue5/WISEYE/test.uproject`、Config/Content/Source 和 Models。源码唯一位置为 `ue5/WISEYE/Source/test`，无需旧电脑 D 盘 Scene 工程。新电脑按根 README 构建启动，AI 先读 `AGENTS.md` 和 `docs/AI_HANDOFF.md`。云台恢复后用户已确认正常，要求直接同步，不再重新调整模型。

> **2026-10-14 后续用户要求覆盖旧的“不调整模型”约定：** 按用户明确提出的四项任务，已调整无人机/云台演示尺寸，增加自动/手动飞行、旋翼动画及云台跟踪/保持切换。尺寸不是厂商计量标定；历史巨大模型尺寸和旧恢复脚本坐标不适用于当前场景。

> **本文档是本项目的唯一长期计划与交接入口。** 本地 Codex、ChatGPT 或其他 AI 每次开始工作前必须先阅读本文档；每次完成工作后必须更新本文档，确保项目状态、决策、风险和下一步任务连续可追踪。
>
> **项目原则：** 先检查现状，再增量实现；先建立可验证的最小闭环，不一次性堆砌全部功能；任何未经实际验证的功能都不得标记为完成。

- 文档版本：`0.3`
- 建立日期：`2026-10-12`
- 项目品牌：`WISEYE`
- 软件名称：`WISEYE Studio`
- 中文名称：`智瞳——无人机光电仿真与智能感知平台`
- 代码仓库建议目录：`WISEYE`
- 当前阶段：本地 UE 两轴云台与无人机运动演示已运行验证；桌面界面、通信与视觉闭环待实现
- 状态约定：`TODO` 待开始；`IN_PROGRESS` 进行中；`BLOCKED` 受阻；`DONE` 已验证完成；`DEFERRED` 暂缓

---

## 0. 项目命名与品牌约定

- **主品牌：** `WISEYE`
- **软件名称：** `WISEYE Studio`
- **中文名称：** `智瞳——无人机光电仿真与智能感知平台`
- **一句话定位：** 面向无人机目标感知的三维光电仿真、云台控制与智能跟踪验证平台。
- **模块命名建议：**
  - `WS` — World Simulation：三维环境与目标运动仿真。
  - `YZ` — YOLO & Zoom：智能目标检测与相机视场/变焦控制。
  - `E` — Electro-Optical：光电成像、云台指向与自动跟踪。
- **命名说明：** 以上是本项目内部采用的品牌与模块释义，不代表这些词组是 `WISEYE` 的标准英文展开。`WISEYE` 作为易识别的主品牌，模块名用于表达系统能力。
- **一致性规则：** 新建的 README、桌面窗口标题、日志前缀、安装包显示名称和演示材料优先使用 `WISEYE Studio`；Python 包名、类名、UE5 项目名等技术标识按现有仓库约定逐步统一，不得为了改名一次性破坏兼容性。若仓库已存在，先盘点再决定是否重命名目录、模块或工程文件。

---

## 1. 项目目标

建设一套可在 Windows 桌面独立运行的无人机光电仿真与视觉算法验证软件，重点是**光电云台控制、相机成像、无人机目标检测与跟踪**，而不是首先实现完整飞控系统。

系统逐步实现：

1. 桌面主界面、仿真状态、参数配置、日志与实验管理。
2. UE5 三维环境、无人机/干扰目标、云台、光电相机及相机图像输出。
3. 云台手动控制、角度/角速度限制、相机变焦和状态查询。
4. 接入现有 Python/YOLO 目标检测环境，输出检测框、置信度和推理耗时。
5. 基于相机图像检测结果实现自动指向与目标跟踪，并处理目标丢失状态。
6. 自动生成 YOLO 格式真值标签、困难样本采集和数据集导出。
7. 保存实验配置、图像、标签、日志和性能指标，支持复现实验与比较结果。

### 1.1 第一阶段明确不做的事

- 不把 PX4、飞控、动力学和完整飞行控制作为首个里程碑的前置条件。
- 不在初期尝试把 UE5 渲染窗口嵌入 Qt 主窗口；先允许 UE5 作为独立进程运行。
- 不在没有基准测试前假定两张 GPU 的显存可以合并，或预先设计复杂的多 GPU 调度。
- 不因开发便利擅自删除用户现有数据、训练权重、配置或实验结果。

## 2. 已知背景与待确认事项

### 2.1 已知背景

- 目标场景：无人机小目标，尤其是城市背景下的检测、跟踪与干扰目标区分。
- 用户已有 Anti-UAV 基础训练及实拍数据集训练经验，也使用过 YOLO 相关工具链。
- 用户报告的开发硬件：NVIDIA RTX 5060 8GB、Intel Arc B580 12GB。
- 主要开发环境目标：Windows 原生运行。
- 推荐先使用 RTX 5060 运行 UE5；视觉推理设备的最终选择应通过实际兼容性和性能测试决定。

### 2.2 第一次执行时必须确认

- [ ] 当前工作目录、仓库是否已经存在、Git 状态及当前分支。
- [ ] Windows 版本、Python 版本、Git 版本及已安装的 Python 环境。
- [ ] UE5 是否已安装、具体版本、是否已有 `.uproject`、项目使用 C++ 还是纯蓝图。
- [ ] 现有 YOLO 项目路径、框架版本、权重位置及推理环境；不得擅自覆盖或迁移。
- [ ] 当前机器可用磁盘空间、GPU 驱动和实际可用推理设备。
- [ ] 用户希望的项目根目录。若当前目录已经包含项目，优先在现有项目上增量建设。

**规则：** 这些事项在盘点后填写到“当前状态”和“变更记录”；未确认的信息不要当作事实写入实现代码。

## 3. 推荐总体架构

采用三个主要进程，降低 UI、仿真和视觉算法之间的耦合：

1. **`desktop_app`：桌面主程序**
   - Python + PySide6。
   - 管理窗口、菜单、参数面板、仿真连接状态、日志、实验配置和用户操作。
   - 不在 UI 线程执行长时间推理或阻塞式网络读取。

2. **`ue_simulator`：三维仿真进程**
   - Unreal Engine 5，C++ 与 Blueprint 配合。
   - 管理场景、目标、云台、相机、Render Target 和仿真状态。
   - 网络线程只负责收发与解析；涉及 UE 对象的操作必须安全地转交游戏线程。

3. **`vision_worker`：视觉服务**
   - Python，优先复用用户已有 YOLO 环境和代码。
   - 负责检测、跟踪、目标状态估计、推理性能统计及可选的困难样本筛选。

4. **数据与实验层**
   - SQLite 保存实验元数据、配置索引和指标。
   - 图像、标签、日志等大文件存储在项目数据目录或用户指定的数据盘。
   - 通过配置指定数据根目录，避免将大型数据集和权重强制放入 Git 仓库。

### 3.1 依赖方向

- UI 依赖稳定的核心数据模型和服务接口，不直接依赖 UE5 内部类。
- 仿真适配器负责把统一命令转换为 UE5 通信协议。
- 视觉服务通过图像帧和结构化检测结果与其他进程交互。
- 业务服务尽量可在没有 UE5 的情况下通过 Mock Server 和测试替身验证。

## 4. 技术选型与默认约定

| 模块 | 默认方案 | 约定 |
|---|---|---|
| Windows 桌面 UI | Python + PySide6 | UI 线程不执行阻塞任务 |
| 三维仿真 | UE5，C++ + Blueprint | 先确认本机 UE5 版本及现有项目 |
| 仿真控制通信 | TCP + JSON Lines | 默认仅监听 `127.0.0.1` |
| 图像传输 | TCP 长度前缀 + JPEG/PNG | 明确帧编号、时间戳、图像尺寸和编码 |
| 视觉服务 | Python + 现有 YOLO 环境 | 不擅自升级或重建用户环境 |
| 图像处理 | OpenCV、NumPy | 按实际需要加入依赖 |
| 配置 | YAML/JSON | 重要参数可追溯、可导出 |
| 实验元数据 | SQLite | 大图像与数据集不直接存进数据库 |
| 测试 | pytest + 协议 Mock | 没有验证的功能不能标记 DONE |
| 版本管理 | Git | 数据集、权重、缓存和大文件默认不入库 |

版本与依赖应在第一次环境盘点后确定。未经确认，不要直接固定一个可能与用户环境冲突的 UE5 或 YOLO 版本。

## 5. 通信协议初始设计

以下端口是**建议默认值**，首次实施时应检查是否被占用，并集中配置，不得在多个文件中散落硬编码。

- Desktop ↔ UE5 控制通道：`127.0.0.1:50051`
- UE5 → 图像接收端：`127.0.0.1:50052`
- Vision Worker ↔ Desktop：`127.0.0.1:50053`

### 5.1 控制消息

控制通道使用 UTF-8 JSON Lines，即每条 JSON 消息以换行符结尾。TCP 是字节流，接收端必须按换行符缓存和组包，**不能假设一次 `recv()` 就对应一条完整消息**。

请求示例：

```json
{
  "version": 1,
  "request_id": "cmd-000001",
  "command": "gimbal.set_angles",
  "timestamp_ms": 1791800000000,
  "payload": {
    "yaw_deg": 10.0,
    "pitch_deg": -5.0
  }
}
```

响应应至少包含：`version`、`request_id`、`status`、`payload`；失败时提供结构化 `error`，并能将响应与请求关联。

### 5.2 初始命令集合

- `sim.ping`
- `sim.get_state`
- `sim.pause`
- `sim.resume`
- `sim.load_scene`
- `target.set_pose`
- `target.set_trajectory`
- `gimbal.set_angles`
- `gimbal.set_rates`
- `gimbal.get_state`
- `camera.set_zoom`
- `camera.get_state`
- `tracking.start`
- `tracking.stop`

每条命令必须有参数校验、明确成功/失败响应和超时处理。按里程碑逐条实现，不要求一次完成全部命令。

### 5.3 图像与检测结果

- 图像通道使用 4 字节网络字节序长度前缀，再跟图像编码数据；接收端需限制最大帧长度并处理断连、半包和非法长度。
- 每帧至少关联 `frame_id`、时间戳、宽高、编码格式。
- 检测结果建议包含 `frame_id`、`timestamp_ns`、`targets`、`bbox_xyxy`、`confidence`、`class_id`、`inference_ms`。
- 检测框坐标统一为原始相机图像坐标，并明确采用左上角原点的 `xyxy` 格式。
- 对断连、过期帧、重复帧、推理超时和空检测结果定义可观察的处理方式。

## 6. 云台、相机与自动指向设计

### 6.1 推荐 UE5 组件层级

```text
VehicleRoot
└── GimbalYawPivot
    └── GimbalPitchPivot
        └── EO_Camera
            └── SceneCaptureComponent2D
```

首次实现时必须明确：UE 坐标轴约定、云台机械零位、正负方向、相机安装偏移、角度和角速度限制，以及相机坐标与目标坐标的转换规则。

### 6.2 自动指向

- 根据检测框中心与相机内参计算视线偏角；不可将像素误差直接当作云台角度。
- 第一版使用带死区、限速、限幅的简单比例控制器，便于调试和验证。
- 显式定义状态，例如 `IDLE`、`TRACKING`、`LOST`、`ERROR`。
- 目标丢失时停止或按配置执行安全策略，不得继续无界地使用过期检测结果。
- 记录目标框、角度误差、云台命令、执行状态和时间戳，以支持调参与复现实验。

## 7. 推荐目录结构

首次执行时应先查看现有仓库。如果已经存在相近结构，优先沿用并更新本文档，不要为了符合下列示例而大规模搬迁文件。

```text
WISEYE/
├── README.md
├── WISEYE_ProjectPlan.md
├── .gitignore
├── requirements.txt
├── apps/
│   └── desktop_app/
│       ├── main.py
│       ├── main_window.py
│       └── panels/
├── core/
│   ├── config.py
│   ├── protocol.py
│   ├── events.py
│   ├── logging_config.py
│   └── models.py
├── adapters/
│   └── simulator/
│       ├── base.py
│       └── ue5_adapter.py
├── services/
│   ├── sim_manager.py
│   ├── gimbal/
│   │   ├── controller.py
│   │   └── target_pointing.py
│   ├── camera/
│   │   └── frame_client.py
│   ├── vision/
│   │   ├── worker.py
│   │   ├── detector.py
│   │   └── tracker.py
│   ├── dataset/
│   │   ├── ground_truth.py
│   │   ├── hard_sample_miner.py
│   │   └── yolo_exporter.py
│   └── experiment/
│       ├── manager.py
│       └── metrics.py
├── configs/
│   ├── app.yaml
│   ├── camera.yaml
│   └── gimbal.yaml
├── ue5/
│   └── UAVOptics/
│       ├── UAVOptics.uproject
│       ├── Config/
│       ├── Content/
│       │   ├── Maps/
│       │   ├── Vehicles/
│       │   ├── Gimbal/
│       │   ├── Cameras/
│       │   └── Targets/
│       └── Source/UAVOptics/
│           ├── Bridge/
│           ├── Gimbal/
│           ├── Camera/
│           └── Targets/
├── data/       # 本地数据，按需加入 .gitignore
├── logs/       # 运行日志，通常不入库
├── tests/
└── scripts/
```

## 8. 里程碑与验收标准

### M0：环境与仓库盘点 — `IN_PROGRESS`

任务：
- [ ] 检查现有仓库、Git 状态、目录结构和已有代码。
- [ ] 检查 Python、PySide6、UE5、C++ 编译工具链、YOLO 环境及 GPU。
- [ ] 记录确认过的版本、路径、缺失项和风险。
- [ ] 生成或更新 README、`.gitignore` 和依赖清单（仅在确认必要时）。

验收：有一份真实环境盘点结果；未覆盖已有项目或数据；明确 M1 的最小任务。

### M1：PySide6 桌面 UI — `DONE`（最小窗口验收）

任务：
- [x] 创建最小主窗口、状态显示、日志区和基础参数面板。
- [x] 定义核心数据模型、配置读取、统一日志和服务接口。
- [x] 增加真实 UE 连接状态、打开 UE、暂停/继续和断开入口。

验收：应用能在目标 Windows 环境启动；界面响应正常；配置错误可读；基础功能有验证记录。

### M2：通信协议与 UE5 Bridge — `IN_PROGRESS`（控制桥已验收）

任务：
- [ ] 先实现 Python Mock Server 和协议单元测试。
- [x] 实现 UE5 Bridge 的连接、JSON Lines 解析、响应关联和错误处理。
- [x] 实现 `sim.ping`、`sim.get_state`、`gimbal.set_angles` 及其他控制。
- [x] 网络请求对 UE 对象的操作在游戏线程执行。

验收：Mock 测试通过；UE5 启动后能完成 ping、状态查询和云台角度命令往返；异常断连不会卡死 UI。

### M3：相机图像通道 — `IN_PROGRESS`

任务：
- [x] UE5 相机/Render Target 输出图像（可见光 1920×1080、IR 640×512，原生 PNG 导出和桌面快照已验证）。
- [x] 实现 CH1/CH2 图像帧打包、接收、帧编号、尺寸与编码校验（稳定原型 2 FPS）。
- [ ] UI 已显示 RTSP 实时图像和断连状态；真实帧率、端到端延迟、丢帧与队列深度仍待完成。

验收：持续接收图像时 UI 不阻塞；能处理断连、无效帧和帧长度异常；基本性能指标可观察。

### M4：YOLO 检测接入 — `TODO`

任务：
- [ ] 复用现有推理环境，先实现单帧输入/输出接口。
- [ ] 实现异步推理、检测结果结构和可视化。
- [ ] 记录推理耗时、帧时间戳和错误信息。

验收：能对 UE5 图像输出检测框；框坐标与原始图像一致；模型/设备错误有明确提示；不破坏现有训练环境。

### M5：自动指向与跟踪 — `TODO`

任务：
- [ ] 明确坐标系、相机内参、云台零位和机械限制。
- [ ] 实现像素偏差到视线角度的换算。
- [ ] 实现带死区、限速和限幅的第一版控制器。
- [ ] 实现目标丢失状态、恢复逻辑和运行日志。

验收：使用静态目标和预设轨迹可重复验证；云台能按检测结果指向目标；目标丢失后不会继续追踪过期框。

### M6：真值标签与实验管理 — `TODO`

任务：
- [ ] 由 UE5 场景真值生成检测框，校验可见性和图像坐标转换。
- [ ] 导出标准 YOLO 标签和数据集配置。
- [ ] 实现困难样本筛选、采集原因记录和人工复核入口。
- [ ] 记录实验配置、模型版本、数据集版本、指标和输出位置。

验收：导出的图像/标签可被现有 YOLO 工具链读取；抽样检查标签准确；实验可以按记录复现。

### M7：系统完善与交付 — `TODO`

任务：
- [ ] 完善异常处理、日志轮转、配置校验和启动/退出流程。
- [ ] 增加测试、性能测试和用户操作说明。
- [ ] 明确打包方式、依赖、运行步骤和已知限制。

验收：在目标机器上按文档可以启动；主要功能有可复现的验收记录；已知问题和限制公开记录。

## 9. 推荐实施顺序（MVP）

1. 先完成 M0，不立即大规模创建代码或安装依赖。
2. 创建最小 PySide6 窗口，验证应用启动和日志。
3. 写 Python Mock Server，验证协议、超时、断连、分包和粘包处理。
4. UE5 端先实现 `sim.ping`、`sim.get_state`、`gimbal.set_angles`。
5. 打通相机图像通道并显示图像。
6. 接入现有 YOLO 环境并叠加检测框。
7. 实现自动指向与目标丢失处理。
8. 最后接入真值标签、困难样本采集和实验管理。

每个阶段都应先定义可观察的验收条件，再实现，再运行验证；不要只以“代码已写”作为完成标准。

## 10. Codex / AI 持续协作规则（必须遵守）

每个 AI 会话均按以下流程执行：

### 开工前

1. 阅读本文件全文，尤其是“当前状态”“下一步任务”“里程碑”和“变更记录”。
2. 检查工作目录与 Git 状态，识别未提交修改；不要覆盖用户已有改动。
3. 对照实际代码确认文档是否过期。若代码与文档冲突，先调查并记录，再作最小、安全的修正。
4. 只选取一个明确且可验证的近期任务；涉及多个独立目标时拆分任务。
5. 对有破坏性或环境影响的操作（删除、覆盖、升级、重装、迁移、修改系统网络配置等），先说明影响并取得用户同意。

### 工作中

1. 优先做小步、可回滚的增量修改。
2. 不伪造测试结果、命令输出、文件路径或完成状态。
3. 发现阻塞时记录具体错误、复现步骤和需要用户确认的事项；不要用未经验证的猜测掩盖问题。
4. 不把密钥、令牌、密码、私有数据写入计划文档或 Git。
5. 新增依赖前说明用途；能复用已有依赖时不要重复引入。

### 每次结束前必须更新本文档

- 更新“当前状态”与“下一步任务”。
- 更新对应里程碑状态和验收项。
- 在“变更记录”追加日期、完成事项、修改文件、验证命令与结果、未完成项、风险及下一步。
- 如果技术方案发生变化，更新对应章节并写明变更原因；不要只追加新方案而保留相互矛盾的旧方案。
- 只有实际运行并通过相关验收的项目才可标记为 `DONE`。未运行、未安装、无法测试或只完成部分的，应明确标记。
- 不得因为一次会话结束而把未完成任务标记为完成。

### 每次交付给用户的简短报告格式

```text
本次目标：
完成内容：
修改/新增文件：
验证命令与结果：
未完成事项：
风险/需要用户决定：
计划文档是否已更新：
建议的下一步：
```

## 11. 当前状态

- **2026-10-19 系统设计讨论：草案完成，实现待审批。** 用户要求仿真平台与扩展数据处理分工，先审批后实现。方案见 docs/WISEYE_SIMULATION_PLATFORM_DESIGN_V2.md，包含场景/传感器布局、参数、自由观察、初始布置、多架和实时数据面。旧算法闭环路线暂不继续实施；本轮只读检查与方案/原型验证，无运行代码或 UE 资源改动。

- **2026-10-19 旋翼速度/点云修复：DONE。** 默认视觉 6000 RPM + 高速扫掠盘；点云去除外形缩放、恢复无人机查询命中，新增等比例三视图。构建、17 单元、15 桌面联调、八方向飞行、两型号停启/扫掠尺寸及米制参考平面验证通过。证据 rotor_lidar_fix_20261019.json。仍为单帧 576 射线，不是累积建图或电机遥测。

- **2026-10-19 当前修复：DONE。** UE/桌面按键统一经 AirSim 控制，修复输入组件优先级、子控件焦点和旧 Play 会话问题；增加松键制动与抢占保护。Mavic 3 机身 34.75×28.3×10.77 cm、Avata 18×18×8 cm、云台高 80 cm，两图保存重开通过。17 单元 + 15 UI 联调，以及八方向实机/实体 UE 键/重播恢复均通过。证据 controls_dimensions_fix_20261019.json。Avata 自身桨叶现已拆为四组独立动态旋翼，统一开关、反向配对、停止/恢复、尺寸和外观切换验证通过（见 avata_rotors_20261019.json）；质量/惯量和光学内参未做实物标定。


- **2026-10-19 第二台电脑完整运行验收：DONE。** E:/Projects 已快进到 667b8a3；本机首次安装固定 AirSim/MediaMTX/FFmpeg，修正 setup 的 PowerShell/CRLF/首次联接问题。AirSim 188/188、UE 53/53 构建成功；14 单元 + 15 真实桌面集成检查通过，CH1 1080p30 与 CH2 640×512p25 RTSP 输出核验通过。系统保持运行，证据 second_pc_run_20261019.json。首次冷启动有非致命 FAppTime ensure，未阻断验证；该现象仍待后续定位。


2026-10-19 实时图像与操作界面更新：CH1 可见光、CH2 红外已通过 MediaMTX/FFmpeg 发布和桌面显示；增加 AirSim 起飞/悬停/降落按钮、键盘手动飞行与 Mavic 3/Avata 外观切换。UE 已使用异步 GPU readback、多帧 JPEG 流水线和持久连接；RTSP 实测输出 CH1 30 FPS、CH2 25 FPS，当前完整场景两路同时运行约产生 20 FPS 独立新渲染帧。完整流程和分阶段验收见 `docs/SYSTEM_UX_DESIGN.md` 与 `docs/RTSP.md`。

2026-10-17 更新：Project AirSim 已嵌入 WISEYE 自己的 UE 地图，Fast Physics/SimpleFlight 成为默认飞行动力学后端；现有无人机模型作为无碰撞整机外观跟随 `Drone1`。桌面已通过独立 50052 飞控服务控制自动/手动、悬停暂停、继续和物理复位，并实时显示云台激光点云。下一步统一相机/点云/飞行时间戳并实现持续图像通道。详见 docs/PROJECTAIRSIM_INTEGRATION.md。

2026-10-19：ZIP 工作副本已安全接回 GitHub `main` 历史，当前工程具备正常 pull/push 能力。多场景配置、桌面地图选择、标准包导入、UE 场景准备入口、运行时切换与自动重连已完成；original 与 test_range 共用设备逻辑。用户反馈的新地图部件分离已修复：Python 旋转参数使用命名参数，按标定局部变换重建装配，整机锁定分组选取。详见 docs/SCENES.md、docs/AI_HANDOFF.md 与 docs/evidence。第三方 Fab/WP 场景尚未实测，标准包 v1 只处理普通地图，不包含独立程序打包/热加载。

截至 2026-10-14：本机运行、模型演示尺寸、自动/手动飞行、旋翼、云台跟踪/保持、双模态最小传感器、PySide6 主窗口和本机 TCP 控制桥均已完成运行验证。UE 5.8.3、VS 2022/MSVC 14.44、SDK 10.0.26100、Intel Arc B580；桌面 Python 3.14.6 / PySide6 6.11.0。VC++ x64 升级经用户明确同意并运行成功。

C++ 构建、真实 PIE 40 秒/79 样本、14 项控制、保存后重开、双模态尺寸/热参数/反转/遮挡通过；桌面真实 UE 10 项与协议单元 4 项通过。原始实验数据留在 Saved/WISEYE，摘要在 docs/evidence。

M1 最小窗口 DONE，M2 含 AirSim 统一飞控 DONE；M3 已有原生图像/点云导出、CH1/CH2 RTSP 实时图像和实时点云预览，性能监测与硬件编码仍 IN_PROGRESS。M4/M5 视觉检测闭环仍 TODO。当前跟踪读取 UE 真值，飞行使用 Project AirSim Fast Physics/SimpleFlight；红外是热强度近似，不是物理测温，尺寸/光心未按厂商图纸标定。

跨电脑以本仓库完整 UE Source/Config/Content（含外部 Actor）及 Python 源码为准，保留 test/testEditor。运行与同步见 docs/DESKTOP.md、GIT_WORKFLOW.md；今天上传和清理结果见 WORKLOG_2026-10-14.md。下方变更记录保留各阶段历史描述，不代表当前状态。

## 12. 下一步任务清单

- [x] **TASK-022（2026-10-19，设计交付）：** 仿真平台 V2 方案与两种可点击布局，当前源码与视频链路盘点、原型浏览器验证。
- [ ] **TASK-023（IN_PROGRESS，用户已批准）：** 按 A/B/C/D 实施；阶段 A 首轮加入四页工作台、设备属性、独立自由观察/输入模式、数值初始布置与 AirSim 同步、待命启动、双画面与有界预览。已补充 UE 点击表面、表面高度校正和命名预设；完整 A 仍需三轴拖拽、初始姿态与操作体验验收；B 硬编/直接数据路径、C 多架和 D 内嵌/独立安装尚未完成。

- [x] **TASK-017（2026-10-17）：** CH1/CH2 RTSP 稳定原型、桌面实时显示、AirSim 起飞/悬停/降落按钮、Mavic 3/Avata 外观切换。
- [x] **TASK-018（2026-10-19，数据通路）：** 异步 GPU readback、多帧编码流水线、持久连接与 CH1 30 FPS/CH2 25 FPS RTSP 输出。
- [ ] **TASK-020：** 去掉 JPEG/Base64 中间层，使用 GPU H.264 硬件编码，使 CH1 每个 30 FPS 输出帧和 CH2 每个 25 FPS 输出帧都是独立新渲染帧，并增加延迟、队列深度和丢帧统计。
- [ ] **TASK-019：** 任务/航点编辑、起飞前检查、一键记录和同步回放。

- [x] **TASK-012（2026-10-15，基础场景能力）：** 原始地图与新测试场切换、统一配置、标准包导入器及 UE 接入脚本；完整编辑器验证设备整体装配、移动、旋转、组选择。第三方复杂地图适配需逐资源验收。
- [ ] **TASK-013：** 在用户选定的 Fab/社区地图中验证依赖、完整迁移、设备安装位置、遮挡及 World Partition 流送。
- [x] **TASK-014（2026-10-17）：** Project AirSim Fast Physics/SimpleFlight 嵌入 WISEYE，现有整机外观跟随 AirSim 位姿；原始地图真实起飞/路径联调通过。
- [x] **TASK-015（2026-10-17）：** 地面光电云台激光扫描器，随 PitchPivot 转动，状态接口与 PLY 点云导出通过。
- [x] **TASK-016（2026-10-17）：** 桌面飞行命令桥接 Project AirSim，实现悬停暂停、物理复位、手动控制和实时点云显示。
- [ ] **TASK-021（下一近期目标）：** 统一相机、点云与飞行状态时间戳和帧编号，并完善端到端性能监测。

- [x] **TASK-009：** 可见光 1920×1080 / IR 640×512 最小双模态及图像、遮挡、保存重开验证。
- [x] **TASK-010：** WISEYE 主窗口与 UE 控制桥，连接/状态/暂停闭环及双模态快照，真实 UE 集成验收通过。
- [x] **TASK-011：** 持续图像通道已完成；帧编号、统一时间与 FPS/延迟监测并入 TASK-021。
- [x] **TASK-001（优先级 P0）：** 在实际项目根目录盘点现有文件、Git 状态与已有实现。
- [ ] **TASK-002（优先级 P0）：** 检查 Python、UE5、编译工具链、YOLO 环境和 GPU 状态。
- [x] **TASK-003（优先级 P1）：** 根据盘点结果确定实际目录结构和首个最小可运行目标（用户指定先完成 UE 云台/无人机演示）。
- [x] **TASK-005（用户当前目标）：** C++ 运动、两轴云台和相机捕获演示，已编译并运行验证。
- [x] **TASK-007（2026-10-14）：** 第二台电脑同步 Git、修正 main 跟踪、首次构建、资源完整性和真实 PIE/PNG 验证；已记录两台电脑协作流程。
- [x] **TASK-008（用户四项要求）：** 合理演示尺寸、自动航线与键盘手动飞行、四组旋翼动画、云台跟踪/保持切换；保存、重开和运行验证通过。
- [ ] **TASK-006（部分完成）：** Mavic 3/Avata 外形与 80 cm 云台已校准并保存重开；镜头光心计量标定及分离零件整理仍待完成。
- [ ] **TASK-004（优先级 P1）：** 设计并测试控制协议 Mock Server。

TASK-001 至 TASK-003 完成并记录后，再决定是否开始 M1。不要在缺乏环境信息时一次性生成整套工程。

## 13. 变更记录

### 2026-10-19：跨电脑发布整理

- ZIP 工作副本已接回 GitHub main 历史；保留远端提交并将当前源码、Avata 原始模型与 UE 资产、多场景、Project AirSim/RTSP 集成和验证证据纳入同一提交范围。
- 功能提交 `375e31b` 已推送至 GitHub `main`；远端与本地提交一致。随后只追加本条发布确认和 AI 交接记录。
- 新增 `docs/INSTALLATION.md` 与 `docs/FILE_STRUCTURE.md`，统一新电脑安装、完整启动、可提交资源和本机生成目录说明；README、桌面说明、Git 协作和 AI 交接同步到当前实时流与飞控状态。
- 上传前检查排除 `.venv`、Saved、Binaries、Intermediate、日志、运行证据、MediaMTX 和 Project AirSim 可重建目录；保留插件描述文件、固定补丁及 World Partition 资源。
- 本轮发布验证结果和远端提交号在上传完成后写入交接文件。

### 2026-10-17：Project AirSim 动力学与云台激光

- WISEYE GameMode 继承 Project AirSim GameMode，在原地图和测试场内启动仿真服务；新增默认 AirSim/可回退 Kinematic 后端、`Drone1` 绑定和无碰撞视觉整机同步。
- 新增 `GimbalLidarMount/GimbalLidarBody`、UE 射线扫描、状态字段、启停/捕获命令和局部米制 PLY 导出。激光继承现有 YawPivot/PitchPivot，不改变云台部件轴向。
- 新增两张 AirSim 场景配置、Fast Physics 机器人配置、自动起飞/路径脚本、首次安装/目录联接脚本与启动入口。第三方大体积源码和二进制仍不上传。
- Project AirSim 自定义环境适配增加公开 GameMode 头文件解耦、外部插件着色器目录解析、场景 Actor 指针初始化和 GIS 安全清理；连续两次场景热重载通过。统一补丁已更新。WISEYE 原有实时图像读回同步修正为 UE 5.8 API，并去掉重复捕获。
- `testEditor` 联合构建成功；真实 UE 监听 8989/8990/50051，完成起飞和 MoveOnPath，WISEYE 绑定成功。100 个遥测样本三轴跨度 1183.852/760.774/733.216 cm；激光 576 射线、接口末端 8 命中并导出 PLY。
- 新增 50052 AirSim 飞控服务、桌面九键手动控制、悬停暂停、自动恢复和物理复位；新增 50051 点云预览接口与桌面实时俯视显示。一键启动自动进入 Play。真实控制与 576 点预览、13 项 Python 测试、UI 启动检查和 UE 增量构建通过。下一步执行 TASK-017。

### 2026-10-15：多地图功能与设备装配修复

- 新增 core/scenes.py、桌面 scene_dialog、场景选择与自动重连、WiseEyeScenes.cpp、scene_tools/prepare_registered_scene/export_scene_pack 脚本，以及标准装配 JSON、两个场景配置和 TestRange 地图。
- C++ 以 sim.load_scene 接受已准备地图，确认后重载并关闭旧连接；桌面确认新 scene_id 后恢复。地图导入不覆盖资源，进行文件清单、路径、SHA256 和共享依赖检查，后台线程避免导入阻塞 UI。
- 用户发现新场景云台部件分开。修复 Python Rotator 位置参数顺序错误，统一使用 pitch/yaw/roll 命名参数，基于原标定的局部变换恢复组件挂接，建立无人机/云台整体选择组。修复 test_range 并保留用户整机位置；原始地图保持原状。
- 曾发现编辑器 MatineeCam 辅助网格进入运行画面，已从设备提取器排除并修复测试地图。早期接口/分辨率通过不能代替几何/图像验收。
- 新增 tests/test_scenes.py、verify_scenes_live.py、UE verify_scene_assembly.py。C++ 构建成功；真实编辑器中保存后装配与新生成装配均通过，几何误差约 3e-8 cm / 1.3e-11 cm（数值复原误差，不是设备精度）。选择验证必须用完整编辑器，commandlet 不重建 GroupActor 编辑器关联。
- 运行/协议/AI 交接文档更新；未提交或推送（当前 ZIP 无 .git）。未下载第三方地图，不代表任意 Fab 或 WP 资源已验收。
- 最终验收：11 项 Python 单元测试通过；4 次真实地图切换和自动重连、8 张可见光/IR 快照通过，已目视确认修复后的测试场无人机图像。修复后场景包成功从 UE 导出，163 个共享依赖通过校验，隔离目录导入的地图文件哈希一致。UE 留在修复后的测试场播放。

### 2026-10-14：可见光/红外最小双模态

- 新增 WiseEyeSensors.cpp、组件/参数、原生尺寸、I/B 控制和模态导出元数据；更新 HUD 与 EO 视角比例。新增 configure_sensors.py、verify_sensors.py、prepare_sensor_test.py；创建 M_IR_Minimal/RT_IR，更新 RT_EO、关卡引用、r.CustomDepth=3、云台热标记与 Config/WISEYE/sensors.json。原网格保持。
- 备份 Content/Config 到忽略的 runtime/Backup-before-sensors。UBT 首次未收录新 CPP，-gather 后构建成功；未暴露的 Python gamma 属性改由 C++ 设置。红外首批 alpha 为 0，补齐材质 Output Alpha/Opacity=1 后验证 alpha 全 255。
- 测试的 Python deferred spawn API 不可用，transient 编辑器对象未复制 PIE；改用不保存的临时普通 Actor。遮挡样本验证通过后停止 PIE、清理测试体并保存。没有遗留测试障碍。
- verify_sensors 通过两套分辨率/比例/共位/变焦/模态切换及样本导出；PIL 验证 RGB 单色、alpha 全 255、调色板反转平均误差 0、热强度响应和遮挡隐藏目标。PNG 在 Saved/WISEYE/20261014_174652，已查看图像；证据摘要 docs/evidence/sensors_validation.json。
- 正常关闭/重开真实编辑器，两套资产、热材质引用/PIE 实例正常；verify_controls 14 项检查再次通过（17:58:21）。当前运行 IR 演示。主窗口、TCP、视觉闭环和物理红外模型仍未实现；未提交推送。
- 用户随后讨论主窗口；下一近期任务为连接 UE、显示状态、暂停/继续最小闭环，再接双模态图像。

### 2026-10-14：尺寸、飞行操作、旋翼和云台保持

- 用户明确授权调整光电云台与无人机大小，选择“自动航线 + 键盘手动飞行”；新增控制状态和操作提示，保留已有相机导出、变焦、暂停/复位能力。
- 修改唯一 C++ 源码 WiseEyeDemo.h/.cpp：四个旋翼根组件、600 RPM 动画、对角同向/相邻反向；M 模式切换、WASD/升降/转向/加速、归一化斜向速度、手动高度上下限、无输入悬停；T 锁定当前云台方向；F 旋翼开关；新增第三个无人机近景视角。自动恢复保持当前位置，R 回到保存航线中心。
- 先保存原编辑器未保存内容，备份 Content/Config 到忽略的 runtime/Backup-before-controls。configure_controls.py 调整根缩放、底座落地、无人机根居中、旋翼轴心及航线/相机；不重导入或修改原始网格。保存更改的 World Partition Actor/对象和地图，更新 Config/WISEYE/calibration.json。
- 首次链接因编辑器 DLL 尚被占用失败，正常关闭已保存的编辑器后重建成功。布局脚本先后修正 UE Python HitResult 返回值和读取 API；控制验证修正空 StaticMeshComponent 的选择。脚本失败阶段未保存关卡，修正后尺寸检查/保存成功。
- Start-WISEYE.ps1 -BuildOnly 编译成功；verify_demo 在真实 PIE 40 秒验证通过（79 个样本），图像在 Saved/WISEYE/20261014_170117。verify_controls 14 项检查通过；原图分别 SHA256 1f1c4e8f1f9bd4cbd867650b52857619ac6a040aa1710d68a05efa5fd42f84a0、310579106358b3a1fb1aaa624ab40a6a5d03710657465e6aec21c26c5e30a845，已目视检查。
- 保存验证最初使用 NullRHI commandlet，World Partition 外部 Actor 未加载，不能据此判定布局失败；改为正常关闭、重新打开真实编辑器，用 validate_controls_scene.py 验证保存内容，随后再次运行 verify_controls 通过。实际键盘 M/T/F 开关测试通过；W 首次因 PIE 未聚焦未观察到位移，聚焦后按住约 900 ms，测得约 278 cm 位移。辅助 key-state 采样因 Key 构造 API 错误未成功，不将其计为通过。
- 新增 configure_controls.py、verify_controls.py、validate_controls_scene.py；更新 README、ue5/README、交接/长期计划、标定和关卡外部 Actor。证据摘要见 docs/evidence/controls_features_validation.json；原始日志/PNG/临时自动化脚本留在 Saved/runtime，不提交。
- 未提交或推送。下一步可提交本次源码及配套关卡供另一台电脑同步；实物尺寸/光心精确标定、红外模式、跨进程图像流与 YOLO 仍待后续任务。

### 2026-10-14：第二台电脑运行昨天成果

- 完整阅读计划、AGENTS、AI_HANDOFF、运行与迁移说明，并检查 C++ 演示及维护/验证脚本。实际功能是 UE 真值指向的运动学演示，不是 YOLO 视觉跟踪。
- `git fetch origin --prune`、`git merge --ff-only origin/main` 同步到 b0b2868，`git branch --set-upstream-to=origin/main main` 修正原本指向已删除 master 的设置；保留未跟踪 papers。
- `scripts/Start-WISEYE.ps1 -EngineRoot E:\Programs\UE_5.8 -BuildOnly` 首次编译成功（61.09 秒，原有 HUD double/float 常量警告）。570 项 Models/Content 哈希检查全部通过。
- 初次启动提示 VC++ 14.44.35211 过旧。用户明确授权后运行引擎自带 vc_redist.x64.exe /install /quiet /norestart，注册表确认 14.50.35719，退出码 3010，未重启。之后 UnrealEditor-Cmd + PythonScriptPlugin + validate_portable.py + NullRHI 退出码 0，0 error(s)、0 warning(s)。
- 首次生成着色器/纹理/网格缓存。自动验证启动脚本最初缺少 keep_python_script_alive，导致脚本返回后 UE 正常退出；修正本地 runtime 脚本并重新启动，没有改动场景或源码。
- 在真实 DX12/Intel Arc B580 编辑器 PIE 运行 verify_demo.py，40 秒集成验证通过，79 个采样，最大真值指向误差约 0.010725°；该误差不代表实物精度或视觉算法精度。报告在 ue5/WISEYE/Saved/WISEYE/verification.json；两张不同 PNG 在 20261014_163650，已目视核验。
- 修改 `.gitignore`、README、scripts/Start-WISEYE.ps1、docs/AI_HANDOFF.md、本计划；新增 docs/GIT_WORKFLOW.md、docs/evidence/second_pc_validation.json。本地引擎路径与验证启动辅助脚本保持忽略；原始运行日志/PNG 留在 Saved，不入库。
- 本次文档和启动入口变更尚未提交/推送。两台电脑开始前 pull --ff-only，结束时保存 UE 资源后检查、提交、push；同一二进制场景轮流修改。下一步仍是比例/光心标定，按用户后续任务推进；M1、M2、M5 尚未完成。

### 2026-10-14：完整工程迁移与 GitHub 同步准备

- 按用户要求保存可跨电脑构建的完整 UE 源工程与模型。补齐 World Partition 外部 Actor，避免只提交代码无法复现场景。
- 收录独立 PTZRecovered 网格、材质和贴图，用户已确认云台恢复正常；原始 Models 保留。
- 移除重复 ue5/Source 镜像，统一源码到 ue5/WISEYE/Source；维护脚本去掉本机运行时桥接路径，启动脚本接收实际引擎路径。
- 更新 README、ue5/README、AGENTS、AI_HANDOFF、迁移检查记录及历史证据。普通运行不依赖 conda，首次编译需 UE 5.8 和 VS C++ 工具链。
- 整理后独立构建 Succeeded；资产加载与上传核对结果写入 docs/PORTABILITY.md。
- 用户授权上传确认后删除 Backup-Content/Backup-Config。只清理本次备份，不删除原 Models、现有工程或实验输出。

### 2026-10-13：UE 两轴光电云台与无人机运动演示

- 用户授权直接编写代码并操作 UE；澄清 bottom 固定，bottom2 只水平转动，camera 与 ptz 一起水平及俯仰转动。
- 新增 `ue5/Source/WiseEyeDemo.h/.cpp`，部署到实际工程 `Source/test`；新增 setup/play/stop/inspect/verify Python 脚本、使用说明及 `.gitignore`。
- 调整已保存关卡：重建轴心和挂接层级，加入 `WISEYE_Demo`、`WISEYE_Overview`、`/Game/WISEYE/RT_EO`，游戏模式设为 WiseEyeGameMode。原 CAM_GroundEO 保留。
- 在修改前保存已有未保存资源，并备份 Content/Config 到 `D:\Projects\WISEYE-Studio\runtime`。
- 构建命令：`Build.bat testEditor Win64 Development -Project=D:\Projects\Scene\test\test\test.uproject -WaitMutex -NoHotReloadFromIDE`，Succeeded（HUD 浮点常量有转换警告）。
- 在 PIE 执行 `ue5/scripts/verify_demo.py`：通过 40 秒运动/轴向/限速/暂停/复位/变焦集成验证；导出和目视核验相机 PNG。验证过程中修复 World Partition 外部 Actor 可移动属性未标脏持久化的问题。
- 两张验证图像位于工程 `Saved/WISEYE/20261013_160000/EO_0000.png` 和 `EO_0001.png`，无界面叠加；全局验证报告和初始标定也在 `Saved/WISEYE`。
- 未实现：真实比例标定、飞行动力学、YOLO 闭环、TCP 图像传输、桌面 UI、打包程序。未提交或推送 GitHub。
- 下一步：模型尺寸/镜头标定；然后最小图像通道。用户可通过 `D:\Projects\WISEYE-Studio\Start-WISEYE.cmd` 打开场景，按播放运行。

### 2026-10-12：建立项目计划文档

- 建立项目目标、边界、推荐架构、通信协议草案、里程碑、MVP 顺序和 AI 持续交接规则。
- 当前仅完成规划文档；尚未检查本地代码库，也未执行代码或运行测试。
- 下一步：本地 Codex 读取本文件，先完成 M0 环境与仓库盘点，并把实际结果更新到本文档。

---

## 给本地 Codex 的启动指令

请先完整阅读 `WISEYE_ProjectPlan.md`。然后检查当前工作区和 Git 状态，执行 M0 环境与仓库盘点。不要擅自删除、覆盖、升级或迁移现有代码、模型、数据集及环境。先把确认到的实际情况、缺失项和风险写回本文档，再提出并执行一个最小、可验证的下一步任务。结束时必须更新本文档的当前状态、下一步任务、里程碑和变更记录，并按第 10 节格式汇报。未经实际验证的内容不得标记为 DONE。


## 变更记录

### 2026-10-12：确定项目品牌名称

- 项目品牌确定为 `WISEYE`，软件名称为 `WISEYE Studio`，中文名称为“智瞳——无人机光电仿真与智能感知平台”。
- 增加 WS / YZ / E 模块释义约定，并说明其为项目内部命名而非标准英文缩写。
- 文档版本升级至 `0.2`；后续改名应以现有仓库盘点为前提，避免破坏兼容性。

### 2026-10-14：桌面窗口与控制桥、今日整理

- 新增 apps/desktop_app、core、configs、requirements、Start-Desktop 启动脚本，以及 WiseEyeBridge C++ 非阻塞本机 TCP 控制桥。
- 实现连接/断开、状态轮询、暂停/继续/复位、飞行模式、跟踪/旋翼、模态/调色板/FOV 和双模态快照；断开清除状态、响应超时保持 UI 响应。
- C++ 构建与真实 UE 桌面 10 项验收、协议 4 项单元测试通过。截图/验收摘要保存到 docs/evidence。
- 用户授权整理文件代码、上传 GitHub、清理不必要备份日志；更新运行/Git/协议/交接说明，详细结果见今日工作记录。
- 下一步：持续图像通道与帧时间/性能指标，再接视觉检测。

- 上传验收：功能提交 a221349 已推送并核对 GitHub main；正式桌面启动入口通过。清理清单已核验，但删除被自动审批检查拒绝，未执行；已提供人工清理脚本，详见今日工作记录。

### 2026-10-19：第二台电脑拉取与测试跑通

- 用户要求从 GitHub 拉取最新代码并测试运行；保留 papers，pull --ff-only 至 667b8a3。
- 本机首次安装 Project AirSim 固定补丁与隔离 Python 环境、MediaMTX 1.21.2、FFmpeg 9.0.2。Setup-ProjectAirSim.ps1 修正预期原生命令失败在 Windows PowerShell 下中止、CRLF 匹配、SimLibs 首建联接时序。
- AirSim 原生库 188 步、UE 编辑器 53 步构建成功；14 项 Python 单元测试、15 项真实 UE/飞控/RTSP/桌面集成通过。FFprobe 核验两种原生尺寸和 30/25 输出帧率，已检查桌面截图。
- 验证报告及截图新增 docs/evidence/second_pc_run_20261019.json、second_pc_desktop_20261019.png；更新 AI_HANDOFF。代码与文档修正未提交推送。
- UE 初次冷启动记录一条时间上下文 handled ensure，未崩溃；保留为待定位现象，不伪称零告警。下一步仍按主计划推进硬件编码与统一时间戳；本轮不扩大功能范围。

### 2026-10-19：修复按键与尺寸/Avata 穿模

- 用户要求两端按键正常、Avata 修复，Mavic/Avata 实际尺寸和云台 80 cm。修改 WiseEyeDemo/Bridge、AirSim runner、桌面事件处理、双地图/外部 Actor、标准装配、标定及运行说明。
- 定位并修复 UE 运动学按键未转入 AirSim、现有 InputComponent 优先级未更新及上游 T/Tab 消费、Qt 子控件抢键、旧 Play 会话失效、Hover 过早完成后残留速度和 Avata 深层桨叶未隐藏。制动任务带代数保护，失焦/松键停止输入。
- 新增 calibrate_device_dimensions.py 与 device_dimensions.json；两张地图均已保存重开，Mavic 无桨机身和云台高度测量通过；Avata 18×18×8 cm，旧 Mavic 网格零可见，近景截图已检查。
- 验证：C++ 构建成功；17 项单元、15 项完整桌面联调；八方向从稳定悬停测得有符号位移/转向、鼠标按住和失焦停止通过；实体 UE M/W/空格/T 通过；重播自动重建并再次手动运动通过。修正上轮仅凭位移判断手动成功的不足。
- 保留原模型、papers、实验输出和先前本机修改。更新 AI_HANDOFF 和相关文档，未提交/推送。外形校准不代表动力学参数或传感器物理标定；Avata 自身独立旋翼动画仍未实现。下一步按用户实际试用反馈继续。

### 2026-10-19：Avata 原生桨叶动态化

- DONE：保留原始模型和材质，将两对合并桨叶拆成四个独立旋翼；生成无静态桨叶的 AvataBody，四个轴心保存在 sockets。资产生成脚本为 ue5/scripts/build_avata_rotors.py，标准导入入口可重建缺失资产。
- 接入既有 RPM/旋翼开关、型号切换和红外热特征；相邻反向、对角同向，尺寸仍为 18×18×8 cm。未改变飞行动力学；当前为统一视觉转速，尚非 AirSim 各电机 RPM。
- 实测：UE 构建成功，17 单元 + 15 桌面联调通过；8 阶段专项检查持续转动、轴心固定、关停保持与恢复，原模型 333613 三角形完整保留。截图与摘要见 docs/evidence/avata_rotors_*20261019.*，交接已更新。
- 本机未提交/推送；下一步按用户反馈完善，若需物理一致转速再接电机遥测与高速模糊。

### 2026-10-19：旋翼转速表现与激光点云

- 用户反馈转速慢和点云异常；提高默认视觉转速到 6000 RPM，并为两型号生成适配桨叶范围的半透明扫掠盘。停止恢复清晰原桨叶，未改变飞行动力学。双地图、标准装配和导入重建入口同步。
- 修复传感器坐标误含模型缩放、UI 丢弃高度并非等比拉伸、扫描忽略无人机。添加查询专用几何，保留 AirSim 物理控制与红外分类；UI 可交互三维/正视/俯视，显示距离、单位和单帧限制。
- 最终构建、17 单元、15 UI 联调通过；八方向/松键悬停/失焦停止通过；两型号高速盘停启、尺寸与热标记、Avata 查询命中、10 m 协议平面和 1 m PLY 平面米制标定通过。三视图渲染与空帧验证通过。证据 docs/evidence/rotor_lidar_fix_20261019.json 与配套截图。
- 修改/新增 WiseEyeDemo/Dynamics/Lidar/Bridge/Sensors、lidar_view.py、main_window.py、材质/地图、导入与验证脚本、协议/桌面/交接文档。本机未提交上传；旧 PLY 不自动改写，需重新采集。
- 后续可按需求提高扫描角分辨率、世界坐标累积点云和读取电机遥测；当前没有将这些标为完成。

### 2026-10-19：仿真平台 V2 设计提案

- 用户要求先讨论、审批后完善；将主系统边界收敛为仿真、设备/飞行控制、原始记录及开放接口，算法/复杂处理在扩展应用。
- 新增 docs/WISEYE_SIMULATION_PLATFORM_DESIGN_V2.md；更新旧设计提示、当前状态和交接。提供场景主导/传感器主导交互原型，检查位置参数、输入控制、组操作、接口页面、两布局和四种屏宽。
- 自由观察与物理设备移动分开；先独立 UE 运行视口，内嵌另行验证；多架先 2 后 4。RTSP 保留，优化分指标基线、最新帧 UI、硬编与去 JPEG 路径，目标数字均待验收。
- 本轮未修改运行代码或 UE 内容，未运行仿真性能压测，未上传 GitHub。下一步等待用户明确审批方案范围与优先级。

### 2026-10-19 V2 首轮实施验收

TASK-023 保持 IN_PROGRESS。20 单元、15 桌面、8 方向飞行/失焦、7 V2 真实联调、实际 UE 自由相机键鼠检查通过，testEditor 构建成功。初始位置跨重载同步真实 AirSim，无自动起飞；双画面/雷达参数已接入，预览邮箱每路≤1。8 秒样本两路完成新帧各 20.50 FPS，UE 控制 P95 57.49 ms，视频端到端延迟与 30 分钟稳定尚未验收。详见 docs/evidence/workbench_v2_20261019.json 与 docs/AI_HANDOFF.md。

当前只实现数值位置预设与独立 UE 观察窗口。拖拽/吸附、命名多预设、初始姿态、硬编、原始录制、多架、内嵌和最终免装 UE 的成品安装包仍待后续实施，不能将 TASK-023 标 DONE。

### 2026-10-19 阶段 A 续作：表面放置与命名预设

已实现 UE 鼠标选表面、当前 X/Y 贴合、草稿隔离、云台底座几何补偿、命名预设另存/读取/更新，以及取点取消/超时/断连后取消。23 单元和 8 项真实放置联调通过；实际平面几何：云台底部 -0.0168 cm、表面 0 cm、零俯仰参考高度 80.0 cm。测试初始配置与命名预设均已恢复清理，基础地图和资源未被放置操作修改。

TASK-023 继续 IN_PROGRESS。当前是点击生成草稿和重载生效，尚无拖拽操纵杆、设备姿态编辑或法线对齐；后续 B 数据链路、C 多架、D 内嵌和独立安装仍按设计推进。

本轮追加回归：15 项桌面、真实自由观察及八方向飞行/编辑焦点检查均通过。取点后重连可取消，数值编辑不会触发驾驶。正式字号最小 1080×740 已渲染检查；当前变更仅保存在本机，未推送。
# 2026-10-26进展补充

- 已实现可编辑、持久化的传感器网络接口：全局RTSP与逐设备流路径，客户端地址、网关发布、可写MediaMTX配置一致；独立UE/飞控监听固定端口限制明确。
- 51核心、11Qt通过；自定义RTSP端口/嵌套路径640×512合成信号收流通过。真实UE外部RTSP延迟及新红外渲染尚未验收。
- 冗余清理候选F5.821GiB/E107.542GiB，自动审批拒绝删除，释放0，详见CLEANUP_REPORT；用户资产和成品保留。
- 红外拟真与插件技术选型已写INFRARED_REALISM_PLAN，尚未实施UE渲染升级或采购插件。

# 2026-10-26红外试验进展

已实现第一版相机外观增强，保留原始模式A/B；支持模糊、固定对比、背景层次及随采集帧变化的噪声，按云台控制。Editor构建与真实城市图像/参数验收、51核心+13Qt通过；用户Fleet与原始材质不变。试用Start-InfraredPreview.ps1，见INFRARED_EXPERIMENT。旧Shipping未重打包；整城热材质、真实相机校准、AGC、GPU耗时与新飞行验收仍待做。
