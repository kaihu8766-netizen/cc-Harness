# -*- coding: utf-8 -*-
"""Install regression suite for cc-Harness (stdlib only, cross-platform).

Every scenario installs into a throwaway workspace *outside the repository*
using the real installer entry point, then checks the installed workspace with
``tools/check_install.py`` and exercises ``tools/verify_all.py``.

Run locally or from CI:
    python tests/install_regression.py [--verbose]
Exit code: 0 = all scenarios pass, 1 = a scenario failed.

Covers:
  1. empty workspace, first install
  2. workspace with user AGENTS.md content and a real checkpoint
  3. repeat install (single rule block, user content and checkpoint kept)
  4. half install (tools/skills copied, no rule block) -> non-zero
  5. duplicate/malformed rule block -> reported, non-zero
  6. self-check success and injected sub-check failure keep user state intact
  7. clean workspace gains no test checkpoint/index/ledger after self-check
macOS is not exercised here (see README for platform status).
"""
import sys, os, json, subprocess, tempfile, shutil, hashlib, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
BEGIN = "<!-- cc-Harness:begin -->"
END = "<!-- cc-Harness:end -->"
VERBOSE = "--verbose" in sys.argv
results = []
FAILS = []


def record(name, ok, detail=""):
    results.append((name, ok, str(detail)[:160]))
    if not ok:
        FAILS.append(name)
    print(("PASS  " if ok else "FAIL  ") + name + (f"  [{detail}]" if (VERBOSE or not ok) else ""))


def run(cmd, cwd, env=None, timeout=240):
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, cwd=cwd, env=e)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def install(target):
    if os.name == "nt":
        ps = shutil.which("powershell") or shutil.which("pwsh")
        cmd = [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
               os.path.join(REPO, "install.ps1"), "-Target", target]
    else:
        cmd = ["bash", os.path.join(REPO, "install.sh"), target]
    return run(cmd, REPO)


def check_install(target):
    return run([PY, os.path.join(target, "tools", "check_install.py"), "--dir", target], target)


def verify(target, extra_env=None):
    env = {"CC_VERIFY_INJECT_FAIL": "1"} if extra_env == "fail" else {}
    return run([PY, os.path.join(target, "tools", "verify_all.py")], target, env)


def checkpoint(target, *args):
    return run([PY, os.path.join(target, "tools", "checkpoint.py")] + list(args), target)


def read(path, default=""):
    if not os.path.exists(path):
        return default
    return open(path, encoding="utf-8-sig", errors="replace").read()


