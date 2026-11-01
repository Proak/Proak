# Claude 交接入口：先审计，再执行

**项目**：THE UNFINISHED CONFESSION / 《未完成的忏悔》。原创线性第一人称心理生存恐怖，PC，六幕24段，最终UE5.8+Blender；12–18分钟高质量垂直切片先行。

## 工作顺序
1. 阅读 `01_CLAUDE_HANDOFF_PROMPT.txt`、`CLAUDE.md`、`docs/AUDIT_REPORT_v04.md`、`docs/GDD_v02_DIRECTORS_CUT.md`、`docs/WORLD_BIBLE_AND_SCRIPT.md`、`docs/SCENE_OUTLINE_24_BEATS.md`、`production/vertical_slice_plan.json`、`docs/PRODUCTION_RUNBOOK.md`。
2. 确认**当前会话具备的工具**：只是对话？有可执行代码环境？可访问本机文件？有UE/Blender？有Git？有图像/音频工具？不要推断。
3. 先运行 `python tools/handoff_preflight.py`、`python tools/studio_static_audit.py`、`python -m unittest discover -s tests -v`，附实际命令输出。如未能运行则标 NOT_RUN。
4. 第一项开发任务：UE最小可编译+可操作项目、角色控制、可开门与checkpoint；**只做L0_B01的功能灰盒**，不抢先做高模。
5. 后续逐门禁推进，追逐和潜行在垂直切片样本中验证。所有视觉质量、性能、音频、实际可玩性均需要运行证据。Claude自己的审美评语不算验收。

## 优先级
真实交付 > 清晰玩法 > 完整因果 > 导演美术 > 优化 > 文案厚度。世界观和主角为原创，不包含任何私人真实人物记录。不可从现实隐私推断故事细节。

## 证据与承诺
当前：引擎可玩性 NOT_RUN、UE compile NOT_RUN、Blender render NOT_RUN、独立真人试玩 NOT_RUN。已有静态源码、GLB灰盒、Godot原型与策划文档。
