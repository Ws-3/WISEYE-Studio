# WISEYE 独立发布技术路线与执行交接

**最新进度（2026-10-23）：** 独立Shipping内测包与F盘交付已完成，三场景起降/图像/云台/点云、city中文路径通过。先读 [RELEASE_BUILD.md](RELEASE_BUILD.md) 和AI_HANDOFF最新节，从剩余的干净Windows、长时负载、安装器/更新器继续；不要照下文原计划重新迁移或把已实现模块当成空白任务。F为源码与成品目录，用户批准E盘临时构建。

日期：2026-10-22。本文是实施任务书，所有新增模块、脚本、参数和目录均为待实现设计，不能当成已有能力。当前未完成 Game/Cook/Shipping 构建、安装器或更新器。详细体积证据见 PACKAGING_AND_UPDATES_PLAN.md。

## 1. 明确目标

交付 Windows x64 软件：用户从移动硬盘拷贝或者网络下载同一版本的安装文件，安装到目标电脑本地 SSD，双击 WISEYE 启动并离线仿真。目标电脑不安装 UE 编辑器、VS、Git、Python 或 Anaconda。首次支持 Windows 11 x64，运行库和显卡驱动条件需检测与说明。

移动硬盘仅为传输渠道，不要求程序从 F 盘运行、不要求配置随盘、不把磁盘修复作为构建前置。安装完成后拔掉传输盘仍能运行。在线更新随后实现；不为实现首包而先重写界面或 GPU 视频链路。

保留现有 Qt 工作台、独立 UE 仿真进程、AirSim 飞控和外部 RTSP 接口。唯一日常入口 WISEYE.exe 管理整个生命周期；多进程可以隐藏后台控制台，UE 渲染窗口按实际界面方案显示，不能把“打包集成”误当成已经实现窗口嵌入或 GPU 纹理共享。

## 2. 首先阅读与保护现状

先读 AGENTS.md、docs/AI_HANDOFF.md 最新节、WISEYE_ProjectPlan.md 最新节，再读本文件、PACKAGING_AND_UPDATES_PLAN.md、INSTALLATION.md、PROTOCOL.md、COLLISION_RECOVERY.md、SENSOR_LATENCY_REPORT.md。检查 git status，保留所有已有未提交修改。

- 仓库：E:\Projects\WISEYE-Studio；引擎：E:\Programs\UE_5.8，当前 5.8.4。
- UE：ue5/WISEYE/test.uproject；模块 test、Game 目标 test、Editor 目标 testEditor，不改名、不升级引擎。
- AirSim：E:\Projects\ProjectAirSim-Evaluation，固定实际提交与基础、GC 完成、粘墙三个补丁。Setup-ProjectAirSim.ps1 已处理补丁，发布必须用已修复的 SimLibs/插件。
- 当前 Qt 6.11.0、Python 3.14.6。桌面 .venv 借用 Anaconda，不能直接复制这个 venv 交付；重新锁定独立构建依赖，不静默替换开发环境。
- 用户 Fleet 以磁盘为准，当前记录为 city 1 UAV + 2 PTZ；不按历史预设覆盖。保存用户布局、航线、位置和设备尺寸。
- 保持 VIS 1920×1080、IR 640×512、OBS 960×540；无人机 R/F 升降；真实 AirSim 电机转速；PTZ 高 80cm。
- 保持最新 JPEG 直连预览和有界队列；RTSP 是对外接口，不将桌面预览退回 H264 编解码往返。
- 不删除源资产来试探减包，不上传 CitySample 原始资产/开发缓存，不自行提交推送。
- 操作现有 UE 前检查正在飞行与未保存状态，不强杀用户会话。构建过程中不要占用现有运行端口启动第二套仿真。

## 3. 实现入口及需要消除的依赖

| 现有入口 | 改造内容 |
|---|---|
| ue5/WISEYE/Source/test.Target.cs | 已有 TargetType.Game，先实际构建 Development Game |
| ue5/WISEYE/Source/test/test.Build.cs | 已对 UnrealEd 使用 bBuildEditor 条件；继续审计插件和其他代码的 Editor 依赖 |
| ue5/WISEYE/Source/test/WiseEyeFleet.cpp | Fleet 当前从 ProjectConfigDir 读；加入统一的可写配置根 |
| ue5/WISEYE/Source/test/WiseEyeScenes.cpp | 场景与 Layout 配置路径；区分只读默认值与可写用户覆盖 |
| core/config.py、core/devices.py、core/layouts.py、core/routes.py | 审计 ROOT 与读写路径，避免冻结程序后继续依赖源码树 |
| apps/desktop_app/main.py | 资源图标和日志当前使用 ROOT；进入统一路径层 |
| apps/desktop_app/main_window.py | 当前启动 PowerShell 开发脚本；接入发布模式进程管理 |
| apps/desktop_app/scene_dialog.py | 发布模式不调用编辑器准备资源，改为检测已安装场景组件 |
| scripts/Start-WISEYE.ps1、Start-ProjectAirSim.ps1 | 只保留开发用途；发布启动不依赖编辑器 Python Play 或兄弟目录 venv |
| integrations/ProjectAirSim/run_wiseye_flight.py | 独立 worker 入口，运行配置/机器人模板/依赖随包 |
| integrations/rtsp/rtsp_gateway.py、mediamtx.yml | 独立 worker 与随包视频工具、可写日志/配置 |
| apps/desktop_app/ue_preview_client.py、rtsp_client.py | 保持预览协议，工具从发布目录解析 |

