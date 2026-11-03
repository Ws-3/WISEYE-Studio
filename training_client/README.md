# WISEYE Training · 独立训练工作台

2026-10-30 V4：VIS／IR 为并排主画面，底部融合缩略窗可展开；顶部显示实测速率、计数及“开始保存／停止保存”。连接参数移至“连接设置”，右侧分组设置源、速率、目录与标注策略。停止保存继续接收；GT 框仍只影响显示。独立部署带上本目录全部 Python 文件（包括 `layout_v4.py` 和 `_theme.py`）。[完整说明与实际截图](../docs/UI_V4_IMPLEMENTATION.md)。

2026-10-29统一预览：已移除视频/样本双模式，始终使用同帧图像与GT，“预览GT框”只改变叠框；隐藏仍保存GT并显示同组融合。连接中可修改策略/目录，VIS/IR自动切换订阅；主机/端口/云台编辑后点击“应用连接设置”。详见[当前验证说明](../docs/GT_RATE_AND_UNIFIED_PREVIEW.md)。

默认预览上限5FPS、保存1FPS，可独立调整为0.1–10；新工作台请求UE允许10，但这是设置上限。本机双路完整GT实采约4–5组/s，最终GUI约4.5FPS、仿真约30Tick/s。协议实验上限20未达到20实帧。未显式配置的客户端后端默认仍2，多个采集者共享同设备策略/限流。

仿真主界面右上角新增“打开训练端”，无需再手动寻找VBS。已连接仿真时传入当前主机/云台并自动连接，默认50100可在训练端修改；重复点击复用现有窗口。源码环境已验证，独立包须额外包含训练端程序。详见[本轮修复](../docs/PLACEMENT_TONE_TRAINING_FIX.md)。

此目录可单独复制到算法电脑，无需 UE、AirSim 或 WISEYE 桌面模块。命令均在其父目录运行。提供按需同帧采样、GT预览、样本保存及手动训练入口；实际高帧率能力以上述测试为准，没有自动训练/模型上线功能。

## 唯一启动入口

双击 **Start-Training.vbs**，打开训练工作台。旧 Start-Preview.cmd 和 Start-Gateway.cmd 已移除。仿真电脑正常启动新版仿真即可，数据服务随仿真自动启动和退出，不需要手动启动网关。

```powershell
python -m pip install -r training_client/requirements.txt
```

本机填 127.0.0.1，另一电脑填仿真电脑有线 IPv4，数据端口默认 50100。仿真端需允许该 TCP 端口入站。服务适用于可信局域网，尚无认证与 TLS；UE 50051 保持本机，不开放飞控命令。服务端口冲突会写仿真日志，不影响飞行，不会结束占用端口的其他程序。RTSP 8554 保持独立，本工具使用成套采样接口。

## 算法电脑 / 本机预览

```powershell
python -m pip install -r training_client/requirements.txt
python -m training_client.preview --host 127.0.0.1 --device ptz-01
```

上述是开发命令，日常只用 Start-Training.vbs。本仓库优先使用已有 builds/python-env；独立电脑使用 training_client/.venv 或 PATH 中的 pythonw。界面复用仿真端的主题、品牌、侧栏与多源卡片；文件夹单独复制时使用随附的相同主题，无需仿真模块。

默认同时勾选VIS和IR，连接后展示可见光、红外和融合三块画面，亦可只勾选一路。策略、GT叠框、融合占比和显示/保存速率均可在线调整；默认预览5、保存1。关闭GT框不会改变采集来源、帧或保存标签。仿真端输出始终不含框，断连或数据错误清空画面。

双路使用共享 pair_id，并强制在同一游戏 Tick 采集，simulation_time_s 一致；两路独立 frame_number 不必相等。融合在红外网格上显示，额外红外视场保留原图，不将16:9直接拉伸为5:4。原始叠加仅统一FOV/焦距尺度，保留两视轴差；视轴对齐利用实际相机旋转投影，补偿旋转但保留基线的深度相关视差。两种都用于观察对照，并非已完成深度配准或学习型融合。

城市默认ptz-01；VIS/IR独立光心，示例基线12cm，红外俯仰/偏航安装偏差0.1°/0.2°，可在仿真传感器页修改。同刻采集不等于逐像素已对齐；严格同光心融合检查仍可通过Python API mode='strict'使用。

融合下方显示采集时差（两路simulation_time_s之差，毫秒）、本机请求到整对样本返回的取帧耗时、实际基线与共同可见目标的GT中心偏差。中心差是在当前融合模式的IR网格上计算，不是配准准确率；两模态可见范围不同也会影响框中心。取帧耗时不是单向网络延迟或硬件曝光时间，仿真采集时差为0不代表零传输延迟。两张图各自的annotations元数据同时保存采集时差与取帧耗时，不另写pairs文件。

三路画面均支持滚轮缩放、左键拖动、适应画面、1:1像素和独立放大窗口（也可双击打开）；放大窗口实时跟随原源，断连同样清屏。缩放百分比表示实际图像像素与显示像素比例。

显示与保存独立限速，源采样跟随两者较高设置（未保存时只看显示），UI上限10FPS。只保存新样本、不补重复帧；接收线程只保留最新一组待显示图像，避免积压。预览驱动源节拍时显示每个新到样本，防止重复限速因网络/读回抖动丢帧。实测按最近新样本统计，源处理、网络或磁盘较慢时会低于设置值。

勾选保存后写入所选目录，默认 `~/WISEYE-Training`：

