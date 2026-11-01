# Claude App 与 Claude Code：能力边界和操作

- 普通 Claude App 聊天：可接收 TXT、PDF等列出的文档，可能有云端文件执行能力；**不能因为读到了文件就认为可操作你本机的 Unreal/Blender**。ZIP上传不是帮助中心明确保证的普通聊天格式；若不能上传，使用根目录 `CLAUDE_APP_SINGLE_FILE.txt`。
- Claude Desktop 可在授权后访问并编辑本地文件夹；本机 Unreal/Blender 的自动控制要取决于对应本地运行环境和接口，必须实际检测。
- Claude Code 在本地解压目录或 Git 仓库打开工程时，才适合执行真实 UE/Blender 命令、管理工作分支和测试；必须先检查工具是否存在。Mac/Windows/其它OS按实际工具链设置。
- 手机：上传单文件文本或 ZIP（若支持）+ 根目录提示词；先让Claude做文件读取/审计/分派；后续用带本地引擎的桌面环境运行实机任务。

官方说明（不作为担保）：
https://support.claude.com/en/articles/8241126-upload-files-to-claude
https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude
https://academy.claude.com/tutorials/navigating-the-claude-desktop-app
https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor
