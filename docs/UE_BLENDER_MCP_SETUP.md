# UE5.8 / Blender AI 控制接入方案

## Unreal（优先官方实验功能）
- 使用 Unreal Engine 5.8 的 **Unreal MCP** 与 **All Toolsets** 两项插件，来自官方实验性接口。
- 在 Editor Preferences 开启 auto-start，可使用默认 `http://127.0.0.1:8000/mcp`，或者按官方文档配置端口；通过官方命令生成客户端配置（`ModelContextProtocol.GenerateClientConfig`）。
- 该服务默认**无身份认证**，只允许 loopback；**绝不能**配置公网访问/端口转发。所有大规模破坏性的变更前先在 Git 分支保存快照。
- 文档：https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor
- **并发限制**：该接口在 game thread 上序列执行 editor tools；多个AI只能共享队列，不直接同时改同一个世界文件。

## Blender
- 可选开源 `ahujasid/mcp-for-blender`，但必须审查其扩展的权限与更新；非官方插件：https://github.com/ahujasid/mcp-for-blender
- 核心模型生产仍以 `blender -b file.blend --python tools/blender_mesh_audit.py` 的**确定性**检查为基本线。MCP负责操作者意图、执行和渲染图回传，不替代独立审美审查。
- 始终输出可复建源文件 `.blend`、导出 `.glb`、三视角实际渲染以及单位/UV/碰撞/面数报告。

## Unreal QA
- Automation Framework（包含 Functional/Smoke/Content Stress/Screenshot Comparison）官方：https://dev.epicgames.com/documentation/unreal-engine/automation-test-framework-in-unreal-engine
- Screenshot Comparison：https://dev.epicgames.com/documentation/unreal-engine/screenshot-comparison-tool-in-unreal-engine
- Gauntlet：https://dev.epicgames.com/documentation/unreal-engine/gauntlet-automation-framework-in-unreal-engine
- Unreal Python仅可用于编辑器资产管线，**不可**当作打包游戏运行时代码：https://dev.epicgames.com/documentation/unreal-engine/scripting-the-unreal-editor-using-python

## 连接确认
只有本地实际执行截图/导入/PIE/构建后才能在质量报告填写“引擎测试 PASS”。当前版本标记：UNREAL=BLOCKED (not installed in generation environment); BLENDER=BLOCKED; PLAYER_TEST=NOT_RUN。
