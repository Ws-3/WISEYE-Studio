# 红外真实／仿真对照基准（初版）

只衡量解码后的 8 位显示图像；不是温度误差、物理 SNR 或检测精度。真实与仿真不是同一地点，不计算 SSIM/PSNR。

| 视角/来源/条件/极性 | 帧数 | 全图灰度中位数 | 亮像素≥204 | 路面ROI帧数 | 路面灰度中位数 | 路面标准差 |
|---|---:|---:|---:|---:|---:|---:|
| aerial/real/HIT-UAV/day/white_hot | 16 | 131.0 | 2.3% | 6 | 171.5 | 18.28 |
| aerial/real/HIT-UAV/night/white_hot | 16 | 127.5 | 0.5% | 6 | 168.0 | 13.97 |
| gimbal/real/Halmstad/day_user_report/white_hot | 16 | 99.5 | 6.3% | 0 | — | — |
| gimbal/real/CESE/day_user_report/white_hot | 16 | 76.5 | 0.8% | 0 | — | — |
| aerial/sim/WISEYE-20261107/day/white_hot | 1 | 155.0 | 0.0% | 1 | 191.0 | 0.57 |
| gimbal/sim/WISEYE-20261031-HISTORICAL/day/white_hot | 1 | 112.0 | 0.0% | 0 | — | — |

## 真实目标对比代理（整框，来源类别编号各自独立）

| 分组 | 有效框 | 宽×高中位数 / px | 框内−环带灰度中位差 / DN |
|---|---:|---:|---:|
| aerial/real/HIT-UAV/day/white_hot/class-0 | 71 | 13.0×18.0 | 10.0 |
| aerial/real/HIT-UAV/day/white_hot/class-1 | 27 | 45.0×64.0 | -8.8 |
| aerial/real/HIT-UAV/day/white_hot/class-2 | 24 | 29.0×21.5 | 4.1 |
| aerial/real/HIT-UAV/night/white_hot/class-0 | 57 | 13.0×16.0 | 38.0 |
| aerial/real/HIT-UAV/night/white_hot/class-1 | 60 | 55.5×33.0 | -22.3 |
| aerial/real/HIT-UAV/night/white_hot/class-2 | 23 | 15.0×17.0 | -16.4 |
| gimbal/real/Halmstad/day_user_report/white_hot/class-0 | 15 | 17.0×13.0 | 19.1 |
| gimbal/real/CESE/day_user_report/white_hot/class-0 | 16 | 33.5×17.5 | 18.3 |

分组统计先按每帧计算，再取帧间中位数；不同分辨率不以像素数量加权。文件名中的 HIT 飞行参数是采集分层，不是已证明独立的视频序列。

## 限制

- 这是小样本显示域基准，不是完整数据集评测、辐射定标或论文最终实验。
- 真实/仿真场景、路面材料、天气与相机不同；路面包含道路及停车场铺装，手工ROI并非完美语义分割。
- HIT按官方文件名解释日夜、高度和俯视角；原图为官方训练子集，不使用官方测试集调参。
- HIT极性按样本外观假定白热，缺少辐射原始值；Halmstad/CESE日间依据用户说明，尚无逐序列时间元数据。
- 地面设备用本机Halmstad/CESE红外训练子集；转换框未逐帧人工复核，空标签不作为已确认无目标。
- 云台仿真图是2026-10-31历史快照，只有背景且无真值框，不宣称已完成当前版本无人机目标对照。
- 当前只有一张航拍仿真路面样本，不能代表所有高度、地图、材质和昼夜。未测夜间仿真。
- 目标对比为整框与周边环带的灰度代理，不是掩模目标、物理SNR、NETD或检测性能；不跨视角/极性/昼夜计算分布距离。
- 参考原图、含本地原图的联系表留在忽略的builds目录；不得把来源不明或未核对许可的本地数据直接发布。
