# 仿真数据输出与独立训练端（2026-10-28）

## 2026-10-29 更新：GT高频测试与统一预览（当前）

训练UI已合并为一套同帧图像/GT管线，单“预览GT框”控制叠框，隐藏仍保存GT及显示同组融合。默认预览5/保存1，UI各0.1–10；本机完整GT约4–5组/s，实际GUI约4.5FPS，仿真约30Tick/s。gt_configure.max_fps新增0.1–20，后端默认2兼容旧客户端，新UI请求10；20是实验配置上限，未达到20实际帧率。93核心/52Qt/Editor及实际运动/保存/隐藏框验证通过。详见GT_RATE_AND_UNIFIED_PREVIEW.md，后续章节中的固定2FPS和双模式说明为历史。

## 2026-10-29 更新：固定模态目录，持续追加（当前）

用户修正目录要求后，新数据固定追加到所选根目录下 visible/{images,labels,annotations} 和 IR/{images,labels,annotations}。不再创建 samples/<组ID>，不生成 pairs。已存在的目录直接复用；双路名称仍为 VIS/IR 前缀 + 完全相同的机型/天气/场景/设备/会话/组ID后缀。schema=3 JSON 使用 counterpart_directory 和 counterpart_image 关联另一模态，训练读取同时兼容历史 schema=2 组目录与原单路目录。

整组先暂存、图像/标签先发布、JSON最后发布；正常写入/发布异常回滚本次新增文件，不覆盖历史数据。两个固定模态目录不能整目录原子提交，断电/强杀后的不完整组由训练读取的完整性/校验和检查拒绝。策略过滤整组跳过、合法负样本空标签逻辑保留。重用之前真实采集的3组JPEG/GT验证新目录与重复保存，证据见 evidence/startup-placement-visible-storage-20261029；不是新可见光效果的实时验收。

## 2026-10-29 前一版：可读命名与整组直接保存（目录已由上节替代）

新采集双路数据保存为samples/<组ID>/images、labels、annotations，同目录两张原图使用VIS/IR前缀与相同后缀，不再生成pairs对应表。命名为传感器_场景机型_天气_场景_设备_会话短号_共享组ID；同一组完整写入暂存目录后整组提交。任一路被训练策略排除时整组不导出，避免半组与错负样本；合法双路负样本仍保存两张图和空标签。

仿真GT快照新增environment与scenario_models/context_source=capture_tick，天气/机型来自采集时数据，负样本也保留机型上下文。weather字符串是配置分类，精确clouds/rain/fog/hour等保留各自JSON。旧后端缺上下文明确Unknown，不使用稍后状态冒充采集时天气。

训练读取递归支持新整组目录及旧目录，--sensor选择visible/infrared，检查另一张图、标签、JSON、配对ID和校验和。旧数据不迁移/删除。本轮未提高GT限流：无GT视频默认20/最多30轮询FPS；同步GT显示/保存默认各1、可选0.1–2。此次隔离本机短测源VIS/IR约9.89/10.38新帧/s，六组GT约1.76组/s；不等于其他场景/硬件的保证。证据docs/evidence/dataset-storage-20261029。

## 最新：融合差异、放大与独立帧率

针对独立双光心相机，工作台新增原始叠加/视轴旋转对齐两种对照，显示仿真采集时差、整对样本取帧耗时、基线与GT中心差。旋转对齐不补偿基线的深度视差；这两个预览模式允许观察错位，旧严格同光心检查保留为mode='strict'。

三路支持滚轮缩放/拖动、适应/1:1及实时放大窗口。显示、保存FPS可在线独立设置0.1–2，源采样随较高者调整；展示实测更新/保存频率，不补重复帧。2 FPS附近的正常限流会可取消地退避重试，避免反复清屏。低显示频率时按显示周期判断过期。

本轮不改UE、相机默认参数、Fleet或入口；仍Start-Training.vbs。验证和截图见docs/evidence/training-inspection-20261028；尚未做深度配准、更高GT采样上限或双物理电脑联调。

## 最新：独立双相机与楼顶单云台

城市默认只保留ptz-01，训练Client/界面默认值已更新。VIS/IR有12cm示例基线及红外0.1°/0.2°俯仰/偏航安装偏差，可在仿真传感器页各自调整。两路采样仍同刻，分别输出实际相机位姿/内参和独立GT，不意味着像素对齐。当前融合只支持同光心同姿态，默认双相机应显示“需深度/标定配准”，保留原始双路显示和保存；未实施跨光心深度配准。新实际楼顶双路、独立GT、停用恢复与负样本验收见[双相机部署](DUAL_CAMERA_ROOFTOP.md)及evidence/dual-camera-rooftop-20261028。下方早期同光心融合记录保留为历史。

## 当前入口与双路融合更新

