# 独立发布构建与运行（2026-10-27）

## 最新成品：仅自带城市场景

版本 **20261027-171140-City-Shipping**，Windows x64独立运行内测包。按用户要求仅自带真实Small City；原始沙漠和测试场保留在源码中，不进入本次Cook关卡和发布场景列表。旧数据目录中保存的其他场景配置会保留，发布界面只显示当前包包含的city。

- F盘交付：`F:\WISEYE-Studio\releases\WISEYE-20261027-City-Windows-x64.zip`。
- 内置盘已验收目录：`E:\Projects\WISEYE-BuildWorkspace\releases\20261027-171140-City-Shipping`。
- 展开目录：18,084,918,983字节，1441文件，约16.843GiB。
- ZIP64：18,085,274,917字节，约16.843GiB；IoStore资源已压缩，外层ZIP使用Store。
- ZIP SHA-256：`7450d6daa7bdf5fa1134f0af3f12ddd8f211f2c099ac5082df66e8cf701f36ba`。
- 已完成全部发布文件SHA校验与ZIP完整CRC校验。F盘复制后再完整读取并计算SHA；交付确认文件为同目录`WISEYE-20261027-City-Windows-x64.zip.delivery-verified.json`，源码证据在`evidence/standalone-release-20261027/delivery-verified.json`。

只保留城市主要减少地图入口及少量独有资源，城市本身仍占绝大部分容量；本版没有降低城市纹理/几何质量来换体积。旧20261023包保留回滚；20261026桌面更新ZIP不能替代本次完整包。

## 普通用户运行与升级

1. 完整解压到目标电脑内置SSD，例如`D:\Apps\WISEYE`，不要在ZIP内运行或单独移动EXE。首次同时保存下载ZIP和展开目录建议预留40GiB以上，录像另计。
2. 双击解压目录的`WISEYE\WISEYE.exe`，点击右上角「启动仿真」。等待城市和飞控就绪，再点击起飞。退出前先降落全部无人机。
3. 不需要安装UE编辑器、VS、Git、Python或Anaconda。若首次提示缺VC++运行库，运行随包`WISEYE\Simulation\Engine\Extras\Redist\en-us\vc_redist.x64.exe`安装一次；显卡驱动仍需在目标电脑正常安装。
4. 设备、航线、接口参数、日志默认在`%LOCALAPPDATA%\WISEYE`。人工升级时先降落并关闭旧程序，将新ZIP解压到新文件夹运行；保留用户数据目录，旧程序目录可作为回滚版本。当前没有自动在线更新器。
5. F盘只是传输介质。将完整ZIP复制到另一台电脑，或下载同一完整ZIP，再完整解压即可；安装后不依赖原移动盘。用户操作见[USER_GUIDE.md](USER_GUIDE.md)。

包含当前V3多设备工作台、原尺寸低延迟预览、可编辑RTSP地址/端口/逐云台路径、增强红外A/B与模糊/对比/噪声、运行主机显卡/显存/CPU/内存/FPS和时间/雾/基础雨效。红外仍为外观近似，天气不是物理温度/降水动力学模型。

## 最终城市包实际验收

54项核心测试、15项Qt回归通过。最终City包实测：场景与冻结飞控run_id一致；可见光1920×1080、红外640×512、观察960×540；云台实际角速度控制；576点非空LIDAR；真实起飞、旋翼RPM、稳定悬停后手动上升约0.962m、降落及四电机归零、Tick持续推进。测试采用隔离的中文空格用户目录，没有覆盖用户设备位置。

增强红外模式/极性/噪声与4项非法请求验证通过；硬件显存使用/预算、昼夜/雾/雨及3项非法请求验证通过并恢复。冻结RTSP worker按自定义19554端口、`acceptance/thermal`路径发布，随包FFmpeg实际解码640×512。冻结桌面清空开发PATH启动和中文GUI通过；模拟旧三场景配置后仅显示city、旧配置文件仍保留。运行后安装目录无新增文件，用户city Fleet SHA不变。

本轮修复：Shipping关闭STATS导致RHI显存快照缺失，改为缺失时按实际D3D12设备Adapter LUID查询DXGI进程显存；雨效Blueprint类改为UPROPERTY强引用，避免AirSim GC后失效。完整证据见`evidence/standalone-release-20261027`的city-report、frozen-report、build-verification、infrared/environment图像与报告。

尚未完成：干净Windows机器验收、30分钟/4+4负载、外部RTSP端到端延迟、正式安装器和签名在线更新器。当前是独立运行内测版，不能视为上述项目已验收；打包也不等于GPU纹理共享或物理红外完成。

