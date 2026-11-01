# 质量门禁与玩家实测方案 v0.2

## 立刻需要验证
- Godot v0.2 源码确实能解析并游玩：阀门按低→高→低后可继续，三张档案可选收集，追逐可重试且可完成。**未实机测试，当前状态 BLOCKED。**
- UE5.8 C++ 只建立最小第一人称角色、射线交互与事件广播基础。需要UE本地编译，并用Blueprint将谜题/存档/UI等系统接入。**不是完整UE可玩游戏，当前状态 BLOCKED。**
- scene01 glb 已用 trimesh 导出并重新解析；有真实网格数据，但未完成室内光影、角色、碰撞、UV、配套导入验证与美术精修。

## 三种首次测试者
A. 重剧情：会主动读文件。检查信息密度与故事清晰度。
B. 重玩法：跳过文本。检查是否仍知道目标、是否有充分谜题反馈。
C. 重恐怖：喜欢惊吓和追逐。检查张弛、是否因拖沓退出。

## 量化但不迷信指标
- 5分钟内至少一次明确可执行的操作（不是拾取可有可无的纸条）。
- 所有关键道具应有二级线索（环境可见提示＋声音/文本至少其一）。
- 初见巡查员前玩家先听到声音且能看到它一次无敌对巡逻。
- 跑酷追逐开始时玩家视线内应有可理解的逃跑出口，或通过灯光/声音在2秒内判断方向。
- 任一谜题卡住超过5分钟时提供逐级提示；保留不用提示通关的可能。
- 从追逐失败到重新拥有操作权目标<8秒。
- 任何关键叙事不依赖可选收集物。

## 测试表
Record: build_hash / engine_version / hardware / fps target / actual fps p10 p50 p90 / test_time / objective clarity / puzzle solve time / death count / bugs / clipping / audio peak / nausea rating / dialogue readability / game completed yes/no / participant comments.

## QA 严格区分
STATIC PASS = 文件存在、Python语法正确、GLB重读正确。
BLENDER PASS = Blender实际渲染并保存三机位，脚本日志保留。
UE IMPORT PASS = UE实际导入资产，编辑器日志与资产清单保留。
UE RUNTIME PASS = PIE通关并录制，帧耗数据保留。
USER PLAYTEST PASS = 三位新玩家实测并保留匿名记录。
禁止用STATIC PASS替代任意后四者。
