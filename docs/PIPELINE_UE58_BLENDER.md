# Unreal Engine 5.8 + Blender 5.2 LTS 生产管线

## 引擎选择与界限
正式游戏基于 UE 5.8.x（5.8.1 热修补优先，安装版本需要本地确认）；Blueprint/C++ 负责运行时逻辑；Unreal Editor Python **只用于编辑器资产导入/场景搭建，不能用于打包后Gameplay**。Godot `game/` 是仍能作为玩法验证的早期独立灰盒，不与UE实时同步，不在Godot做高精美术。

建议配置来自 Epic 文档：内存32 GB、VRAM8 GB+；运行时动态效果需要具体 GPU 与项目预算验证。未经实机测试不可声称性能达标。

## 每场景固定制作流水线（不得跳步骤）
S0 **构图与参考研究**：负责人搜索建筑/电影摄影和材料真实参考3–5条，录入 `production/reference/scene_*.json`，字段包括 sourceURL、artist、license、visualTakeaway、dontCopy、dateChecked。参考图不直接放入游戏。维护一个“现实逻辑”表：建筑为何存在、谁使用、门通向哪里、设备怎样接电。
S1 **导演分镜**：3个重要视角（入口、人机交互、回看），每个视角标注可见目的、光比、玩家视线方向、音源、要避免的CG假感。
S2 **实际尺度灰盒**：1 Unreal Unit=1 cm；门高210–240cm，通道≥130cm，头高170cm左右（具体依动作尺度复核），保证碰撞、敌人/玩家Nav、目标可达。以12–18分钟切片亲自验证功能后再做资产精修。
S3 **Blender 原创建模**：先大形体，再功能道具，然后结构细节/使用痕迹。全部可复用件（门框、顶灯、扣件、文件盒）做kitbash库，资产命名 SM_/SK_/MAT_/TEX_。应用scale，校验法线、UV、非流形；家具与门类考虑门轴、碰撞和可交互部件。
S4 **高质量材质**：优先 Poly Haven、ambientCG 明确CC0纹理；材质色彩和粗糙度不能随机贴满，PBR贴图与UV应匹配实物尺度。不要从受版权保护的实物照片直接提取纹理。
S5 **UE灯光调色**：Lumen全局照明、Nanite用于适合的静态高面数物体；局部主光不能打平；MegaLights看真实项目性能酌情使用。视觉目标来自场景主视角而非随意堆HDR特效。
S6 **声音**：无版权风险的原创音效/已核验授权的音效，至少三个距离层（环境床、位置声、剧情事件声）；按绝对响度和动态范围审查，不用震耳音量制造恐怖。
S7 **自动自查**：Blender headless preview（可用时）、几何三机位截图、glb导出、资产路径检查、许可与引用核验、分镜对照、碰撞空间导航审查、Unreal Editor导入、场景lint与实际游玩录像。做不到的项目写 BLOCKED，不准写PASS。
S8 **外部玩家测试**：三位不了解故事的玩家，每5分钟检查是否知道当前目标；记录卡死、迷路和听不懂谜题；只依据可观察行为修改节奏。

## 资产采集层次
**原创建模优先**：关键道具（回执机、相框、巡查员、光影谜题设备）、所有带谜题交互的实体。
**允许复用CC0**：水泥、石膏、金属、木材、散碎石子与基础环境自然物件；记录许可网址及检查日期。
**明确许可证的付费/免费现成模型**：只有经过许可证核验才纳入，不把免费=CC0。
**AI生成内容**：可辅助参考构图、材质研究、脚本和原型；3D网格必须经拓扑、UV、碰撞、版权、性能和审美人工质检，不自动视为最终可用资产。

## 视听质量规范
- 入口：视觉焦点应该始终是通往地下的维修门；灯光引导而非悬浮任务箭头。
- 资产表面：至少主资产同时经过远景轮廓 / 中景材料 / 近景交互三尺度检验。
- 细节“真实”优于“繁杂”：磕碰集中在边缘、接触区积灰、清洁痕有方向、文件有真实编号体系。
- 图像优化：优先遮挡与分室卸载，其次实例化模块，材质实例合并、纹理流送、Nanite适用性，再考虑降低材质复杂度。

## 性能门槛（目标，不是已经验证）
- Windows目标：1920×1080，60fps 中等预设；高画质目标1440p且稳定至少30fps。实际由测试 GPU 决定。
- 任意单次视角转向不发生明显shader加载卡顿；入口大堂中等预设不应出现固定频率卡顿。
- 不把场景面数作为唯一成本指标：GPU耗时、GameThread/RenderThread、光影、透明、材质、贴图与音频缓存都要采集。
- 预算要分场景记录，通过 `stat unit`, `stat gpu`, Unreal Insights 和 RenderDoc/Nsight（可用时）验证；记录硬件和驱动。

## Unreal Python 使用界限与入口
1. 在UE5.8 Project Settings启用 `Python Editor Script Plugin` 和 `Editor Scripting Utilities`；重启。
2. Editor的 Tools → Execute Python Script 运行 `production/scripts/unreal_import_validate.py`（尚需在你的本地UE做兼容测试）。
3. 编辑器的导入动作需用 Unreal API；不要用外部 Python 在`.uasset`目录里直接移动资源。
4. Python不是游戏运行脚本。游戏 AI 状态机、交互、谜题、UI应使用 Blueprint/C++。

## 首间场景 01 审美 QA
- 主机位 16:9，右侧深色柜台遮挡前景，后景单扇维修门可读，天井光形成一个不对称矩形。
- 站在门厅中央时能够看出柜台后有人工作过，绝不是“只有几个随机方块”的AI环境。
- 电影语言上只强调第一次进入的简洁、二次回来时的缺失：不把全图做成诡异壁纸。
- 不得只交一张概念图作为建模完成证明，必须输出源 .blend、可导入网格、三角面审计、碰撞验证、实际UE截图。

## 官方文档
- UE5.8: https://www.unrealengine.com/news/unreal-engine-5-8-is-now-available
- Unreal Editor Python: https://dev.epicgames.com/documentation/unreal-engine/scripting-the-unreal-editor-using-python
- Lumen: https://dev.epicgames.com/documentation/unreal-engine/lumen-global-illumination-and-reflections-in-unreal-engine
- Nanite: https://dev.epicgames.com/documentation/unreal-engine/nanite-in-unreal-engine
- Poly Haven CC0: https://polyhaven.com/license
- ambientCG CC0: https://ambientcg.com/
