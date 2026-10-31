# -*- coding: utf-8 -*-
"""主动守护（通用版）：定时检查断点/回执/同步状态，命中异常即记录并可选通知。

用法:
  python tools/watchdog.py --once
  python tools/watchdog.py --daemon --interval 300
"""
import sys, io, os, json, subprocess, time, argparse, datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
LOG = os.path.join(ROOT, "out", "watchdog.log")


def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=ROOT)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 99, str(e)


def check_blocked():
    code, out = run([PY, "tools/checkpoint.py", "get"])
    txt = out.strip()
    if any(k in txt for k in ("BLOCKED", "卡住", "失败", "blocked")):
        return f"断点存在阻塞: {txt[:60]}"
    return None


def check_failed_receipts():
    import glob
    files = glob.glob(os.path.join(ROOT, "out", "receipt_*.md")) + glob.glob(os.path.join(ROOT, "out", "**", "receipt_*.md"), recursive=True)
    latest = {}
    for f in files:
        m = re.search(r"receipt_(T\d+)", os.path.basename(f))
        key = m.group(1) if m else os.path.basename(f)
        if key not in latest or os.path.getmtime(f) > os.path.getmtime(latest[key]):
            latest[key] = f
    for f in latest.values():
        try:
            head = open(f, encoding="utf-8", errors="replace").read(300)
        except Exception:
            continue
        if "FAIL" in head or "BLOCKED" in head:
            return f"最新回执未通过: {os.path.basename(f)}"
    return None


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts} {msg}\n")
    print(f"[{ts}] {msg}")


def one_round():
    hits = [h for h in (check_blocked(), check_failed_receipts()) if h]
    if not hits:
        log("OK 无异常")
    for h in hits:
        log(h)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--interval", type=int, default=300)
    a = ap.parse_args()
    if a.once or not a.daemon:
        one_round(); return 0
    while True:
        one_round(); time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
