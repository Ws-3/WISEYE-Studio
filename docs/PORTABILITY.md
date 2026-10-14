# 迁移检查（2026-10-14）

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
