# UE 5.8 灰盒运行手册 v0.5（L0_B01 雨廊入口 / 回执局门厅）

> 状态：**源码已写、未编译**。本文所有 UE 步骤需在装有 UE 5.8 的本机执行；云端会话没有 Unreal。
> 运行后请把 `ue58/Saved/Logs/*.log` 与 `ue58/Saved/Confession/Evidence/<时间>/` 整个目录交回，作为 G3/G7 证据。

## 一键运行（Windows）
```bat
tools\ue\build_and_playtest.bat "C:\Program Files\Epic Games\UE_5.8"
```
三步：① 编译 `ConfessionEditor`；② `Automation RunTests Confession`（数据与规则，无渲染）；
③ 以真实渲染窗口启动游戏，机器人按 `autopilot` 路线**真实行走、真实按 E**（不瞬移），拍 8 张截图后退出。
退出码：0 PASS / 2 编译失败 / 3 自动化失败 / 4 试玩失败。macOS/Linux 用 `tools/ue/build_and_playtest.sh <UE根目录>`。

## 手动游玩
1. 打开 `ue58/Confession.uproject`（首次会编译 C++）。
2. 启动地图就是引擎自带的空地图 `/Engine/Maps/Entry`——**不需要任何 .umap**。按 Play：
   `AConfessionGameMode` 读取 `Content/Confession/Data/L0_B01_layout.json`，在运行时生成墙体、灯光、声源和交互物。
3. 操作：WASD 移动 · 鼠标视角 · Shift 疾走 · Ctrl/C 蹲 · E 互动/关闭文件 · Tab 物证本。手柄：左摇杆/右摇杆/A/B/菜单键。
4. 控制台：`Confession.AutoPlaytest`（同一机器人路线）· `Confession.Respawn`（回检查点）· `Confession.DumpState` ·
   `confession.Language 1`（英文）· `confession.FOV 100` · `confession.ObjectiveReminder 0`。

## 本段应当发生的事（验收时逐条看）
| # | 玩家行为 | 应有反馈 | 来源 |
|---|---|---|---|
| 1 | 出生在雨廊南端，面向北 | 雨声、远处叫号声；服务窗口上方是唯一暖光；地上有赭黄维修标线 | 剧本第0幕、24段 L0_B01 |
| 2 | 走到服务窗口，E 拿起工单 | 纸张声；显示工单 21-47 原文（E 放下）；目标变为“进入回执局” | 剧本原文 |
| 3 | 不拿工单直接按门 | 读卡灯红闪 + 拒绝声 +“需要工单” | 失败路径 |
| 4 | 持工单按门 | 拒绝声 + “门禁显示上一个号码：21-46”，灯转琥珀；提示变为“读卡中……”；约 2.6 s 后咔哒，号码行保留、下方加一行“锁舌松开”，灯转绿，门自己开一条缝 | 24段 L0_B01“入口门禁重新提示上一个号码”；节拍表“门禁拒绝一次后机械松动” |
| 5 | 再按 E 推门，进门厅 | 门缓慢打开；越过门槛触发检查点（右下角“已记录”+盖章声） | |
| 6 | 去左侧柜台，E 从卡槽取工号卡 | 卡槽琥珀指示灯熄灭；柜台电话响一次 | 剧本“玩家拿到工号卡时，电话响一次” |
| 7 | 铃响时接听（可选；文件关闭后才响） | “只听到拨号静音”；约 2.5 s 后门厅另一端的墙上电话响起 | 剧本“挂断后铃声从走廊另一端响起” |
| 8 | 看一眼右墙空相框，再转开 | 相框向右移 8 cm，只发生一次，永远不在视野中移动 | 节拍表关键演出 01 |
| 9 | 刷工号卡开地下维修门，进入平台 | 第二检查点；“本段灰盒结束” | |

## 证据要求（G3/G7）
- `autoplaytest.json`：PASS/FAIL、每一步结果与坐标、引擎版本、RHI、CPU/GPU、帧时间 avg/p99/max。
- 截图：每个镜头一张第一人称 `fp_*.png` + 一张固定机位 `shot_*.png`（机位来自布局 `shots`）。
- 另请人工录制 10–30 秒游玩视频（OBS 等），机器人不能证明“好不好玩”。

## 已知限制（不要误读为完成）
- 灰盒材质是引擎 BasicShapeMaterial 着色，玻璃在 UE 中显示为不透明深色块。
- 没有存档到磁盘（检查点仅在本次运行内存中）；Esc 暂停菜单未做；敌人/追逐尚未接入 UE（规则核心已测试）。
- 运行时生成的几何没有 NavMesh；VS05 巡查员接入前需要放置 NavMeshBoundsVolume 或改为编辑器内生成关卡。
