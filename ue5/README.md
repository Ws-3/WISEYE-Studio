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

停止播放，选中 WISEYE_Demo 调整 Flight Origin、Flight Radius、Period、Yaw Rate、Pitch Rate、Min/Max Pitch、Field Of View。默认 36 秒一圈、半径 4000 cm、垂向幅度 450 cm；水平 45°/s、俯仰 30°/s；俯仰 -15°～75°；1280×720、FOV 45°。

轴心和镜头位置参考 `Config/WISEYE/calibration.json`；这是几何近似，不是实物计量标定。

## 可选编辑器脚本

在 UE 控制台执行 `py "当前仓库路径/ue5/scripts/脚本名.py"`，不能用普通 conda Python 运行。

- play_demo / stop_demo：播放/停止。
- inspect_runtime：PIE 中读取状态并导出图像。
- verify_demo：PIE 中运行 40 秒测试，报告在 Saved/WISEYE/verification.json；更改布局后要更新标定。
- restore_ptz：仅云台损坏时手动运行，按保存坐标恢复四部件；资源已入库，不依赖备份。需要已有 PTZ_Camera 和 WISEYE_Demo。
- setup_scene：历史初始化工具，会重配场景；正常启动不要运行。
- validate_portable：命令行检查关键资源和 C++ 类加载。

PNG 不含界面叠加；元数据时间是导出请求时间，图像为上一完成渲染帧，尚未严格同步。模型比例和少量分离零件问题保留，没有在迁移中擅自改变用户确认的效果。
