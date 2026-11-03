# 无人机夜间灯光

Mavic 3 和 Avata 默认启用自动夜间红绿灯。桌面环境面板开启时间覆盖，设为夜间（例如22点）即可看到；06:00至18:00关闭，18:00至次日06:00开启。恢复场景原始光照时，依据场景主太阳光的朝向判断，不强制把默认12点当成当前时间。

机体左侧红灯、右侧绿灯，四个小型灯珠装在电机/护圈外缘，跟随真实姿态。每1.6秒一轮：红灯双闪、绿灯双闪，中间熄灭。待机也会闪；暂停仿真运动不会冻结提示灯。该灯语与安装点是仿真近似，未复刻厂商原厂灯语。

灯珠使用独立自发光材质，没有投射光/阴影。直径分别0.9cm/0.6cm，亮度参数为视觉效果，未作光度学标定。远距离小于像素时不保证看得见，不人为放大实体目标。可见光图像包含灯光；IR 相机隐藏灯珠，热分类跳过灯珠，保留当前机身/电机/电池热模型。

GT沿用场景深度和独立目标深度。VIS中的有形灯珠进入目标轮廓，后期 Bloom 光晕不算实体轮廓；IR深度继承IR相机的隐藏组件列表，不把光学灯珠计入热像轮廓。保存与接收协议无需新增一条图像通道。

`sim.get_state.devices[]` 的无人机增加 `navigation_lights`：`enabled`、`night`、`red_on`、`green_on`、`lamp_count`、`period_s`。这些是查询时状态，不能据此给有缓存延迟的JPEG逐帧标记闪烁相位。需要时用图像本身判断。当前未新增桌面独立开关；开发者可通过 Actor 的 `NavigationLightsEnabled` 属性关闭。

源码：`WiseEyeDemo.cpp::StepNavigationLights`；材质生成：`ue5/scripts/build_navigation_lights.py`，已接入无人机导入脚本，运行资产位于 `/Game/WISEYE/DroneModels/Common/M_NavigationLamp`，Cook包含整个DroneModels目录。

验证方式（只在自有测试运行中执行，测试会起飞并修改环境/型号）：

```powershell
& builds/python-env/Scripts/python.exe -m tests.verify_navigation_lights_live --output docs/evidence/navigation-lights-20261029/final
```

最终证据及实际测试结果见同目录 `final/report.json` 和交接说明。旧Shipping包尚未重包，新增功能属于当前源码和本机Editor构建。
