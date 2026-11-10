# 构建、分发与升级 · v1.1.0

## 本轮产物

| 产物 | 获取与运行 |
|---|---|
| `WISEYE-Plugin-v1.1.0-UE5.8-Win64.zip` | [GitHub Release](https://github.com/Ws-3/WISEYE-Studio/releases/tag/v1.1.0)，源码插件及宿主兼容资源安装器；约 529 MiB |
| `WISEYE-Full-20261110.zip` | 本地 builds/distributions，约 27.3 GiB；完整解压后运行 WISEYE/WISEYE.exe，未上传本次 GitHub Release |
| `releases/20261110-164135-City-Shipping` | 完整包展开目录，包含仿真、训练、UE 运行时、大小城市和流工具 |

插件包不包含 City Sample 和桌面 Python 环境，需要 UE 5.8 C++ 宿主及源码客户端；安装步骤见[插件指南](PLUGIN_DISTRIBUTION.md)。完整包运行不需 UE 编辑器、VS 或 Python，仍需 Windows x64、DX12/SM6 驱动及 VC++ x64 运行库。自定义宿主已通过 Shipping 编译，尚未完成完整 Cook 后实跑。

## 从源码构建

先完成[安装与原生依赖准备](INSTALLATION.md)，关闭占用工程的仿真/编辑器。在仓库根目录执行：

```powershell
# 从唯一原生源码导出，无城市依赖进入 SDK
.\scripts\Build-Distribution.ps1 -Kind Plugin -OutputDirectory 'D:\Output\WISEYE-Plugin-v1.1.0'

# 完整 Shipping；默认小城，加开关同时包含大城
.\scripts\Build-Distribution.ps1 -Kind Full -Configuration Shipping -IncludeBigCity -EngineRoot 'C:\Program Files\Epic Games\UE_5.8'
```

Full 串行执行 Game → Cook/Stage → Desktop → Assemble，输出 builds/staged 与 releases 新版本目录。支持显式 `-Python` 选择已配置环境；`-IterativeCook` 仅用于已具备有效 Cook 产物的增量开发，不代替首次完整验收。不要并发两套 Cook 或在内存吃紧时同时加载大城。

归档 `packaging/archive_release.py --release <展开目录> --output <目标.zip>` 会先逐文件校验 SHA，再写 ZIP64、验证 CRC 并输出 ZIP 哈希；UE IoStore 已压缩，完整包外层采用 Store。校验命令：

```powershell
Get-FileHash 'D:\Downloads\WISEYE-Plugin-v1.1.0-UE5.8-Win64.zip' -Algorithm SHA256
```

## 实际验证与已知问题

最终 Cook 31,925 个包、UAT ExitCode=0；完整目录 1,666 文件，checksums.json 覆盖其余 1,665 文件。大小城市冻结飞控/UE 验证通过，含双光、观察画面、云台、点云、起飞/手动爬升/降落；仿真和训练冻结界面单独启动通过。短时功能测试不是全城、多机或持续帧率承诺。

第三方 `M_Crowd_Head_v2` 的 Nanite 计算着色器超过 SRV 上限 65/64，Cook 使用回退材质，可能影响部分人物头部；既有 Mass CustomData ensure 等未宣称修复。尚未完成干净 Windows 和其他 GPU 验收。详[本轮实施记录](DISTRIBUTION_IMPLEMENTATION_20261110.md)及[发行说明](releases/v1.1.0.md)。

## 更新和发布

当前没有在线更新器或签名安装器。人工升级：先停止飞行并关闭程序，备份 UserData，将新完整包解压到新目录，再迁入兼容配置；不要覆盖正在运行的文件。插件安装器会拒绝不同内容的既有文件，宿主升级需备份并预检，未实现托管原地升级。

后续可拆成桌面、UE 原生、场景资源三个版本通道；仅改桌面逻辑可做小更新，改 C++ 或 cooked 资源需要更新对应 UE 文件。本轮未实现差分下载、签名验证或自动回滚，不应写成已有功能。

本次只发布插件 ZIP 和校验文件，完整包另行托管；第三方城市等再分发许可应在公开提供完整包前逐项核对。历史 v1.0.0 与旧便携包记录保留其日期，不作为当前构建状态。
