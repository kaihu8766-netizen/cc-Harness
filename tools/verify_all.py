# -*- coding: utf-8 -*-
"""One-command self-check: run this after installing cc-Harness.

Checks:
  1. registry.json is valid and every tool entry file exists
  2. gateway list / one read-only tool invocation
  3. checkpoint write + read-back
  4. ctx_search index and search latency
  5. skills present and loadable
  6. MCP protocol self-test
  7. fanout parallel smoke

State isolation: every subprocess runs with ``CC_HARNESS_STATE_DIR`` pointing
at a throwaway directory, so the user's real checkpoint, search index, error
ledger, locks and temp task files are never touched. The checkpoint test still
performs a real write + read-back, just inside that throwaway directory.

Usage: python tools/verify_all.py [--verbose]
Exit code: 0 = all checks pass, 1 = at least one check failed.
Test hook: set CC_VERIFY_INJECT_FAIL=1 to force one failing check (used by the
install regression suite; it is not part of normal usage).
"""
import sys, io, os, json, subprocess, time, tempfile, shutil, hashlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
VERBOSE = "--verbose" in sys.argv
results = []
STATE = None
ENV = None


def add(name, ok, detail=""):
    results.append((name, bool(ok), str(detail)[:2400]))


def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, cwd=ROOT, env=ENV)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 99, str(e)


def _sha(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def user_state():
    """Fingerprint user-owned state that the self-check must never change."""
    fp = {}
    state_files = ["state.db", "context.db"]
    for name in state_files:
        p = os.path.join(ROOT, "out", "state", name)
        fp[name] = _sha(p) if os.path.exists(p) else None
    ledger = os.path.join(ROOT, "out", "review", "errors", "error_ledger.jsonl")
    fp["error_ledger"] = _sha(ledger) if os.path.exists(ledger) else None
    for name in ["skills/INDEX.md", "AGENTS.md"]:
        p = os.path.join(ROOT, name)
        fp[name] = _sha(p) if os.path.exists(p) else None
    tmp = os.path.join(ROOT, "out", "tmp")
    if os.path.isdir(tmp):
        fp["out/tmp"] = sorted(os.listdir(tmp))
    else:
        fp["out/tmp"] = None
    return fp


def main():
    global STATE, ENV
    t0 = time.time()
    before = user_state()

    STATE = tempfile.mkdtemp(prefix="cc-harness-verify-")
    ENV = dict(os.environ)
    ENV["CC_HARNESS_STATE_DIR"] = STATE

    cleanup_ok = False
    try:
        # 1) registry validity
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

        # 3) checkpoint: real write + read-back inside the disposable state dir
        marker = "verify_all 自检写入 %d" % os.getpid()
        code, out = run([PY, "tools/checkpoint.py", "set", marker])
        code2, out2 = run([PY, "tools/checkpoint.py", "get"])
        add("checkpoint 读写", code == 0 and code2 == 0 and marker in out2, out2.strip()[:70])

        # 4) ctx_search (index lives in the disposable state dir)
        code, out = run([PY, "tools/ctx_search.py", "index"])
        add("ctx 索引", code == 0, out.strip()[:2400])
        code, out = run([PY, "tools/ctx_search.py", "bench", "install"])
        add("ctx 检索 <50ms", code == 0, out.strip().splitlines()[-1][:60] if out.strip() else "")

        # 5) skills
        need = ["apply_form", "doc_build", "deploy_verify"]
        missing = [s for s in need if not os.path.exists(os.path.join(ROOT, "skills", s, "SKILL.md"))]
        add("skills 完整", not missing, f"{len(need)-len(missing)}/{len(need)}" + (f" 缺 {missing}" if missing else ""))
        if not missing:
            code, out = run([PY, "tools/gateway.py", "skill", "apply_form", "--limit", "80"])
            add("技能可加载", code == 0 and len(out.strip()) > 20, out.strip().splitlines()[0][:50] if out.strip() else "")

        # 5.4) error ledger readable
        code_e, out_e = run([PY, "tools/error_ledger.py", "stats"])
        add("错误台账可读", code_e == 0 and ("总记录" in out_e or "无记录" in out_e), out_e.strip().splitlines()[0][:60] if out_e.strip() else "")

        # 5.5) skills index matches SKILL.md files
        code, out = run([PY, "tools/skills_index.py", "--check"])
        add("技能索引同步", code == 0, out.strip()[:70])

        # 6) MCP protocol self-test
        code, out = run([PY, "tools/mcp_server.py", "--selftest"])
        add("MCP 协议自测", code == 0 and "ALL PASS" in out, out.strip().splitlines()[-1] if out.strip() else "")

        # 6.5) human-voice assets
        persona_ok = os.path.exists(os.path.join(ROOT, "persona.md")) or os.path.exists(os.path.join(ROOT, "out", "persona.md"))
        profile_ok = os.path.exists(os.path.join(ROOT, "user_profile.example.json")) or os.path.exists(os.path.join(ROOT, "out", "user_profile.json"))
        add("人味模板完整", persona_ok and profile_ok, f"persona={persona_ok} profile={profile_ok}")
        code, out = run([PY, "tools/detect_ai_smell.py", "--text", "收到，遵命，为您服务。综上所述，我已完成。"])
        add("AI 味检测可用", code == 0 and "100/100" not in out, out.strip().splitlines()[0][:60] if out.strip() else "")

        # 7) fanout smoke (task file + locks in the disposable state dir)
        tasks = os.path.join(STATE, "_verify_tasks.json")
        os.makedirs(os.path.dirname(tasks), exist_ok=True)
        json.dump([{"tool": "checkpoint.get"}, {"tool": "gateway.list"}], open(tasks, "w", encoding="utf-8"))
        code, out = run([PY, "tools/fanout.py", "--file", tasks])
        add("并行调度", code == 0, out.strip().splitlines()[0][:60] if out.strip() else "")

        if os.environ.get("CC_VERIFY_INJECT_FAIL"):
            add("injected failure (test hook)", False, "CC_VERIFY_INJECT_FAIL was set")

        # 8) user state must be byte-identical after the self-check
        after = user_state()
        add("用户状态未被改写", before == after,
            "" if before == after else f"changed: {[k for k in before if before.get(k) != after.get(k)]}")
    finally:
        try:
            shutil.rmtree(STATE, ignore_errors=True)
        except Exception:
            pass
        cleanup_ok = not os.path.exists(STATE)
        add("临时状态已清理", cleanup_ok, "" if cleanup_ok else f"leftover: {STATE}")

    elapsed = round(time.time() - t0, 1)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"== cc-Harness verify_all {elapsed}s ==")
    for name, ok, detail in results:
        line = f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if VERBOSE or not ok else "")
        print(line.replace("\n", "\n      "))
    print(f"结果: {passed}/{len(results)} PASS" + ("  ✅ ALL PASS" if passed == len(results) else "  ❌ 有失败"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
