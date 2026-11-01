# 《未完成的忏悔》 Claude Handoff v0.4（2026-11-01）

本包是供 Claude Code / Claude Desktop / Claude Chat 接收并**继续制作**的源文件与方案，不是已完成的 UE 游戏。请从 `00_READ_ME_FIRST.md` 开始。

- `01_CLAUDE_HANDOFF_PROMPT.txt`：复制到 Claude 的交接指令。需要附上此 ZIP 或开放解压文件夹。
- `CLAUDE_APP_SINGLE_FILE.txt`：若 Claude App 不接受 ZIP，直接上传这份**文本版完整交接书**；包含剧本、关键约束、玩法分解与审查要求，但不含原项目二进制资源。
- `docs/AUDIT_REPORT_v04.md`：上一版的可复核问题、改动、未完成项和真实验收状态。
- `production/vertical_slice_plan.json`：14–17分钟（设计估算）可玩切片的独立内容清单。
- `ue58/`：真正的 UE 工程骨架（源代码，未编译测试）；`game/` 是 Godot 实验性原型，**不是**可发售 UE 游戏。
- `blender/`、`production/blockout/`：场景脚本与 GLB 灰盒，不是已完成的高精度美术。
- `tools/handoff_preflight.py`：静态交接一致性核验，不可当作引擎/审美验证。
- `docs/PROMPTS/`、`.claude/agents/`：真正的 Claude Code 并行任务协议。

**请勿声称：已经运行、已经实机录制、已完成精细建模、已达 AAA、AI 审稿等于真人试玩。**

若在普通 Claude 手机 App 中只上传一个文件：优先传 `CLAUDE_APP_SINGLE_FILE.txt`。需要真正操作 Unreal/Blender 则必须使用可访问项目文件和本地编辑器的 Claude Desktop/Claude Code 工作环境，并授权相关目录。