def sha(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def markers(target):
    text = read(os.path.join(target, "AGENTS.md"))
    return text.count(BEGIN), text.count(END)


def tree_snapshot(root):
    out = {}
    if not os.path.isdir(root):
        return out
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            p = os.path.join(dirpath, name)
            out[os.path.relpath(p, root)] = sha(p)
    return out


def scenario(desc, fn):
    tmp = tempfile.mkdtemp(prefix="cc-harness-regress-")
    try:
        fn(tmp)
    except AssertionError as e:
        record(desc, False, str(e))
    except Exception as e:
        record(desc, False, f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def require(cond, msg):
    if not cond:
        raise AssertionError(msg)


# ---------------- scenarios ----------------

def s_empty_first_install(tmp):
    code, out = install(tmp)
    require(code == 0, f"installer exit={code}\n{out[-600:]}")
    b, e = markers(tmp)
    require(b == 1 and e == 1, f"marker counts begin={b} end={e}")
    code, out = check_install(tmp)
    require(code == 0, f"check_install exit={code}\n{out[-800:]}")
    code, out = verify(tmp)
    require(code == 0, f"verify_all exit={code}\n{out[-800:]}")
    # self-check must not leave state behind in a workspace that had none
    for name in ("state.db", "context.db"):
        require(not os.path.exists(os.path.join(tmp, "out", "state", name)),
                f"self-check left out/state/{name}")
    require(not os.path.isdir(os.path.join(tmp, "out", "tmp")) or
            not os.listdir(os.path.join(tmp, "out", "tmp")),
            "self-check left files in out/tmp")
    record("empty workspace: first install + check_install + verify_all", True)


def s_user_content_and_checkpoint(tmp):
    os.makedirs(tmp, exist_ok=True)
    agents = os.path.join(tmp, "AGENTS.md")
    user_text = "# My rules\n\n- keep my wording\n- do not lose this line\n"
    open(agents, "w", encoding="utf-8").write(user_text)
    code, out = checkpoint(tmp, "set", "user real checkpoint 42")
    # checkpoint tool only exists after install; seed via install then set
    if code != 0:
        code, out = install(tmp)
        require(code == 0, f"installer exit={code}")
        code, out = checkpoint(tmp, "set", "user real checkpoint 42")
    require(code == 0, f"checkpoint set exit={code}\n{out}")
    code, out = checkpoint(tmp, "get")
    require(code == 0 and "user real checkpoint 42" in out, f"checkpoint get: {out}")
    code, out = install(tmp)
    require(code == 0, f"installer exit={code}\n{out[-600:]}")
    text = read(agents)
    require("keep my wording" in text and "do not lose this line" in text, "user AGENTS.md content lost")
    b, e = markers(tmp)
    require(b == 1 and e == 1, f"marker counts begin={b} end={e}")
    code, out = checkpoint(tmp, "get")
    require("user real checkpoint 42" in out, f"checkpoint lost: {out}")
    code, out = check_install(tmp)
    require(code == 0, f"check_install exit={code}\n{out[-800:]}")
    code, out = verify(tmp)
    require(code == 0, f"verify_all exit={code}\n{out[-600:]}")
    code, out = checkpoint(tmp, "get")
    require("user real checkpoint 42" in out, f"self-check changed user checkpoint: {out}")
    record("user AGENTS.md + real checkpoint preserved across install and self-check", True)


def s_repeat_install(tmp):
    require(install(tmp)[0] == 0, "first install failed")
    agents = os.path.join(tmp, "AGENTS.md")
    code, _ = checkpoint(tmp, "set", "repeat checkpoint 7")
    require(code == 0, "checkpoint set failed")
    before = read(agents)
    code, out = install(tmp)
    require(code == 0, f"second install exit={code}\n{out[-500:]}")
    b, e = markers(tmp)
    require(b == 1 and e == 1, f"repeat install marker counts begin={b} end={e}")
    require(read(agents).startswith(before.rstrip()), "repeat install changed existing AGENTS.md content")
    code, out = checkpoint(tmp, "get")
    require("repeat checkpoint 7" in out, "repeat install lost checkpoint")
    record("repeat install keeps a single block, user content and checkpoint", True)


def s_half_install(tmp):
    for d in ("tools", "skills"):
        shutil.copytree(os.path.join(REPO, d), os.path.join(tmp, d))
    code, out = check_install(tmp)
    require(code != 0, f"half install unexpectedly passed: {out[-500:]}")
    require("missing cc-Harness rule block" in out, f"missing message: {out[-500:]}")
    require("half install" in out, f"half-install hint missing: {out[-500:]}")
    record("half install (no rule block) returns non-zero with missing item", True)


def s_duplicate_markers(tmp):
    require(install(tmp)[0] == 0, "install failed")
    agents = os.path.join(tmp, "AGENTS.md")
    text = read(agents)
    block = text[text.find(BEGIN):text.find(END) + len(END)]
    open(agents, "w", encoding="utf-8").write(text + "\n" + block + "\n")
    corrupt_hash = sha(agents)
    code, out = check_install(tmp)
    require(code != 0, "duplicate markers unexpectedly passed")
    require("malformed markers" in out, f"duplicate marker not reported: {out[-500:]}")
    code, out = install(tmp)
    require(code != 0, f"installer unexpectedly succeeded on duplicate markers: {out[-400:]}")
    require(sha(agents) == corrupt_hash, "installer modified AGENTS.md despite malformed markers")
    record("duplicate rule block is reported and installer refuses without editing", True)


def s_failure_preserves_state(tmp):
    require(install(tmp)[0] == 0, "install failed")
    require(checkpoint(tmp, "set", "state guard 99")[0] == 0, "checkpoint set failed")
    agents_before = sha(os.path.join(tmp, "AGENTS.md"))
    code, out = checkpoint(tmp, "get")
    require("state guard 99" in out, "checkpoint baseline lost")
    code_fail, out_fail = verify(tmp, extra_env="fail")
    require(code_fail != 0, f"injected failure did not return non-zero: {out_fail[-500:]}")
    require("injected failure" in out_fail, "injected failure not reported")
    code, out = checkpoint(tmp, "get")
    require("state guard 99" in out, f"failed self-check changed checkpoint: {out}")
    require(sha(os.path.join(tmp, "AGENTS.md")) == agents_before, "failed self-check changed AGENTS.md")
    code_ok, out_ok = verify(tmp)
    require(code_ok == 0, f"successful self-check failed: {out_ok[-500:]}")
    require("state guard 99" in checkpoint(tmp, "get")[1], "successful self-check changed checkpoint")
    record("self-check failure and success both preserve user state", True)


def s_ledger_and_index_preserved(tmp):
    require(install(tmp)[0] == 0, "install failed")
    err = os.path.join(tmp, "out", "review", "errors", "error_ledger.jsonl")
    os.makedirs(os.path.dirname(err), exist_ok=True)
    open(err, "w", encoding="utf-8").write('{"id":1,"task":"user","status":"open"}\n')
    idx_path = os.path.join(tmp, "skills", "INDEX.md")
    idx_hash = sha(idx_path)
    err_hash = sha(err)
    code, out = verify(tmp)
    require(code == 0, f"verify_all exit={code}\n{out[-500:]}")
    require(sha(err) == err_hash, "self-check modified the user error ledger")
    require(sha(idx_path) == idx_hash, "self-check modified skills/INDEX.md")
    require(not os.path.exists(os.path.join(tmp, "out", "state", "context.db")),
            "self-check created out/state/context.db")
    record("error ledger and skill index untouched by self-check", True)


def s_missing_registered_tool(tmp):
    require(install(tmp)[0] == 0, "install failed")
    require(check_install(tmp)[0] == 0, "baseline installed check failed")
    os.remove(os.path.join(tmp, "tools", "checkpoint.py"))
    code, out = check_install(tmp)
    require(code != 0, "check_install passed after tools/checkpoint.py was deleted")
    require("missing tool scripts" in out, f"missing-tool message absent: {out[-600:]}")
    require("checkpoint.get" in out, f"missing tool name not listed: {out[-600:]}")
    record("missing registered tool script is detected and named", True)


def s_invalid_block_exits_before_writes(tmp):
    begin = "<!-- cc-Harness:begin -->"
    end = "<!-- cc-Harness:end -->"
    variants = {
        "missing_end": begin + "\n## user rules\n- keep me\n",
        "duplicate_blocks": (begin + "\n## block one\n" + end + "\n\n" +
                             begin + "\n## block two\n" + end + "\n"),
        "wrong_order": end + "\n## user rules\n" + begin + "\n",
    }
    for label, content in variants.items():
        case = os.path.join(tmp, label)
        os.makedirs(case, exist_ok=True)
        open(os.path.join(case, "AGENTS.md"), "w", encoding="utf-8").write(content)
        open(os.path.join(case, "user-sentinel.txt"), "w", encoding="utf-8").write("keep this file\n")
        before = tree_snapshot(case)
        code, out = install(case)
        require(code != 0, f"{label}: installer returned 0 despite invalid rule block")
        require(tree_snapshot(case) == before,
                f"{label}: installer changed the target before rejecting the rule block")
        require(("标记块" in out) or ("rule block" in out), f"{label}: no clear rule-block error: {out[-400:]}")
    record("invalid rule block (missing end / duplicate / wrong order) exits before writes", True)


def main():
    print(f"repo: {REPO}")
    print(f"python: {PY}")
    print(f"platform: {sys.platform}")
    scenario("1. empty workspace first install", s_empty_first_install)
    scenario("2. user content + checkpoint", s_user_content_and_checkpoint)
    scenario("3. repeat install", s_repeat_install)
    scenario("4. half install", s_half_install)
    scenario("5. duplicate markers", s_duplicate_markers)
    scenario("6. failure/success preserve state", s_failure_preserves_state)
    scenario("7. ledger/index preserved", s_ledger_and_index_preserved)
    scenario("8. missing registered tool", s_missing_registered_tool)
    scenario("9. invalid block exits before writes", s_invalid_block_exits_before_writes)
    print(f"\nresult: {len(results)-len(FAILS)}/{len(results)} scenarios PASS")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
