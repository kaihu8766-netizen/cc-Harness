# -*- coding: utf-8 -*-
"""一键自检（通用版）：装完 cc-Harness 跑这个，全绿才算环境可用。

检查项：
 1. registry.json 合法 + 所有工具入口文件存在
 2. gateway list / 运行一个只读工具
 3. checkpoint 可读写
 4. ctx_search 索引与检索
 5. skills 技能包存在且可加载
 6. MCP 协议自测
 7. fanout 并行冒烟
用法: python tools/verify_all.py [--verbose]
"""
import sys, io, os, json, subprocess, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
VERBOSE = "--verbose" in sys.argv
results = []


def add(name, ok, detail=""):
    results.append((name, bool(ok), str(detail)[:140]))


def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=ROOT)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 99, str(e)


def main():
    t0 = time.time()

    # 1) registry 合法性
    try:
        reg = json.load(open(os.path.join(ROOT, "tools", "registry.json"), encoding="utf-8"))["tools"]
        bad = []
        for name, spec in reg.items():
            target = [t for t in spec["cmd"] if t.endswith((".py", ".mjs"))]
            if "-c" in spec["cmd"]:
                continue
            if not target or not os.path.exists(os.path.join(ROOT, target[0])):
                bad.append(name)
        add("registry 合法且入口存在", not bad, f"{len(reg)} 个工具" + (f" 缺: {bad[:3]}" if bad else ""))
    except Exception as e:
        add("registry 合法且入口存在", False, e)

    # 2) gateway
    code, out = run([PY, "tools/gateway.py", "list"])
    add("gateway list", code == 0, out.strip().splitlines()[-1] if out.strip() else "")
    code, out = run([PY, "tools/gateway.py", "run", "checkpoint.get", "--raw"])
    add("gateway run checkpoint.get", code == 0, out.strip()[:60])

    # 3) checkpoint 读写
    code, out = run([PY, "tools/checkpoint.py", "set", "verify_all 自检写入"])
    ok_set = code == 0
    code2, out2 = run([PY, "tools/checkpoint.py", "get"])
    add("checkpoint 读写", ok_set and "verify_all" in out2, out2.strip()[:50])

    # 4) ctx_search
    code, out = run([PY, "tools/ctx_search.py", "index"])
    add("ctx 索引", code == 0, out.strip()[:60])
    code, out = run([PY, "tools/ctx_search.py", "bench", "install"])
    add("ctx 检索 <50ms", code == 0, out.strip().splitlines()[-1][:60] if out.strip() else "")

    # 5) skills
    need = ["apply_form", "doc_build", "deploy_verify"]
    missing = [s for s in need if not os.path.exists(os.path.join(ROOT, "skills", s, "SKILL.md"))]
    add("skills 完整", not missing, f"{len(need)-len(missing)}/{len(need)}" + (f" 缺 {missing}" if missing else ""))
    if not missing:
        code, out = run([PY, "tools/gateway.py", "skill", "apply_form", "--limit", "80"])
        add("技能可加载", code == 0 and len(out.strip()) > 20, out.strip().splitlines()[0][:50] if out.strip() else "")

    # 5.5) 技能索引与 SKILL.md 同步（防"模型想不起来有哪些技能"）
    code, out = run([PY, "tools/skills_index.py", "--check"])
    add("技能索引同步", code == 0, out.strip()[:70])

    # 6) MCP
    code, out = run([PY, "tools/mcp_server.py", "--selftest"])
    add("MCP 协议自测", code == 0 and "ALL PASS" in out, out.strip().splitlines()[-1] if out.strip() else "")

    # 6.5) 人味资产
    persona_ok = os.path.exists(os.path.join(ROOT, "persona.md")) or os.path.exists(os.path.join(ROOT, "out", "persona.md"))
    profile_ok = os.path.exists(os.path.join(ROOT, "user_profile.example.json")) or os.path.exists(os.path.join(ROOT, "out", "user_profile.json"))
    add("人味模板完整", persona_ok and profile_ok, f"persona={persona_ok} profile={profile_ok}")
    code, out = run([PY, "tools/detect_ai_smell.py", "--text", "收到，遵命，为您服务。综上所述，我已完成。"])
    add("AI 味检测可用", code == 0 and "100/100" not in out, out.strip().splitlines()[0][:60] if out.strip() else "")

    # 7) fanout 冒烟
    tasks = os.path.join(ROOT, "out", "tmp", "_verify_tasks.json")
    os.makedirs(os.path.dirname(tasks), exist_ok=True)
    json.dump([{"tool": "checkpoint.get"}, {"tool": "gateway.list"}], open(tasks, "w", encoding="utf-8"))
    code, out = run([PY, "tools/fanout.py", "--file", tasks])
    add("并行调度", code == 0, out.strip().splitlines()[0][:60] if out.strip() else "")

    elapsed = round(time.time() - t0, 1)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"== cc-Harness verify_all {elapsed}s ==")
    for name, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if VERBOSE or not ok else ""))
    print(f"结果: {passed}/{len(results)} PASS" + ("  ✅ ALL PASS" if passed == len(results) else "  ❌ 有失败"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
