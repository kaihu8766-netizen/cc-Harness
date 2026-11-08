# -*- coding: utf-8 -*-
"""错误台账：自动记录工作过程中的报错 → 归类 → 统计 → 提炼规则（自我升级闭环）。

存储：out/review/errors/error_ledger.jsonl（append-only，永不删）
用法：
  python tools/error_ledger.py add --task "京东改简历" --cmd "upload" --symptom "附件没变化" \
      --cause "盲选 file input index 0" --fix "遍历 input 核对 accept/所属区块" --tag browser
  python tools/error_ledger.py list [--open] [--tag browser] [--limit 20]
  python tools/error_ledger.py stats              # 按标签/状态统计
  python tools/error_ledger.py learn              # 高频错误 → 建议规则行（不自动写）
  python tools/error_ledger.py learn --apply      # 追加到 DISCIPLINE 的"错误台账自动提炼"区
  python tools/error_ledger.py resolve --id 3     # 标记已修复

自动化：gateway.py 工具失败（含自愈后仍失败）会自动 add 一条。
"""
import sys, io, os, json, argparse, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state_paths import errors_dir

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = errors_dir()
LEDGER = os.path.join(DIR, "error_ledger.jsonl")
DISCIPLINE = os.path.join(ROOT, "out", "review", "DISCIPLINE.md")


def load():
    if not os.path.exists(LEDGER):
        return []
    out = []
    for line in open(LEDGER, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def save_all(rows):
    os.makedirs(DIR, exist_ok=True)
    with open(LEDGER, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def add(task, cmd, symptom, cause, fix, tag="", status="open"):
    os.makedirs(DIR, exist_ok=True)
    rows = load()
    rec = {
        "id": (max([r["id"] for r in rows]) + 1) if rows else 1,
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "task": (task or "")[:80],
        "cmd": (cmd or "")[:120],
        "symptom": (symptom or "")[:200],
        "cause": (cause or "")[:200],
        "fix": (fix or "")[:200],
        "tag": (tag or "misc")[:20],
        "status": status,
    }
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def cmd_add(a):
    rec = add(a.task, a.cmd, a.symptom, a.cause, a.fix, a.tag, a.status)
    print(f"OK 已记录错误 #{rec['id']} [{rec['tag']}] {rec['symptom'][:40]}")
    return 0


def cmd_list(a):
    rows = load()
    if a.open:
        rows = [r for r in rows if r.get("status") != "fixed"]
    if a.tag:
        rows = [r for r in rows if r.get("tag") == a.tag]
    rows = rows[-a.limit:]
    if not rows:
        print("(无记录)")
        return 0
    for r in rows:
        mark = "✅" if r.get("status") == "fixed" else "⚠️"
        print(f"{mark} #{r['id']} {r['ts'][:16]} [{r['tag']}] {r['symptom'][:50]}")
        if r.get("cause"):
            print(f"     根因: {r['cause'][:70]}")
        if r.get("fix"):
            print(f"     解法: {r['fix'][:70]}")
    print(f"\n共 {len(rows)} 条")
    return 0


def cmd_stats(_a):
    rows = load()
    if not rows:
        print("(无记录)")
        return 0
    by_tag = collections.Counter(r.get("tag", "misc") for r in rows)
    by_status = collections.Counter(r.get("status", "open") for r in rows)
    print(f"总记录 {len(rows)} 条")
    print("按标签: " + " | ".join(f"{k}×{v}" for k, v in by_tag.most_common()))
    print("按状态: " + " | ".join(f"{k}×{v}" for k, v in by_status.most_common()))
    return 0


def cmd_learn(a):
    rows = load()
    if not rows:
        print("(无记录，先 add 几条)")
        return 0
    # 按 (tag, symptom 前 20 字) 聚类，出现 ≥2 次即视为高频
    groups = collections.defaultdict(list)
    for r in rows:
        key = (r.get("tag", "misc"), (r.get("symptom") or "")[:20])
        groups[key].append(r)
    hot = [(k, v) for k, v in groups.items() if len(v) >= 2 and any(x.get("status") != "fixed" for x in v)]
    if not hot:
        print("暂无明显高频错误（同类 ≥2 次才算）")
        return 0
    lines = []
    for (tag, sym), items in sorted(hot, key=lambda x: -len(x[1])):
        fixes = [x.get("fix") for x in items if x.get("fix")]
        line = f"- **[{tag}] {sym}…**（{len(items)} 次）：{fixes[-1] if fixes else '待补解法'}"
        lines.append(line)
    md = "\n".join(lines)
    print("== 高频错误 → 建议规则 ==")
    print(md)
    if a.apply:
        marker = "## 错误台账自动提炼"
        txt = open(DISCIPLINE, encoding="utf-8").read() if os.path.exists(DISCIPLINE) else ""
        block = f"\n\n{marker}（{datetime.datetime.now():%Y-%m-%d}）\n" + md + "\n"
        if marker in txt:
            # 覆盖旧块
            head = txt.split(marker)[0].rstrip()
            txt = head + block
        else:
            txt = txt.rstrip() + block
        open(DISCIPLINE, "w", encoding="utf-8").write(txt)
        print(f"\n已写入 DISCIPLINE（{marker}）")
    else:
        print("\n（加 --apply 才会写入 DISCIPLINE）")
    return 0


def cmd_resolve(a):
    rows = load()
    hit = 0
    for r in rows:
        if r.get("id") == a.id:
            r["status"] = "fixed"
            r["fixed_at"] = datetime.datetime.now().isoformat(timespec="seconds")
            hit += 1
    if hit:
        save_all(rows)
        print(f"OK #{a.id} 标记已修复")
    else:
        print(f"未找到 #{a.id}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add")
    p.add_argument("--task", default=""); p.add_argument("--cmd", default="")
    p.add_argument("--symptom", required=True); p.add_argument("--cause", default="")
    p.add_argument("--fix", default=""); p.add_argument("--tag", default="misc")
    p.add_argument("--status", default="open")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list")
    p.add_argument("--open", action="store_true"); p.add_argument("--tag", default="")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("stats"); p.set_defaults(func=cmd_stats)

    p = sub.add_parser("learn")
    p.add_argument("--apply", action="store_true"); p.set_defaults(func=cmd_learn)

    p = sub.add_parser("resolve")
    p.add_argument("--id", type=int, required=True); p.set_defaults(func=cmd_resolve)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