```text
WISEYE-Training/
  visible/
    images/       VIS_Mavic3_Clear_city_ptz-01_s<会话>_<组ID>.jpg
    labels/       同名 YOLO .txt，负样本为空文件
    annotations/  同名 JSON，含完整 GT 和采集上下文
  IR/
    images/       IR_Mavic3_Clear_city_ptz-01_s<会话>_<组ID>.jpg
    labels/
    annotations/
```

新格式以传感器/机型/天气开头，后接场景、设备、会话短号、共享组ID，避免连续采集重名。两路分别追加到固定 visible / IR 子目录，已有目录直接复用，不覆盖旧文件，不再逐组建立 samples 子目录。除 VIS/IR 前缀外共享同一文件名后缀，不需要 pairs 对应表；JSON 中保留另一模态的目录和文件名。单路采集也使用相同 visible / IR 结构。

保存前暂存整组图像和标签，完整写入后逐文件发布，JSON 最后发布；普通写入/发布异常会回滚本次新增文件，不动历史数据。固定双目录无法使用原来的整目录原子重命名：突然断电/强杀可能留下未完成组，训练读取会检查另一模态的图像、标签、JSON 及校验和并拒绝坏组。任一路被策略排除则整组不导出；合法负样本保留两图及空标签。

机型来自采集时场景机型快照，负样本仍能命名；多机型用Avata-Mavic3等组合。天气标签来自同一采集Tick的环境参数：clouds/rain/fog非零分别标Clouds/Rain/Fog，全零为Clear；显式时间覆盖时按06:00–18:00标Day，其余标Night。这是仿真配置标签，非实测气象分类；精确参数仍在JSON。旧后端缺失上下文时明确标EnvUnknown/ModelUnknown，不猜测晴天或机型。

历史保存目录仍可读取，不自动删除或改名。训练入口递归识别新整组目录与旧分模态目录，检查配对完整性和校验和；整组数据通过--sensor选择模态，避免无意混用。

无界面采样并导出带框预览：

```powershell
python -m training_client.preview --count 5 --output E:/training-test
```

## GT 语义

- 目标类目前为 `0: drone`，覆盖当前 Fleet 中可渲染无人机，附带 target_id、model_id；不把建筑或云台当无人机。
- 图像、场景深度、各目标独立深度在同一次游戏线程采集内排队，GPU 读回时绑定，不能再用当前状态拼接旧图像。元数据与实际 JPEG 共同缓存。帧主键为 run_id/device_id/sensor_id/frame_number。
- 用全场景深度与目标独立深度比较，得到可见像素；框为可见像素范围，xyxy 像素坐标，右/下边界不包含。不是完整被遮挡物体的推测框。
- 完全遮挡、完全出画、相机背后：不输出对象；计算成功时空 objects 是可训练负样本。
- 部分遮挡：可见像素少于图内目标独立像素。`visible_fraction_in_frame` 是图内可见比例，不是出画前完整目标比例。
- 部分出画：目标独立光栅触及画幅边缘，属于光栅裁切判据，并非精确网格出画面积。
- 被策略或最小像素阈值排除、但图里仍存在可见目标时，记录 ignored_objects，整帧 training_eligible=false；预览显示橙框，暂不导出普通 YOLO 训练集，以免产生错误负样本。
- 深度失败为 annotation_status=unavailable，不能作负样本。透明材质、运动模糊和极小子像素目标的可见性不等同于几何深度，需要后续专项标定。
- 独立深度捕获有额外渲染/读回成本，仅按请求开启。后端默认每路2请求/秒，支持max_fps调整；新工作台请求10，本机实得约4–5。资源复用，同设备同一时刻建议一个采集客户端。

## 接口（JSON Lines v1）

数据网关转发至本机 UE，默认 TCP 50100：

- `camera.gt_configure`: device_id，keep_partial_occlusion / keep_partial_outside严格布尔，min_visible_pixels为1..2073600整数，min_visible_fraction为0..1，max_fps为0.1..20有限数字（默认2）。省略保留，全部校验后原子生效，按云台隔离，仅当前会话；max_fps是限流配置，不是硬件性能保证。
- `camera.sample_request`: device_id、sensor（visible/infrared），返回 sample_token。采集异步，采样限流。
- `camera.sample_frame`: device_id、sensor、sample_token，返回原图 JPEG Base64 和同帧完整标注。尚未完成返回 frame_unavailable，禁用返回 sensor_disabled。
- `camera.sample_pair_request`: device_id，返回双路共享 sample_token；要求 VIS/IR 均已启用，在两路可排队时强制同 Tick 捕获。
- `camera.sample_pair_frame`: device_id、sample_token，返回 pair_id、run_id、simulation_time_s、samples.visible/infrared；两路完整样本及各自 GT。尚未同时完成时返回 frame_unavailable。任一路停用时返回 sensor_disabled，绝不复用旧配对。
- `sim.get_state` / `sim.ping`: 状态与连通性；新状态 training_samples_supported=true。

sample_token 关联一次采集，返回上一任务的最新帧不能当本任务成功。超时或仿真重启后应申请新样本。每源只保留最近一份样本，无历史下载/断点补传保证。

## 手动训练入口

在算法电脑安装适配该机器的 PyTorch，再安装 `requirements-training.txt`。分别采集两个独立仿真会话作为训练集、验证集：

```powershell
python -m training_client.train --train-data E:/data/train --val-data E:/data/val --sensor infrared --output E:/experiments/run01 --weights E:/models/base.pt --epochs 5 --device cpu
```

`--prepare-only` 只验证并生成数据清单；同一仿真 run_id 或完全相同图像不得同时进入训练与验证。有效负样本照常参与训练。实际训练与 GPU 安装不属于本次图像接收验收。
