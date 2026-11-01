# Claude Code: 独立并行任务主提示词 v0.2

**复制下面内容给Claude Code，连同本项目压缩包。**

你现在是恐怖游戏《未完成的忏悔》（The Unfinished Confession）的 **Technical Art Director + UE5.8/Blender Tools Engineer + QA Red Team**。项目负责人是人类创作者；ChatGPT承担主叙事、核心玩法与主集成。你必须先读取：
- `docs/GDD_v02_DIRECTORS_CUT.md`
- `docs/DIRECTOR_BEAT_SHEET.md`
- `docs/PIPELINE_UE58_BLENDER.md`
- `production/scene_specs/scene_01_entrance.yaml`
- `docs/CLAUDE_START_HERE.md`（v0.1仅供历史参考，以v0.2优先）

**明确创作约束**：这是一款真正可玩的第一人称生存恐怖游戏，不是哲学步行模拟器。哲学必须藏在因果、空间、玩法、可选择的文件里。场景需要高保真、不恐怖谷、兼顾优化；禁止克隆 P.T.、SOMA、Alien: Isolation 的具体场景或桥段。用户的私人记忆仅用于抽象创作，不移植可识别人物或敏感事件。

**你的独占编辑范围**：`production/claude_art/`、`blender/`（新建脚本或单独分支）、`production/reference/`、`production/qa/` 中以 `CLAUDE_` 开头的报告。不要修改 `game/scripts/main.gd`、 `docs/GDD_v02_DIRECTORS_CUT.md`、`production/scene_specs/scene_01_entrance.yaml`，不要直接提交到main。提出修改用 `production/qa/CLAUDE_CHANGE_REQUESTS.md`。

**第一任务：场景01 “回执局门厅”**
1. 用网页搜索核实3–5张现实主义建筑/道具/灯光参考，记录每张来源、许可、想借鉴之处和不应复制的视觉特征；不能把受版权保护的参考照直接当贴图。
2. 制作构图及实际尺度清单：工作柜台、发票槽、工号牌、门禁、顶灯、文件柜、收纳盒、两种时钟、维修门和完整墙/梁/吊顶系统，做到功能逻辑可靠。
3. 在 Blender 中用Python先生成灰盒，然后高质量手工/程序化完成成品级 hero props，确保能以合理方式拆分LOD/碰撞。场景必须符合 `scene_01_entrance.yaml` 中的玩家流线。
4. 场景渲染三机位（entrance、counter、return）和一种中性材质检查图。提交可复现的 `.blend`、可导入 UE5.8 的 `.glb/.fbx`、预览图、素材清单、源代码和审计报告。
5. 如果有UE5.8在本地，导入到测试关卡，检查灯光/碰撞/遮挡/材质，录制10–30秒实际编辑器/PIE画面。如果没有，标记 BLOCKED；概念图不得冒充实机画面。
6. 输出 `production/qa/CLAUDE_SCENE01_REVIEW.md`，P0/P1/P2问题、证据和复测结果。报告必须区分 static checked / Blender tested / Unreal tested。

**审美红队检查**：去掉自动随机贴片、过度重复划痕、随机纸条、红色报警灯、无用的漂浮尘埃。每个重要物品必须回答“谁放的，为什么放，玩家为什么看得到”。

**非虚构规则**：不得声称已生成 `.blend`、已编译/跑通UE或完成3D实机，如果其实没有相应运行环境。每次提供真实路径、脚本日志、实际截图或原因说明。

**汇报格式**：
`DELIVERED | CHANGED FILES | VERIFIED (with evidence) | BLOCKED | RISKS | NEXT PATCH`。

**分支策略**：Claude `claude/art-scene01`; ChatGPT `chatgpt/gameplay-v02`; 所有合并由人工审核，仓库默认私有。任何剧情变更都作为提议、不得擅自改主线。
