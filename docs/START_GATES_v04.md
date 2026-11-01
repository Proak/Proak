# v0.4 首发里程碑验收与客观停止条件

| Gate | Deliverable | 实际验证 | 无法执行时 |
|---|---|---|---|
| M0 | UE toolchain/env manifest | 实际路径、版本、Build工具可发现 | BLOCKED |
| M1 | UE C++ compile + Play in Editor | compile log, UE version and PIE screen/video | BLOCKED |
| M2 | VS01 scene: input + pick up + door | 手柄/键鼠交互视频；离开触发 | NOT_RUN |
| M3 | VS02–04 机械谜题 | 容错、重复操作、故障状态单元测试+盲测 | NOT_RUN |
| M4 | VS05–06 敌人AI与逃脱 | 可预警、可躲避、无硬锁、checkpoint video | NOT_RUN |
| M5 | Blender真实环境资产 | Blender源工程、真实三角形计数、渲染及质量判定 | NOT_RUN |
| M6 | UE lighting/audio cinematic pass | 真实PIE画面与空间音频播放对比，字幕/低闪烁可用 | NOT_RUN |
| M7 | 14–17分钟slice playable | 真人3人无指导通关/反馈+真实计时 | NOT_RUN |
| M8 | Perf and polish | 真机spec+统计FPS, frame time, hitch, memory and defects | NOT_RUN |
| M9 | Human signoff | 导演按实际游戏录像与试玩签收 | NOT_RUN |

任何 AI 自评的“AAA”或“电影级”不是 gate。若没有人类/引擎，止于源码与文档的真实测试，不要谎称完成。
