# 无人机航拍与自动车辆、行人（2026-11-05）

后续更新：可长按四方向按钮实时调整相机，或直接修改俯仰／朝向；人群骨骼项目设置和加载期告警已修复。见 [航拍朝向与运行提示](AERIAL_AIM_PERFORMANCE_20261105.md)。

本轮完成仿真端的机载可见光相机和地图原生交通、人群控制。训练端保持原有流程；当前新增的是航拍预览与原始单帧保存，尚未把地面人车生成2D GT或接入训练导出。

## 使用

启动仿真并连接后，打开顶部「场景 → 无人机航拍…」。选择无人机，点击「设为主画面」；也可从设备树的「机载航拍」加入预览。每架无人机相机独立，不会因选择相机而切换飞控接管。画面上的「航拍」按钮打开参数，更多菜单可保存原始PNG。现有画面放大、弹窗和缩放继续可用。

- 前视0°、斜视−60°、下视−90°；俯仰范围−90°至20°，相对机头偏航±180°。
- 水平FOV为5°至90°，采样上限1至30Hz，默认15Hz。桌面预览轮询上限20Hz，显示实际收到的新帧率；实际显示还受渲染和机器负载限制，上限设置不等于实得帧率。
- 默认稳定云台保持地平线；取消后跟随机体姿态。示例安装点为机体物理原点下方12cm，隐藏自机及其附属外形。不同真实载荷仍需校准安装位置。
- 相机复制可见光外观与天气后处理。未添加航拍红外、事件或雷达；航拍也不是原来的外部跟随观察视角。
- 只有预览或取图时分配采集资源；停止请求约2秒后释放。额外注册Mass观察者，让人车LOD跟随航拍视角。放置草稿不进入航拍源图。

打开「场景 → 车辆与行人…」，分别启用车辆、行人并设置0至100%密度，点击「应用」实时生效。车辆沿原生道路行驶，行人沿人行路径活动，无需逐个驾驶。车辆开关同时控制本功能生成的行驶和停放车辆；地图固有的静态装饰车辆不受此开关控制。

默认两类均启用、密度25%。100%对应每张地图最多300辆行驶车辆、300辆停放车辆、600名行人的生成预算；50%为150/150/300，10%为30/30/60。预算不等于当前画面可见数量，也不是按平方米定义的物理密度。异步生成完成前显示「正在更新生成预算」，启动阶段需要载入原生人车资源，首次缓存缺失时还会编译纹理和模型。当前车辆预设使用一款轿车，暂未开放车型组合及个体路线编辑。

「应用」只改变本次运行。「保存为本场景默认」保存所有无人机航拍参数及人车设置，随后启动该场景恢复。按场景写入 `UserData/ue5/WISEYE/Config/WISEYE/Observation/<scene>.json`（实际前缀由运行数据目录决定）；不会修改Fleet初始位置。地图切换或断开后，设置窗口必须重新读取实际状态才能应用。

## UE资源和后续构建

源码位于 `E:/Projects/WISEYE`，本机预览构建 `E:/Projects/WISEYE-IR-Work`，UE5.8.4。新增 `WiseEyeAerial.cpp`、`WiseEyePopulation.*`，Mass模块依赖和 `DefaultPlugins.ini` / `DefaultMass.ini` 的原生ZoneGraph、交通、人群配置。

旧地图准备流程把部分Mass生成器标记为EditorOnly，大城甚至删除了生成器。新增 `ue5/scripts/prepare_observation_population.py` 在**WISEYE地图副本**恢复并准备原生生成器、ZoneGraph和路口，设置正确的大小城停车位与信号资产。对缺少实例生成配置的大城，复制已验证的小城预设并在目标Actor下重新创建生成器子对象，防止跨地图悬空引用。仅保存这些副本的外部Actor包，不修改原始CitySample和用户设备放置。12个外部Actor包已同步回源码资源目录。车型限制为轿车，禁用额外挂车生成。

以后重新装配大小城市后，需要对构建工程运行该脚本。旧 `install_city_sample.py` / `install_big_city.py` 会清理生成器，不能只重跑旧脚本就认为人口功能仍然存在。用UE Python commandlet运行，例如：

```powershell
& E:/Programs/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe E:/Projects/WISEYE-IR-Work/test.uproject -run=pythonscript -script=E:/Projects/WISEYE/ue5/scripts/prepare_observation_population.py -unattended -nosplash -nullrhi
```

脚本输出 `Saved/WISEYE/observation-population-prepare.json`。依赖原有CitySample交通、人群、道路资产；本轮未下载新模型，未完成Shipping重新打包，旧发行程序不会自动获得这些功能。

## 接口

50051支持 `aerial.get_state`、`aerial.configure`（device_id选择无人机），以及 `population.get_state`、`population.configure`、`observation.save`。这些控制命令回传完整仿真状态；相机参数在 `devices[].aerial`，人车参数在 `population`。

```json
{"device_id":"uav-01","enabled":true,"stabilized":true,"pitch_deg":-60,"yaw_deg":0,"fov_deg":65,"sample_hz":15}
```

```json
{"vehicles_enabled":true,"vehicle_density":0.25,"pedestrians_enabled":true,"pedestrian_density":0.25}
```

configure字段需完整提供，先校验再修改。`camera.stream_frame` 用 `device_id=uav-01, channel=AERIAL` 获取原生1920×1080 JPEG（缓存quality90），首次未产生帧可重试。该通道目前只走本机RPC预览，不提供RTSP地址，也未添加训练网关通道。

诊断 `population.get_agents` 回传实际Mass实体数量和每类最多256个位置样本，`samples_truncated`提示截断。样本包含run内稳定的 `target_id`（run/type/index/serial）、`class_name=person/vehicle`、UE厘米坐标。它不提供同帧图像同步、遮挡判定或2D框，不能直接当训练标注。

## 验证记录

129项核心测试、23项Qt组合测试通过，UE Editor编译通过。隔离小城实跑验证关闭后实体清零、50%和10%预算、原生车辆和行人位置随时间变化；Mavic实际起飞、爬升、三种航拍视角、独立调FOV与安全降落通过。单次低密度空中状态快照约28.7 UE FPS，仅供本机参考，不是持续性能保证。Editor启动的人车资源加载需要等待，缓存缺失的资源编译期间有明显CPU和内存压力。

独立第二相机、非法配置拒绝和空闲释放已通过。首次大城验证发现新建生成器缺少实例生成配置，修复后专项复测通过：大城75行驶/75停放/150行人，车辆与行人均移动，机载通道出图；回到小城恢复30/30/60及已保存的85° FOV、−90°俯仰。大城取图是在停机状态，安装点接近地面，画面为近地遮挡，不作为空中视野验收；实际飞行三视角验收来自小城。最终地图专项 `report.json` 的scope为scenes-only；较早小城完整成功为small-city-baseline.json，随后含空闲/独立相机检查的运行因大城缺配置失败，原始失败报告与日志保留，不能当全流程通过。所有所属进程已退出。证据位于 `docs/evidence/aerial-population-20261105/`。测试使用独立 `builds/aerial-population-test-data`，日常用户数据未用于写入测试。
