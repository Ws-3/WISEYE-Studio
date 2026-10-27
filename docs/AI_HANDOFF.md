# WISEYE 当前交接（2026-10-27）

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
