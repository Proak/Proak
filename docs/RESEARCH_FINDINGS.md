# 开源研究与负面反馈（检索日期 2026-11-01）

## 可复用工作流
| 项目 | URL | 有价值的部分 | 不应照搬 |
|---|---|---|---|
| Claude-Code-Game-Studios | https://github.com/Donchitos/Claude-Code-Game-Studios | 部门分工、门禁、截图实证、整套命令模板 | 大量角色和文档不能保证好玩；其自述测试中重文档流程反而输掉盲测 |
| ArcadeRelay | https://github.com/takeshijuan/arcade-relay | 漏斗式分工、三个引擎、艺术/代码/QA分离、模型成本路由 | 实验项目；不是已验证3A生产系统 |
| Everything Game Dev Code | https://github.com/MRCalderon3D/everything-game-dev-code | 跨Claude/Codex的规则、引擎隔离、Git hooks | 不可全部技能自动激活造成上下文/维护压力 |
| Claude Code官方 | https://support.claude.com/en/articles/14554000-claude-code-power-user-tips | 3–5 worktrees 并发、subagents、hooks、可复用skills | worktree≠共享UE编辑器并行写安全 |
| Anthropic Skills库 | https://github.com/anthropics/skills | 具备验收案例的技能化Prompt，baseline与技能比较 | 不要盲信Prompt产物，应验证行为 |
| Blender MCP | https://github.com/ahujasid/mcp-for-blender | Blender自然语言控制与直接模型操作 | 第三方插件运行前审查权限，实际品质需渲染验证 |
| UE5.8 官方实验MCP | https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor | 官方编辑器MCP、自动测试、工具扩展 | 实验功能未齐全；本地无鉴权接口不要暴露公网；工具调用序列化 |
| Unreal自动测试 | https://dev.epicgames.com/documentation/unreal-engine/automation-test-framework-in-unreal-engine | Functional/Smoke/Stress/Screenshot Comparison | 自动通过不能证明恐怖节奏、交互体验优质 |
| Gauntlet | https://dev.epicgames.com/documentation/unreal-engine/gauntlet-automation-framework-in-unreal-engine | 打包游戏会话测试/构建测试 | 需要真实安装引擎和编译环境 |

## 用户反馈（轶事，不能当作代表性数据）
- https://www.reddit.com/r/gamedev/comments/1q043ym/how_vibe_coding_lead_to_my_projects_downfall/ ：长大脚本、耦合、修一个错误产生另一个错误、开发者不理解代码。
- https://www.reddit.com/r/aigamedev/comments/1tr7z19/6_months_of_development_few_people_say_the_game/ ：认真打磨的AI辅助游戏仍面临感知标签与信任问题。
- https://www.theguardian.com/games/2025/jun/26/video-game-developers-using-ai-even-when-they-arent-stamina-zero ：玩家对AI风格敏感、也可能误判非AI作品。
- https://www.reddit.com/r/aigamedev/comments/1uml7ja/is_my_ai_game_dev_workflow_actually_terrible_or/ ：短周期AI工具在较小项目可能有效，但个人自述不能证明大型恐怖游戏可量产。

## 我们的对策
从众多 Agent 中抽取小型工作室，**一个一体化创作人 + 分离制作执行与敌对审查**。固定风格规则，模块边界，真实录像，未引导试玩；去泛化不是隐藏AI使用，而是避免空洞素材、可识别克隆、无因果剧情、无记忆角色、不完整交互。Steam的AI内容申报按照现行内容问卷执行：https://partner.steamgames.com/doc/gettingstarted/contentsurvey
