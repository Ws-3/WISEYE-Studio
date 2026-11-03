# 地图与场景管理

2026-10-31最新：小城市 `city` 仍默认；大城市 `city_large` 已通过局部飞行与切回小城市验收，作为独立试验入口提供。根目录 `Start-WISEYE-Studio.vbs` 只开GUI。在“场景编排”选择场景后，未运行UE时点击“启动仿真”；已有UE时先降落再加载所选场景。详细实测、E盘资源依赖及边界见[大城市接入](BIG_CITY_INTEGRATION.md)。旧测试/沙漠入口已移除，受审批限制未删的二进制见[清理清单](BIG_CITY_ASSESSMENT.md)。旧包仍仅小城市，本轮未重包。

WISEYE 使用一个 UE 工程、多张环境地图、同一套设备装配与控制代码。当前是 **UE 编辑器工作流**，不是可接收任意原始地图的独立打包程序。

## 日常切换

1. 首次更新代码后在 PowerShell 中运行 `scripts/Start-WISEYE.ps1` 完成编译，在 UE 点击播放。
2. 启动 `scripts/Start-Desktop.ps1`，连接 UE。
3. 左侧“实验场景”选择地图，点击“切换到所选场景”。切换会重置本次运行，旧截图清除，连接恢复后显示新场景 ID。
4. 点击“获取当前画面”检查新场景。现有自动/手动飞行、旋翼、云台、可见光/红外和相机设置继续使用。

预置场景：`city`（City Sample小城市）、`city_large`（City Sample大城市，试验）。切换中连接短暂断开属于预期行为；切入大城市桌面最多重连900秒，小城市90秒。超时检查UE输出日志再手动连接，断开前正在执行的操作不能假定成功。小城市未加载大城市的整张地图，但两者共享建筑等资源；切换也不能保证进程内存立即归还系统。

未启动 UE 时，选择场景后点“打开 UE 仿真”，可直接打开该地图。需要先完成一次 C++ 构建。

## 接入 Fab / 社区地图

1. 使用 UE 编辑器/资源提供方的导入方式，把完整场景添加或迁移到本工程 `ue5/WISEYE/test.uproject`。保留原包路径及依赖；仅导入 FBX 模型不会自动成为完整地图。
2. 在 UE 检查地图是否正常打开，所需插件与引擎版本是否兼容。当前工程使用 UE 5.8，不自动安装第三方插件。
3. 保存并关闭 UE。桌面选择“地图管理 / 导入 → 接入 UE / Fab 地图”。填写场景 ID、显示名称，选择源地图并填写云台位置、航线中心、总览视角、半径、周期、升降幅度和视场。
4. 点击“保存配置，准备场景”。普通地图将复制到 `/Game/WISEYE/Scenes/<id>/Scene`，再安装标准设备。源地图保持原状。UE 打开后检查输出日志，成功消息为 `WISEYE scene prepared`。
5. 检查设备是否落在合理位置、航线是否穿过建筑。当前飞控由Project AirSim承担，仍无自动避障；必须验证新地图碰撞与分区流送。新场景还需对应飞控配置、启动选项及运行验证，不能只登记地图就视为完成。保存后回到桌面刷新列表，再播放、连接和切换。

尚未安装设备的地图标记为“待准备”，不能从主窗口切入。失败后保留目标文件供检查，不会覆盖或自动删除；可修复后使用下方安装入口，或另选新 ID。

### World Partition 大地图

自动准备入口会拒绝直接复制 World Partition 地图。先在 UE 中通过适用于该工程的地图复制/迁移工具创建副本，确认外部 Actor 和对象完整、地图已正常加载。副本路径必须与配置中的 `map` 一致。不要只用文件管理器复制 `.umap`。

打开副本，停止播放，加载设备安装区域。UE 的 Python 控制台执行以下代码（路径按实际仓库修改）：

```python
import sys
sys.path.insert(0, r'D:/Projects/WISEYE-Studio/ue5/scripts')
from scene_tools import install_current_scene
install_current_scene(r'D:/Projects/WISEYE-Studio/ue5/WISEYE/Config/WISEYE/Scenes/city_day.json')
```

安装入口检查当前地图路径，禁止重复安装，并保存新设备和配置。同步项目时同时保留 Content 下的 `__ExternalActors__` 和 `__ExternalObjects__`。第三方 World Partition 场景尚未在本次环境中实际验收；需要针对选定资源验证流送、引用和性能。

## 标准场景包 v1

