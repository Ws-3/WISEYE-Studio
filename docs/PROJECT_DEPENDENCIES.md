# 项目源码、构建工作区与城市资源

2026-11-02便携性补充：当前F并未自包含。新核查IR-Work约37.33GiB、CitySample104.70GiB、VaultCache104.26GiB、UE30.58GiB；F Python venv的base_prefix仍是E:/Environments/anaconda3，需独立基础Python/重建开发环境或冻结运行包才能断开此依赖。F卷Health=Warning且Dirty、磁盘设备Healthy，未修复；先备份检查再大规模迁移/清理源副本。完整只读评估、目标目录及验收步骤见 [F_DRIVE_PORTABILITY_ASSESSMENT.md](F_DRIVE_PORTABILITY_ASSESSMENT.md)。本轮未迁移、删除或打包；不把本评估当迁移已完成。

2026-11-02实机核查。F:\WISEYE-Studio仍是主源码目录。下面的目录不是三个独立的WISEYE版本。

| 目录 | 内容与本轮文件体积 | 当前是否能整体删除 |
| --- | --- | --- |
| E:\Projects\WISEYE-IR-Work | UE衍生构建工程；Source编译副本、Binaries/Intermediate/Saved、独有大城市地图及外部Actor、正常preview-data和隔离验收目录。跳过目录联接统计约36.09GiB，另有大量共享城市资源。 | 不能。当前桌面直接启动这里的test.uproject，且大城市副本与正常用户数据还在这里。 |
| E:\Projects\ProjectAirSim-Evaluation | 固定版本的上游源码、补丁后的物理/飞控代码、旧构建与虚拟环境。约6.17GiB。 | 本轮解除两处插件资源联接后，不再是当前日常预览的依赖。保留本地修改归档后可以归档/清理；本轮没有删除原目录。 |
| E:\Projects\Scene | 原始CitySample与Fab/Vault缓存，总文件体积约208.96GiB。 | 不能整体删。CitySample仍是共享建筑、材质、地图等资源的实际目标；VaultCache须单独核查。 |

以上是扫描时文件长度之和，排除目录联接，不是Cook包大小、全依赖增量或精确NTFS占用空间；数据见docs/evidence/workbench-weather-20261102/directory-inventory.json。

## ProjectAirSim已放进项目的部分

- UE插件源码、资源和SimLibs：ue5/WISEYE/Plugins/ProjectAirSim；Drone插件亦在同层。
- 日常桌面Python环境：builds/python-env。安装的projectairsim是实体包，不是指向Evaluation的editable链接；安装来源记录为本项目builds/dependencies/projectairsim。
- 上游固定提交与可重放补丁：scripts/Setup-ProjectAirSim.ps1和third_party/patches/projectairsim-*.patch。
- 旧Evaluation工作树的完整本地差异已另存到builds/dependencies/evaluation-source-handoff-20261102/local-changes.patch，manifest.json记录原提交62229cd7c77ad31da7bc8aba8dd6303c564d8ba2及状态；没有未跟踪源文件。这些是本地依赖归档，不自动上传Git。

实际发现E构建工程的ProjectAirSim/Content和Drone/Content仍联接到Evaluation。与F项目内实体副本逐文件SHA256比较，分别131和70个文件全部一致，本轮已经将这两处联接改到F项目内。SimLibs原本就指向F。工具scripts/Use-LocalPluginContent.ps1会先确认工程退出、目标为实体目录、全部资源匹配，再仅替换联接本身；不递归删除原目标，失败会还原旧联接。

旧Start-ProjectAirSim.ps1也改用项目内Python，不再寻找外部Evaluation虚拟环境。Setup-ProjectAirSim默认把新的可重建上游源码放到本项目builds/dependencies/ProjectAirSimSource，仍可显式传-AirSimRoot。此变更不会自动克隆、复制6GiB旧工作树或重建物理库。

本轮解除的是当前预览依赖；若还要继续使用旧Evaluation的独立C++测试、ROS/Unity实验或其虚拟环境，应保留/归档相应工作，不把它们称为本次日常运行必需文件。

## 为什么IR-Work和Scene还要保留

日常根VBS只开GUI；桌面选择的正常用户目录默认是IR-Work/preview-data，RuntimeManager启动IR-Work/test.uproject。正常目录里的Content又联接到IR-Work/Content。衍生工程的Building、Map等大量资源则联接到Scene/CitySample。本轮没有搬走这些数据。

新大城市的WISEYE副本及约8.69GiB外部Actor保存在E衍生Content中，不能只复制一张umap到F，更不能把共享城市目录当缓存删掉。F主源码里的新JSON不等于已经携带整套大城市资源。

Scene/VaultCache是单独的下载/库缓存，当前联接清单没有目标指向它。确认Epic/Fab没有进行下载/创建项目后，可通过Launcher管理缓存；不要同时删除CitySample项目，更不要因VaultCache可清理就删除整个Scene。本轮未清理缓存。

## 以后整合到一个项目目录的路线

1. 先将正常preview-data中的用户配置、Fleet/Layout、地理基准和接口参数复制到目标数据目录，逐文件校验；不以默认F配置覆盖用户当前布置。
2. 把衍生工程中WISEYE自有地图/外部Actor/模型/材质与所需插件整理为独立本地资源包。城市原始资源根据UE依赖审计或官方迁移/Cook流程准备，保留路径、插件和授权信息；不手工复制孤立umap。
3. 选择“项目目录内实体资源”或“项目目录内独立Assets目录”并重建联接。当前F曾有Building模型目录读取损坏记录，批量迁入前应先确认目标盘可靠；不能只看518GiB余量就开始写入200GiB资源。
4. 更新Start-Desktop/预览脚本与RuntimeManager使用的工程和数据路径，重新编译、跑大小城市、天气、双路图像、控制与退出验收；源目录暂时改名隔离后再验证没有回读。
5. 通过校验后，才清理旧IR-Work与原始资源副本。编译缓存可重建，但独有地图、用户配置和共享资产必须先迁走。

本轮没有执行这次大规模迁移或目录删除。最终发行包走Cook/打包路线，可不携带UE编辑器和这些源码工作区；现有旧发行包尚未更新到本轮修改。
