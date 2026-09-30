# web_server.py
#
# EchoLover Web 版服务端。
#
# ==================================================
# 这是什么
# --------------------------------------------------
# 手机上没法跑 Windows exe，但可以跑浏览器。
# 这个文件把 EchoLover 的大脑（Brain：记忆、性格、
# 理解、输出、主动消息）原样暴露成 HTTP 服务，
# 手机浏览器连进来就是一个聊天界面。
#
# 记忆完全不动：和桌面版共用同一个
# ECHO_DATA_DIR，385 条记忆原样接着用。
#
# ==================================================
# 零新增依赖
# --------------------------------------------------
# 只用 Python 标准库（http.server / threading /
# secrets / json）。
# 这样家里电脑现在就能跑，
# 以后搬去云服务器也只需要 EchoLover 本来的
# 那几个依赖（openai / faiss / sentence-transformers），
# 不用为了一个 Web 框架再装东西。
#
# ==================================================
# 接口
# --------------------------------------------------
#   POST /api/login   {passcode}      → {token}
#   GET  /api/history?limit=200       → 聊天记录
#   POST /api/chat    {message}       → 流式文本
#   GET  /api/poll?seq=N              → 她主动说的话
#   GET  /api/status                  → 顶栏状态
#   GET  /                            → 手机端页面
#
# ==================================================
# 安全
# --------------------------------------------------
# 服务器开在 0.0.0.0，等于对整个局域网可见，
# 以后上公网更是全世界可见——
# 所以所有 /api/* 都要过 token。
# 密码第一次启动自动生成，
# 存在数据目录 web_passcode.txt，
# 同时打印在控制台上。
#
# ==================================================
# 一个必须知道的限制
# --------------------------------------------------
# 桌面版和 Web 版**不要同时开**。
# 两边共用 conversations.json 等文件，
# 同时写会互相覆盖（最后写的赢，
# 中间那条会丢）。
# 用哪个开哪个。
# ==================================================

import json
import os
import re
import secrets
import socket
import sys
import threading
import time

from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)

from datetime import datetime


# 脚本在项目根目录下跑，
# 保证 core/ memory/ prompt/ 能被找到

sys.path.insert(
    0, os.path.dirname(
        os.path.abspath(__file__)
    )
)

from core.paths import (
    data_dir,
    resource_path,
)

from core.runlock import (
    acquire as _lock_acquire,
)


# =========================
# 防双开：
# 必须在加载大脑之前检查，
# 否则白等几十秒模型加载
# 才发现开重了。
# =========================

_ok, _running = _lock_acquire(
    "web"
)

if not _ok:

    print()
    print("=" * 46)
    print(" 开不了：%s正在运行" % _running)
    print("=" * 46)
    print()
    print(" 桌面版和手机端服务共用同一份")
    print(" 聊天记录，同时开会互相覆盖、")
    print(" 中间的消息会丢。")
    print()
    print(" 先关掉正在用的那个，再重开。")
    print()

    sys.exit(1)


# =========================
# 配置
# =========================

PORT = int(
    os.environ.get(
        "ECHO_WEB_PORT", "8787"
    )
)

# token 有效期：30 天
# （手机上每次都输密码会烦死人）

TOKEN_DAYS = 30

_SESSIONS = {}

_sessions_lock = threading.Lock()


# =========================
# 密码与 token
# =========================

def _passcode_file():

    return (
        data_dir() / "web_passcode.txt"
    )


def get_passcode():
    """
    读密码；没有就生成一个存下。
    6 位数字——手机上好输，
    密度对这个场景够用
    （token 之外还有网络层）。
    """

    path = _passcode_file()

    try:

        with open(
            path, "r", encoding="utf-8"
        ) as f:

            code = f.read().strip()

        if re.fullmatch(
            r"\d{6}", code
        ):

            return code

    except OSError:

        pass

    code = "".join(
        secrets.choice("0123456789")
        for _ in range(6)
    )

    path.parent.mkdir(
        parents=True, exist_ok=True
    )

    with open(
        path, "w", encoding="utf-8"
    ) as f:

        f.write(code)

    return code


def make_token():

    token = secrets.token_urlsafe(32)

    with _sessions_lock:

        _SESSIONS[token] = (
            time.time()
            + TOKEN_DAYS * 86400
        )

    return token


def check_token(token):

    if not token:

        return False

    with _sessions_lock:

        exp = _SESSIONS.get(token)

        if exp is None:

            return False

        if time.time() > exp:

            _SESSIONS.pop(token, None)

            return False

    return True


# =========================
# 事件队列：
# 手机端轮询拿新消息用
# =========================

_events = []

_events_lock = threading.Lock()

_event_seq = 0