现有 Start-ProjectAirSim.ps1 含按脚本名终止 runner 的开发逻辑，不能照搬为发布管理器。曾发现 Start-WISEYE.ps1 的正反斜杠进程匹配会漏认已有 UE；发布版按持有的进程句柄/PID及会话握手管理，避免按可执行文件名字广泛终止进程。

## 4. 发布目录与统一路径协议

建议首版目录部署，不做巨型 onefile 每次解压：

```text
WISEYE/
  WISEYE.exe
  current.json
  versions/<release-id>/
    Desktop/
    Workers/
    Simulation/          # 保留 UE Stage 产生的相对目录结构
    Defaults/
    release.json
  content/<content-id>/  # 后续分包；须先验证 UE 容器加载规则
  Updater/
  Prerequisites/
```

首个验证包允许城市容器保留在 UE 原始 Stage 布局内，不为目录美观提前移动 Pak/IoStore。把 content 外置、复用或分块时必须验证挂载、AssetRegistry、地图和通用资产归属。禁止假设任意目录的 .ucas 能自动被加载。

新增 core/runtime_paths.py（建议名）：install_root、resource_root、user_data_root、cache_root、log_root。默认用户数据为 %LOCALAPPDATA%\WISEYE；录制目录可选。安装目录可只读，资源路径相对安装根，不能写死 F/E/开发用户名。

建议由启动器传递 WISEYE_DATA_DIR 给 worker，并给 UE 增加明确的 -WiseEyeDataDir 参数；这些接口目前尚不存在，须两端一起实现。所有进程解析到同一规范化绝对目录。只读 Defaults 首次复制，后续升级不覆盖用户 Fleet/航线；schema 迁移先备份，原子写入，失败可回退。日志和缓存不进入版本目录。

## 5. 分阶段执行及门槛

### P0：构建基线和风险探测

产物：构建清单，包含引擎实际版本、仓库提交和未提交工作快照说明、AirSim 提交/补丁哈希、编译器、SDK、Python/Qt/native 依赖版本。

读取本机配置确定基础场景地图路径，不凭空编路径。首先尝试 test Win64 Development Game 构建，确认 AirSim/CitySampleSupport 的 Runtime、Editor、UncookedOnly 模块边界和 DLL 暂存规则。失败先修复首个根因，记录日志，不在编辑器成功基础上宣称 Game 已通过。

可作为构建起点的现有工具（启动前按本机情况核实）：

```powershell
& 'E:\Programs\UE_5.8\Engine\Build\BatchFiles\Build.bat' test Win64 Development '-Project=E:\Projects\WISEYE-Studio\ue5\WISEYE\test.uproject' -WaitMutex -NoHotReloadFromIDE
```

下一步通过 RunUAT BuildCookRun 实施 Cook/Stage/Pak/IoStore；先查当前引擎参数并在构建脚本中明确 project、target、Win64、Development、地图白名单、归档目录。输出到仓库外 E:\Projects\WISEYE-Builds，防止混入 Git。构建日志保存在该次构建目录。

### P1：最小独立端到端包

1. 实现路径层、UE 用户配置根和发布启动模式；UE Game 加载地图后自动初始化现有仿真 Actor/Bridge，不要求 PythonScriptPlugin/PIE。
2. 建立干净依赖环境。桌面先验证 pyside6-deploy standalone；若当前 Python/依赖与部署工具不兼容，记录具体失败并选兼容的独立构建环境，保留开发环境不动。飞控/视频优先独立 worker 可执行入口；私有 Python 目录可作首包备选，但须完整依赖闭包。
3. 不把冻结后的 sys.executable 当通用 Python。显式解析 worker.exe 或私有解释器，随包包括 AirSim 客户端、NNG/native DLL、模板、Qt 插件、必要 FFmpeg/MediaMTX。
4. 新增发布进程管理器（建议 apps/desktop_app/runtime_manager.py），由当前实际主窗口接入；保留开发模式。后台启动无控制台弹窗，参数使用数组，禁止拼接 shell 命令。
5. 状态机：检查配置/组件 → 启动 UE → 验证 scene_id/run_id/设备起点 → 启动飞控 → 飞控就绪 → 按需外部 RTSP → 允许控制。端口监听不等于就绪；超时报告具体阶段，失败清理本次创建的进程。
6. 退出时停止输入并执行既有安全停止流程，等待关联进程结束。使用进程句柄或合适的 Windows Job 管理只属于本次启动的进程，禁止误杀其他 UE/Python。仿真中不自动升级替换文件。

门槛：基础场景完整运行，控制/预览/配置保存可用；脱离源码工作目录、清理开发 PATH 后仍能启动。此项是本机冒烟，不替代干净系统验收。

