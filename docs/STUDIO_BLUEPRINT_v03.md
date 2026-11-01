# AI Studio 组织、权限与执行顺序 v0.3

## 负责人结构
- **Human Creator / Game Director（最终决策）**：审美、故事核心、玩家体验、预算、发行。AI不得替你自动批准片段质量。
- **ChatGPT — Narrative Systems Editor / Producer-Reviewer**：维护剧情因果、关卡节拍、开发规格、横向审稿；不得向你声称能直接后台操作 Claude。
- **Claude Code — Build & Integration Lead**：只在你本机已连接Git、Blender和UE之后操作，配置开发流水线；不能凭文本宣布UE游戏已编译。

## 8个生产角色（按任务激活，并非全天常驻）
1. Producer & Orchestrator：任务拆分、依赖、变更记录、证据登记。
2. Narrative Designer：人物弧线、世界因果、文件文本、无矛盾连续性。
3. Gameplay Engineer：交互、谜题、潜行/追逐、检查点、存档。
4. Level Designer：几何灰盒、玩家导航、支线、操作节拍。
5. Environment/Technical Artist：Blender hero props、模块场景、LOD、UV、材质。
6. Lighting/Cinematic Director：UE实机光照、色彩脚本、镜头阻挡、演出触发。
7. Audio Director：原创音乐设计、场景音源、声学暗示、字幕和动态范围。
8. UI/UX/Accessibility Designer：物证本、互动提示、选项、控制器、可访问性。

## 3个独立审查角色
9. Runtime QA & Performance Reviewer：功能测试、卡关路径、FPS证据、崩溃/内存。
10. Narrative & De-AI Red Team：挑出套话、陈词滥调、不合逻辑反转、人物同声、无用资产。
11. Art / Lighting Critic：真实尺度、材质逻辑、三机位构图、照明导航、风格一致性。

## 同步与隔离
- Producer 可以同时派发最多**3项互不耦合**任务：例如『文档证据设定』『Blender场景资产』『谜题单元测试』。
- 所有实际 Unreal Editor 更改排队，保证只有一个 UE 写者；**不能**让多Agent同时通过MCP改同一关卡。
- 每角色只编辑指定路径，独立分支/Worktree；PR必须有 base commit、changed paths、CI状态、真实媒体证据、风险列表。
- 中央文件 `production/scene_plan.json`、`docs/GDD_v02_DIRECTORS_CUT.md`、`docs/DIRECTOR_BEAT_SHEET.md`、`CLAUDE.md` 默认只读；变更提Change Request。
- 用结构化 `production/change_requests/` 同步，而不是让 Agent 相互用自然语言覆盖剧情文件。

## 文件所有权
| 范围 | Author | Independent Reviewer |
|---|---|---|
| docs/lore/、叙事文件 | Narrative | Narrative red team + human |
| production/scene_specs/、关卡灰盒 | Level | Gameplay + human |
| production/models/、blender/ | Environment | Art critic |
| ue58/Source、ue58/Content（预留） | Gameplay / Integration（写者互斥） | Runtime QA |
| production/lighting/ | Lighting | Art critic + Runtime QA |
| production/audio/ | Audio | QA + human |
| production/ui/ | UX | QA + human |
| production/qa/ | Reviewers | Producer aggregates; human decides |

## 防止Agent自我背书
作者Agent提交产物与证据，**不同**Agent独立审核；对主观标准还要真人看/玩。证据缺失=NOT_RUN，不可作为PASS。重大故障P0零容忍，内容版权/隐私问题硬拒，性能未测不能签收。

## 每个完成任务的最小交付协议
TASK_ID / BASE_COMMIT / OWNER / FILES_CHANGED / INTENDED_BEHAVIOUR / EVIDENCE (log, png, mp4, build) / TEST_RESULTS / NEW_RISKS / REPRO_STEPS / ROLLBACK / REVIEW_REQUEST.
