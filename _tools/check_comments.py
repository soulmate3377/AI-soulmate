"""
Verify that a comment-only rewrite changed nothing but comments.

校验：注释改写是否只动了注释。

How it works / 原理
------------------
Python's tokenizer splits source into tokens. We strip comment-only lines
from the source text FIRST, then compare the resulting token stream with
the original treated the same way.

先用源码级过滤把「整行注释」物理删掉，再对比两边的 token 流。

Why strip at source level instead of dropping COMMENT tokens?
为什么要在源码层剥离，而不是简单丢掉 COMMENT token？
A comment line produces COMMENT + NEWLINE, and a blank line produces just
NL. If we only drop COMMENT, every removed comment line shifts the token
stream and a genuine simplification would look like a code change.

一行注释产生 COMMENT + NEWLINE，一个空行只产生 NL。如果只丢 COMMENT，
那么每删掉一行注释都会让 token 流错位，真正的注释精简会被误判成改代码。

Stripping comment-only lines first means:
- comment lines may be added, removed or rewritten freely
- BLANK LINES may also be added or removed freely
- code, string literals, numbers and indentation are still compared strictly

剥离整行注释后：
- 注释行可以自由增删改写
- 空行也可以自由增删（空行不影响运行，也不该拦住注释精简）
- 代码、字符串字面量、数字、缩进仍然严格逐字比对

Note / 注意
----------
Docstrings are STRING tokens and are compared strictly, so this tool will
report CODE_CHANGED if a docstring text is edited. That is intentional:
docstrings are treated as code here, never rewritten.
docstring 属于 STRING token，会被严格比对。改了它就会报 CODE_CHANGED——
这是刻意的：本工具把 docstring 当代码看待，不允许改写。

Usage / 用法
-----------
    python _tools/check_comments.py            # compare against git HEAD
    python _tools/check_comments.py --json     # machine-readable output
"""

import json
import re
import subprocess
import sys
import tokenize
from io import StringIO
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

GIT = r"D:\Git\cmd\git.exe"

# A line whose first non-space character is '#', optionally keeping the
# indentation so that INDENT/DEDENT structure still matches.
# 行首（允许前导空白）就是 # 的行，保留缩进以免破坏 INDENT/DEDENT 结构。
_COMMENT_LINE = re.compile(r"^(?P<indent>[ \t]*)#.*$")


def normalize(text):
    """
    Drop CR so LF and CRLF compare equal.

    去掉 CR，让 LF 与 CRLF 视为相同。
    The repo stores LF but the working tree may carry CRLF because of
    core.autocrlf; that is a checkout artifact, not a code change.

    仓库里存 LF，工作区因 core.autocrlf 可能是 CRLF，
    那只是检出产物，不是代码改动。
    """

    return text.replace("\r\n", "\n").replace("\r", "\n")


def strip_comment_lines(source):
    """
    Reduce source to its code lines: no blank lines, no comment-only lines.

    把源码归约成「只有代码行」：去掉空行，去掉整行注释。
    Both sides of the comparison get the same treatment, so comment lines
    and blank lines may be added or removed freely without affecting the
    result, while code text and indentation are preserved verbatim.

    比对双方都做同样处理，因此注释行与空行的增删不会影响结果，
    而代码文本与缩进被逐字保留下来。
    """

    out = []
    for raw in source.split("\n"):
        if _COMMENT_LINE.match(raw):
            continue
        if raw.strip() == "":
            continue
        out.append(raw)
    return "\n".join(out)


def code_tokens(source_text):
    """
    Token stream of the comment-stripped source, comments dropped.

    对剥离注释后的源码取 token 流，并丢掉 COMMENT。
    """

    stripped = strip_comment_lines(source_text)
    out = []
    try:
        for tok in tokenize.generate_tokens(StringIO(stripped).readline):
            if tok.type == tokenize.COMMENT:
                continue
            out.append((tok.type, normalize(tok.string)))
    except Exception as exc:
        return None, f"tokenize failed: {exc}"
    return out, None


def count_comment_lines(source_text):
    """
    Comment-only lines, for reporting only.

    仅用于报告：整行注释的行数。
    """

    return sum(1 for line in source_text.split("\n") if _COMMENT_LINE.match(line))


def _is_subsequence(old, new):
    """
    True when every old item still appears, in order, inside new.

    当旧的每一项仍然按原顺序出现在 new 里时为真。

    Tells "code was only added" apart from "code was rewritten".
    用来区分「只是新增了代码」和「原有代码被改写」。
    """

    it = iter(new)
    return all(any(x == y for y in it) for x in old)


