# F盘完整归档与跨电脑运行评估

2026-11-02实机只读核查。本轮未迁移、删除目录或执行磁盘修复，未重新打包。

## 结论

可以把WISEYE专属代码、地图、城市资产、插件、当前配置、开发用引擎及运行版全部收进 `F:\WISEYE-Studio`，消除当前对E盘工程文件的依赖。**当前目录还不能直接拔走运行**。完整源码与独立运行版应同时保留；换电脑运行用打包版，继续编译开发另需目标电脑具备VS C++/Windows SDK等工具链。Windows、显卡驱动、系统运行库以及系统自身缓存不可能随项目文件夹完全替代。

## 当前依赖与体积

下表是排除目录联接后的文件长度之和，非精确分配空间、最终Cook包或去重后的迁移增量。扫描无读取错误；未全盘扫描已有F资产，不能据此认定F历史损坏已修复。

| 当前E盘目录 | 本次统计 | 处理建议 |
|---|---:|---|
| Projects/WISEYE-IR-Work | 37.33 GiB，128239文件 | 必需内容需归位：独有大城市地图/外部Actor、当前preview-data用户配置、工程差异；编译/测试缓存无需全搬。 |
| Projects/Scene/CitySample | 104.70 GiB，149720文件 | 当前资产联接实际目标；迁入实体资产并校验依赖，不能只复制umap或保留指向E的联接。与F已有资产去重。 |
| Projects/Scene/VaultCache | 104.26 GiB，149288文件 | 下载库缓存，不是当前运行资产目标；不需要为了便携运行搬入。 |
| Projects/ProjectAirSim-Evaluation | 6.17 GiB，22272文件 | 当前日常运行不依赖，插件已在F；固定提交与完整本地补丁已有归档。若需完整上游离线开发，可归档入builds/dependencies，不搬旧venv/缓存。 |
| Programs/UE_5.8 | 30.58 GiB，253688文件 | 开发模式需可定位到同版本引擎；可收进项目Tools。打包版运行不需安装完整UE编辑器。 |
| Environments/anaconda3 | 5.34 GiB，110973文件 | 当前F下venv确实依赖这里的基础Python；建议换成项目内独立Python/可复建开发环境与冻结运行程序，不整搬Anaconda作为可移植方案。 |

上述构建工程+原始城市+引擎约172.61 GiB，含缓存且未去重，不是必然新增空间；若机械搬全部E相关目录，会把大量可省略缓存一起搬入。F当前NTFS总容量约931.51 GiB、可用约554.94 GiB，容量足够合理整合，仍须给Cook/Staged/打包/缓存预留空间。

## 阻止当前直接带走的具体问题

