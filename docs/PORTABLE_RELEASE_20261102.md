# 2026-11-02 便携运行包与迁移状态

## 当前可以运行的成品

目录：`E:\Projects\WISEYE-PortableBuild\releases\20261102-191254-City-Shipping`。

最终传输包：`releases/WISEYE-20261102-Win64-Portable.zip`，25,427,827,257字节，约23.68GiB；已逐文件校验并通过ZIP CRC。SHA256：`45f5bcfb5ca65b9c7053319749a75ea03f9c3d20f9940c7b8974b01b7fd99d7d`，同目录`.sha256`和`.zip.json`可核对。ZIP内顶层为WISEYE，完整解压后运行WISEYE/WISEYE.exe。此行补记在源码说明中，未修改已封存成品清单。

双击根目录 `WISEYE.exe`，桌面不会自动启动UE；选择城市，点击“启动仿真”。训练端可从右上角打开，或运行 `Training\WISEYE-Training.exe`。保持整个目录完整，不单独移动EXE。

这是UE5.8.4 Shipping双城市内测包，小城市默认、大城市保留“试验”标记。包含当前红外、夜空、空间雨线、独立事件相机、距离遥测、0.8m/s降落设定、多设备界面与训练采集端。算法框架/训练权重为可选扩展，未声称已内置全部算法。

根目录 `portable.flag` 启用便携模式：配置、航线、日志、采集输出和界面设置默认保存在旁边的 `UserData`，首次启动从Resources复制，后续不覆盖已有配置。可通过WISEYE_DATA_DIR明确改数据位置；删除portable.flag后使用原LocalAppData模式。项目须位于可写目录。Windows、显卡驱动、系统运行库和系统自身缓存仍是主机条件；提示缺少运行库时使用Simulation/Engine/Extras/Redist/en-us前置安装程序。

## 本机验收

- Shipping Game和双城市Cook/Stage/Archive真实成功。Cook 39分14秒、0错误、1个SDK调试字体嵌套警告；整个UE BuildCookRun 41分51秒。压缩资源.ucas约22.35GiB。
- 新独立Python3.14.6（官方Windows完整发行目录），不再依赖Anaconda打包。111核心测试、24项相关Qt检查、便携目录重定位/配置保留测试通过。
- 冻结仿真端、冻结训练端在清空开发PATH后实际启动并生成截图；初始不启动UE。
- 成品实际小城市起飞、转速、手动上升、降落/停桨，云台角速度、非空点云，以及VIS1920×1080/IR640×512/OBS960×540原尺寸图像通过；使用隔离中文空格数据目录。
- 成品city→city_large→city切换通过，两地图夜空、空间雨线、事件独立启停、参数/非法值、有序原始事件、JSON/JSONL导出和关闭释放采集通过。采样约30Hz，雨量0.7约6293–6297条雨线；这是单场景固定视角样本，非全城/长时性能保证。
- 自定义RTSP `rtsp://127.0.0.1:19554/portable/thermal`由冻结worker发布，随包FFmpeg实际解码640×512；冻结训练端由工作台成功启动并随父窗口关闭。所有所属测试进程退出。
- 运行中Game模块审计未发现包目录以外的E盘DLL。测试没有使用F盘，不需要主机安装UE编辑器、VS或Python；仍未做干净Windows/第二台电脑验收。

事件为帧驱动、时间戳插值的近似模型，有界生成/缓存可能丢弃事件，不能称硬件微秒响应或无损。红外仍非辐射温度标定，天气非完整降水物理。尚未做长时间/多机压力、全城遍历、全部算法训练、正式签名安装器或在线更新。

验收证据：`docs/evidence/portable-release-20261102/event-weather-verified/report.json`、`tools/report.json`；飞行报告在 `builds/live-tests/city-1793618195107407000/用户数据 测试/report.json`。首轮天气测试等待了Shipping没有提供的编辑器编译任务字段，已调整测试默认值后重跑通过，不是仿真冻结。

## 磁盘修复和F迁移尚未完成的部分

用户已授权修复/搬迁，后明确选择“先在内置盘打包，F盘稍后处理”。

修复前，6,019文件、1,542,595,961字节的代码/Git状态/自有资产/模型安全备份已与F逐文件SHA256一致。备份：`E:\Projects\_WISEYE-MigrationSafety-20261102-181223\source`，原始备份不当工作副本修改。

管理员CHKDSK `/f /x` 修正MFT及卷位图，exit=1表示已修复；当时Dirty清除、卷Healthy、坏扇区报告0KB。随后复制负载下18:20:26再次I/O重试、18:21:13 UASPStor重置，两项复制已停止，后续F文件访问出现“指定不存在的设备”。这不能以先前Healthy状态认定USB链路已经稳定。

F完整迁移未验收，E源项目/原始城市/备份未删除；不要清理它们。F上五个便携路径文件曾在故障前尝试修改，其应用/回滚状态未能校验；恢复连接后须与原始安全备份及本E工作副本核对，不把失败时控制台的“Restored”提示当成功证据。F城市/独立Python的部分复制也未校验，不应作为完成迁移的目录使用。

当前便携相关新改动在 `E:\Projects\WISEYE-PortableBuild` 工作副本，尚未同步回F、未提交/推送GitHub。该目录含完整代码、自有模型、独立Python、流工具和独立上游ProjectAirSim源码（原提交及20,940字节本地差异已保留）。开发用UE完整资源/引擎尚未全收进这个源码目录；用户现在运行上方成品，不用源码VBS当迁移完成验证。

内部临时构建仍用 `E:\Projects\WISEYE-IR-Work` 和 `E:\Programs\UE_5.8`；它的PJA SimLibs联接临时指向安全备份，PJA/Drone Content指向原Evaluation的Blocks/Plugins。成品已封装所需DLL/资源，不依赖这些联接。待F连接稳定后再迁引擎/实体城市/当前配置、同步代码、复核全部联接和校验，最后才能清理旧E副本。
