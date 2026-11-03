# 大城市接入评估与旧场景清理（2026-10-31）

后续进展：用户随后授权尝试接入，现已完成大城市初始街区的1机1云台飞行与切回小城市验收，约30FPS；见[大城市接入结果](BIG_CITY_INTEGRATION.md)。下文是接入前评估记录，其中“尚未接入/未实测”不再代表当前状态；共享资源与旧场景删除限制仍适用。
结论：可以做受控接入试验，目前不适合承诺全城、多机、多传感器流畅。小城市继续作为默认场景。本轮没有导入、加载或实测大城市，也没有重打包。

## 本机与资源核查

- CPU：i5-14600KF；GPU：Intel Arc B580（此前设备诊断约12GB专用显存）；系统物理内存本轮查询31.84GiB。
- 原始下载工程 `E:\Projects\Scene\CitySample` 已有 `Content/Map/Big_City_LVL.umap`。其外部Actor目录本轮枚举101981个文件，9329717379字节（约8.69GiB）。这只是外部Actor文件，不是完整场景大小、内存需求或打包增量，也未据此认定全部依赖完整。
- 衍生工程 `E:\Projects\WISEYE-IR-Work` 的 Map、原始Map外部Actor和大量共享目录是指向下载工程的目录联接。因此其资源注册表能看到Big City；这不表示已经接入WISEYE。正式源码F当前只有Small City的WISEYE场景配置和设备装配。
- Epic对原始City Sample推荐64GB内存、至少8GB显存和SSD；Big City约4×4km。当前32GB低于推荐内存。GPU显存容量不能单独证明运行性能，也不能把其他品牌推荐型号等同为B580性能。
- 既有小城市训练实测约4–5组同刻VIS/IR+GT每秒，详见GT_RATE_AND_UNIFIED_PREVIEW。打包或换大地图不会自动改善采集吞吐；本轮没有新的大城市FPS或峰值内存数据。
- 本轮F盘枚举 `ue5/WISEYE/Content/Building/CH/C/Kit_Bldg_CHC_L1_A/Mesh` 两次返回“文件或目录损坏且无法读取”；E衍生工程相应联接目标可枚举。未修复磁盘、未删除或覆盖该资源。建议先备份源码并检查移动盘文件系统/连接健康，再考虑大批量复制、Cook；不能把此错误归因于GPU满载。

## 不用大城市时会不会拖累小城市

| 层面 | 实际含义 |
| --- | --- |
| 磁盘安装 | 两张图及其依赖会占空间；共享模型/贴图尽量复用，不应重复迁移一整份。磁盘占用不等于运行内存。 |
| 小城市运行 | 正常独立OpenLevel后不同时运行大城市世界。小城市加载自身引用的资源；不能保证任意公共蓝图、插件、软/硬引用均零额外开销。编辑器资产注册表、缩略图、缓存也有少量开销。 |
| 大城市运行 | World Partition启用流送后按流送源距离载入单元；非空间加载Actor、相互引用的Actor、远景HLOD和共享资源仍有成本。不是“镜头没看见就完全不加载”。 |
| 切换 | 世界卸载、垃圾回收和GPU资源释放并非瞬时；切换期间可能有峰值。当前项目切场景重建run，旧任务应失效。不要同时保留两个UE实例。 |
| 发布包 | 只有显式Cook并随包发布的大城市才可供运行版选择。当前Build-Release仅City，未纳入Big City。两图一起Cook的体积须以最终Cook依赖及压缩结果测量。旧PAK/UCAS无法靠删除源码中的umap就缩小。 |

## 推荐实施顺序与验收

