# -*- coding: utf-8 -*-
"""上下文检索（FTS5）：把日志/回执/决策/长文入索引，按需检索注入，替代"整段塞上下文"。

用法：
  python tools/ctx_search.py index [--paths glob...]   # 建/更新索引
  python tools/ctx_search.py search "<关键词>" [--limit 5] [--maxchars 500]
  python tools/ctx_search.py stats                    # 索引统计
  python tools/ctx_search.py bench "<关键词>"          # 计时（验收用：应 <50ms）

存储：out/state/context.db（FTS5 虚拟表；中文用 trigram 分词，兼容子串匹配）
"""
import sys, io, os, sqlite3, glob, time, argparse, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state_paths import state_file

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = state_file("context.db")

DEFAULT_GLOBS = [
    "AGENTS.md",
    "docs/*.md",
    "README.md",
    "out/**/*.md",
    "out/**/*.json",
    "out/**/*.txt",
    "out/**/*.log",
]
CHUNK = 400  # 每段字符数


def conn():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB)
    # 优先 trigram（中文子串友好），失败退回 unicode61
    try:
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(path, chunk_no, body, tokenize='trigram')")
    except sqlite3.OperationalError:
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(path, chunk_no, body)")
    c.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    return c


def files_of(patterns):
    out = []
    for pat in patterns:
        full = pat if os.path.isabs(pat) else os.path.join(ROOT, pat)
        out += [f for f in glob.glob(full) if os.path.isfile(f)]
    return sorted(set(out))


def do_index(patterns):
    c = conn()
    c.execute("DELETE FROM docs")
    n_files = n_chunks = 0
    for f in files_of(patterns):
        try:
            txt = open(f, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        rel = os.path.relpath(f, ROOT)
        chunks = [txt[i:i + CHUNK] for i in range(0, len(txt), CHUNK)] or [""]
        for i, ch in enumerate(chunks):
            c.execute("INSERT INTO docs (path, chunk_no, body) VALUES (?,?,?)", (rel, i, ch))
            n_chunks += 1
        n_files += 1
    c.execute("INSERT OR REPLACE INTO meta (k,v) VALUES ('updated', ?)", (time.strftime("%Y-%m-%d %H:%M:%S"),))
    c.commit()
    print(json.dumps({"files": n_files, "chunks": n_chunks, "db": os.path.relpath(DB, ROOT)}, ensure_ascii=False))


def do_search(q, limit=5, maxchars=500):
    c = conn()
    t0 = time.time()
    try:
        rows = c.execute(
            "SELECT path, chunk_no, snippet(docs, 2, '', '', '…', 24) FROM docs WHERE docs MATCH ? ORDER BY rank LIMIT ?",
            (q, limit)).fetchall()
    except sqlite3.OperationalError:
        rows = c.execute("SELECT path, chunk_no, body FROM docs WHERE body LIKE ? LIMIT ?", ("%" + q + "%", limit)).fetchall()
    ms = round((time.time() - t0) * 1000, 1)
    out, total = [], 0
    for path, no, body in rows:
        piece = (body or "").strip()
        if total + len(piece) > maxchars:
            piece = piece[: max(0, maxchars - total)]
        out.append({"path": path, "chunk": no, "text": piece})
        total += len(piece)
    print(json.dumps({"query": q, "hits": len(out), "chars": total, "ms": ms, "results": out}, ensure_ascii=False, indent=1))
    return ms


def do_stats():
    c = conn()
    n = c.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
    paths = c.execute("SELECT COUNT(DISTINCT path) FROM docs").fetchone()[0]
    upd = c.execute("SELECT v FROM meta WHERE k='updated'").fetchone()
    print(json.dumps({"chunks": n, "files": paths, "updated": upd[0] if upd else None}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["index", "search", "stats", "bench"])
    ap.add_argument("q", nargs="?", default="")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--maxchars", type=int, default=500)
    ap.add_argument("--paths", nargs="*", default=None)
    a = ap.parse_args()
    if a.cmd == "index":
        do_index(a.paths or DEFAULT_GLOBS)
        return 0
    if a.cmd == "stats":
        do_stats(); return 0
    if a.cmd == "search":
        do_search(a.q, a.limit, a.maxchars); return 0
    if a.cmd == "bench":
        ms = do_search(a.q, a.limit, a.maxchars)
        return 0 if ms < 50 else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
