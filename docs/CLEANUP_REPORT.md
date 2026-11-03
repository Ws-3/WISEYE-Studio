# 清理核查（2026-10-27）

## 2026-10-28：根目录启动入口及自有Python缓存（已实际执行）

根目录六入口合并为唯一 `Start-WISEYE-Studio.vbs`，改为隐藏启动 `scripts/Start-SimulationPreview.ps1`（当前E盘城市UE预览+飞控+桌面），失败提示可复制的诊断命令；尚未等加载完成时请在桌面稍后连接，勿重复双击。当前入口不自动同步/编译UE源。已有UE时仅打开桌面用 `scripts/Start-Desktop.ps1 -Connect`，已修复该脚本先找builds/python-env、再找.venv。

实际删除：Start-CitySample.vbs、Start-Desktop.cmd、Start-ProjectAirSim.cmd、Start-ProjectAirSim.vbs、Start-WISEYE.cmd；根目录projectairsim_client.log；8个自有源码__pycache__目录中的86个.pyc。原文件合计1,001,975字节（约0.96MiB，不是磁盘空间净增减测量）。缓存和日志以后运行可能重建。仅固定路径、拒绝目录联接和意外内容；未进入Python环境或第三方资源清理。

保留训练端Start-Training.vbs，所有开发/安装PS脚本、证书、模型/城市/配置/实验数据/发布包及外部依赖。README、使用指南、文件结构、安装/开发引用已更新；历史工作日志与证据中的旧文件名保留作为历史记录。删除清单docs/entry-cleanup-20261028.json。

验证：同一VBS内容复制至E盘含空格临时目录，以无副作用PowerShell桩执行成功；全部Start-*.ps1 AST语法通过；替换Start-Process核实桌面解释器及--connect参数；临时测试目录已删除。本轮未启动真实UE/GUI，不把桩测试写成全链路运行验收。

## 最新核查：用户自行删除，尚未执行

用户明确授权删除旧项目/临时文件，并确认保留最新20261027城市ZIP。执行环境对批量删除和单个固定旧ZIP删除均返回blocked by policy，命令未启动，本轮实际删除0字节。后续用户选择查看清单并自行删除，不能将下列候选写成已清理。

优先候选：E:\Projects\WISEYE-Studio旧工程约64.361GiB；E:\Projects\WISEYE-BuildWorkspace临时构建约316.561GiB。F盘可清理20261023旧ZIP/附属文件、20261026桌面增量包、releases/.incoming-20261023-001704，以及builds/desktop、pyinstaller、smoke-data、logs，UE Binaries/Intermediate/DerivedDataCache与Saved内Cooked/Logs/ShaderDebugInfo/Shaders/UnrealBuildTool。不删除Saved/Config、Collections或任何Content。

保留F:\WISEYE-Studio主项目、.git、Config/configs/航线、Source、Content、Models、论文与依赖、builds/python-env，以及releases/WISEYE-20261027*。保留E:\Projects\Scene和ProjectAirSim-Evaluation共享原始资源/依赖。旧E工程含6处指向共享AirSim的目录联接，删除工程时只删除联接本身，不进入联接清空目标。

已读取全部1010个Git文件共250276881字节，和临时构建副本逐字节一致；Git fsck通过。构建Content39860文件在F对应路径全部存在且长度一致（不是全部城市资产重新哈希）。F盘2个PyInstaller Python __pycache__目录报WinError1392，仅此两处被本轮遍历记录，未执行磁盘修复，python-env不纳入删除。审计详见evidence/cleanup-20261027。清理脚本仅通过语法检查，未执行删除。

删除E构建目录会让原默认预览入口缺少依赖；删除UE编译缓存后源码需要重新构建。最新独立ZIP完整保留，可解压后运行。用户完成删除后需更新交接中的构建目录状态，不能假设已删。

## 以下为2026-10-26历史核查

本轮实际释放：0字节。批量路径和固定目录递归删除均被自动审批审查拒绝，未绕过审查或执行替代删除。以下为已核对的可再生成候选，不代表已删除。

| 位置 | 可清理GiB |
|---|---|
| F: | 5.821 |
| E: | 107.542 |

保留：F盘已校验完整ZIP、E盘001704最终验收运行目录、所有Content与ExternalActors、模型/权重/实验数据、用户Fleet/航线、构建Python依赖、E盘有效Cooked与DDC。旧E原工程及CitySample原项目未列入自动清理。

清理暂存只能减少开发占用，不会自动减小16.864GiB分发包。要减分发包应先统计IoStore容器、引用链、贴图平台尺寸及实际关卡依赖，制作精简内容配置并重新Cook验收；不能直接删除城市源资产。

| 已核对候选 | GiB |
|---|---|
| `F:\WISEYE-Studio\builds\desktop` | 0.096 |
| `F:\WISEYE-Studio\builds\pyinstaller` | 0.024 |
| `F:\WISEYE-Studio\builds\smoke-data` | 0.000 |
| `F:\WISEYE-Studio\ue5\WISEYE\Saved\Cooked` | 1.190 |
| `F:\WISEYE-Studio\ue5\WISEYE\Saved\ShaderDebugInfo` | 0.003 |
| `F:\WISEYE-Studio\ue5\WISEYE\Saved\Shaders` | 0.175 |
| `F:\WISEYE-Studio\ue5\WISEYE\Intermediate` | 4.332 |
| `E:\Projects\WISEYE-BuildWorkspace\builds\distribution` | 16.864 |
| `E:\Projects\WISEYE-BuildWorkspace\builds\staged` | 34.968 |
| `E:\Projects\WISEYE-BuildWorkspace\releases\20261022-233112-Base-Development` | 1.767 |
| `E:\Projects\WISEYE-BuildWorkspace\releases\20261022-233243-Base-Development` | 1.767 |
| `E:\Projects\WISEYE-BuildWorkspace\releases\20261022-234233-Base-Development` | 1.817 |
| `E:\Projects\WISEYE-BuildWorkspace\releases\20261022-235803-All-Development` | 17.089 |
| `E:\Projects\WISEYE-BuildWorkspace\releases\WISEYE 城市版 20261023-000219-All-Shipping` | 16.864 |
| `E:\Projects\WISEYE-BuildWorkspace\ue5\WISEYE\Saved\StagedBuilds` | 16.404 |
