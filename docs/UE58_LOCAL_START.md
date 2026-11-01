# Unreal Engine 5.8 本地启动：当前是UE代码骨架和资产导入素材

1. 安装 Unreal Engine 5.8.x，Visual Studio 2022及UE要求的C++工具链（Windows），或官方要求的对应macOS/Linux编译环境。
2. 打开 `ue58/Confession.uproject`；允许生成项目文件并编译。若有编译错误，复制完整UE Build日志，先修复，不能假称已跑通。
3. 在空白关卡中放置 PlayerStart，World Settings 的 GameMode 指向 `ConfessionGameMode`（或全局默认）以使用第一人称角色。WASD和鼠标使用传统输入绑定，E对 `AConfessionInteractable` 进行射线互动。交互需在其Visual上配置带碰撞的具体模型/蓝图。
4. 启用 glTF Importer（如编辑器要求），运行 `production/scripts/unreal_import_validate.py`，或从 Content Browser 手工导入 `production/blockout/scene_01_entrance_BLOCKOUT.glb`。
5. **本脚本仅把glb导入Content Browser，不会自动建好一个可玩的UE关卡。** 还需将各网格合理摆放/按导入层级重建、碰撞、灯光、门禁、谜题、敌人和UI接入。当前不能声称已有可运行的UE游戏。
6. Blender 运行 `blender/scene01_art_pass.py` 以产生 `.blend` 及三机位预览；先检查初步美术，再进入材质和UV精修。

## Godot机制原型（可先做快速技术试验）
安装Godot 4.7.2后打开 `game/project.godot`；WASD移动、鼠标转向、E互动、Shift跑步、Ctrl慢走、RMB观察、Esc切鼠标。
该原型跟正式UE项目是两个独立产物。只有在互动与时间节奏完成验证后才移植相应逻辑；不在Godot完成商业级美术，也不自动同步引擎。
