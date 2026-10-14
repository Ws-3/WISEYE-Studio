# 迁移检查（2026-10-14）

完整工程提交 `1b3db2213cde71853c9faf0b819f4979d76b83d6` 已推送 GitHub main，`git ls-remote` 返回相同提交号。核对后删除原机 Backup-Content/Backup-Config，释放 70,598,834 字节；没有删除原工程、Models 或实验输出。

- 将原工程的完整 Content、Config、Source 和 uproject 收入 `ue5/WISEYE`；原始 Models 一起收录。
- 逐文件 SHA256 比较：迁移后的 Content 与已保存的原工程完全一致。Models + Content 共 570 个文件、131,781,547 字节；完整清单见 `evidence/asset_manifest.json`。
- 在新仓库路径执行 `scripts/Start-WISEYE.ps1 -EngineRoot D:\Projects\UE_5.8 -BuildOnly`：Succeeded。此前该路径没有 Binaries/Intermediate，完成了独立构建；编译有 HUD 常量 double 转 float 的非阻塞警告。
- 在复制后的工程执行 UE Python commandlet + NullRHI：成功加载地图、Render Target、四个独立恢复云台网格及 `/Script/test.WiseEyeDemo`、`WiseEyeGameMode` 类，退出码 0。
- 普通 Git 二进制存储，不依赖 LFS。默认地图、5.8 引擎关联及启动路径已处理。
- 未在另一台实体电脑运行，未打包 Shipping；新电脑仍需安装兼容的 UE 5.8 和 VS C++ 工具链。资源加载检查不是新的图像渲染验收。
- 历史可视仿真和云台用户验收情况详见 AI_HANDOFF，不混同于本次迁移测试。

复现资源检查（将路径替换为本机实际路径）：

```powershell
& "<UE>/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "<repo>/ue5/WISEYE/test.uproject" -run=pythonscript -script="<repo>/ue5/scripts/validate_portable.py" -unattended -NullRHI -nosplash
```

报告在工程 Saved/WISEYE/portable_validation.json。构建缓存、日志和个人配置不提交。

## 2026-10-14 桌面与最新工程

今日新增 PySide6 主窗口、TCP 控制桥及双模态资源。新机器仍需本机构建 C++，独立创建 .venv 并安装 requirements.txt；不要复制本机环境/编译产物。运行与手工同步分别见 DESKTOP.md、GIT_WORKFLOW.md。今日测试详情见 WORKLOG_2026-10-14.md。
