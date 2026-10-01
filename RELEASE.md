# 打包与发布 / Building and releasing

面向维护者。用户只需要去 Releases 页面下载 exe。

For maintainers. Users only need to grab the exe from the Releases page.

---

## 为什么会有这份文档

`dist/` 和 `build/` 都在 `.gitignore` 里，所以 **exe 不进仓库**（386MB 的二进制塞进 git 历史会让仓库永远瘦不下来）。

分发靠 **GitHub Releases**：Release 的附件不占仓库体积，而且有版本号和下载计数。

**Why this document exists**

`dist/` and `build/` are gitignored, so **the exe never enters the repo** — a 386MB binary in git history bloats the repo forever.

Distribution goes through **GitHub Releases**, whose attachments live outside the repo and come with version numbers and download counts.

---

## 一、准备打包环境（只做一次）

用 uv 建一个 Python 3.12 环境。**不要用系统 Python**——版本不确定，而且不想让全局环境被塞满。

```powershell
cd C:\Users\Lenovo\Desktop\SoulMate\AI-companion

# uv 的缓存在 AppData 下可能没有写权限，指到项目内
$env:UV_CACHE_DIR="$PWD\.uv-cache"

uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt pyinstaller
```

装完大约 1.5GB（torch 和 PySide6 占大头）。

**为什么必须是 3.12**：`requirements.txt` 写的就是 3.12+，而 PySide6 / faiss-cpu / torch 在 3.12 上的 wheel 最成熟。3.14 上可能装不上。

---

## 二、打包

```powershell
cd C:\Users\Lenovo\Desktop\SoulMate\AI-companion
$env:UV_CACHE_DIR="$PWD\.uv-cache"

.venv\Scripts\python.exe -m PyInstaller soulmate.spec --noconfirm
```

产物：**`dist\Soulmate.exe`**（约 386MB，单文件，双击即用）

打包耗时几分钟。`build/` 目录会占接近 1GB，之后可以删。

### 另外两个 spec

| spec | 产物 | 说明 |
| --- | --- | --- |
| `soulmate.spec` | `dist\Soulmate.exe` | 桌面版 GUI（主入口）|
| `soulmate_web.spec` | `dist\SoulmateWeb.exe` | Web 版，手机浏览器用。`excludes` 排掉了 PySide6，所以小一些 |

```powershell
.venv\Scripts\python.exe -m PyInstaller soulmate_web.spec --noconfirm
```

### 打包前先验证源码能跑

打包不会告诉你逻辑有错。先确认：

```powershell
.venv\Scripts\python.exe companion.py --apply-persona
```

（`--apply-persona` 不需要 API Key，能验证依赖和路径解析都正常。）

---

## 三、打包后必须做的三件事

### 1. 在**干净环境**里试跑

