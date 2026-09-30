# EchoLover

一个住在你电脑里的虚拟恋人。不是"你问它答"的聊天机器人，而是具备三样关键能力：

- **长期记忆**：她记得你说过的话、你的喜好、你们之间的约定。每次对话前自动检索相关记忆注入上下文，对话后自动归档新内容——每一次对话都建立在过去之上。
- **主动发消息**：她会在合适的时间主动找你。背后不是定时器，是一个一千多行的"守门人"——判断时机、避免打扰、做意象去重、记得自己主动说过什么，下次你回话时她自然找补。
- **有分寸的心情**：她今天可能想聊，也可能不太想；敷衍一句她也不算数。一个不会说"今天不太想聊"的不是人，是服务。

项目以可运行的代码为主体：桌面应用（PySide6）+ 无界面 CLI + 一个 Claude Code Skill 作为便捷入口。你可以换不同的模型、改人设、加语音、设计更聪明的记忆策略。

作为第一次做开源项目的人，我更想探索：**当 AI 有了记忆和主动性，人和它的联结会变成什么样？**

欢迎 fork、提 issue、交 PR，一起把它变得更好。

## 核心特性

- **记忆系统**：本地 faiss 向量检索 + 摘要管线，宽进严出——闲聊不丢，噪声不进；关系、人格状态随对话演进
- **主动消息守门人**：沉默时长、话题余额、意象去重、话茬跟踪，每天有上限，凭什么开口要过审
- **真实感细节**：流式输出、微信式分条气泡、"打了一半删掉重打"、按小时稳定的日常安排
- **多服务商**：任何 OpenAI 兼容接口（DeepSeek / Kimi / 智谱 / 千问 / OpenRouter / 本地 Ollama）；理解、回看、说话三个角色可分别指定模型；瞬时错误自动重试
- **人设外置**：`config/persona.yaml` 定义名字、性格、事实档案，不用读代码就能捏人
- **中英双语**：首次启动选语言，设置里切换即时生效
- **数据安全**：JSON 原子写入、每日自动备份（保留 7 份）、API Key 用 Windows DPAPI 加密

## 快速开始

需要 Python 3.12+ 和 Windows（DPAPI 加密与自启用到 Windows；macOS/Linux 未测试）。

```bash
git clone https://github.com/<你的用户名>/EchoLover.git
cd EchoLover
pip install -r requirements.txt
python main.py
```

首次启动依次出现：语言选择 → 设置向导（选服务商、填 API Key、给她起名字）→ 主界面。

终端党 / Claude Code 用户可以直接用无界面入口：

```bash
python companion.py                # 交互聊天，她会主动开口
python companion.py "在吗"          # 单条模式
python companion.py --apply-persona  # 修改 config/persona.yaml 后应用人设
```

Embedding 模型（BAAI/bge-small-zh-v1.5，93MB）首次使用记忆功能时自动下载。

## 模型与配置

- **服务商**：设置页内置 DeepSeek / Kimi / 智谱 / 千问 / OpenRouter 预设，或手填任意 OpenAI 兼容地址
- **三角色分工**：理解模型（每句话前读心，建议开思考的）、回看模型（说完复盘，选强的）、说话模型（她开口，选快的）——都可用环境变量 `ECHO_MODEL_THINK / ECHO_MODEL_REFLECT / ECHO_MODEL_SPEAK` 覆盖
- **人设**：`config/persona.yaml`，改完运行 `python companion.py --apply-persona`
- **主动消息频率**：`persona.yaml` 的 `proactive.max_per_day`

## 用 Claude Code 驱动

仓库内置 Skill（`.claude/skills/echo-lover/`）。把这个仓库放进你的 Claude Code 工作区，说"和 EchoLover 聊天"或"帮我改 EchoLover 的人设"，它会调用 `companion.py` 完成操作。Skill 只做入口，所有逻辑都在 Python 里——见 [SKILL.md](.claude/skills/echo-lover/SKILL.md)。

## 架构一览

```
main.py                 桌面端入口（PySide6）
companion.py            无界面 CLI / 库入口
web_server.py           网页端服务（可选）
core/
  brain.py              大脑：把十几个子系统拼成一次对话
  proactive_guard.py    主动消息守门人
  perception.py         理解端：情绪/场景/指代消解
  personality.py        人格
  self_facts.py         她的事实档案（persona.yaml 优先）
memory/
  vector_memory.py      faiss 向量记忆
  memory_pipeline.py    记忆宽进严出管线
  relationship.py       关系演进
llm/api.py              多服务商接入、重试、降级
prompt/builder.py       提示词拼装
ui/                     桌面界面
config/persona.yaml     人设配置
.claude/skills/         Claude Code Skill
```

## 数据与隐私

- 所有对话和记忆只存在你自己的电脑上：程序旁的 `SoulmateData/`，没有就是 `%APPDATA%/EchoLover/`。**备份这个目录 = 备份她**
- API Key 用 Windows DPAPI 按当前用户加密，拷到别的机器解不开
- 主动联网的只有你配置的模型服务商和天气查询
- 仓库本身不含任何用户数据（`.gitignore` 已排除）

## Roadmap

- [ ] 语音：TTS / ASR 接入
- [ ] Telegram / 微信机器人接入（`companion.py` 的 Brain 就是现成的接口层）
- [ ] 可插拔记忆后端（SQLite / MemOS / Zep）
- [ ] macOS / Linux 支持

## 贡献

Issue 和 PR 都欢迎。改代码前先跑一遍现有流程（桌面版 + companion.py），界面文案记得过 `ui/i18n.py` 的双语表。

## License

[MIT](LICENSE)
