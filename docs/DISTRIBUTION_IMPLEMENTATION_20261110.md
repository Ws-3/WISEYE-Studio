# 插件接入包、完整运行包与目录整合

日期：2026-11-10。源码唯一入口 E:/Projects/WISEYE，UE 工程唯一入口 ue5/WISEYE/test.uproject。本轮源码插件与完整 Shipping 运行目录均已完成，传输 ZIP 的哈希见各 ZIP 旁的校验文件。

## 已完成

- 旧预览的 38 个 C++ 源文件与主源码初始完全一致。收回 114762 个自有/衍生资源文件，包含大小城市地图和 World Partition 外部 Actor，逐文件检查目标存在及大小；旧 city 地图差异另存 builds/consolidation。设备尺寸采用主源码，保留较新的固定翼定义。
- 从 Evaluation 收回 ProjectAirSim/Drone 的 201 个 Content 文件并逐项 SHA256 验证。城市公共 Content 与 5 个城市插件 Content 链接回 Scene/CitySample，保留原始城市资产，不把联接当实体拷贝。
- 日常预览设置改为仓库相对路径 ue5/WISEYE/test.uproject。运行管理器、预览脚本和场景查找支持仓库相对工程路径；自定义宿主可通过环境变量明确指定。
- E:/Projects/WISEYE-IR-Work 已隔离至 builds/legacy-preview-20261110；Evaluation 已隔离至 builds/legacy-evaluation-20261110。它们不是开发副本。旧 Evaluation 与 builds/dependencies/ProjectAirSimSource 的 Git HEAD 和完整本地差异相同，补丁哈希一致；原始目录名不再存在。隔离档案保留原验收/用户配置等资料，不在本轮声称已物理清空其占用。
- 城市人车原生适配按是否安装 Traffic 编译。无该城市适配时返回不可用能力，不强迫核心传感器依赖 City Sample 的 MassTraffic。
- 源码插件导出将单一 test 模块转换为插件模块入口，保留 /Script/test 类路径；安装器处理 /Game 兼容资源，预检冲突/哈希/路径并保留宿主配置。插件不是第二份可编辑源码。
- 飞控桥接接受合法自定义场景 ID，使用通用动力学模板和 UE 确认的初始位姿。新增 Start-CustomEnvironment.ps1 为宿主建立隔离用户数据，打开桌面但不自动启动 UE。
- 新增统一 Build-Distribution.ps1，Plugin 导出接入包，Full 串行执行 Game/Cook/Desktop/Assemble，可选 IncludeBigCity；支持显式 IterativeCook，但不将不完整 Cook 当交付。

## 已执行验证

- 主项目 Editor 构建通过；首次 415 个动作，412.59 秒。
- 独立 WISEYEHost 工程不包含 City Sample / Traffic，安装源码插件并编译通过，73 动作，126.36 秒。独立基础验证地图仅用于验收，不冒充用户城市场景。
- 自定义宿主完成设备装配、原生与 Python 飞控同 run 连接、1920×1080 / 640×512 双光取图、实际起飞/手动爬升/降落、所属进程退出。报告 builds/plugin-validation/live-flight/report.json。
- 主项目小城实际起飞、昼夜/航拍/云台 8 图、降落退出通过；项目成像材质编译/运行错误为 0。报告 builds/imaging-realism/consolidation-city/report.json。
- 主项目大城在两个旧外部路径被隔离后完成取图、起飞、手动爬升约 0.77m、降落及退出。报告 builds/consolidation/big-city-live/report.json。
- 39 项安装/场景/启动/发布路径/固定翼/传感器格式回归通过。PowerShell 新脚本解析通过。检查记录 builds/consolidation/regression-final.log。
- 独立宿主 Shipping 编译通过，运行依赖清单包含宿主配置与 JSBSim XML；未对自定义宿主执行完整 Cook 与打包后实跑。
- 完整运行包大小城市分别通过冻结飞控工作进程、原生双光及观察画面、云台转动、非空点云、起飞/手动爬升/降落停桨和退出检查。使用中文及空格用户目录、仅系统 PATH；飞行验证使用源码 Qt 测试界面，冻结后的两个桌面 EXE 另行通过界面启动和诊断检查，未默认拉起 UE。
- 完整目录 1,666 个文件，其中 checksums.json 校验 1,665 个文件全部通过。验收报告摘要见 docs/evidence/distribution-20261110。

## 构建结果与边界

最终 Shipping Game/Cook/Desktop/Assemble 成功，Cook 31,925 个包，UAT ExitCode=0，日志 builds/consolidation/full-distribution-final.log。首次 Cook 与大城验收并发导致内存压力，主动停止改为串行；第二轮发现遗漏的城市插件 Content，补齐后停止并启动最终新 Cook。前两轮日志保留为被主动中止，不作为成功记录。

城市完整包明确采用已测试的 DX12/SM6，移除未验收 DX11/SM5 的额外 Cook 目标；不限制源码插件宿主自行配置渲染平台。未在其他 GPU/干净 Windows 验收，不把本机通过当成普遍兼容。

完整 Cook 中第三方 M_Crowd_Head_v2 的 Nanite BasePass 计算着色器超过 SRV 上限（65/64），存在默认材质回退，可能影响部分人物头部外观；本轮没有修改原始城市资产解决它。仍有上游未使用 CVar、无 SunSky，以及既有城市 Mass CustomData ensure 等诊断；独立基础地图无 SunSky 不影响已测飞控/双光，但不意味着完整真实天气支持。在线更新、公开上传、资产再分发授权确认不在本次已完成声明中。尚未完成干净 Windows、其他 GPU 和自定义宿主完整打包的验收。

## 产物与使用

源码插件目录为 builds/distributions/WISEYE-Plugin-20261110，ZIP 与 SHA256 位于同层。源码包不含 City Sample；SDK 不内置桌面 Python 环境，桌面端使用完整源码仓库或另行准备的客户端。详细安装见 [PLUGIN_DISTRIBUTION.md](PLUGIN_DISTRIBUTION.md)。

完整目录：releases/20261110-164135-City-Shipping，约 27.34 GiB。传输包：builds/distributions/WISEYE-Full-20261110.zip。完整解压后运行 WISEYE/WISEYE.exe；训练端为 WISEYE/Training/WISEYE-Training.exe。保留整个目录结构，不单独移动 EXE。普通用户不需要 UE 编辑器、VS 或 Python；需要支持 DX12/SM6 的显卡驱动及对应 VC++ 运行库。大小城市运行资源已内置，运行此包不依赖 E:/Projects/Scene 或源码目录。大城市仍为试验场景，短时起降通过不等于全城稳定性能承诺。
