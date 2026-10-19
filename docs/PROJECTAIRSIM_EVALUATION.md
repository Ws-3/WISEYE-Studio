# Project AirSim 独立接入评估

本轮先验证独立 Blocks 工程，之后才连接 WISEYE。用户已在评估后同意修改独立 AirSim 副本；现有 WISEYE 飞行与云台后端仍未替换。

## 固定版本和隔离环境

- 上游：https://github.com/iamaisim/ProjectAirSim
- commit：`62229cd7c77ad31da7bc8aba8dd6303c564d8ba2`
- 本机测试目录：`D:/Projects/ProjectAirSim-Evaluation`，不是 WISEYE 内置依赖；换电脑需单独克隆并 checkout 此提交。
- 引擎：UE 5.8.3；VS 2022 14.44 工具链；Windows SDK 10.0.26100.0。
- Python：测试目录自己的 `.venv`，Python 3.13.9，安装 `client/python/projectairsim`，没有修改 WISEYE 桌面或训练环境。
- 上游 README、build.cmd、UnrealCompatibility.h 已包含 5.8 支持；部分旧开发文档仍只列 5.2/5.7。支持声明不等于本机飞行验证通过。

## 复现构建

在 WISEYE 根目录运行（替换本机路径）：

```powershell
./scripts/Test-ProjectAirSimBuild.ps1 -AirSimRoot D:/Projects/ProjectAirSim-Evaluation -EngineRoot D:/Projects/UE_5.8 -VisualStudioRoot 'D:/programs/Microsoft/Visual Studio/2022/Community' -Stage SimLibs
./scripts/Test-ProjectAirSimBuild.ps1 -AirSimRoot D:/Projects/ProjectAirSim-Evaluation -EngineRoot D:/Projects/UE_5.8 -VisualStudioRoot 'D:/programs/Microsoft/Visual Studio/2022/Community' -Stage Tests
./scripts/Test-ProjectAirSimBuild.ps1 -AirSimRoot D:/Projects/ProjectAirSim-Evaluation -EngineRoot D:/Projects/UE_5.8 -VisualStudioRoot 'D:/programs/Microsoft/Visual Studio/2022/Community' -Stage Editor
```

包装脚本只设置当前进程环境并在退出时恢复；预设 VSINSTALLDIR 必须以反斜杠结尾，否则 vcvarsall 可能遗漏编译器路径和运行库目录。无需为这个环境问题修改上游源码。

## 验收入口

编辑器插件成功构建后，使用指定 UE 的 UnrealEditor.exe 打开测试目录 `unreal/Blocks/Blocks.uproject`，运行 BlocksMap，再执行：

```powershell
D:/Projects/ProjectAirSim-Evaluation/.venv/Scripts/python.exe scripts/Test-ProjectAirSimFlight.py --airsim-root D:/Projects/ProjectAirSim-Evaluation --output runtime/projectairsim-flight.json --regression
```

脚本仅连接本地测试服务 8989/8990，加载上游 SimpleFlight/FastPhysics 示例。验收起飞、悬停三秒漂移小于一米、三米航点误差小于一米、降落状态，以及 RGB/深度消息收到。消息计数不是图像质量、传感器精度或实时帧率验收。脚本语法检查不代表真实飞行已通过。

## 当前验证

- Release 仿真库：188/188 构建步骤完成。
- Python 客户端：安装与 ProjectAirSimClient/World/Drone 导入通过。
- UE 插件：UE 5.8.3 的 BlocksEditor Development 初次构建 47/47 通过；无需修改 UE 5.8 兼容层。
- 运行：BlocksMap 成功加载，本地 8989/8990 服务正常，SimpleFlight/FastPhysics 无人机能离地、悬停、移动并回到平台。
- 原版严格验收失败：MoveOnPath 用单轮路径推进量判断结束，前视点到达末段后没有把 FunctionCaller 标记完成，导致 Takeoff 实际离地却返回 false；SimpleFlight 仅靠电机输出推断落地，API Land 已确认接地后仍可能报告 Flying。
- 用户同意后，在独立分支 `wiseye/flight-completion-fix` 修复：用真实终点距离和控制器自身 0.5 m 精度判断命令完成；成功 Land 后把已确认的接地结果同步到 SimpleFlight 状态机。没有把 false 强制改成 true。
- 最终严格回归连续两次通过。最终一次：三秒悬停漂移 0.00905 m、三米航点误差 0.49276 m、0.75 m 短航点实际移动 0.26295 m且误差 0.48705 m、超时返回 false、被 Hover 替换的长航点返回 false、降落状态为 Landed；收到 RGB 872、深度 871 条消息。位置误差符合 SimpleFlight 明确的 0.5 m 控制器容差，不是精度保证。
- Release C++ 单元测试 391/391 通过；补丁通过 `git diff --check`。证据为 `docs/evidence/projectairsim_flight_fixed.json`。
- 尚未接入 WISEYE；PX4、其他地图、雷达/激光雷达实际输出均未验收。
- 原始本机日志：`runtime/projectairsim-build-release.log`、`runtime/projectairsim-editor-build.log`、`runtime/projectairsim-python-install.log`，不上传构建缓存。

## 接入边界

独立验收后再规划 WISEYE 的运动后端：保留运动学演示模式，增加动力学模式；每架无人机每次只由一个后端驱动。需要明确 UE 厘米/Z 向上与 AirSim NED 米/Z 向下的转换、仿真时钟、暂停/重置语义，再接云台目标位姿。PX4 SITL、额外传感器和第二张地图属于后续验证，当前不能标记为已完成。

## 修复的迁移方式

独立仓库没有 Git 作者身份，未伪造身份创建提交；五个上游源码文件保持 staged 状态。可迁移补丁已保存为 `third_party/patches/projectairsim-simpleflight-completion.patch`。在固定上游提交的新克隆中运行：

```powershell
git checkout 62229cd7c77ad31da7bc8aba8dd6303c564d8ba2
git apply --check D:/Projects/WISEYE-Studio/third_party/patches/projectairsim-simpleflight-completion.patch
git apply D:/Projects/WISEYE-Studio/third_party/patches/projectairsim-simpleflight-completion.patch
```

应用后按本文顺序运行 SimLibs、Tests、Editor 和 `--regression`。上游更新后若 `git apply --check` 失败，需要重新审查冲突，不能盲目套用。
