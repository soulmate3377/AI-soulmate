"""
Verify that a comment-only rewrite changed nothing but comments.

校验：注释改写是否只动了注释。

How it works / 原理
------------------
Python's own tokenizer splits source into tokens. We keep every token
EXCEPT COMMENT, and compare the remaining stream with the original.
If the streams match, no code, string, number or indentation changed.

用 Python 官方 tokenizer 把源码切成 token，丢掉 COMMENT 后对比原始文件。
token 流一致 => 代码、字符串、数字、缩进全都没变。

Usage / 用法
-----------
    python _tools/check_comments.py            # compare against git HEAD
    python _tools/check_comments.py --json     # machine-readable output
"""

import json
import subprocess
import sys
import tokenize
from io import BytesIO
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

GIT = r"D:\Git\cmd\git.exe"


def code_tokens(source_bytes):
    """
    Return the token stream with comments dropped.

    返回剔除 COMMENT 后的 token 流。
    Comments carry no runtime meaning, so dropping only them keeps the
    comparison strict about everything else.

    注释不影响运行，所以只丢它，其余一律严格比对。
    """

    out = []
    try:
        for tok in tokenize.tokenize(BytesIO(source_bytes).readline):
            if tok.type == tokenize.COMMENT:
                continue
            out.append((tok.type, tok.string))
    except Exception as exc:
        return None, f"tokenize failed: {exc}"
    return out, None


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
        return res.stdout
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

        old_bytes = git_show(rel)
        if old_bytes is None:
            results.append({"file": rel, "status": "NEW", "detail": "not in HEAD"})
            continue

        new_bytes = local.read_bytes()

        old_toks, err = code_tokens(old_bytes)
        if err:
            results.append({"file": rel, "status": "ERROR", "detail": f"old: {err}"})
            continue
        new_toks, err = code_tokens(new_bytes)
        if err:
            results.append({"file": rel, "status": "ERROR", "detail": f"new: {err}"})
            continue

        # Count comment lines so we can report how much was rewritten.
        old_comments = sum(
            1 for t in tokenize.tokenize(BytesIO(old_bytes).readline)
            if t.type == tokenize.COMMENT
        )
        new_comments = sum(
            1 for t in tokenize.tokenize(BytesIO(new_bytes).readline)
            if t.type == tokenize.COMMENT
        )

        if old_toks == new_toks:
            changed = old_bytes != new_bytes
            results.append({
                "file": rel,
                "status": "COMMENTS_ONLY" if changed else "UNCHANGED",
                "old_comments": old_comments,
                "new_comments": new_comments,
                "detail": "",
            })
        else:
            # Locate the first divergence to make fixing easy.
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
                "detail": where,
            })

    if want_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    bad = [r for r in results if r["status"] in ("CODE_CHANGED", "ERROR", "MISSING")]
    changed = [r for r in results if r["status"] == "COMMENTS_ONLY"]
    same = [r for r in results if r["status"] == "UNCHANGED"]

    print("=" * 62)
    print("Comment-only verification / 注释改写校验")
    print("=" * 62)
    print(f"comments-only rewrite : {len(changed)}")
    print(f"untouched             : {len(same)}")
    print(f"PROBLEMS              : {len(bad)}")
    print()

    if changed:
        print("-- rewritten (comments only) / 已改写 --")
        for r in changed:
            print(f"  {r['file']:<42} comments {r['old_comments']} -> {r['new_comments']}")
        print()

    if bad:
        print("-- PROBLEMS / 有问题 --")
        for r in bad:
            print(f"  {r['file']:<42} {r['status']}: {r['detail']}")
        print()

    total_reduction = sum(r["old_comments"] - r["new_comments"] for r in changed)
    print(f"comment lines removed: {total_reduction}")
    print("RESULT:", "PASS - code untouched" if not bad else "FAIL - see above")


if __name__ == "__main__":
    main()
