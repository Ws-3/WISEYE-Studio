# WISEYE Studio（智瞳）

<div align="center">
  <img src="LOGO.jpg" alt="WISEYE Studio Logo" width="200"/>
  
  **智瞳——无人机光电仿真与智能感知平台**
  
  *面向无人机目标感知的三维光电仿真、云台控制与智能跟踪验证平台*
</div>

---

## 🎯 项目定位

**WISEYE Studio** 是一个面向无人机光电仿真与视觉算法验证的桌面软件平台，重点解决：
- 🎮 **三维仿真环境** - 基于 Unreal Engine 5 的场景、目标、云台与光电相机仿真
- 🔭 **云台精确控制** - 角度/角速度限制、相机变焦、状态查询
- 🤖 **智能目标检测与跟踪** - 接入 YOLO 等检测模型，实现自动指向与目标跟踪
- 📊 **实验管理与数据生成** - 自动生成 YOLO 格式真值标签、困难样本采集、实验复现

## 🏗️ 系统架构

采用三进程解耦架构：

| 进程 | 技术栈 | 职责 |
|------|--------|------|
| **desktop_app** | Python + PySide6 | 桌面主界面、参数配置、日志、实验管理 |
| **ue_simulator** | UE5 (C++ + Blueprint) | 三维场景、目标运动、云台相机、图像渲染输出 |
| **vision_worker** | Python + YOLO | 目标检测、跟踪、推理性能统计 |

## 📁 仓库结构

```
WISEYE-Studio/
├── README.md                    # 本文件
├── LOGO.jpg                     # 项目Logo
├── WISEYE_ProjectPlan.md        # 详细项目计划与交接文档
├── .gitignore
├── requirements.txt
├── apps/
│   └── desktop_app/             # 桌面主程序
├── core/                        # 核心模型、协议、配置
├── adapters/                    # 仿真适配器
├── services/                    # 业务服务（云台、相机、视觉、数据集、实验）
├── configs/                     # 配置文件
├── ue5/                         # UE5 项目
├── data/                        # 本地数据（不入库）
├── logs/                        # 运行日志（不入库）
└── tests/                       # 测试代码
```

## 🚀 快速开始

> **当前状态**：项目处于 **M0 环境与仓库盘点** 阶段，详见 [项目计划文档](WISEYE_ProjectPlan.md)

### 环境要求
- Windows 10/11
- Python 3.12+
- Unreal Engine 5.3+
- NVIDIA GPU (推荐 RTX 5060 8GB+)

### 安装步骤
```bash
# 1. 克隆仓库
git clone https://github.com/Ws-3/WISEYE-Studio.git
cd WISEYE-Studio

# 2. 创建并激活 conda 环境
conda create -n WISEYE python=3.12 -y
conda activate WISEYE

# 3. 安装 Python 依赖
pip install -r requirements.txt

# 4. 启动桌面应用（开发中）
python -m apps.desktop_app.main
```

## 📋 里程碑规划

| 里程碑 | 状态 | 核心目标 |
|--------|------|----------|
| **M0** | 🟡 进行中 | 环境与仓库盘点、确认技术栈版本 |
| **M1** | ⏳ 待开始 | PySide6 桌面 UI 基础框架 |
| **M2** | ⏳ 待开始 | 通信协议与 UE5 Bridge |
| **M3** | ⏳ 待开始 | 相机图像通道与实时显示 |
| **M4** | ⏳ 待开始 | YOLO 检测接入与可视化 |
| **M5** | ⏳ 待开始 | 自动指向与目标跟踪 |
| **M6** | ⏳ 待开始 | 真值标签生成与实验管理 |
| **M7** | ⏳ 待开始 | 系统完善与交付 |

详细任务清单见 [WISEYE_ProjectPlan.md](WISEYE_ProjectPlan.md)

## 🤝 贡献指南

本项目采用 **AI 协作开发模式**，每次会话前需阅读 `WISEYE_ProjectPlan.md`，遵循文档中的协作规则：
1. 先检查现状，再增量实现
2. 先建立可验证的最小闭环
3. 任何未经实际验证的功能不得标记为完成
4. 每次结束前必须更新计划文档

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📞 联系方式

- 项目主页：https://github.com/Ws-3/WISEYE-Studio
- 问题反馈：[GitHub Issues](https://github.com/Ws-3/WISEYE-Studio/issues)

---

<div align="center">
  <sub>Built with ❤️ for UAV Electro-Optical Simulation & Intelligent Perception</sub>
</div>