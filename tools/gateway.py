# -*- coding: utf-8 -*-
"""统一工具网关（模拟 MCP 生态）：所有能力一个入口 + 统一 JSON + 单次自愈重试。

用法：
  python tools/gateway.py list [--category browser]
  python tools/gateway.py describe browser.click
  python tools/gateway.py run guard.ledger
  python tools/gateway.py run ledger.due --json '{"days":7}'
  python tools/gateway.py run panel.tail --json '{"n":20}' --raw
  python tools/gateway.py run browser.click --dry-run          # 只打印将要执行的命令

自愈机制（Brain 要求）：首次失败时，自动分析 stderr 并做一次针对性修正后重试：
  - 参数缺失/占位符未替换 → 提示补参数（不重试）
  - 编码类错误（UnicodeDecodeError/GBK）→ 加 PYTHONIOENCODING=utf-8 重试 1 次
  - 超时 → 放宽 timeout×2 重试 1 次（仅一次）
输出统一 JSON：{ok, tool, code, attempt, stdout, stderr, elapsed}
"""
import sys, io, os, json, subprocess, time, argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG_PATH = os.path.join(ROOT, "tools", "registry.json")


def load_reg():
    return json.load(open(REG_PATH, encoding="utf-8"))["tools"]


def build_args(arg_template, values):
    out = []
    for token in arg_template:
        s = token
        for k, v in values.items():
            s = s.replace("{" + k + "}", str(v))
        out.append(s)
    return out


def missing_args(arg_template, values):
    need = set()
    for t in arg_template:
        if t.startswith("{") and t.endswith("}"):
            need.add(t[1:-1])
    return sorted(n for n in need if n not in values)


import re as _re


def plan_heals(stderr):
    """从 stderr 推断可执行的修复动作（有序队列，最多 2 个）。"""
    plans = []
    if not stderr:
        return plans
    low = stderr.lower()
    # 1) 缺目录：从报错里提取路径并建父目录
    m = _re.search(r"[\"']([A-Za-z]:\\[^\"']+)[\"']", stderr)
    if ("no such file" in low or "cannot find" in low) and m:
        path = m.group(1).replace("\\\\", "\\")
        plans.append(("mkdir", path))
    # 2) 缺环境变量
    m2 = _re.search(r"environment variable ([A-Z_][A-Z0-9_]*)", stderr, _re.I)
    if m2:
        plans.append(("env", m2.group(1)))
    # 3) 编码问题
    if "unicodedecodeerror" in low or "gbk" in low or "codec" in low:
        plans.append(("env", "PYTHONIOENCODING"))
    # 4) 超时
    if "timed out" in low or "timeout" in low:
        plans.append(("timeout", "2x"))
    seen, out = set(), []
    for p in plans:
        if p not in seen:
            seen.add(p); out.append(p)
    return out[:2]


def apply_heal(plan, env, timeout):
    kind, arg = plan
    if kind == "mkdir":
        try:
            os.makedirs(os.path.dirname(arg) or arg, exist_ok=True)
            if not arg.endswith((".py", ".json", ".md", ".txt", ".pdf", ".mjs")):
                os.makedirs(arg, exist_ok=True)
            return f"mkdir {arg}", env, timeout
        except Exception:
            return None, env, timeout
    if kind == "env":
        if arg.upper() == "PYTHONIOENCODING":
            env["PYTHONIOENCODING"] = "utf-8"
            return "set PYTHONIOENCODING=utf-8", env, timeout
        env[arg] = "1"
        return f"set {arg}=1", env, timeout
    if kind == "timeout":
        return f"timeout x2 → {timeout*2}", env, timeout * 2
    return None, env, timeout


def run_one(tool_name, spec, values, raw=False, dry=False):
    argv = build_args(spec["cmd"], values)
    if dry:
        print("DRY-RUN:", " ".join(argv))
        return 0
    miss = missing_args(spec.get("cmd", []), values)
    if miss:
        print(json.dumps({"ok": False, "tool": tool_name, "error": f"缺参数: {miss}"}, ensure_ascii=False))
        return 2
    timeout = spec.get("timeout", 120)
    env = dict(os.environ)
    total_start = time.time()
    heals_done = []
    last = None
    for attempt in (1, 2, 3):
        t0 = time.time()
        try:
            r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout, cwd=ROOT, env=env)
            code, out, err = r.returncode, r.stdout or "", r.stderr or ""
        except subprocess.TimeoutExpired:
            code, out, err = 124, "", "Timeout"
        elapsed = round(time.time() - t0, 1)
        last = {"ok": code == 0, "tool": tool_name, "code": code, "attempt": attempt,
                "elapsed": elapsed, "stdout": out.strip()[-1200:], "stderr": err.strip()[-600:]}
        if heals_done:
            last["heals"] = heals_done
        if code == 0 or attempt == 3:
            break
        plans = plan_heals(err)
        if not plans:
            break
        plan = plans[0]
        desc, env, timeout = apply_heal(plan, env, timeout)
        if not desc:
            break
        heals_done.append(desc)
        last["healed"] = True
    last["total_elapsed"] = round(time.time() - total_start, 1)
    if raw and last.get("ok"):
        print(last["stdout"])
    else:
        print(json.dumps(last, ensure_ascii=False, indent=1))
    return 0 if last.get("ok") else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "describe", "run", "skill"])
    ap.add_argument("name", nargs="?", default="")
    ap.add_argument("--category", default="")
    ap.add_argument("--json", default="")
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=2400)
    a = ap.parse_args()
    reg = load_reg()

    if a.cmd == "list":
        cats = {}
        for name, spec in reg.items():
            cats.setdefault(spec.get("category", "misc"), []).append((name, spec.get("desc", ""), spec.get("risky", False)))
        for cat in sorted(cats):
            if a.category and cat != a.category:
                continue
            print(f"[{cat}]")
            for name, desc, risky in cats[cat]:
                print(f"  {name:<20} {'⚠ ' if risky else '  '}{desc}")
        print(f"\n共 {len(reg)} 个工具")
        return 0
    if a.cmd == "describe":
        if a.name not in reg:
            print("未知工具:", a.name); return 2
        print(json.dumps({a.name: reg[a.name]}, ensure_ascii=False, indent=1))
        return 0
    # skill: 技能动态装载（Brain 建议的第 4 项）
    if a.cmd == "skill":
        sk = os.path.join(ROOT, "skills")
        names = sorted(d for d in os.listdir(sk) if os.path.isdir(os.path.join(sk, d))) if os.path.isdir(sk) else []
        if not a.name:
            print("可用技能:", ", ".join(names) or "无")
            return 0
        if a.name not in names:
            print("未知技能:", a.name, "| 可用:", names); return 2
        md_path = os.path.join(sk, a.name, "SKILL.md")
        txt = open(md_path, encoding="utf-8").read()
        limit = a.limit
        print(txt[:limit])
        if len(txt) > limit:
            print(f"\n[截断：全文 {len(txt)} 字，已加载前 {limit} 字]")
        return 0
    # run
    if a.name not in reg:
        print("未知工具:", a.name); return 2
    values = json.loads(a.json) if a.json else {}
    return run_one(a.name, reg[a.name], values, raw=a.raw, dry=a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
