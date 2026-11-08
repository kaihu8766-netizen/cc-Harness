# -*- coding: utf-8 -*-
"""并行调度器：同时跑多个网关工具（补"并行/多智能体"短板）。

用法：
  python tools/fanout.py --json '[{"tool":"guard.ledger"},{"tool":"brain.brief"},{"tool":"checkpoint.get"}]'
  python tools/fanout.py --json '[...]' --seq        # 顺序执行（对照组）
输出：每个任务的 ok/code/elapsed + 总耗时 + 加速比
"""
import sys, io, os, json, time, subprocess, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state_paths import tmp_dir
from concurrent.futures import ThreadPoolExecutor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


import time as _t
LOCKDIR = os.path.join(tmp_dir(), "locks")


def _acquire_lock(path, timeout=120):
    import time
    os.makedirs(LOCKDIR, exist_ok=True)
    key = str(abs(hash(path)))[:10]
    lp = os.path.join(LOCKDIR, key + ".lock")
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            fd = os.open(lp, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return lp
        except FileExistsError:
            time.sleep(0.1)
    raise TimeoutError(f"锁超时: {path}")


def _release_lock(lp):
    try:
        os.remove(lp)
    except Exception:
        pass


def run_task(task):
    name = task["tool"]
    args = task.get("args") or {}
    t0 = time.time()
    argv = [PY, os.path.join(ROOT, "tools", "gateway.py"), "run", name, "--json", json.dumps(args, ensure_ascii=False), "--raw"]
    locks = []
    wait = 0.0
    for lk in task.get("locks") or []:
        _t0 = _t.time()
        locks.append(_acquire_lock(lk, task.get("lock_timeout", 120)))
        wait += _t.time() - _t0
    try:
        r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=task.get("timeout", 300), cwd=ROOT)
        code, out = r.returncode, (r.stdout or "").strip()
    except Exception as e:
        code, out = 99, str(e)
    finally:
        for lk in locks:
            _release_lock(lk)
    return {"tool": name, "ok": code == 0, "code": code, "elapsed": round(time.time() - t0, 2),
            "lock_wait": round(wait, 2), "stdout": out[-400:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    ap.add_argument("--file", default="")
    ap.add_argument("--seq", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    raw = open(a.file, encoding="utf-8-sig").read() if a.file else a.json
    tasks = json.loads(raw.replace("\ufeff", ""))
    t0 = time.time()
    if a.seq:
        results = [run_task(t) for t in tasks]
    else:
        with ThreadPoolExecutor(max_workers=min(a.workers, max(1, len(tasks)))) as ex:
            results = list(ex.map(run_task, tasks))
    total = round(time.time() - t0, 2)
    serial_sum = round(sum(r["elapsed"] for r in results), 2)
    print(json.dumps({
        "mode": "seq" if a.seq else "parallel",
        "tasks": len(results),
        "ok": sum(1 for r in results if r["ok"]),
        "total_elapsed": total,
        "serial_sum_elapsed": serial_sum,
        "speedup": round(serial_sum / total, 2) if total else 0,
        "results": [{k: r[k] for k in ("tool", "ok", "elapsed")} for r in results],
    }, ensure_ascii=False, indent=1))
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
