# UE 工程

打开 `WISEYE/test.uproject`，运行 `/Game/WISEYE-test`。模块仍叫 `test`，构建目标 `testEditor`；不要为改名破坏 `/Script/test` 资源引用。唯一源码在 `WISEYE/Source/test/WiseEyeDemo.h/.cpp`。

已经配置好的地图不需要运行 setup/恢复脚本。构建与按键见根 [README](../README.md)。

```text
PTZ_Camera（固定安装根）
├─ bottom（固定）
└─ WISEYE_Demo
   └─ YawPivot
      ├─ bottom2（仅水平转动）
      └─ PitchPivot
         ├─ camera
         ├─ ptz
         └─ EO_Camera → EO_Capture → /Game/WISEYE/RT_EO
```

云台资产在 `/Game/WISEYE/PTZRecovered`，不要重新指向有导入名称冲突的 `/Game/Mesh*`。原始模型在仓库 Models。
网格前方为局部 +Y、控制光轴 +X，已通过安装旋转对齐。网格欧拉角显示 Roll 不代表控制轴错误。独立 pivot 是机械旋转中心；各网格原点不一定是机械轴。

停止播放，选中 WISEYE_Demo 调整 Flight Origin、Flight Radius、Period、Vertical Amplitude、Manual Speed、Rotor RPM、Yaw/Pitch Rate、Min/Max Pitch、Field Of View。当前保存场景为 24 秒一圈、半径 600 cm、垂向幅度 150 cm；手动速度 300 cm/s、转向 90°/s，Shift 加速；旋翼 600 RPM。云台水平 45°/s、俯仰 30°/s，俯仰 -15°～75°；可见光 1920×1080、红外 640×512，水平 FOV 25°。

I 切换可见光/红外，B 切换红外白热/黑热，P 导出当前模式。两套 SceneCapture 共用光心/姿态和水平 FOV，垂直 FOV 随 16:9 / 5:4 比例变化。RT_EO 保存可见光，Sensors/RT_IR 保存红外；Synthetic IR 材质为 Sensors/M_IR_Minimal。红外采用 Custom Stencil 标记模拟热强度，比较 Custom Depth 与 Scene Depth 保证遮挡；机身、电机和桨叶强度不同，天空/背景独立生成，有弱固定图案噪声。Heat/Noise 参数在 WISEYE_Demo 的 Sensors 分类，运行中调整后调用 RefreshSensors；这些值不是摄氏温度。实现源文件 WiseEyeSensors.cpp。

M 切换自动/手动，WASD 移动，方向键上下升降，Q/E 转向；T 切换真值跟踪/保持当前方向，F 切换旋翼动画。停止旋翼动画不会停止运动学飞行；空格暂停会同时冻结飞行、云台和旋翼。Tab 循环总览、EO 和无人机近景。R 回到保存的航线起点，并保留当前飞行模式、跟踪和旋翼开关。

无人机最大水平跨度约 60 cm，云台高度约 40 cm，底座落地；尺寸是演示设定，不是实物测量。原网格不变，通过装配根节点统一缩放，轴心和相机跟随缩放。无人机根已移到几何中心；本模型局部 +Y 为机头，Model Heading Offset 为 -90°。四组 WISEYE_Rotor_* 包含原始桨毂及两片桨叶，对角同向、相邻反向。

轴心和镜头位置参考 `Config/WISEYE/calibration.json`；这是几何近似，不是实物计量标定。

## 可选编辑器脚本

在 UE 控制台执行 `py "当前仓库路径/ue5/scripts/脚本名.py"`，不能用普通 conda Python 运行。

- play_demo / stop_demo：播放/停止。
- inspect_runtime：PIE 中读取状态并导出图像。
- verify_demo：PIE 中运行 40 秒测试，报告在 Saved/WISEYE/verification.json；更改布局后要更新标定。
- verify_controls：verify_demo 完成后在 PIE 验证手动/自动切换、旋翼启停和轴心稳定、云台保持/恢复、升降与高度限位、暂停/复位和三种视角，报告在 Saved/WISEYE/controls_verification.json。
- configure_controls：首次配置尺寸和旋翼轴心的维护工具，会调整并保存关卡；已配置好的场景不需要重跑。
- restore_ptz：历史原尺度恢复工具，当前 40 cm 云台不能直接运行；恢复须以当前 calibration.json 和已保存关卡为准。
- setup_scene：历史初始化工具，会重配场景；正常启动不要运行。
- validate_portable：命令行检查关键资源和 C++ 类加载。
- validate_controls_scene：重新打开可视编辑器后检查保存的尺寸、四组旋翼及控制参数；World Partition Actor 必须加载，不作为地图 commandlet 运行。
- configure_sensors：首次创建/保存材质、两套 Render Target 和关卡引用；正常启动不需要重跑。
- prepare_sensor_test：停止 PIE 后创建临时遮挡测试物体，不保存；随后播放并运行 verify_sensors，检查分辨率、切换、姿态、变焦并导出白热/黑热/热强度/遮挡样本。停止 PIE 后用 `py "仓库路径/ue5/scripts/prepare_sensor_test.py" --cleanup` 清理测试物体再保存。

PNG 不含界面叠加；元数据时间是导出请求时间，图像为上一完成渲染帧，尚未严格同步。模型比例已按本次演示需求调整，少量分离零件仍可能存在。

## 桌面控制

先构建并在 UE 点击播放，再运行仓库 Start-Desktop.cmd 连接 127.0.0.1:50051。控制桥仅在 PIE/游戏运行期间存在，详见 ../docs/DESKTOP.md 与 PROTOCOL.md。窗口当前获取 PNG 快照，实时流待实现。