把 `dist\Soulmate.exe` 复制到一个**没有 Python、没有项目文件**的目录（比如 `D:\test\`），双击。

要确认：
- 能起来，不报缺少 DLL
- 能进设置页、能连上模型
- 数据写在 exe 旁边的 `SoulmateData\`（便携模式）

**为什么必须在干净目录试**：在项目目录里试会"借用"到旁边的源码和 `.venv`，掩盖缺文件的问题。

#### ⚠️ 试跑时最容易踩的坑

**`SoulmateData` 是"便携优先"的**（`core/paths.py`）：

1. exe 旁边有 `SoulmateData\` → 用它
2. 没有，但 exe 所在目录**可写** → 自动创建 `SoulmateData\` 并用它
3. 不可写（Program Files、只读盘）→ 退回 `%APPDATA%\Soulmate`

**所以：在一个空文件夹里试跑，她会从零开始**（空记忆、要重新配置 API Key），因为你原来的数据在**项目目录旁边**那个 `SoulmateData` 里，不在你试跑的空文件夹里。

想用**现有数据**试跑，就把 exe 放到项目根目录（`AI-companion\` 旁边那层，也就是 `SoulMate\`）旁边，或者设环境变量指过去：

```powershell
$env:ECHO_DATA_DIR="C:\Users\Lenovo\Desktop\SoulMate\SoulmateData"
.\Soulmate.exe
```

> 这也解释了为什么改动这个逻辑要小心：它决定用户的数据是放在**看得见的 exe 旁边**，还是**隐藏的 `%APPDATA%`**。前者用户找得到、备份得了，所以是优先项。

### 2. 确认没有把私密数据打进去

```powershell
# 检查 exe 里有没有混进聊天记录或 API Key
Select-String -Path dist\Soulmate.exe -Pattern "conversations","api_key_protected" -Encoding Byte -List
```

`SoulmateData\` 已被 `.gitignore` 排除，但打包时如果工作目录里有残留，`datas` 可能会把它带上。**`soulmate.spec` 的 `datas` 只列了 `assets` 和 `models`，正常不会带上**，但发版前确认一次没坏处。

### 3. 记下体积

如果体积突然暴涨（比如从 386MB 到 800MB），通常是 `collect_all` 多收了一个包。看 `build\Soulmate\warn-Soulmate.txt` 和 `xref-Soulmate.html`。

---

## 四、发 Release

### 1. 定版本号

建议用 `v0.1.0` 这样的语义化版本：

- `v0.x.y` —— 还在早期，接口和人设都可能变
- `v1.0.0` —— 觉得可以让人长期用了

### 2. 在 GitHub 上创建 Release

1. 仓库页右侧 **Releases** → **Create a new release**
2. **Choose a tag** → 输入 `v0.1.0` → **Create new tag on publish**
3. **Release title**：`v0.1.0`
4. **Describe this release**：写这一版做了什么。可以直接用 git log：

   ```powershell
   git log --oneline --no-merges v0.0.9..HEAD
   ```

5. **Attach binaries**：把 `dist\Soulmate.exe` 拖进去
6. **Publish release**

### 3. 附件大小限制

GitHub Release 单个附件上限 **2GB**，`Soulmate.exe` 的 386MB 没问题。但注意：

> **别人下载 386MB 会很慢。** 如果以后想瘦身，可以考虑：
> - 不把 `models/` 打进去（省 92MB），改成首次运行时自动下载
> - 用 `--onedir` 代替单文件（启动更快、体积相近，但要发压缩包）

---

## 五、发布之后

- **README 里加下载链接**：指向 Releases 页面，别指向具体某个版本的附件（否则以后要改）
- **不要 force push 已经发过 release 的 tag**：已经有人下载了，改动会造成版本和内容对不上
- 用户报"缺 DLL / 起不来"时，先问**是不是在干净目录试的**——十有八九是环境问题

---

## 常见问题

### 打包报 `Failed to initialize cache`

uv 的缓存目录没写权限。设 `UV_CACHE_DIR` 到项目内（见上面第一步）。

### 打包报缺少 `libcrypto-3-x64.dll` / `libssl-3-x64.dll`

spec 里已经从 `sys.base_prefix\DLLs` 手动收集了。如果仍然报，检查这个目录下是不是真有这两个 DLL。

### exe 双击报 `Could not create temporary directory!`

**这是发版前必须知道的一个坑。**

单文件（onefile）exe 每次启动都要把自己 344MB 解压到一个新的 `%TEMP%\_MEIxxxx` 目录再执行。这个"自己解压自己再运行"的行为**正是杀毒软件启发式重点拦截的模式**，火绒 / 360 / 腾讯电脑管家 / 卡巴斯基 都可能直接拦掉，用户只会看到一个光秃秃的报错框：

```
Error
Could not create temporary directory!
```

`%TEMP%` 被组策略锁死、或指向不存在的路径时，也会报同一个错。

**解决办法已经写进 `soulmate.spec`**：

```python
runtime_tmpdir='.',
```

让 exe 解压到**自己旁边**，而不是系统 `%TEMP%`。这样绕开了杀软对临时目录的监控，而且仍然是单文件分发。

**代价（要写进发布说明告诉用户）**：

| 事项 | 说明 |
| --- | --- |
| exe 必须放在**可写目录** | 桌面、文档、U 盘都行；**不能放 `Program Files`** |
| 运行时会多一个 `_MEIxxxx` 文件夹 | 就在 exe 旁边，**退出时自动删除** |
| 首次启动慢 | 要解压 344MB，之后正常 |

如果加了这个配置**仍然被拦**，退路是发**文件夹版**（onedir）——它启动时不解压任何东西，杀软没有理由拦：

```powershell
# 在 spec 里把 EXE(...) 的 binaries/datas 移到 COLLECT(...)，然后：
.venv\Scripts\python.exe -m PyInstaller soulmate_onedir.spec --noconfirm
# 产物是 dist\Soulmate\ 文件夹，压成 zip 发给用户
```


多半是 `assets/` 没打进去。确认 spec 的 `datas` 里有 `('assets', 'assets')`。

### 双击闪一下就没了（无控制台版本看不到报错）

临时把 spec 里的 `console=False` 改成 `console=True` 重新打包，就能看到报错。定位完再改回去。
