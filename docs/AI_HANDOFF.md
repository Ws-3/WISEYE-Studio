# WISEYE 当前交接（2026-10-14）

先读根 README、AGENTS 和长期计划，检查 git status。工程为本仓库 ue5/WISEYE/test.uproject，地图 /Game/WISEYE-test，唯一 UE 源码 ue5/WISEYE/Source/test；桌面源码 apps/desktop_app 与 core。保留 test 模块和 testEditor 目标。

## 已完成与运行

- 本机成功运行昨天完整工程；UE 5.8.3、VS 2022/MSVC 14.44.35229、SDK 10.0.26100.0、Intel Arc B580。经用户授权升级 VC++ x64 至 14.50.35719，安装提示重启，未自动重启，实际运行通过。
- 无人机跨度 60 cm、云台高 40 cm；自动航线/键盘手动飞行、四组旋翼、云台跟踪/保持。bottom 固定、bottom2 水平转、camera 与 ptz 共用俯仰。
- 可见光 1920×1080、IR 640×512，双 Capture/Render Target，共光心/水平 FOV、不同垂直 FOV。IR 以部件模拟热强度生成，有白热/黑热及遮挡。
- PySide6 桌面主窗口、本机 JSON Lines TCP 控制桥、状态轮询、暂停/继续/复位、飞行模式、跟踪、旋翼、模态/调色板/FOV、原生 PNG 快照显示。
- 开始时 pull --ff-only，双击 Start-WISEYE.cmd，UE 点击播放，再 Start-Desktop.cmd 连接 127.0.0.1:50051。完整配置见 DESKTOP.md；协议见 PROTOCOL.md；人工上传下载见 GIT_WORKFLOW.md。

本机仓库 E:/Projects/WISEYE-Studio，UE E:/Programs/UE_5.8；机器路径在忽略的 scripts/engine-root.local.txt。桌面 .venv 复用已安装 PySide6 6.11.0 的 Python 3.14.6；未更改既有 conda WISEYE 训练环境。新机器自行创建 venv 并安装 requirements。

## 验收与证据

C++ 构建成功，真实 PIE 40 秒/79 样本验证通过；14 项控制检查及保存关闭重开后的布局验证通过。双模态尺寸、灰度、不透明 alpha、参数响应、白黑反转、遮挡通过；测试遮挡物已清理并保存。
桌面真实 UE 集成 10 项通过，包括连接/轮询、时间暂停恢复、跟踪/旋翼、两种原生快照/FOV、TCP 分段合并及错误、断开重连、超时期间 GUI 保持响应；协议单元测试 4 项通过。证据在 docs/evidence，原始实验输出保留于 ue5/WISEYE/Saved/WISEYE。

## 边界与后续

当前是真值指向和运动学演示，无 YOLO、动力学/碰撞、物理红外测温或打包程序。桌面图像为按需快照，尚无实时视频或跨机图像通道；PNG 渲染帧与请求时间未精确同步。几何尺寸与轴心是演示近似。
下一步优先做持续图像通道与帧时间/性能监测，再接单帧视觉检测和闭环。保留已确认场景；旧 setup_scene.py/restore_ptz.py 恢复旧尺度，不要直接运行覆盖当前布局。

World Partition 外部 Actor/对象必须与源码一起提交，不上传 Saved/logs/runtime/.venv 或凭据。用户 papers 保持原状。今天已明确授权整理、上传 GitHub 和删除不必要备份日志；具体上传和清理结果见 WORKLOG_2026-10-14.md。历史阶段状态以本文件当前描述为准。