def push_event(role, content):
    """
    一条新消息（主要是她主动说的话）。
    手机带着上次拿到的 seq 来要增量。
    """

    global _event_seq

    with _events_lock:

        _event_seq += 1

        _events.append({
            "seq": _event_seq,
            "time": datetime.now()
            .strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "role": role,
            "content": content,
        })

        # 内存里只留最近 200 条，
        # 完整历史在 conversations.json

        del _events[:-200]


def events_after(seq):

    with _events_lock:

        return [
            e for e in _events
            if e["seq"] > seq
        ]


# =========================
# 大脑
#
# 启动就建好（加载 embedding
# 模型要几秒，来一个请求才建
# 会让人等出错觉）。
#
# brain 不是线程安全的：
# 同一时间只允许一个调用
# 在跑（聊天 / 主动消息共用
# 一把锁）。
# =========================

print("正在启动 EchoLover 的大脑……")

from core.brain import Brain

brain = Brain()

from memory.conversation import (
    ConversationManager
)

conversations = ConversationManager()


_brain_lock = threading.RLock()


# =========================
# 主动消息线程
#
# 桌面版 60 秒查一次守门人，
# 这里照抄。
# =========================

def _proactive_loop():

    while True:

        time.sleep(60)

        try:

            with _brain_lock:

                result = (
                    brain.scheduler
                    .run_once()
                )

            text = (
                result or {}
            ).get("text")

            if text:

                # 和桌面版一样：
                # 落盘 + 通知界面

                conversations.add_message(
                    "echo", text
                )

                push_event(
                    "echo", text
                )

        except Exception as e:

            print(
                "主动消息检查失败:",
                e
            )


threading.Thread(
    target=_proactive_loop,
    daemon=True,
).start()


# =========================
# 顶栏状态
# =========================

def presence_text():

    try:

        from core.presence import (
            activity_text
        )

        return activity_text()

    except Exception:

        return "在线"


# =========================
# HTTP
# =========================

# 手机端页面目录：
# 打包后 web/ 在 _MEIPASS 里
# （spec 的 datas 打进去），
# 开发时在脚本旁边。

def _find_web_dir():

    p = resource_path("web")

    if os.path.isdir(p):

        return p

    return os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)
        ),
        "web",
    )


_WEB_DIR = _find_web_dir()

# PWA 静态资源白名单。
# 浏览器自己来拉，带不了
# token，但只有这几个
# 固定名字，目录外的东西
# 一律不伺服。

_STATIC_FILES = {
    "/manifest.webmanifest":
        "application/manifest+json",
    "/icon-192.png":
        "image/png",
    "/icon-512.png":
        "image/png",
    "/icon-512-maskable.png":
        "image/png",
    "/apple-touch-icon.png":
        "image/png",
    "/favicon.ico":
        "image/x-icon",
}