1. 小城市保持 `city` 与默认入口；未来大城市用独立ID，例如 `city_large`，初始prepared=false。保留原始下载工程，通过UE正确复制World Partition地图和外部Actor，不用文件管理器只拷贝umap。
2. 先做局部试验区，关闭人群、交通和原始游戏控制器，安装当前标准云台/无人机、独立VIS/IR、观察相机、热分类和环境控制。保留原始下载资源不修改。
3. 检查启用Runtime Streaming及HLOD。按云台、无人机、自由观察视角配置必要的流送源；需兼顾远距相机视线、高空远景和无人机附近碰撞。不要为保证传感器看到远目标而无条件常驻全城，也不要让目标进入未加载建筑区域。
4. 先1机1云台、仅VIS、经济画质/30FPS上限；再开IR，再开GT采集与点云，最后逐步增加设备。当前采集系统已有吞吐限制，分别记录UE帧时、UI预览/采集率，不能只看UE FPS。
5. 做与小城市相同路线/画质/分辨率的对照：首次与缓存启动耗时，RAM/VRAM峰值和预算，平均/P95/P99帧时、最长停顿，移动跨分区与高空远眺、双相机远距遮挡、碰撞、反复切回小城市。单轮至少10分钟，并测一轮多次切换。
6. 建议项目验收门槛（不是已测结果）：30FPS目标对应约33.3ms帧预算；持续内存/显存超过可用预算85–90%或出现持续分页、秒级卡顿时停止扩大加载范围。先缩小流送半径/关高成本功能；若仍内存不足，再评估64GB内存。升级内存不能解决全部GPU/采集瓶颈。
7. 完成实际验证后才prepared=true并加入启动/飞控配置与Cook/组包清单。现有飞控还保留旧ID的协议兼容校验，不能仅新添一个下拉项就认为支持新地图。

## 本轮清理的真实状态

已移除F主源码、E衍生工程、E的preview-data中 `original`（原始沙漠）和 `test_range`（通用测试场）的场景JSON及对应自带旧Fleet/Layout；移除旧AirSim场景JSONC。启动入口和组包选项改为小城市，UI示例改为城市楼顶。通用场景导入/地理基准/设备代码和单元测试框架保留。

UE无图形命令行只读资产注册表核查：312个旧场景包，外部引用为空；小城市和原始大城市均可被注册表识别。详见 `evidence/city-scene-cleanup-20261031/reference-audit-before.json`。这是引用图核查，不是运行或渲染验收。

**二进制地图和Actor物理删除未完成：批量递归删除与随后逐项umap删除均被自动审批拒绝，工具只返回“blocked by policy”，没有更具体原因。未绕过限制。** 源码配置删除成功，所以这两个场景不再由系统列出，但以下独立资源仍占磁盘；每份约32.78MiB，绝非城市资源的几十/几百GB。

关闭UE后，可在资源管理器手动删除下面四个准确位置；分别在两个工程根目录下处理：

- 工程根：`F:\WISEYE-Studio\ue5\WISEYE`、`E:\Projects\WISEYE-IR-Work`。
- `Content\WISEYE-test.umap`
- `Content\WISEYE\Scenes\test_range`（仅此子目录）
- `Content\__ExternalActors__\WISEYE-test`（仅此子目录）
- `Content\__ExternalObjects__\WISEYE-test`（仅此子目录）

不要删除整个Content、WISEYE、__ExternalActors__、Map、Building、Environment或模型/传感器共享目录；不要删除 `E:\Projects\Scene\CitySample`。本轮不改旧发行包/日志中的历史场景记录，也不删除使用虚构ID的隔离测试。

验证：102项核心与65项Qt回归通过；未启动图形预览、未运行大城市、未重编译UE或更新旧发行包。日常仍由根VBS只启动GUI，用户点击“启动仿真”才开UE。

## 官方依据

- [City Sample：推荐配置、地图规模与资源共用](https://dev.epicgames.com/documentation/unreal-engine/city-sample-project-unreal-engine-demonstration)
- [World Partition：分区、流送源与加载规则](https://dev.epicgames.com/documentation/unreal-engine/world-partition-in-unreal-engine)
