# -*- coding: utf-8 -*-
"""单行断点（checkpoint）：始终覆写"当前步 + 卡点"，供上下文重置后凭证开工。

用法：
  python tools/checkpoint.py set "正在做X；已完成Y；卡在Z"     # 覆写（≤100 字）
  python tools/checkpoint.py get                              # 读回
  python tools/checkpoint.py clear
说明：只保留最新一条（brain 规则：单行状态覆写，物理隔绝冗长日志）。
"""
import sys, io, os, sqlite3, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state_paths import state_file

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = state_file("state.db")
MAX = 100


def db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS active_checkpoint (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        step TEXT, blocker TEXT, updated TEXT)""")
    return c


def main():
    if len(sys.argv) < 2:
        print("usage: set <text> | get | clear"); return 2
    cmd = sys.argv[1]
    c = db()
    if cmd == "set":
        text = " ".join(sys.argv[2:]).strip()
        if not text:
            print("REJECT: 空断点"); return 9
        if len(text) > MAX:
            print(f"REJECT: 超过 {MAX} 字（{len(text)}）"); return 9
        now = datetime.datetime.now().isoformat(timespec="seconds")
        c.execute("INSERT INTO active_checkpoint (id, step, blocker, updated) VALUES (1, ?, '', ?) "
                  "ON CONFLICT(id) DO UPDATE SET step=excluded.step, updated=excluded.updated",
                  (text, now))
        c.commit()
        print(f"OK checkpoint: {text}")
    elif cmd == "get":
        row = c.execute("SELECT step, updated FROM active_checkpoint WHERE id=1").fetchone()
        print(row[0] if row else "(无断点)")
    elif cmd == "clear":
        c.execute("DELETE FROM active_checkpoint WHERE id=1"); c.commit()
        print("OK cleared")
    return 0


if __name__ == "__main__":
    sys.exit(main())