### P2：城市 Cook 与实际减包

发布地图 /Game/WISEYE/Scenes/city/CitySample；按地图白名单和依赖 Cook。明确收集通过 LoadObject 字符串加载的无人机、桨叶、模糊/红外材质。审计十个已知缺失源引用是否影响当前依赖；不能靠忽略全部警告绕过。

World Partition、HLOD、FastGeo 道路/建筑碰撞都要进入独立包。移除 Crowd/Traffic 生成器不等于依赖资源已经不被 Cook；用实际 Cook 报告决定后续引用精简。保留源工程。

先独立城市包验证，再拆通用/基础/城市逻辑组件；不要把所有内容重写成新项目。Shipping 必须再次构建运行，不只验 Development。

产物：UE 程序/插件大小、基础资源大小、城市容器大小、完整安装大小、压缩下载大小；分别记录字节与 GiB。当前 25–60 GiB 只是预算，不能作为验收结果。排除开发 DDC、Intermediate、PDB、日志和源工程，保留必要运行着色器等数据。

### P3：安装及离线交付

采用安装器加资源数据分卷，首选验证 Inno Setup。用户可选本地 SSD 安装目录；安装依赖检测、快捷方式、版本说明与卸载行为明确。卸载默认保留用户数据或明确让用户选择。

同一签名发布清单和哈希用于移动盘拷贝、完整下载、后续在线安装。先从安装源校验并安装到目标目录；安装源可删除、移动盘可拔除。F 卷现有 Dirty 问题不阻塞 E 盘产物生成，使用该盘交付前再处理介质可靠性。

正式验收：无 UE/VS/Python/Anaconda 的 Windows，普通用户、中文/空格路径、不同盘符、安装目录只读、断网启动；必要系统运行库随安装器处理。记录实际显卡、驱动、RAM/VRAM与系统版本，不称任意办公机兼容。

### P4：在线更新（首包通过后）

清单至少含 release_id、平台、组件版本、协议/schema/UE内容基线兼容关系、URL、大小、SHA-256、发布签名。客户端仅放公钥；密钥不进入源码/安装包。对象存储/CDN 放大文件，GitHub 管代码与版本说明。

先实现组件完整替换与未变组件复用：断点下载、校验、空间检查、仿真退出后独立 Updater 激活。下载/展开/旧版回滚空间逐项计算；暂存和激活在安装目标同卷完成，跨盘复制不能当原子切换。保留一个兼容旧版本和配置备份，启动握手失败回滚。

UE .utoc/.ucas/.pak 按兼容集合发布，不能只换一个文件。界面更新无需下载未变城市，但引擎/序列化基线改变可能要求重下内容；不得承诺所有更新都是小补丁。第二阶段再做稳定 Cook 基线和资产补丁，不混淆 HTTP 文件分片与 UE 资产 Chunk。

## 6. 必须通过的验收

- 无编辑器：没有 UnrealEditor.exe，只有发布的 Game 和自带 worker；不访问开发 E 盘路径。
- 完整操作：R/F、手动/航线、起降、真实 RPM、云台遥杆/跟踪、观察视角、传感器独立参数和多设备寻址。
- 城市：道路表面取点、建筑碰撞后可脱离；连续运行至少30分钟，记录加载时间、资源占用、异常。
- 视频：原分辨率、预览源绑定、帧率及内容年龄，外部 RTSP 独立检验；不拿旧的1机1云台历史数据当新包结果。
- 用户数据：升级/重装不覆盖 Fleet、航线和布局；拷贝安装源不意外携带开发者个人配置。
- 生命周期：启动失败、端口被占、重复启动、退出、断连均有明确状态，无遗留子进程和无效控制输入。
- 更新：仅桌面更新不下载城市，断网可离线启动，中断可续传，坏包拒绝、空间不足不破坏旧版、失败可回滚。

旧 tests/verify_* 脚本中可能包含编辑器日志/PIE前提，审计后再用于独立包；修改测试适配真实接口，不删断言来通过。核心单元和 Qt 测试按现有各自环境执行。涉及实际飞行必须先核实用户当前状态和测试配置，保留原用户数据。

## 7. 建议新增交付文件与完成规则

建议新增 scripts/Build-Release.ps1、scripts/Verify-Release.ps1、packaging/（部署配置/安装器/版本清单 schema）、core/runtime_paths.py、发布进程管理器、docs/RELEASE_BUILD.md 和每次构建证据。名称可按现有仓库惯例调整，必须说明真实调用入口。

每阶段交付代码、可重复命令、实际产物位置、日志与测试结果，并更新 AI_HANDOFF/ProjectPlan。明确区分“已实现”“本机验证”“干净电脑验证”“尚未验证”。遇到可修复的构建失败持续处理，不退回只写方案；确实缺外部条件时报告失败根因和具体下一步。不承诺未测出的大小/帧率，不上传发布包或发版，除非用户另行授权。

下一位 AI 的第一件事：读取最新交接和 git 状态，建立 P0 基线，开始 Development Game 构建及基础包验证；不要先做完整在线更新 UI，也不要复制完整 UE/CitySample 源工程到 F 盘。
