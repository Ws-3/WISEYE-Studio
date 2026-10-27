# 清理核查（2026-10-26）

本轮实际释放：0字节。批量路径和固定目录递归删除均被自动审批审查拒绝，未绕过审查或执行替代删除。以下为已核对的可再生成候选，不代表已删除。

| 位置 | 可清理GiB |
|---|---|
| F: | 5.821 |
| E: | 107.542 |

保留：F盘已校验完整ZIP、E盘001704最终验收运行目录、所有Content与ExternalActors、模型/权重/实验数据、用户Fleet/航线、构建Python依赖、E盘有效Cooked与DDC。旧E原工程及CitySample原项目未列入自动清理。

清理暂存只能减少开发占用，不会自动减小16.864GiB分发包。要减分发包应先统计IoStore容器、引用链、贴图平台尺寸及实际关卡依赖，制作精简内容配置并重新Cook验收；不能直接删除城市源资产。

| 已核对候选 | GiB |
|---|---|
| `F:\WISEYE-Studio\builds\desktop` | 0.096 |
| `F:\WISEYE-Studio\builds\pyinstaller` | 0.024 |
| `F:\WISEYE-Studio\builds\smoke-data` | 0.000 |
| `F:\WISEYE-Studio\ue5\WISEYE\Saved\Cooked` | 1.190 |
| `F:\WISEYE-Studio\ue5\WISEYE\Saved\ShaderDebugInfo` | 0.003 |
| `F:\WISEYE-Studio\ue5\WISEYE\Saved\Shaders` | 0.175 |
| `F:\WISEYE-Studio\ue5\WISEYE\Intermediate` | 4.332 |
| `E:\Projects\WISEYE-BuildWorkspace\builds\distribution` | 16.864 |
| `E:\Projects\WISEYE-BuildWorkspace\builds\staged` | 34.968 |
| `E:\Projects\WISEYE-BuildWorkspace\releases\20261022-233112-Base-Development` | 1.767 |
| `E:\Projects\WISEYE-BuildWorkspace\releases\20261022-233243-Base-Development` | 1.767 |
| `E:\Projects\WISEYE-BuildWorkspace\releases\20261022-234233-Base-Development` | 1.817 |
| `E:\Projects\WISEYE-BuildWorkspace\releases\20261022-235803-All-Development` | 17.089 |
| `E:\Projects\WISEYE-BuildWorkspace\releases\WISEYE 城市版 20261023-000219-All-Shipping` | 16.864 |
| `E:\Projects\WISEYE-BuildWorkspace\ue5\WISEYE\Saved\StagedBuilds` | 16.404 |
