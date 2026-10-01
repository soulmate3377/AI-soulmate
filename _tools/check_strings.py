"""
Compare STRING tokens only, to prove prompt strings were not touched.

只比对 STRING token，证明提示词字符串没被改动。

Comment rewriting must never alter runtime strings. The comment checker
allows comment lines and blank lines to move around, so this is a separate,
narrower check: every string literal, byte for byte.
注释改写不该碰运行时字符串。校验脚本允许注释行和空行移动，所以这里单独
做一个更窄的检查：每一个字符串字面量，逐字比对。

Usage / 用法
    python _tools/check_strings.py
"""

import subprocess
import sys
import tokenize
from io import BytesIO, StringIO
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GIT = r"D:\Git\cmd\git.exe"

# Files known to hold runtime prompt bodies.
# 已知含有运行时提示词正文的文件。
FOCUS = [
    "core/emotion.py",
    "core/personality.py",
    "memory/memory_analyzer.py",
    "prompt/builder.py",
    "core/perception.py",
    "memory/memory_pipeline.py",
]


def strings_of(text):
    """
    All STRING token values, in order.

    按顺序取出所有 STRING token 的值。
    """

    out = []
    for tok in tokenize.generate_tokens(StringIO(text).readline):
        if tok.type == tokenize.STRING:
            out.append(tok.string)
    return out


def is_subsequence(old, new):
    """
    True when every old item still appears, in order, inside new.

    当旧的每一项仍然按原顺序出现在 new 里时为真。

    Used to tell "strings were only added" (fine, e.g. new log messages)
    apart from "an existing string was rewritten or deleted" (a real risk).
    用来区分「只是新增了字符串」（正常，例如新的日志文案）和
    「原有字符串被改写或删除」（真正的风险）。
    """

    it = iter(new)
    return all(any(x == y for y in it) for x in old)


def main():
    all_files = subprocess.run(
        [GIT, "-C", str(REPO), "ls-files", "*.py"],
        capture_output=True, text=True, check=True,
    ).stdout.split()

    # Check every tracked .py file, not just the prompt-bearing ones.
    # 检查全部跟踪的 .py 文件，而不只是含提示词的那几个。
    targets = [f for f in all_files if f != "_tools/check_strings.py"]

    changed = 0
    grown = 0
    added_map = {}

    for rel in targets:
        old_raw = subprocess.run(
            [GIT, "-C", str(REPO), "show", f"HEAD:{rel}"],
            capture_output=True, check=True,
        ).stdout.decode("utf-8")
        new_raw = (REPO / rel).read_text(encoding="utf-8")

        a = strings_of(old_raw)
        b = strings_of(new_raw)

        # Normalize CRLF inside strings so a checkout artifact is not a failure.
        # 归一化字符串内部的 CRLF，避免检出差异被误判。
        a = [s.replace("\r\n", "\n") for s in a]
        b = [s.replace("\r\n", "\n") for s in b]

        if a == b:
            continue

        if is_subsequence(a, b):
            # Only additions: every original string survived untouched.
            # 只有新增：原有字符串全部原样保留。
            grown += 1
            added = len(b) - len(a)
            added_map[rel] = added
            print(f"ADDED    {rel}  (+{added} new strings, all {len(a)} originals kept)")
        else:
            changed += 1
            print(f"CHANGED  {rel}")
            missing = [s for s in a if s not in b]
            print(f"           {len(missing)} original string(s) no longer present")
            for s in missing[:5]:
                print(f"             - {s!r}"[:160])

    print()
    print(f"files with added strings only : {grown}")
    print(f"files where a string changed  : {changed}")
    print()
    print("RESULT:", "PASS - no existing string was modified or removed"
          if not changed else f"FAIL - {changed} file(s) lost or rewrote a string")
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
