# City Sample 城市场景

2026-10-28：本机日常统一双击根目录 **`Start-WISEYE-Studio.vbs`**，一次启动当前城市预览、飞控和桌面。下方保留的分步 PowerShell 命令面向开发；在仓库 PowerShell 执行，遇执行策略限制加 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File`。已启动UE时仅重开桌面用 `scripts/Start-Desktop.ps1 -Connect`。详见[当前使用指南](USER_GUIDE.md)。

## 本机接入状态（2026-10-22）

源工程：`E:\Projects\Scene\CitySample\CitySample.uproject`，UE 5.8。使用真实 `/Game/Map/Small_City_LVL`，WISEYE 副本为 `/Game/WISEYE/Scenes/city/CitySample`。原始 CitySample 工程、原沙漠场景设备配置和尺寸配置均保留。

已复制并校验 26854 个本地依赖文件，约 44.96 GB；World Partition 副本包含 12102 个城市外部 Actor。第三方模块通过本地 `CitySampleSupport` 插件接入，保留 WISEYE 的 test/testEditor 模块。地图副本安装相同标定设备，并移除五个人群/交通生成器和依赖原GameState的昼夜控制器；首轮提供静态城市环境。

**本机已完成接入，`prepared=true`，城市入口可用。** UE 5.8.4 构建成功、44项Python单元通过、5组真实UE/AirSim/桌面验收通过；保存修改后再次通过正式启动脚本重播。当前无人机落地待命。

## 地图与安装位置

City Sample 原项目直接打开后显示黑色说明页属于正常现象。在内容浏览器 `Content/Map` 打开 `Small_City_LVL` 才是城市；实际仿真请打开 WISEYE 的 `test.uproject` 及其城市副本。

完整运行时流式加载后，此处人行道实际高度约 Z=73 cm，编辑器未加载街区时只能探测到底层 Z=0 碰撞块，不能用后者安装设备。默认云台底部落在人行道上，根坐标约 `(-304.987, -1.007, 0.781) m`；无人机初始中心约 `(-292.987, -1.007, 0.980) m`，触地后由真实 AirSim 碰撞决定位置。总览相机位于街道上方 12 m。

持久化记录：`Config/WISEYE/CitySample/placement.json`、`Scenes/city.json`、`Fleets/city.json`（均相对于 `ue5/WISEYE`）。城市设备配置从接入时实际原配置克隆，当前一机一云台；不会把旧交接记录中的设备数量写回原场景。云台保持总高 80 cm，无人机沿用现有真实尺寸与动力学。

## 两台电脑通过 Git 同步

Git 同步 WISEYE 的代码、接入配置、自有模型与原始/测试场的 World Partition 装配。完整 City Sample 原始资源、插件源码和生成的城市地图副本（包括整套城市外部 Actor）在 `.gitignore` 中，不随公开源码上传。另一台电脑先通过自己的 Epic/Fab Library 获取同版本 City Sample，再通过以下脚本重建本地城市副本；运行版本则使用包含城市的独立发布包。

首次接入一个没有城市副本的工作目录，先保存并关闭 UE，在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Setup-CitySample.ps1 -SourceProject "E:\Projects\Scene\CitySample\CitySample.uproject" -EngineRoot "E:\Programs\UE_5.8"
```

脚本依次处理本地插件和编译、资源审计与逐文件 SHA256 校验、UE 官方 World Partition 地图复制、标准装配。它拒绝覆盖已有目标地图；失败后先检查日志，按 `-Stage Dependencies|Assets|Duplicate|Assemble` 恢复，不要对已有装配重复运行 Assemble。

若该电脑已经保留完整的本地城市副本与外部 Actor，只补本地依赖与资源：

```powershell
.\scripts\Setup-CitySample.ps1 -SourceProject "E:\Projects\Scene\CitySample\CitySample.uproject" -EngineRoot "E:\Programs\UE_5.8" -Stage Dependencies
.\scripts\Setup-CitySample.ps1 -SourceProject "E:\Projects\Scene\CitySample\CitySample.uproject" -EngineRoot "E:\Programs\UE_5.8" -Stage Assets
```

资源保持原 `/Game/...` 包路径，不能随意挪进 WISEYE 子目录。只复制 `.umap` 不会带上 World Partition 外部 Actor。审计包含本地插件的回指资源，以及 GameplayTags 配置直接引用的两个数据表。原资源中十个旧车辆/破损玻璃引用本身缺文件，明确记录在本地 `logs/city_asset_audit.json`，不会伪造替代资源。

## 运行与限制

本机日常双击 `Start-WISEYE-Studio.vbs` 使用当前E盘城市预览。下方为常规源码工程的开发分步启动命令，在仓库 PowerShell 执行：

```powershell
.\scripts\Start-ProjectAirSim.ps1 -Scene city -SkipBuild
```

等待 UE 播放、飞控准备完成，再在 PowerShell 中运行 `scripts/Start-Desktop.ps1` 并连接。无人机地面待命，点击起飞开始；首次缓存阶段请等网格、纹理处理和画面稳定后再操作。已运行其他地图时，通过桌面“场景编排”选择城市并加载，避免同时启动第二个 WISEYE 编辑器。

当前支持现有传感器、按设备寻址接口和手动/航线飞行；城市不增加避障能力，航线需要人工检查建筑与树木。红外支持原始/增强外观，不代表真实城市物理热辐射。Small City的独立包交付见[RELEASE_BUILD.md](RELEASE_BUILD.md)；Big City、自动人群/车流、多机性能和长时间稳定性另行验收。本机 32 GB 内存的首次缓存耗时明显，地图出现不代表缓存完成。

## 接入修复与证据

- 本地兼容模块补全 AIModule、ChaosVehicles、UMG、MovieScene 依赖；加入虚拟纹理/材质层、PhysicalSurfaces、GameplayTags、WorldAudio Mass 和 FastGeo 所需异步碰撞初始化配置。
- 飞控先等待 UE 确认 run/scene/每架初始坐标；连接超时不再等同于 UE 退出，避免城市加载堵塞监听队列时误重建。创建 AirSim 场景后恢复观察视角需要收到确认。
- 可见光和观察图像按 2.2 显示 Gamma 输出；观察 Capture 保留渲染历史，修复城市预览过暗和曝光重置。红外热强度映射不改。
- 原始装配完整回归通过，本地 `logs/city_rig_validation.json`；迁移文件校验 `logs/city_migration_files.json`；完整加载人行道探测 `logs/city_runtime_ground.json`。
- 历史冷启动阶段出现过 Renderer 访问冲突，原因尚不能仅凭堆栈判定；不能据此声称长时稳定。初次地图复制日志中的枚举缺失已补配置，之后的地图检查通过；最终运行结果以最新验收记录为准。

最新验收：`docs/evidence/city_runtime_20261022.json`、`city_reload_20261022.json`、`city_render_configuration_20261022.json`；截图 `city_workbench_20261022.png`。当前引擎是5.8.4（本轮未执行升级），完整399项重编通过。12秒样本仿真推进357 Tick；这是短测，不代表长时稳定或传感器独立30FPS。AirSim未使用的旧CVar和缺SunSky提示仍保留。

新电脑若使用All阶段新生成地图，需本机运行验收并确认道路/起点后再将 `Scenes/city.json` 的 prepared 设为 true；已有完整本地城市副本则仅运行Dependencies和Assets，保留其地图与装配。当前用户city设备清单为1机2云台，以Fleets/city.json为准；前文接入时数量是历史记录。
