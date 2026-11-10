# 源码、资源与构建目录 · v1.1.0

截至 2026-11-10，唯一开发源码为仓库根目录，本机 `E:\Projects\WISEYE`。UE 工程为 `ue5/WISEYE/test.uproject`，C++ 源码为 `ue5/WISEYE/Source/test`。本机路径不是其他电脑的安装前提。

| 目录 | 内容 | 是否需要 |
|---|---|---|
| apps、core、training_client、integrations | 桌面、训练数据端、协议与飞控桥 | 源码开发需要 |
| ue5/WISEYE | 原生源码、配置、自有资源及本地依赖接入 | 原生开发需要 |
| third_party | 补丁、许可证及 JSBSim 适配源码 | 构建/再分发需要保留对应许可 |
| builds/dependencies | 固定提交的上游源码与编译依赖 | 可重建；清理前确认没有独有改动 |
| builds/distributions | 生成的插件和完整传输 ZIP | 交付产物，不是源码工作副本 |
| releases | 独立软件展开目录 | 普通用户运行所需 |
| UserData | 本机配置、日志及运行输出 | 用户数据，不上传、不随意删除 |
| builds/legacy-preview-20261110、legacy-evaluation-20261110 | 两个旧外部工程的历史隔离档案 | 已退出活动依赖；保留回退和独有资料，未物理清空 |
| 本机 Scene/CitySample | Epic 原始城市和城市插件资源 | 构建城市示例需要；源码插件与完整运行包不依赖该外部目录 |

旧 `E:\Projects\WISEYE-IR-Work` 和 `E:\Projects\ProjectAirSim-Evaluation` 路径已不存在，不在旧工程中编辑或启动。原生源码、SimLibs、插件 Content、自有/衍生地图和设备资源已回收到主项目。本机活动工程仍有 34 处城市资源联接指向 `Scene/CitySample`，因此不能直接删除该原始工程。VaultCache 是下载缓存，先通过 Launcher 确认不再需要，不等于 CitySample 项目本身。

源码仓库不提交引擎、完整第三方城市/生成城市副本、构建缓存、Python 环境或 UserData。新克隆通过安装脚本准备依赖和重建地图。源码 SDK 不包含城市；完整包包含已 Cook 城市和运行依赖，可脱离源码及 Scene 目录运行。

`scripts/audit_project_dependencies.py` 只读审计活动链接；隔离目录不算新的开发副本。迁移核对及原始验证报告见[整合实施记录](DISTRIBUTION_IMPLEMENTATION_20261110.md)。不要把“目录已隔离”写成“文件已经全部删除”或“磁盘空间已回收”。
