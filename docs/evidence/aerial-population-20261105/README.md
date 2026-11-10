# 航拍与自动人车验收

版本说明：本目录是 2026-11-05 的历史验收，保留当时范围与失败记录。v1.1.0 后续完整包与大小城市 Shipping 验证另见 [分发证据](../distribution-20261110/summary.json)，不将后续结果反写成这里已执行的测试。

- `aerial-core-tests.log.txt`：129核心测试通过（含7原生JSBSim测试）。
- `aerial-qt-tests.log.txt`：23项Qt组合回归通过。
- `build-aerial-population.log.txt`：最终原生Editor编译通过，含航拍隐藏放置草稿。
- `small-city-baseline.json`：较早小城完整成功记录，含实际起降、三个航拍视角、人车关闭和密度切换。
- `small-city-and-large-city-generator-failure.json`：后续完整验证的原始失败记录，小城所有步骤完成（含第二架固定翼相机、非法参数拒绝、空闲释放），但大城生成器缺少实例生成配置而超时。不得把此报告当全流程通过。最终降落状态快照ready，转速约125RPM处于收尾衰减阶段；未声称该快照为RPM全零。
- `asset-prepare.json` / `asset-prepare.log.txt`：修复后两张地图的生成器配置检查，大城车辆/停车各1组、行人4组。
- `report.json`：**修复后的地图专项通过记录**，scope=scenes-only；大城75/75/150，车辆和行人实际移动，机载通道取图；切回小城30/30/60，相机FOV85、pitch−90和密度0.1从文件恢复；所属测试进程已退出。该专项不重复起飞。
- PNG：小城实际起飞后的前视、斜视、下视与设置界面。`large-city-aerial.jpg`为大城停机时相机原始帧，安装点受地面遮挡，只证明通道可取图，**不是大城空中画面**。
- `source-build-sync.json` / `asset-sync.json`：原生源码、配置及12个本地授权地图Actor包SHA核对。
- `normal-fleet-comparison.json`：日常两地图Fleet与测试开始前复制的隔离文件一致。

测试入口为 `tests/verify_aerial_population_live.py`，必须指定独立 `WISEYE_DATA_DIR`，路径需含 `aerial-population-test-data`。默认执行完整流程；`WISEYE_OBSERVATION_SCENES_ONLY=1`只复测大小城生成、移动和配置恢复，依赖先前完整步骤已保存的隔离小城相机/密度配置。脚本由Qt RuntimeManager启动和清理所属会话。

中间失败用于记录修复原因；最终结果按上述分项范围解释，没有完成Shipping或持续高密度性能验收。