class Handler(
    BaseHTTPRequestHandler
):

    # HTTP/1.1，正确的 keep-alive
    # 语义（流式回复靠
    # Connection: close 收尾）

    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):

        # 只记 /api，静态资源
        # 的请求刷屏没意义

        if "/api/" in self.path:

            print(
                "%s %s"
                % (
                    self.command,
                    self.path,
                )
            )

    # --------------------
    # 工具
    # --------------------

    def _send_json(
        self, obj, status=200
    ):

        body = json.dumps(
            obj, ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; "
            "charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.end_headers()

        self.wfile.write(body)

    def _authed(self):

        token = (
            self.headers.get(
                "X-Echo-Token"
            )
            or ""
        )

        if check_token(token):

            return True

        self._send_json(
            {"error": "unauthorized"},
            status=401,
        )

        return False

    def _body_json(self):

        length = int(
            self.headers.get(
                "Content-Length"
            ) or 0
        )

        if length <= 0:

            return {}

        raw = self.rfile.read(
            length
        )

        try:

            return json.loads(
                raw.decode("utf-8")
            )

        except ValueError:

            return {}

    # --------------------
    # GET
    # --------------------

    def do_GET(self):

        path = self.path.split("?")[0]

        # ---- 手机页面（无需
        #      token，页面上
        #      自己会要密码）----

        if path in ("/", "/index.html"):

            self._serve_index()

            return

        # ---- PWA 资源（manifest /
        #      图标），浏览器自动
        #      拉取，带不了 token ----

        if path in _STATIC_FILES:

            self._serve_static(path)

            return

        if path == "/api/login":

            # login 是 POST 的，
            # GET 不该到这

            self._send_json(
                {"error": "post only"},
                status=405,
            )

            return

        # ---- 以下全部要 token ----

        if not self._authed():

            return

        if path == "/api/history":

            limit = 200

            try:

                q = self.path.split(
                    "?"
                )[1]

                for kv in q.split("&"):

                    k, _, v = (
                        kv.partition("=")
                    )

                    if k == "limit":

                        limit = min(
                            500,
                            max(
                                1,
                                int(v),
                            ),
                        )

            except (IndexError, ValueError):

                pass

            self._send_json({
                "messages":
                    conversations
                    .get_recent(limit),
            })

            return

        if path == "/api/poll":

            seq = 0

            try:

                q = self.path.split(
                    "?"
                )[1]

                for kv in q.split("&"):

                    k, _, v = (
                        kv.partition("=")
                    )

                    if k == "seq":

                        seq = int(v)

            except (IndexError, ValueError):

                pass

            self._send_json({
                "messages":
                    events_after(seq),
            })

            return

        if path == "/api/status":

            self._send_json({
                "name": "Echo",
                "status": presence_text(),
            })

            return

        self._send_json(
            {"error": "not found"},
            status=404,
        )

    def _serve_static(self, path):
        """
        伺服白名单里的静态资源。
        """

        name = path.lstrip("/")

        full = os.path.join(
            _WEB_DIR, name
        )

        ctype = _STATIC_FILES.get(
            path, "application/octet-stream"
        )

        try:

            with open(
                full, "rb"
            ) as f:
                body = f.read()

        except OSError:
            self._send_json(
                {"error": "not found"},
                status=404,
            )
            return

        self.send_response(200)

        self.send_header(
            "Content-Type", ctype
        )

        self.send_header(
            "Cache-Control",
            "max-age=86400",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.end_headers()

        self.wfile.write(body)

    def _serve_index(self):

        index = os.path.join(
            _WEB_DIR, "index.html"
        )

        try:

            with open(
                index, "rb"
            ) as f:

                body = f.read()

        except OSError:

            self._send_json(
                {"error": "no index.html"},
                status=500,
            )

            return

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.end_headers()

        self.wfile.write(body)

    # --------------------
    # POST
    # --------------------

    def do_POST(self):

        path = self.path.split("?")[0]

        if path == "/api/login":

            body = self._body_json()

            code = str(
                body.get("passcode")
                or ""
            ).strip()

            if code == get_passcode():

                self._send_json({
                    "token":
                        make_token()
                })

            else:

                # 错密码睡 0.6 秒，
                # 让暴力试码
                # 变得不值得

                time.sleep(0.6)

                self._send_json(
                    {"error": "wrong"},
                    status=401,
                )

            return

        if not self._authed():

            return

        if path == "/api/chat":

            self._do_chat()

            return

        self._send_json(
            {"error": "not found"},
            status=404,
        )

    def _do_chat(self):

        body = self._body_json()

        message = str(
            body.get("message") or ""
        ).strip()

        if not message:

            self._send_json(
                {"error": "empty"},
                status=400,
            )

            return

        # 消息太长的当异常挡掉
        # （正常聊天不会超过）

        if len(message) > 2000:

            self._send_json(
                {"error": "too long"},
                status=400,
            )

            return

        # 用户消息先落盘
        # （和桌面版同时序）

        conversations.add_message(
            "user", message
        )

        # ---- 流式回复 ----
        #
        # Connection: close + 不给
        # Content-Length，
        # 客户端读到 EOF 即完整。

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )

        self.send_header(
            "Connection", "close"
        )

        self.end_headers()

        self.close_connection = True

        parts = []

        try:

            with _brain_lock:

                for delta in (
                    brain.think_stream(
                        message
                    )
                ):

                    parts.append(delta)

                    self.wfile.write(
                        delta.encode(
                            "utf-8"
                        )
                    )

                    self.wfile.flush()

        except (BrokenPipeError,
                ConnectionResetError):

            # 手机锁屏 / 切后台
            # 会把连接掐了。
            # 她的话继续生成完
            # 并落盘，只是这次
            # 没送到屏幕上。

            pass

        except Exception as e:

            print("聊天失败:", e)

        full = "".join(parts)

        if full:

            conversations.add_message(
                "echo", full
            )

            push_event(
                "echo", full
            )


# =========================
# 局域网 IP：
# 手机上要输的就是这个
# =========================

def lan_ip():

    try:

        s = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )

        # 不真的发包，
        # 只是让系统挑路由

        s.connect(
            ("8.8.8.8", 80)
        )

        ip = s.getsockname()[0]

        s.close()

        return ip

    except OSError:

        return "127.0.0.1"


def main():

    code = get_passcode()

    server = ThreadingHTTPServer(
        ("0.0.0.0", PORT), Handler
    )

    print()
    print("=" * 46)
    print(" Echo Web 版已启动")
    print("=" * 46)
    print()
    print(" 手机和电脑连同一个 WiFi，")
    print(" 手机浏览器打开：")
    print()
    print(
        "     http://%s:%d"
        % (lan_ip(), PORT)
    )
    print()
    print(" 密码（6 位）：%s" % code)
    print(
        "   （存在 %s）"
        % _passcode_file()
    )
    print()
    print(" 记忆目录：%s" % data_dir())
    print(" 桌面版和本服务不要同时开。")
    print(" Ctrl+C 停止。")
    print()

    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print()
        print("已停止。")


if __name__ == "__main__":

    main()
