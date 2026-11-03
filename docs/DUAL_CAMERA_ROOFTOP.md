# 双相机几何与楼边部署（2026-10-28）

训练端后续已增加“原始叠加”和“视轴对齐”两种差异观察模式，支持不同光心预览，并显示基线、采集时间差及GT中心差；不将其称为深度配准完成。原严格同光心检查作为Python mode='strict'保留。见training_client/README.md及训练接口最新节。

## 本批改动

VIS和IR原来已有独立SceneCapture/RenderTarget，但同属EO_Camera且无相对位姿，导致同光心、同视轴。现在以共同机械头部OpticalMount为参考，两个采集相机成为独立的同级组件，分别设安装位置和视轴偏差；UE光学观察相机跟随当前选择的实际相机。光学头部保留原模型标定锚点，安装偏置使用物理厘米，不随导入模型缩放放大。雷达跟随共同机械头部，不因VIS/IR观察切换而换位置。

红外从自己的场景视角单独渲染，并非读取可见光相机的视频/RenderTarget再转灰度。但当前热像仍为工程代理：目标热状态、材料分类及部分场景外观参与信号生成，楼宇/云层仍含可见光材质或天空外观代理。本批修正相机几何，不等于完成真实LWIR温度、发射率和大气辐射模型。

## 相机参数

进入云台 → 传感器 → 可见光/红外，分别编辑“镜头前向/右向/上向偏置”“视轴俯仰/偏航/滚转偏差”，点击应用。各自FOV、启停、分辨率保持独立。位置以共同光学锚点为原点，X前/Y右/Z上，单位cm；旋转为UE局部pitch/yaw/roll，按机械头部旋转复合。当前参数本次运行有效，重启回到代码/UE实例默认值。

| 默认示例 | 可见光 | 红外 |
|---|---|---|
| 分辨率 | 1920×1080 | 640×512 |
| 安装位置cm | (0,-6,0) | (0,6,0) |
| 视轴pitch/yaw/roll ° | (0,0,0) | (0.1,0.2,0) |

横向基线12cm为当前仿真假设，角度也未由实机标定，不宣称是该80cm云台真实镜头的测量结果；后续按实机安装测量替换。绝对世界位姿随云台转动改变，物理基线保持不变。

`sensor.configure`在原参数基础上支持`mount_x_cm/mount_y_cm/mount_z_cm`（±100cm），`boresight_pitch_deg/boresight_yaw_deg/boresight_roll_deg`（±15°）。严格有限数值，布尔/字符串不算数值；与其余参数一起验证后原子提交。`sensors.<sensor>.extrinsics_supported`门控旧后端；状态回读六个设置值和实际`camera_position_cm`、`camera_rotation_pitch_yaw_roll_deg`。旧请求不带这些字段时保留现值。

热电机/电池投影改用InfraredCapture位姿。GT深度采集本来就按各模态相机，现实际生成各自光心/姿态下的标注；PNG导出元数据也改用被导出的相机，不再取当前观察相机。导出仍是最近完成图像与当前位姿说明，不是新增硬件同步测量；训练同刻样本的元数据取捕获时刻。

## 楼边布局（已于本轮更新为角位）

城市仅保留`uav-01` Mavic3 + `ptz-01`双光云台；只改运行布置配置，未修改城市模型或取消多设备能力。

| 对象 | 世界位置cm |
|---|---|
| 云台锚点 | (-27066.552734375,-2092.68798828125,4059.1168165) |
| 云台底面/楼顶 | z=4055 |
| 无人机初始锚点 | (-27400,-2600,4080) |
| 观察视点 | (-24900,0,6500)，pitch=-36°、yaw=-136° |

云台距东/北两碰撞楼边各100cm，底座±35cm九点同高；无人机周围±100cm九点同高。原远处无人机起点受屋顶结构遮挡，已改同楼顶角部内侧开阔区域；真实Mavic起降和两路GT通过。位置、证据及预览操作见[本轮说明](STARTUP_PLACEMENT_IR_TUNING.md)。旧版坐标仅适用于下方历史验收。

永久默认更新：`Config/WISEYE/Fleets/city.json`、`Layouts/city.json`、`Scenes/city.json`，并同步当前E衍生构建/本轮隔离数据。主入口下次首次创建preview-data时会从F复制新配置；若日后已有用户preview-data需要保留其编辑，不自动覆盖。本轮核查时该日常preview-data尚不存在。旧Shipping包/其用户目录未更新。

## 训练端影响

默认设备改为ptz-01。双路仍共享同刻token、仿真时间，但同刻不等于像素对齐。当前训练端支持raw/rotation观察叠加；strict仍拒绝跨光心直接融合。继续显示、保存原始双路及各自GT，raw/rotation不等于完成深度配准。后续应使用内外参及深度或立体配准；单个FOV缩放/全图平移无法校正整个有不同深度的城市场景。

基准配置`configs/infrared_benchmark.json`更新为v3/ptz-01（角位）。楼顶位置与双光几何已变化，不能将新场景统计直接当作之前地面机位v1的画质收益；原证据保留原manifest。

## 已执行验收

最终Editor `build-dual-camera-final.log`成功；68核心+35Qt通过。

实际城市run_id `1257AD154F9416E54CA522918D3273D1`：

- 三组云台姿态下基线保持12cm；VIS/IR姿态不同；单独改变IR安装位置不移动VIS；4组非法参数原子拒绝。
- 两相机分别启停，停用方采集序号停止、另一路继续；同刻样本/独立相机元数据通过；PNG双路导出相机坐标检查通过。
- 仿真内置50100服务双路接收、不同FOV、停IR拒绝/恢复、双路负样本与单路兼容通过；跨相机无配准融合被明确拒绝。
- Mavic楼顶实际起飞/悬停/降落通过：稳定起点z=4119.27cm，悬停4268.87cm，落地4119.27cm；最后ready、四RPM=0。初始4125配置落到物理接触面后约沉降5.73cm。
- 悬停两路均取得可见无人机GT，像素框随独立光心/视轴自然不同；不是共享一套像素框。

证据`docs/evidence/dual-camera-rooftop-20261028`包含楼顶图、双路图、几何/飞行/接收报告、取点与配置SHA256。自有仿真进程测试结束后退出。未重包、未推送；未做真实相机测量、跨相机深度融合或多物理电脑/长期验收。

重测（先在本机准备并启动当前E构建）：

```powershell
python -m tests.verify_dual_camera_live --output E:/Projects/WISEYE-IR-Work/new-dual-check
python -m tests.verify_rooftop_flight_live --output E:/Projects/WISEYE-IR-Work/new-roof-check
python -m tests.verify_training_pair_live --output E:/Projects/WISEYE-IR-Work/new-pair-check
```

日常双击根目录`Start-WISEYE-Studio.vbs`，等城市载入后连接仿真；当前E编辑器构建已包含本批代码。
