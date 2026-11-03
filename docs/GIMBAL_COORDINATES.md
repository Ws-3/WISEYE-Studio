# 云台设备数值与仿真地理坐标（2026-10-30）

用户已放弃边缘盒子方案。本轮完善当前电脑上的云台和坐标接口，不推进边缘部署。

## 距离与坐标的含义

当前UE世界厘米制，100单位对应1米。设备位置和尺寸用厘米；雷达量程用米×100追踪，命中距离用厘米÷100回传。可以计算有物理尺度的米制空间位置、光心到目标斜距、水平距离和高差。

这些是**仿真几何距离**，不是已标定的测距仪；也不能保证City Sample建筑与现实测绘尺寸完全一致。UE世界Z不是海拔，当前城市没有真实地理原点和北向配准。

## 操作入口

工作台右侧切“云台”，点击 **设备数值与坐标…**。

- 设备数值：相对底座的实际偏航／俯仰、当前仿真限位和速度能力；各镜头水平／垂直FOV及输出规格；底座、光心、所选无人机XYZ；光心到无人机斜距／水平距离／高差；控制地址和设备ID。
- 配置基准后还显示云台、无人机的仿真经纬高，以及镜头仿真北向方位／仰角。未设置时明确显示未设置；断连时清除有效值。
- 坐标指向：选择VIS或IR，按已回读无人机坐标指向一次，或输入UE世界米／WGS84仿真经纬高指向一次。
- 仿真地理基准：设置基准点经纬高、对应UE世界点和北向。保存基准不会移动地图和设备。

VIS输出1920×1080、IR输出640×512，水平FOV各自独立，垂直FOV由各自画幅比例计算。当前仿真俯仰-15～75°、偏航输入±180°，速度能力30／20°每秒，非厂商标定规格。毫米焦距、物理感光尺寸、真实变倍倍率没有可靠参数，不伪造这些数据。

## 自定义仿真地理基准

用户选择先用自定义基准，不做真实测绘配准。填写方法：

1. 在“仿真地理基准”页选UE世界参考点；可点击使用当前云台底座。
2. 填该点希望对应的WGS84纬度、经度、**椭球高**。
3. 填UE世界+X相对仿真真北的顺时针方位。0°表示+X北、+Y东、+Z上；90°表示+X东、+Y南。
4. 点击保存，所有设备和无人机使用同一转换。

0只是待填写输入，保存前不生效。高度不是海拔／相对起飞点高／离地高，未来接真实GNSS时须先统一高程。GCJ-02、BD-09也不能直接当作WGS84。文件固定标记purpose=simulation_anchor，不能称为真实城市位置。

转换采用WGS84经纬高⇄ECEF⇄局部ENU⇄UE世界，双精度计算。场景按参考点切平面建系，没有把城市地形弯到地球椭球上，也没有做全球地形配准。

基准保存到当前DATA_ROOT下 `configs/georeferences/<scene_id>.json`，窗口显示实际路径；本机通常在 `E:\Projects\WISEYE-IR-Work\preview-data` 下。用户配置不会自动复制回F源码或同步Git；跨电脑应明确复制／管理。测试仅写证据目录isolated-config，没有替用户把虚拟地点保存到日常配置。

## 原生接口

`gimbal.point_at`使用现有TCP JSON Lines、version=1，请求中需有request_id。payload：

| 字段 | 内容 |
|---|---|
| device_id | 云台实例ID |
| scene_id / run_id | 从sim.get_state读取的当前场景／会话 |
| sensor | visible或infrared |
| position_cm | 三个有限UE世界厘米坐标，绝对值不超过1e7 |

求解使用实际底座变换、所选镜头光心、独立安装偏移和视轴偏差。距光心不足1cm、非法坐标、旧场景／会话及不可达俯仰会拒绝，恢复原姿态，不静默限幅。成功清除远程比例输入、退出原真值跟踪并保持新朝向，返回coordinate_pointing（sensor、position_cm、error_deg、slant_range_m）。

