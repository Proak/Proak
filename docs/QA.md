# 自动检查与人工 QA

## 机器检查
运行 `python tools/audit_project.py` ：检查目录、场景资源引用、音乐文件是否正常、纹理尺寸、剧情五站数量、Blender 代码是否存在、外部许可清单、禁用未经许可的 reference 图片复制入 assets。报告存为 `qa_report.json`。
运行 `python -m py_compile blender/scene_generator.py`：检查建模脚本 Python 语法。该步骤**不等价于**实际 Blender 导出验证。

## Godot 运行（真正验收）
1. 打开项目时 Output/Debugger 无 Parse Error；游戏启动显示中文 UI。
2. 看视角与行走方向：W 向走廊前方前进；墙地有碰撞，无穿模。
3. 场景 01 E 读相框，读到第 3 页后第一门消失。
4. 顺序 02 呼吸、03 按住右键观察、04 档案、05 终点；不能跳过关卡；终点可完整显示。
5. Esc 释放/锁定鼠标；在文本对话期间不会导致角色乱走；更换焦点不会错触发。
6. 两段 ambient 循环播放；音量舒适；不出现连续爆音。
7. 针对低端设备测帧率目标 60 fps；记录实测而不是宣称达到。

## Blender 模型（真正验收）
1. 用 Blender 后台模式运行 `blender -b -P blender/scene_generator.py -- --scene 01 --output game/assets/models/scene_01.glb`。
2. 检查非流形、重复顶点、重叠面、法线方向、模型尺度、单位、灯光、贴图是否丢失。
3. 渲染 3 个视角，并实际打开查看：可读性、构图、撞色、明显穿插和阴影。
4. Godot 导入 glb 检查材质、层级、轴线转换、mesh 可视与碰撞。

## 已知不确定项
此交付制作环境没有 Godot/Blender 可执行文件，Godot 项目**尚未 runtime-validated**；Blender 脚本**未执行**。这些不能通过对源文本的检查来替代。

## 可执行自动化入口
- `tools/audit_project.py`：在本机或 GitHub Actions 的每次 push / PR 自动执行静态审查。
- `tools/build_scene.sh 01`：要求本机已安装 Blender；自动生成 `.blend`、`.glb`、场景预览 PNG 与几何 QA JSON。
- `.github/workflows/static_qa.yml`：提交至 GitHub 后自动运行，仅静态检测。照片/建筑参考仍需每场景先经过网上检索与权利核对；脚本**不假装**能在缺少搜索服务的情形自动完成视觉调研。