训练端现在只保留 `training_client/Start-Training.vbs` 一个日常入口。数据服务由仿真飞控进程自动管理，启动仿真即可在 TCP 50100 提供数据，无需单独启动网关。旧两个 cmd 入口已移除。默认同时接收 VIS/IR，工作台复用仿真端主题，分可见光、红外、融合三块画面。

新增 `camera.sample_pair_request/frame` 与能力 `paired_training_samples_supported`。两路共享 token，在同一游戏 Tick 强制采集，返回时间戳相同；帧序号各自累计。融合按相机光心、姿态、FOV 对齐到红外像素网格，只在共同视场叠加，红外权重可调。两路原图/标注分别保存，pairs 清单记录关联，融合图只用于显示。手动训练入口按具体模态目录使用。

当前源码城市已验证自动服务、同刻双路、不同FOV对齐、停用拒绝/恢复、双路负样本、单路兼容、真实接收GUI及VBS单入口。最新证据见 `docs/evidence/training-fusion-20261028`。旧版本记录如下，启动方式以本节为准。

本轮按用户要求，将仿真和算法程序分离。唯一源码仍在 F:/WISEYE-Studio；UE 本机验证使用 E:/Projects/WISEYE-IR-Work 最小衍生构建。仿真端不绘制 GT 框；框仅在新增 training_client 程序中显示。现有 RTSP 和桌面原尺寸预览不改用途。

## 新增内容

- UE：独立场景深度与每架无人机的独立深度采集；按可见像素生成实例框。全部深度与传感器图像在同一游戏线程采集阶段排队，GPU 读回与 JPEG 处理绑定，避免“旧图＋当前目标位置”。按需启动，默认无额外深度采集。
- 数据接口：camera.gt_configure / camera.sample_request / camera.sample_frame。每次请求返回独立 UUID token；按 token 轮询取成套图像、标注、相机参数。状态包含 training_samples_supported。实例 frame_id 包含 run_id、云台、模态和源帧号。
- 标注配置：部分遮挡、部分出画分别决定保留，默认均保留；可设置最小可见像素数、图内可见比例。按云台隔离，非法参数原子拒绝。
- 空对象且计算完整：negative_sample=true，允许训练，导出空 YOLO 标签。计算失败不可作负样本。仍有可见目标被策略过滤时记录 ignored_objects，整帧暂不加入普通 YOLO 数据集，防止错标背景。
- 局域网网关：training_client/gateway.py。默认本机 50100，显式 --bind 0.0.0.0 可供另一台电脑访问。UE 50051 保持本机，网关只放行数据、状态和 GT 策略，拒绝飞控。
- 独立接收界面：training_client/preview.py。接收线程不阻塞 GUI；同帧 GT 叠加、配置选项、样本保存、错误和过期清屏。无界面模式可导出原图与带框预览。
- 手动训练入口：training_client/train.py。独立训练/验证会话、图像校验、包含负样本；可先 --prepare-only。实际训练需算法电脑安装适配的 PyTorch/Ultralytics，本轮不声明模型效果已验证。

完整命令、数据字段与样本约定见 [training_client/README.md](../training_client/README.md)。启动新版仿真后只打开 Start-Training.vbs；另一台电脑无需 UE/AirSim，只复制 training_client 文件夹并安装其 requirements.txt。

## 验证与限制

Editor 构建通过；67 核心单测、20 项相关 Qt 回归、1 项 GT 原生自动化通过。真实城市已验证红外/可见光 GT、部分遮挡/部分出画策略、遮挡空标注、负样本落盘、设备隔离与独立 GUI。结果见 [验证记录](evidence/training-interface-20261028/validation.json)、[实际采样报告](evidence/training-interface-20261028/report.json) 和 [界面截图](evidence/training-interface-20261028/training-preview.png)。实际运行使用隔离 gt-test-data，不修改用户 Fleet 或地图资产；结束时待命、四电机转速为零，自有进程退出。

当前属于低频数据采集原型：界面约 1 Hz，服务每传感器最多接受 2 次采样请求/秒。每次额外渲染全场景深度和各目标独立深度，开销随分辨率、目标数量增加；按模态保留复用资源到会话结束。不是 30 FPS 连续 GT 服务，也没有历史队列/补传保证，当前建议每源一个采集客户端。

框是可见像素外包矩形（xyxy，右下边界不包含），不是不可见部分的推测框。图内可见比例不等于完整目标可见比例；部分出画按独立目标光栅触边判断。透明表面、LOD/抗锯齿边界、运动模糊、1–3 像素目标和大规模多设备需专项测试。初版仅 drone 单类别，保留稳定 target_id 与模型型号，不是全城语义标签。

本机端到端采样与独立 GUI 已测试；两台物理电脑、长期网络负载、实际 YOLO 训练、自动增量训练、模型热切换和新版 Shipping 打包尚未验收。网关当前为可信局域网明文服务，无认证/TLS。不要将旧 Shipping 包当作已包含新接口。