这是直接位置设置，与set_angles相同，**未模拟完整伺服加减速、回差或绕线**。已有真值跟踪仍使用原有速度逻辑，不将本次位置指令伪装为真实机械响应。

sim.get_state新增coordinate_pointing_supported、gimbal_geometry（厘米、底座／转轴位置、底座旋转、角度参考及速度能力）；传感器新增vertical_fov_deg、width_px、height_px。原pointing_error_deg仍是既有真值目标误差，不能当作任意坐标目标误差；新命令的误差读coordinate_pointing.error_deg。

## Python SDK

```python
from integrations.gimbal_client import GimbalClient
from core.georeference import GeoReferenceStore
from core.config import ROOT

ptz = GimbalClient('ptz-01')
state = ptz.state()
ref = GeoReferenceStore(ROOT).load(state['scene_id'])
locations = ptz.coordinates(ref)  # 没有ref时geodetic为None
drone = next(d for d in locations['devices'] if d['id'] == 'uav-01')

ptz.point_at_world(drone['position_cm'], sensor='visible',
                  scene_id=state['scene_id'], run_id=state['run_id'])

if ref is not None:
    p = drone['geodetic']
    ptz.point_at_geodetic(ref, p['latitude_deg'], p['longitude_deg'],
                         p['ellipsoid_height_m'], sensor='infrared',
                         run_id=state['run_id'])
```

经纬高在Python侧用显式基准转换，UE仍接收世界厘米；原生sim.get_state没有因此变成GNSS接口，训练样本也没有自动加入地理元数据。不同程序须使用同一基准；尚无配置版本协商和多控制端独占锁，勿与桌面摇杆或真值跟踪争用。

持续跟随需不断提交新坐标。提供 `examples/gimbal_coordinate_tracking.py`，stdin接收严格递增sequence的JSONL。默认字段position_cm；指定--reference后字段为latitude_deg、longitude_deg、ellipsoid_height_m。

```powershell
python -m examples.gimbal_coordinate_tracking --device ptz-01 --sensor visible --reference "<实际基准文件路径>"
```

输入坐标消息，EOF结束；结束后保持方向。它不接GPS硬件。真实坐标源适配、时钟同步、过期样本检测、预测滤波和视觉闭环仍需后续做。停止更新时保持最后姿态，不保持角速度。现有控制服务仍仅本机监听。

## 实际验收与边界

- Editor编译成功；102核心／65Qt回归通过。含已知WGS84轴值、各种北向／高纬／经度边界往返、未设置保持空、场景／会话保护及按设备回包隔离。
- 实城run `5CFCFED442F678E9CA8FBA995694D4C4`：VIS／IR各自光心沿视轴2000cm目标回读约20.000000m，FOV／输出规格正确，光轴误差小于0.01°；经纬高往返后指向通过。这不代表真实地图测绘精度。
- 旧会话、布尔伪坐标、超限俯仰均拒绝，原姿态保留。
- 实际无人机起飞／升高／悬停时，10次回读位置→仿真经纬高→VIS指向通过，不代表高速机动或长时跟踪验收。
- 最终ready／四RPM=0，恢复角度和真值跟踪状态，自有进程全退出。高位降落仍先下降到起点附近再Land，未修复此前60秒高位Land问题。
- 证据 `evidence/gimbal-geometry-20261030/final`；截图30°N／120°E／100m仅隔离测试基准，不是城市真实位置，未改用户Fleet和日常基准文件。

未Cook／重包／提交推送。重开源码预览使用新Editor，旧运行包不支持新命令。正常启动仍不自动开启UE。

后续真正地理配准可评估UE自带GeoReferencing与测绘／GIS数据：[Epic配准说明](https://dev.epicgames.com/documentation/unreal-engine/georeferencing-a-level-in-unreal-engine)。本轮没加该插件或更换城市。坐标转换背景见[GeographicLib文档](https://geographiclib.sourceforge.io/)。
