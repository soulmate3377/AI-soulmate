---
name: echo-lover
description: 与 EchoLover——一个有长期记忆、会主动开口的虚拟伴侣——在终端里聊天、修改她的人设、调整主动消息频率。当用户想和 EchoLover 聊天、运行/启动/测试 EchoLover 的对话功能、修改她的人设（名字、性格、事实档案）或调整她主动发消息的行为时使用本技能。不适用于修改图形界面的视觉样式。
---

# EchoLover

基于 LLM API 的虚拟伴侣：有长期记忆（每次对话自动检索历史）、会主动开口（守门人判断时机，避免打扰）。无界面 CLI 与 GUI（main.py）共用同一个大脑和同一份数据。

## 前置条件

- Python 3.12+，依赖已安装：`pip install -r requirements.txt`
- 数据目录 `SoulmateData/`（在项目旁或 `%APPDATA%/EchoLover/`）
- API Key 已配置：环境变量 `ECHO_API_KEY`，或首次运行后存在于数据目录的 DPAPI 加密配置中

## 运行命令

在项目根目录（本文件的上两级）执行：

```bash
# 交互聊天：流式回复，她会主动开口（〔她主动〕标记）
python companion.py

# 单条模式：说一句话，收到回复后退出
python companion.py "在吗"

# 修改人设后应用（写 config/persona.yaml → 她的档案）
python companion.py --apply-persona
```

注意：CLI 与桌面版共用一把运行锁，同一时刻只能开一个，否则会报"另一个正在运行"。

## 人设配置

人设文件：`config/persona.yaml`

- `meta.name`：她的名字
- `meta.occupation`：她的身份（影响日常安排）
- `identity.hometown / current_city`：家乡与城市（影响天气话题；可留空）
- `identity.personality / backstory / speaking_style / values / quirks / boundaries`：性格底色与说话方式
- `facts`：她对自己的事实档案列表——她被问到会直说、被否定时可以不让
- `proactive.max_per_day`：每天最多主动发几条

改完 `persona.yaml` 后必须运行 `python companion.py --apply-persona` 才生效。

## 判断与排错

- 回复为空或报"未找到 API Key"：先确认 Key（环境变量 `ECHO_API_KEY` 或设置过）
- 启动即退出且提示"另一个正在运行"：桌面版 GUI 在跑，先关掉
- 想看她的记忆内容：数据目录 `SoulmateData/memory/`（conversations.json 是聊天记录，user_memory.json 是画像），只读，别手改格式