1. `RuntimeManager`默认工程和UE编辑器仍指向E；Start-Desktop默认数据是E的preview-data；预览/构建/城市准备脚本和engine-root.local.txt也含E绝对路径。
2. E构建工程中的城市Content/插件资源仍联接到原始CitySample；正常preview-data的Content又指向构建工程。复制联接本身不会带走目标资产。
3. `builds/python-env/pyvenv.cfg`的home和运行时`sys.base_prefix`均为 `E:\Environments\anaconda3`。文件夹在F不表示解释器自包含。Python官方明确venv一般不可直接搬移，应在目标位置重建：[venv说明](https://docs.python.org/3.14/library/venv.html)。还须审计.pth、editable依赖、console-script绝对路径及DLL搜索。
4. FFmpeg等工具需明确放进项目Tools并从启动器定位，不能依赖另一台电脑的PATH。现有发行组装脚本已有复制FFmpeg/MediaMTX流程，但源码预览链尚需统一。
5. 移动硬盘在其他电脑可能变成G/H盘；所有启动/资源/Data/工具路径应由启动器目录解析，不能把E硬编码机械替换成F硬编码。UE内部联接需要重建/校验；不支持重建时优先实体目录。不能同时保留两份相互不一致的UE工程源码。
6. 当前releases目录未发现可直接复用的发行子目录；不能假设已有旧运行包等同于当前源码成果。现有assemble脚本仍只声明city，小城市/大城市的最终发行范围和真实Cook结果需要独立验收。

## 建议最终目录（目标，尚未迁移）

```text
WISEYE-Studio/
  apps/ core/ training_client/ integrations/ ...  # 现有代码，仍由Git管理
  ue5/WISEYE/                                    # 唯一完整UE工程与自有地图
  Assets/CitySample/                             # 必要实体城市资源，去重后管理
  Tools/UE_5.8/                                  # 完整开发选配；运行包不依赖它
  Tools/Python/                                  # 独立基础Python/开发环境引导
  Tools/FFmpeg/                                  # 其他外部工具
  UserData/                                     # 现有preview-data配置/Fleet/航线/基准
  builds/                                       # 可重建缓存、上游依赖/构建输出
  releases/current/                             # 自包含桌面+飞控+UE Cook程序
```

这不会把整个城市、引擎、Python环境和缓存都提交GitHub。代码、配置模板、依赖清单和迁移脚本入Git；大型授权资产、工具、用户数据、缓存与运行包分别归档/发布。配置迁移以E正常preview-data为准，不用F默认配置覆盖现有放置和接口设置。

## 必须先处理的F盘状态

本次 `Get-Volume F` 显示HealthStatus=Warning；`fsutil dirty query F:` 返回 **Volume - F: is Dirty**。对应USB磁盘设备报告Healthy/Online，这两者是设备层和文件系统层不同信息，不能据此诊断硬件损坏，也不能认定文件系统正常。历史还有USB重置/I/O重试及F城市模型目录读取异常。

Microsoft说明Dirty可能表示未提交变更、异常断电或文件系统损坏：[fsutil dirty](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/fsutil-dirty)。迁入上百GiB和删除源副本前，应先备份不可重建代码/配置，检查并处理文件系统问题，复核之前出错目录。磁盘修复应单独安排，不能边运行UE边强制卸载修复。本轮只查询，没有运行修复命令。

## 建议实施顺序和完成标准

1. 备份现有代码/Git未提交内容、preview-data和独有地图；处理F文件系统状态，确认连接稳定。
2. 输出依赖/联接/哈希清单，合并E独有工程内容和当前用户数据；校验F已有资产，去重迁入必要城市实体资源，保留原E副本。
3. 引擎和基础Python归入项目目录；开发环境重建，启动器改相对解析，自动检查外部工具、盘符变化和联接目标。无需复制VS安装目录，目标开发电脑按需安装VS/SDK。
4. 构建当前独立运行包，放releases/current；打包Python桌面和飞控依赖、Cook后的UE、流工具和前置安装程序。用户机器仍需满足显卡/驱动/Windows及运行库要求：[Epic硬件与前置要求](https://dev.epicgames.com/documentation/en-us/unreal-engine/hardware-and-software-specifications-for-unreal-engine)。
5. 临时隔离原E工程/原资产/基础Python引用，验证全链无回读；测试启动、连接、双光谱/事件、雨雾、导航灯、控制、起降和安全退出。再以不同盘符或第二台Windows电脑验收运行包。Shader/驱动缓存可能在新主机重新生成，不能承诺零首次加载准备。
6. 证明不依赖E后，再清理旧WISEYE工程、CitySample副本和无用缓存。Anaconda、UE、VS可能被其他项目使用，解除WISEYE依赖不等于可以卸载它们。

对于此USB盘，不建议把高频UE完整编译/Cook负载作为默认便携使用路径；日常跨电脑运行优先Cook包。如果坚持开发也全部放F，技术上可做，但文件系统修复、USB稳定性、读写性能、断电/热插拔和独立备份是实际验收条件。运行中的仿真/采集/写入停止并安全弹出后再拔盘。