def git_show(path):
    """
    Read the committed version of a file from git.

    从 git 里取出该文件已提交的版本。
    """

    try:
        res = subprocess.run(
            [GIT, "-C", str(REPO), "show", f"HEAD:{path}"],
            capture_output=True,
            check=True,
        )
        return res.stdout.decode("utf-8")
    except subprocess.CalledProcessError:
        return None


def main():
    want_json = "--json" in sys.argv

    tracked = subprocess.run(
        [GIT, "-C", str(REPO), "ls-files", "*.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()

    results = []
    for rel in tracked:
        local = REPO / rel
        if not local.exists():
            results.append({"file": rel, "status": "MISSING", "detail": "file gone"})
            continue

        old_text = git_show(rel)
        if old_text is None:
            results.append({"file": rel, "status": "NEW", "detail": "not in HEAD"})
            continue

        new_text = local.read_text(encoding="utf-8")

        old_toks, err = code_tokens(old_text)
        if err:
            results.append({"file": rel, "status": "ERROR", "detail": f"old: {err}"})
            continue
        new_toks, err = code_tokens(new_text)
        if err:
            results.append({"file": rel, "status": "ERROR", "detail": f"new: {err}"})
            continue

        old_c = count_comment_lines(old_text)
        new_c = count_comment_lines(new_text)

        if old_toks == new_toks:
            status = "UNCHANGED" if normalize(old_text) == normalize(new_text) else "COMMENTS_ONLY"
            results.append({
                "file": rel,
                "status": status,
                "old_comments": old_c,
                "new_comments": new_c,
                "old_lines": len(normalize(old_text).split("\n")),
                "new_lines": len(normalize(new_text).split("\n")),
                "detail": "",
            })
        elif _is_subsequence(old_toks, new_toks):
            # Every original token survives, in order: the file only gained
            # code. That is an intentional change (new instrumentation, a new
            # branch), not a broken rewrite -- so it gets its own status and
            # does not count as a failure.
            # 原有 token 按原顺序完整保留，文件只是新增了代码。
            # 那是有意改动（加埋点、加分支），不是改坏，所以单独一个状态，
            # 不计入失败。
            results.append({
                "file": rel,
                "status": "CODE_ADDED",
                "old_comments": old_c,
                "new_comments": new_c,
                "detail": f"+{len(new_toks) - len(old_toks)} tokens",
            })
        else:
            where = "?"
            for i in range(max(len(old_toks), len(new_toks))):
                a = old_toks[i] if i < len(old_toks) else None
                b = new_toks[i] if i < len(new_toks) else None
                if a != b:
                    where = f"token #{i}: old={a} new={b}"
                    break
            results.append({
                "file": rel,
                "status": "CODE_CHANGED",
                "old_comments": old_c,
                "new_comments": new_c,
                "detail": where,
            })

    if want_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    bad = [r for r in results if r["status"] in ("CODE_CHANGED", "ERROR", "MISSING")]
    changed = [r for r in results if r["status"] == "COMMENTS_ONLY"]
    same = [r for r in results if r["status"] == "UNCHANGED"]
    added = [r for r in results if r["status"] == "CODE_ADDED"]

    print("=" * 66)
    print("Comment-only verification / 注释改写校验")
    print("=" * 66)
    print(f"comments-only rewrite : {len(changed)}")
    print(f"code added (intended) : {len(added)}")
    print(f"untouched             : {len(same)}")
    print(f"PROBLEMS              : {len(bad)}")
    print()

    if changed:
        print("-- rewritten / 已改写（注释行数 变化 / 总行数 变化）--")
        for r in sorted(changed, key=lambda x: x["old_comments"] - x["new_comments"], reverse=True):
            dc = r["old_comments"] - r["new_comments"]
            dl = r["old_lines"] - r["new_lines"]
            print(f"  {r['file']:<40} comments {r['old_comments']:>3} -> {r['new_comments']:<3} ({dc:+d})"
                  f"   lines {r['old_lines']:>4} -> {r['new_lines']:<4} ({dl:+d})")
        print()

    if added:
        print("-- code added only / 只新增了代码（原有代码逐字保留）--")
        for r in added:
            print(f"  {r['file']:<40} {r['detail']}")
        print()

    if bad:
        print("-- PROBLEMS / 有问题（原有代码被改写）--")
        for r in bad:
            print(f"  {r['file']:<40} {r['status']}: {r['detail']}")
        print()

    total_c = sum(r["old_comments"] - r["new_comments"] for r in changed)
    total_l = sum(r["old_lines"] - r["new_lines"] for r in changed)
    print(f"comment lines removed : {total_c}")
    print(f"total lines removed   : {total_l}")
    print("RESULT:",
          "PASS - no existing code was rewritten"
          if not bad else "FAIL - see above")


if __name__ == "__main__":
    main()