桌面“导入标准场景包”接收 WISEYE 格式 ZIP，**不直接接收 Fab 下载 ZIP**。文件校验与复制在后台线程进行；不覆盖已有 ID，也不执行包中的代码。导入后重新打开 UE，使新资源被扫描。

v1 支持已完成设备安装的普通地图，资源位于独立命名空间 `Content/WISEYE/Scenes/<id>/`。格式如下（ZIP 不含空目录条目）：

```text
scene.json
Content/WISEYE/Scenes/<id>/Scene.umap
Content/WISEYE/Scenes/<id>/...uasset
```

`scene.json` 包含 `engine_version: "5.8"`、`scene` 配置、`files`（包内资源相对路径 → SHA256）以及 `required_assets`（共享 /Game 资源路径 → SHA256）。标准云台和无人机资源来自同版本 WISEYE 基础工程；若缺少或不匹配，导入会拒绝并列出资源。包内所有文件通过校验后才安装。

通过 UE Python 导出已保存场景（目标 ZIP 不得已存在）：

```python
import sys
sys.path.insert(0, r'D:/Projects/WISEYE-Studio/ue5/scripts')
from export_scene_pack import export_pack
export_pack('test_range', r'D:/Exports/test_range.zip')
```

导出会收集递归资源依赖：本场景命名空间内资源入包，共享资源列为带哈希依赖。第三方资源如果位于场景命名空间外，需要先通过 UE 迁移到接收工程；不要在磁盘上随意移动资产。依赖插件资源、World Partition 或其他子地图的复杂场景使用 UE 完整迁移流程，v1 包不代替该流程。

场景包最多 20 GiB 解压资源和 50000 文件。此限制只针对导入器，不限制通过 UE 编辑器接入的场景。

## 配置与设备复用

- `ue5/WISEYE/Config/WISEYE/Scenes/<id>.json`：统一场景配置，距离单位 cm，角度 deg；总览旋转依次为 pitch/yaw/roll。
- `prepared: true` 仅在设备安装与地图保存成功后设置。不得仅为了显示列表手工标记未准备地图。
- `standard_rig.json`：从原地图提取的标准装配，包括 162 个装配 Actor 的变换、网格/材质、挂接点、四旋翼及光心。新地图使用同一份装配数据；bottom 固定，bottom2 水平旋转，camera/ptz 跟随水平和俯仰。
- 原地图保持原来的手工装配；新地图中的设备是按同一标准数据生成的实例。后续改变装配结构时需要显式迁移已生成地图，不会静默覆盖它们。
- 生成的云台和无人机分别建立锁定的编辑器选择组。保持 UE 的“允许组选取”开启；选择部件时会选择整台设备，移动整体不会改变内部装配。要改变安装位置，操作 `PTZ_Camera` / `Mavic3` 设备根或整体选择组；不要解组后单独拖动网格。
- `assembly_revision: 2` 修复了 Python Rotator 参数顺序导致的部件分离。脚本用命名参数构造旋转，并根据标定数据恢复子节点/网格的局部变换。已有早期生成场景可在停止播放后执行 `from repair_scene_assembly import repair_current_scene; repair_current_scene()`；该操作只接受 `/Game/WISEYE/Scenes/` 下的地图，保留设备根的当前位置和方向，校验节点后保存。
- 运行时 `WiseEyeScenes.cpp` 读取当前配置，设置安装位置、航线和 FOV；所有地图共用 `WiseEyeDemo`、传感器与控制桥。
- 配置修改在下次启动或切换场景时生效。环境本身保留地图中的光照；天气编辑、安装点可视化选择、算法选择和多目标配置尚未加入此界面。

地图能运行不代表已完成设备性能标定。社区环境未自动获得物理红外材质；当前红外仍是模拟热强度，跟踪仍使用 UE 真值。

### 验证入口

- Python：`python -m unittest tests.test_scenes tests.test_protocol -v`。
- 真实 UE 播放后：`python -m tests.verify_scenes_live`，会切换两个预置地图，最后停在测试场。
- 完整 UE 编辑器打开生成场景且停止播放：`from verify_scene_assembly import verify; print(verify())`。检查装配相对变换、整机平移/旋转、云台轴向和整组选取；测试变换会恢复，不保存测试姿态。
- 整组选取必须在完整编辑器验证。引擎 `AGroupActor::PostLoad` 在 commandlet 中跳过组关系重建，不能用无界面选择结果判断编辑器分组失败。
