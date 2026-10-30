# -*- coding: utf-8 -*-
"""公开前隐私扫描：跟踪文件里的 QQ 号/名字/本机路径/密钥/evidence。"""
import pathlib
import re
import sys

PATTERNS = [
    ("qq_number", re.compile(r"private:\d{5,12}")),
    ("qq_bare", re.compile(r"(?:private:|QQ|qq)[^\d]{0,12}\d{8,11}")),
    ("windows_path", re.compile(r"[A-Za-z]:\\\\")),
    ("user_dir", re.compile(r"C:\\\\Users\\\\[A-Za-z0-9_.-]+")),
    ("name", re.compile("程莫雯")),
    ("token", re.compile(r"sk-[A-Za-z0-9]{16,}")),
    ("api_key", re.compile(r"api[_-]?key['\"]?\s*[:=]\s*['\"][^'\"]{16,}")),
]
SKIP = {".git", "evidence", "__pycache__"}


def scan(root):
    hits = []
    for p in pathlib.Path(root).rglob("*"):
        if not p.is_file() or any(s in p.parts for s in SKIP):
            continue
        if p.suffix not in (".py", ".md", ".json", ".mjs", ".js", ".ps1", ".bat", ".txt", ".yml", ".yaml"):
            continue
        if p.name in ("privacy_scan.py",):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for name, rx in PATTERNS:
                if rx.search(line):
                    hits.append((str(p.relative_to(root)), lineno, name, line.strip()[:100]))
    return hits


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    hits = scan(root)
    for h in hits:
        print("%s:%d [%s] %s" % h)
    print("hits:", len(hits))
    raise SystemExit(1 if hits else 0)