## 本轮构建与GitHub源码

主源码`F:\WISEYE-Studio`；用户授权的内置盘临时构建`E:\Projects\WISEYE-BuildWorkspace`；旧E工程未改。UE5.8.4、Game Shipping、Editor Development与冻结桌面均真实构建，City执行完整Cook，不是旧包只替换Python。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Build-Release.ps1 -Stage Game -Configuration Shipping -Content City
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Build-Release.ps1 -Stage Desktop -Configuration Shipping -Content City
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Build-Release.ps1 -Stage Cook -Configuration Shipping -Content City
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Build-Release.ps1 -Stage Assemble -Configuration Shipping -Content City
```

Cook阶段先增量编译Editor，确保反射类与Game一致。验收可用桌面构建环境运行`python -m tests.verify_release_live --release <展开目录> --scene city --allow-flight --unicode-paths --check-features`，实际会起飞，需先退出已有仿真。

[GitHub仓库](https://github.com/Ws-3/WISEYE-Studio)提供代码、补丁、自有模型、配置和文档；功能/修复提交3a3d99b、e3045af，城市专用构建提交0be8144，后续文档以main为准。完整城市第三方源资产/生成副本、构建环境、运行ZIP、自动TLS私钥和本地论文不进入Git。新机器源码开发仍需按INSTALLATION和CITY_SAMPLE_SETUP准备依赖；GitHub源码ZIP不是独立运行ZIP。人工上传/下载见[GIT_WORKFLOW.md](GIT_WORKFLOW.md)。

## 以下为2026-10-23历史发布记录，当前交付以上文为准

## 当前成品

已生成 Windows x64 **Shipping 独立运行内测包**，版本 20261023-001704-All-Shipping，含原始场景、测试场、真实 Small City。F盘交付目标：`F:\WISEYE-Studio\releases\WISEYE-20261023-Windows-x64.zip`；是否传输校验成功以旁边的 delivery-verified.json 为准。

- 完整运行目录：18,107,757,190字节，1438文件（包含 checksums.json），约16.864GiB。
- ZIP64传输包：18,108,112,700字节，约16.864GiB。资源容器已压缩，ZIP采用Store避免重复压缩，并保留完整目录结构。
- ZIP SHA-256：`5a74e3d33b7bef3102ca8219d050b85f58c46c25eaf4ef1bacb845a82e15a20f`。
- 压缩前已校验全部发布文件SHA-256；ZIP已完整CRC校验。复制回F盘后另外复核SHA-256，不把传输中的 .incoming 当作成品。

## 用户如何运行

1. 将上述ZIP完整解压到目标电脑内置SSD，例如 `D:\WISEYE`；不要在ZIP内直接运行，也不要只拷贝EXE。
2. 双击解压目录 `WISEYE\WISEYE.exe`，选择场景，点击右上角“启动仿真”，等待场景和飞控就绪再起飞。
3. 首次机器若缺VC++运行库，运行随包 `WISEYE\Simulation\Engine\Extras\Redist\en-us\vc_redist.x64.exe` 安装一次。显卡与驱动需满足该场景图形要求。
4. 不需要安装UE编辑器、VS、Git、Python、Anaconda。配置/航线/日志默认在 `%LOCALAPPDATA%\WISEYE`，升级不应覆盖用户数据。退出前先降落全部无人机。
5. 移动盘用于传输。解压安装后可移除安装源，已安装场景可离线运行。网络下载同一ZIP也适用。

首版建议本地SSD预留40GiB以上以容纳下载ZIP、展开目录和少量缓存，录像另计；直接从移动盘解压时空间分布不同。后续更新空间需按实际下载、展开、旧版回滚计算。该建议不代表任何容量下都能无上限录像。

## 已实际验证与限制

最终Shipping在 original/test_range/city 三场景均通过：正确场景与run_id、冻结飞控worker就绪、VIS1920×1080/IR640×512/OBS960×540预览、实际云台角速度控制、非空点云、真实起飞/RPM、稳定悬停后手动升高、真实降落及四电机归零、仿真tick持续推进。手动升高实测约0.795/0.796/0.923m。city验证了1机2云台清单；这不等于4+4性能验收。

最终城市测试使用中文空格安装路径与用户数据路径，并核对运行后安装目录没有新增日志/密钥等文件。冻结桌面在清空开发PATH后能启动和显示完整中文界面。47项核心/路径/进程测试、9项Qt回归通过。证据见 evidence/standalone_release_20261023.json、standalone_city_20261023.png、standalone_desktop_20261023.png。

尚未在没有开发环境的干净Windows机器验收，未完成30分钟稳定/4+4负载/完整外部RTSP延迟验收。当前是可解压运行内测目录包，没有正式安装器、签名在线更新器或GPU纹理共享；打包不等于预览延迟优化。这些不能标记为已交付。

## 源码、构建及复现

源码主目录：`F:\WISEYE-Studio`。用户在F盘连续出现disk153/UASPStor129后明确授权临时内置盘构建，实际临时目录为 `E:\Projects\WISEYE-BuildWorkspace`；E原项目不覆盖。恢复后的成品仍回F。F此前的连接异常未被认定已修复，不建议在该连接上高负载编译。

在健康内置盘的同步工程中执行：

```powershell
.\scripts\Build-Release.ps1 -Stage Game -Configuration Shipping
.\scripts\Build-Release.ps1 -Stage Desktop
.\scripts\Build-Release.ps1 -Stage Cook -Content All -Configuration Shipping
.\scripts\Build-Release.ps1 -Stage Assemble -Content All -Configuration Shipping
```

`Stage`模式仅在现有Cook数据与当前代码/引擎兼容时使用。本轮先Development Cook后Shipping Stage；后续仅修复了无反射布局变化的原生启动/日志逻辑，以重新构建的Shipping EXE刷新归档后重新装配、校验并实测。不要将这种代码修补复用当作任意资产/引擎升级都可跳过Cook。

Cook使用同UE5.8.4的既有Editor DLL/receipt作为工具引导；Game Development/Shipping分别真实构建。下一次干净构建还需验证Editor构建与依赖安装全流程，不能用本轮引导结果冒充干净源码构建验收。

本轮新增/修复：runtime_paths与WiseEyeDataDir；冻结多角色入口；RuntimeManager就绪握手、Windows Job、可写工作目录；PyInstaller构建子进程的ICU预加载确保Qt平台插件收齐；Game模块用WiseEyeScene清单设置默认地图以支持Shipping启动；AirSim避免重复设置CustomDepth、天气资源Cook及缺失防护、Unicode日志路径；CitySample支持模块宏；仅保留MediaMTX所需RTSP功能。AirSim改动由第三方补丁和Setup脚本保存，原碰撞/GC/真实RPM修复保留。

详细原始构建、错误和恢复记录保留在临时目录 builds/logs，正式摘要在本文与AI_HANDOFF。未提交、推送或上传GitHub。

## 以下为2026-10-22旧过程记录，当前状态以上文为准

本轮工作目录已迁至 **F:\WISEYE-Studio**。E 盘原工程保留；F 盘是后续源码与打包工作目录。UE 5.8.4、VS 和基础 Python 仍是本机已安装的构建工具，不随源码迁移。所有新增源码、脚本、构建环境、构建日志及预期发布目录位于 F 盘工程内。

## 实际进度

- 已复制约43.334GiB源工程，40939文件，无复制失败；六处 AirSim/Drone 目录联接已展开为 F 盘实体文件，插件源文件和SimLibs不再指向E盘。
- 已在 builds/python-env 建立独立环境：Python3.14.6、Qt/PySide6 6.11.0、PyInstaller6.22.3、AirSim1.1.0；锁定清单 builds/python-requirements.lock.txt。
- **Development Game 构建成功**：ue5/WISEYE/Binaries/Win64/test.exe，399874560字节。独立AirSim着色器初始化和CitySample主模块冲突已修复，并保留可复现补丁/安装脚本改动。
- 已实现统一可写数据根、安装资源根、发布启动管理、显式flight/rtsp worker、进程Job清理、已发布场景清单识别；开发模式保留。
- 桌面EXE早期版本在清空开发PATH后诊断成功（Qt/AirSim/配置）。**最终重打包在磁盘异常时被中断，不能将 builds/desktop 当前目录当成完整交付件。**
- 46项核心/路径测试、9项Qt测试、1项Job进程清理测试分别通过。尚无完整独立仿真或干净电脑验收。
- 基础Cook第一次遇到Zen输出存储连接问题；改为 bUseZenStore=False、SkipZenStore，本地Cook已继续到约987/1008资源，但尚未Cook/Stage成功。
- **没有完成基础发布包、城市Cook、Shipping、安装器、在线更新或实际包体统计。**

## 当前阻塞：F盘USB存储I/O异常

本轮开始F卷Healthy/OK、Dirty未设置。随后Windows System日志出现磁盘1 disk事件153（I/O重试），以及UASPStor事件129（存储端口重置），可见时间22:21–22:23。F盘文件读取出现长时间阻塞。物理原因未确诊，不能仅凭这些事件认定SSD本体损坏。

已停止本轮Cook命令行编辑器、相关ShaderCompileWorker和PyInstaller进程，未格式化/修复/删除磁盘数据。需要更换USB连接并确认恢复，或经用户选择在内置盘临时构建后将成品回传F盘。不要继续在异常连接上重启高负载构建；安全弹出前确认相关进程和写入已结束。

## 恢复后的命令

在 F:\WISEYE-Studio 中执行，各阶段独立运行并检查返回码：

```powershell
.\scripts\Build-Release.ps1 -Stage Game
.\scripts\Build-Release.ps1 -Stage Desktop
.\scripts\Build-Release.ps1 -Stage Cook -Content Base
.\scripts\Build-Release.ps1 -Stage Assemble -Content Base
```

先验证基础包，再用 -Content All Cook/Assemble 包含真实城市；-Configuration Shipping 需先完成对应Game构建及验收。最终目录为 releases/<时间-内容-构建配置>，双击其中WISEYE.exe。这些是恢复后步骤，当前并无通过验收的releases目录。

UE 5.8 将位置参数test解释为特殊参数，因此Game使用 -TargetType=Game 推导现有目标，不改名。Cook使用本机旧编辑器二进制和receipt作为工具引导（从同版本E盘工程复制至F盘）；新Game从F盘源码构建。后续需添加/执行F盘testEditor构建以验证编辑器分支及干净构建可重复性，不能将引导Cook当作全部新源码的Editor验证。

主要日志：builds/logs/game-development-build.log、cook-base-development.log、desktop-build.log、core-tests.log、qt-tests.log、job-tests.log。诊断结果 builds/desktop-diagnostic.json。

## 后续必须处理与验证

1. 恢复存储后重新生成桌面包，检查完整性；不要使用被中断的COLLECT目录。
2. Cook/Stage通过后运行Assemble；当前发布结构是目录部署，本轮未实现版本更新激活器。
3. 原E盘flight runner仍占50052，RTSP服务占8554；本轮未强杀这些旧用户进程。新发布启动器会拒绝占用的飞控端口，正式联调前确认旧会话已退出后只关闭对应进程。
4. 真实启动验证Game、配置根、传感器和飞控；当前启动/退出管理和RTSP分支尚未完整联调。退出使用已落地状态保护；异常断连与场景切换需专项测试。
5. 城市资源与动态加载模型/材质、WorldPartition/FastGeo碰撞的Cook完整性、已知缺失引用、Shipping、普通用户和干净系统均未验收。
6. 当前/Drone整目录AlwaysCook包含无关机型，首包通过后按引用报告收紧，不删除原始资产。现有D3D11 SM5与DX12 SM6均会编译，是否只支持SM6应在后续明确取舍。
7. 打包附带第三方许可与必要依赖说明，实际交付前核对完整性。Zen输出失败产生的认证projectstore仅在忽略的builds内，不应加入发布物或Git。

详细路线见 PACKAGING_IMPLEMENTATION_HANDOFF.md。用户最新要求优先于其中原E盘暂存建议：源码与产物默认全部位于F:\WISEYE-Studio。未提交或上传GitHub。
# 2026-10-26 桌面接口更新包

`F:\WISEYE-Studio\releases\WISEYE-Desktop-Update-20261026.zip`，330,377,510字节（约315MiB），SHA256 `758bb24fceb444a52a3a583ea975a557e0391b505689eafab6e495f9a180aaa3`，复制到F后复核一致。

仅适配20261023-001704-All-Shipping完整包：先降落并关闭WISEYE/仿真/视频服务，再将更新ZIP所有内容覆盖解压到原WISEYE.exe所在目录；保留原完整ZIP作恢复来源。本更新包不能单独运行，继续使用原Simulation与Tools，不修改用户数据。新release.json带base_release_id及desktop_version，checksums.json合并原UE与新桌面文件清单。

冻结程序诊断、GUI冒烟及最新接口编辑模块收集检查通过；51核心、11Qt回归通过；MediaMTX自定义端口与路径的合成信号收流通过。没有重跑完整UE飞行/延迟验收，没有改UE红外材质；清理被审批拒绝、释放0。证据interface-release-20261026.json。
