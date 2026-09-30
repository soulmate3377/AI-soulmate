"""
Prove a YAML edit touched only comments.

证明 YAML 的改动只碰了注释。

Strip comments and blank lines from both files and compare what is left,
byte for byte. If the data lines match exactly, no key or value changed.
把两个文件的注释行和空行都剔掉，剩下的逐字比对。数据行完全一致 => 键和值都没动。

Usage / 用法
    python _tools/check_yaml.py <old> <new>
"""

import sys
from pathlib import Path


def data_lines(path):
    """
    Non-comment, non-blank lines, CRLF-normalised.

    剔除注释行与空行后的内容行，并归一化换行。
    """

    text = Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")
    out = []
    for raw in text.split("\n"):
        if raw.lstrip().startswith("#"):
            continue
        if raw.strip() == "":
            continue
        out.append(raw)
    return out


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2

    old = data_lines(sys.argv[1])
    new = data_lines(sys.argv[2])

    print(f"old data lines: {len(old)}")
    print(f"new data lines: {len(new)}")

    if old == new:
        print("RESULT: PASS - YAML data identical, only comments changed")
        return 0

    print("RESULT: FAIL - data differs")
    for i in range(max(len(old), len(new))):
        a = old[i] if i < len(old) else None
        b = new[i] if i < len(new) else None
        if a != b:
            print(f"  first difference at line #{i}")
            print(f"    old: {a!r}")
            print(f"    new: {b!r}")
            break
    return 1


if __name__ == "__main__":
    sys.exit(main())
