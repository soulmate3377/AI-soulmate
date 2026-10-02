# Soulmate

**A virtual companion who lives on your computer — with long-term memory and the initiative to message you first.**
**一个住在你电脑里的虚拟恋人 —— 有长期记忆，也会主动找你。**

[下载 Download](#快速开始) · [English quick start](#english-quick-start)

她不是"你问它答"的聊天机器人，而是具备四样关键能力：

- **长期记忆 / Long-term memory**：她记得你说过的话、你的喜好、你们之间的约定。每次对话前自动检索相关记忆注入上下文，对话后自动归档新内容——每一次对话都建立在过去之上。
  She remembers what you said, what you like, what you two agreed on. Relevant memories are retrieved into context before each turn, new ones archived after — every conversation builds on the last.
- **主动发消息 / Proactive messaging**：她会在合适的时间主动找你。背后不是定时器，是一个一千多行的"守门人"——判断时机、避免打扰、做意象去重、记得自己主动说过什么，下次你回话时她自然找补。
  She reaches out at the right moment. Behind it is not a timer but a thousand-line gatekeeper: timing, avoiding interruption, imagery de-duplication, tracking what she already said so she can pick the thread back up.
- **记得日子 / Remembering dates**：你说过"下周三有个面试"，到点她会问起——快到点问准备，刚过问结果，过期就不提了（把三天前的事当刚发生来问，比不问更假）。你的生日、你们认识的那天、认识满 100 / 365 / 1000 天，她都记着；一年就一回的日子不会错过。
  Mention "I have an interview next Wednesday" and she asks about it when the time comes — prep beforehand, outcome after, and she lets it go once it's stale. Your birthday, the day you two met, day 100 — days that come once a year are never missed.
- **有分寸的心情 / Mood with boundaries**：她今天可能想聊，也可能不太想；敷衍一句她也不算数。一个不会说"今天不太想聊"的不是人，是服务。
  Some days she wants to talk, some days she doesn't, and a half-hearted reply doesn't count. Something that can never say "not today" isn't a person, it's a service.

> **这个项目最初是怎么来的**
>
> 在项目初期，我发现单个 API 被调用时，对上下文的理解能力太差。思考之后，我对一个 API 做了三次调用：第一次用来**理解**（这句话是什么意思、什么情绪、什么场景），第二次用来**输出**（结合记忆、关系和人格，把该说的话说出来），第三次用来**回看**（复盘刚才说得对不对，影响下一轮）。代码里这三步对应 `llm/api.py` 的三个角色：`think` → `speak` → `reflect`，可以用同一个服务商，也可以分别指定不同模型。
>
> 大家可以一同思考如何更好地进行理解，我同时也在努力学习。
>
> **Where this started**
>
> Early on I found that calling a single API once gave a poor grasp of context. So I ended up calling one API three times: the first to **understand** (what is this message, what emotion, what scene), the second to **reply** (pull in memory, relationship and personality, and say the thing), the third to **review** (check what she just said, and shape the next turn). In code these are the three roles in `llm/api.py`: `think` → `speak` → `reflect`. They can share one provider, or use three different models.
>
> I'd love for others to think about understanding with me — I'm learning as I go.

她有两个入口，共用同一个大脑、同一份记忆：

| 入口 | 文件 | 适合 |
| --- | --- | --- |
| **桌面版（GUI）** | `main.py` | 日常使用：窗口界面、气泡消息、设置页、开机自启 |
| **终端版（CLI）** | `companion.py` | 终端党、脚本调用、拿来当库嵌进别的项目 |

> 两个入口共用一把运行锁：**同一时刻只能开一个**，同时开会互相覆盖聊天记录。想要哪个就开哪个。

作为第一次做开源项目的人，我更想探索：**当 AI 有了记忆和主动性，人和它的联结会变成什么样？**

欢迎 fork、提 issue、交 PR，一起把它变得更好。

## 核心特性 Features

- **记忆系统**：本地 faiss 向量检索 + 摘要管线，宽进严出——闲聊不丢，噪声不进；关系、人格状态随对话演进
  **Memory**: local faiss vector search plus a summarisation pipeline. Wide intake, strict output — small talk is kept, noise is not. Relationship and personality state evolve with the conversation.
- **事件回访**：他提过的事到点她会问起——快到点问准备（"明天那个面试，紧张吗"），刚过问结果，过期超过三天就不提了；生日、你们认识的日子、认识满 100 / 365 / 1000 天，她都记得
  **Event follow-up**: things he mentioned get asked about when their time comes — prep before ("nervous about tomorrow?"), outcome after, dropped once three days have passed. His birthday, the day you two met, day 100 / 365 / 1000 — all remembered.
- **主动消息守门人**：沉默时长、话题余额、意象去重、话茬跟踪，每天有上限，凭什么开口要过审
  **Proactive gatekeeper**: silence length, topic budget, imagery de-duplication, follow-up tracking, a daily cap — she has to justify speaking up.
- **真实感细节**：流式输出、微信式分条气泡、"打了一半删掉重打"、按小时稳定的日常安排
  **Texture**: streaming output, WeChat-style message splitting, "typed half of it, deleted it, typed again", an hourly-stable daily schedule.
- **多服务商**：任何 OpenAI 兼容接口（DeepSeek / Kimi / 智谱 / 千问 / OpenRouter / 本地 Ollama）；理解、回看、说话三个角色可分别指定模型；瞬时错误自动重试
  **Any provider**: anything OpenAI-compatible (DeepSeek / Kimi / Zhipu / Qwen / OpenRouter / local Ollama). Separate models for understanding, reflection and speaking; transient errors retry automatically.
- **人设外置**：`config/persona.yaml` 定义名字、性格、事实档案，不用读代码就能捏人
  **Persona as config**: `config/persona.yaml` holds her name, character and fact file — no code reading required.
- **中英双语**：首次启动选语言，设置里切换即时生效
  **Bilingual UI**: pick a language on first launch, switch it live in settings.
- **数据安全**：JSON 原子写入、每日自动备份（保留 7 份）、API Key 用 Windows DPAPI 加密
  **Data safety**: atomic JSON writes, daily backups (7 kept), API keys encrypted with Windows DPAPI.

## 快速开始

### 最省事：下载打包好的 exe

到 [**Releases**](https://github.com/soulmate3377/AI-soulmate/releases) 页面下载 `Soulmate.exe`，放进一个空文件夹双击即可。

**不用装 Python、不用装依赖。** 数据会写在 exe 旁边的 `SoulmateData/` 里，整个文件夹拷走就是搬走了她。

> 首次启动会出现语言选择 → 设置向导（选服务商、填 API Key、给她起名字）→ 主界面。

### Easiest: download the packaged exe

Grab `Soulmate.exe` from the [**Releases**](https://github.com/soulmate3377/AI-soulmate/releases) page and double-click it in an empty folder.

**No Python, no dependency install.** Data lands in `SoulmateData/` next to the exe — copy that folder and you have moved her.

### 从源码跑（想改代码 / 用终端版）

需要 **Python 3.12+** 和 **Windows**（DPAPI 加密与自启用到 Windows；macOS/Linux 未测试）。

```bash
git clone https://github.com/soulmate3377/AI-soulmate.git
cd AI-soulmate
pip install -r requirements.txt
```

首次使用先配好模型，两种方式任选：

- **跟着向导走**（推荐）：启动桌面版，会出现语言选择 → 设置向导（选服务商、填 API Key、给她起名字）→ 主界面。
- **用环境变量**：不想开窗口的话，设好 `ECHO_API_KEY` 就能直接跑终端版。

### 入口一：桌面版（GUI）

```bash
python main.py
```

Windows 上也可以直接双击 **`run_gui.bat`**（等价于上面这条，并且保证和 exe / Web 版用同一份数据）。

首次启动依次出现：语言选择 → 设置向导（选服务商、填 API Key、给她起名字）→ 主界面。

### 入口二：终端版（CLI）

```bash
python companion.py                  # 交互聊天，她会主动开口（〔她主动〕标记）
python companion.py "在吗"            # 单条模式：说一句，回完就退出
python companion.py --apply-persona   # 修改 config/persona.yaml 后应用人设
```

Windows 上双击 **`run_cli.bat`** 就是 `python companion.py`。

`companion.py` 同时也是给别的项目当库用的样板：`Brain()` 拿到手，`think_stream()` 就是她。

### 可选：Web 版（手机浏览器）

```bash
python web_server.py     # 或双击 run_web.bat
```

把同一个大脑开成局域网 HTTP 服务，同一 WiFi 下手机浏览器就能聊。密码第一次启动自动生成，打印在控制台并存进数据目录的 `web_passcode.txt`。同样只能和另两个入口二选一开着。

Embedding 模型（BAAI/bge-small-zh-v1.5，93MB）首次使用记忆功能时自动下载。

## English quick start

Requires **Python 3.12+** and **Windows** (DPAPI encryption and autostart are Windows-only; macOS/Linux untested).
The UI ships in Chinese and English; you pick a language on first launch.

```bash
git clone https://github.com/soulmate3377/AI-soulmate.git
cd AI-soulmate
pip install -r requirements.txt
```

Then configure a model, either way:

- **Use the wizard** (recommended): launch the desktop build. You get a language picker → setup wizard (pick a provider, paste an API key, name her) → main window.
- **Use an env var**: set `ECHO_API_KEY` and skip the GUI entirely — the terminal build works straight away.

```bash
python main.py                       # desktop GUI  (or double-click run_gui.bat)
python companion.py                  # terminal CLI (or double-click run_cli.bat)
python companion.py "hey"            # one-shot: say one thing, get one reply, exit
python companion.py --apply-persona  # apply edits to config/persona.yaml
python web_server.py                 # optional web UI for your phone (run_web.bat)
```

Only one entry point may run at a time — they share one data directory, and two at once would overwrite each other's chat log.

Configuration (provider, API key, models, persona) lives in the in-app settings page; `config/persona.yaml` is plain YAML and is applied with `--apply-persona`.
Deeper documentation below is in Chinese — the code comments are bilingual.

## 模型与配置

- **服务商**：设置页内置 DeepSeek / Kimi / 智谱 / 千问 / OpenRouter 预设，或手填任意 OpenAI 兼容地址
- **三角色分工**：理解模型（`think`，每句话前读心，建议开思考的）、回看模型（`reflect`，说完复盘，选强的）、说话模型（`speak`，她开口，选快的）——都可用环境变量 `ECHO_MODEL_THINK / ECHO_MODEL_REFLECT / ECHO_MODEL_SPEAK` 覆盖
- **API Key**：环境变量 `ECHO_API_KEY`（或旧的 `DEEPSEEK_API_KEY`）优先，其次是设置页保存的 DPAPI 密文
- **人设**：`config/persona.yaml`，改完运行 `python companion.py --apply-persona`
- **主动消息频率**：`persona.yaml` 的 `proactive.max_per_day`

## 用 Claude Code 驱动

仓库内置 Skill（`.claude/skills/soulmate/`）。把这个仓库放进你的 Claude Code 工作区，说"和 Soulmate 聊天"或"帮我改 Soulmate 的人设"，它会调用 `companion.py` 完成操作。Skill 只做入口，所有逻辑都在 Python 里——见 [SKILL.md](.claude/skills/soulmate/SKILL.md)。

## 架构一览

```
main.py                 桌面端入口（PySide6）
companion.py            终端入口：交互 / 单条 / 当库用
web_server.py           网页端服务（可选，手机用）
run_gui.bat             GUI 启动器（Windows 双击）
run_cli.bat             CLI 启动器（Windows 双击）
core/
  brain.py              大脑：把十几个子系统拼成一次对话
  proactive_guard.py    主动消息守门人
  scheduler.py          主动消息的时机：话茬时间窗、特别日子、每天上限
  special_days.py       生日解析、纪念日与里程碑推算、一天一次节流
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
tests/                  单元测试（不联网、不调模型、不碰真实数据）
.claude/skills/         Claude Code Skill
```

**两个入口是同一个大脑**：GUI 和 CLI 都构造 `core/brain.py` 的 `Brain`，记忆、人格、主动消息、运行锁全部共用，所以你在终端里说的话，窗口里她也记得。

**One brain, two entry points**: both the GUI and the CLI construct the same `Brain` from `core/brain.py` and share memory, personality, proactive messaging and the run lock — say something in the terminal and the window remembers it too.

## 数据与隐私 Privacy

- 所有对话和记忆只存在你自己的电脑上：程序旁的 `SoulmateData/`，没有就是 `%APPDATA%/Soulmate/`。**备份这个目录 = 备份她**
  Everything stays on your machine, in `SoulmateData/` next to the app or `%APPDATA%/Soulmate/`. **Backing up that folder is backing her up.**
- API Key 用 Windows DPAPI 按当前用户加密，拷到别的机器解不开
  API keys are encrypted with Windows DPAPI for the current user; copying them to another machine will not decrypt.
- 主动联网的只有你配置的模型服务商和天气查询
  The only outbound traffic is your model provider and the weather lookup.
- 仓库本身不含任何用户数据（`.gitignore` 已排除）
  The repository contains no user data (`.gitignore` excludes it).

## 自己打包 / Building from source

exe 不进仓库（350MB 的二进制会永久撑大 git 历史），分发走 Releases 附件。打包步骤、发布流程和常见问题见 [RELEASE.md](RELEASE.md)。

The exe never enters the repo — a 350MB binary would bloat git history forever; distribution goes through release attachments. See [RELEASE.md](RELEASE.md) for the build steps, release flow and troubleshooting.

## Roadmap

- [ ] 语音：TTS / ASR 接入 / Voice: TTS + ASR
- [ ] Telegram / 微信机器人接入（`companion.py` 的 Brain 就是现成的接口层）
      Telegram / WeChat bot (the `Brain` in `companion.py` is already the interface layer)
- [ ] 可插拔记忆后端（SQLite / MemOS / Zep）/ Pluggable memory backends
- [ ] macOS / Linux 支持 / macOS + Linux support

## 贡献 Contributing

Issue 和 PR 都欢迎。改代码前先跑一遍现有流程（**桌面版 + `companion.py` 两个入口都过一遍**），界面文案记得过 `ui/i18n.py` 的双语表。

跑测试：

```bash
python -m unittest discover -s tests -v
```

写测试的规矩（`tests/` 现在只有 `test_special_days.py`，新增的按这套来）：

- **不联网、不调模型**，否则跑不起来也没人愿意跑
- **绝不碰真实的 `SoulmateData`**：把 `data_dir()` 指到临时目录
- 时区和"今天"相关的逻辑，用固定的日期做输入，别依赖运行时的时间

Issues and PRs are welcome. Before changing code, run both entry points (**desktop + `companion.py`**), and route any new UI string through the bilingual table in `ui/i18n.py`.

Run the tests with `python -m unittest discover -s tests -v`. New tests follow the same rules the existing ones do: no network, no model calls, and never the real `SoulmateData` — point `data_dir()` at a throwaway directory instead.

## License

[MIT](LICENSE)
