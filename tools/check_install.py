# -*- coding: utf-8 -*-
"""Validate an **installed** cc-Harness workspace.

This is deliberately separate from the source-checkout self-check
(``tools/verify_all.py``): the repository checkout has no installed workflow
block in ``AGENTS.md``, so it must keep working in CI without one.

Usage:
  python tools/check_install.py [--dir PATH] [--verbose]

Exit code: 0 = install is complete, 1 = missing/duplicated markers, incomplete
rules, unusable tool entry points or a stale skill index.

The check is read-only: the installed ``AGENTS.md`` is hashed before and after
to prove user content was preserved, and tool probes run with a throwaway
``CC_HARNESS_STATE_DIR``.
"""
import sys, io, os, subprocess, tempfile, shutil, hashlib, argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
BEGIN = "<!-- cc-Harness:begin -->"
END = "<!-- cc-Harness:end -->"
results = []
VERBOSE = False


def add(name, ok, detail=""):
    results.append((name, bool(ok), str(detail)[:200]))


def sha(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, cwd, env, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, cwd=cwd, env=env)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 99, str(e)


def main():
    global VERBOSE
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    VERBOSE = a.verbose
    target = os.path.abspath(a.dir or os.getcwd())

    print(f"== cc-Harness installed-workspace check ==")
    print(f"target: {target}")

    state = tempfile.mkdtemp(prefix="cc-harness-check-")
    env = dict(os.environ)
    env["CC_HARNESS_STATE_DIR"] = state
    try:
        # --- AGENTS.md markers ---
        agents = os.path.join(target, "AGENTS.md")
        before_hash = sha(agents)
        text = ""
        if os.path.exists(agents):
            text = open(agents, encoding="utf-8-sig", errors="replace").read()
        begins = text.count(BEGIN)
        ends = text.count(END)
        add("AGENTS.md exists", os.path.exists(agents), agents)
        if begins == 0 and ends == 0:
            half = os.path.isdir(os.path.join(target, "tools")) or os.path.isdir(os.path.join(target, "skills"))
            add("workflow block present", False,
                "missing cc-Harness rule block in AGENTS.md"
                + (" (half install: tools/skills copied but no rule block)" if half else ""))
        elif begins != 1 or ends != 1:
            add("workflow block present", False, f"malformed markers: begin={begins}, end={ends}")
        else:
            first_begin = text.find(BEGIN)
            first_end = text.find(END)
            if first_begin > first_end:
                add("workflow block present", False, "malformed markers: end precedes begin")
            else:
                block = text[first_begin + len(BEGIN):first_end].strip()
                add("workflow block present", True, f"{len(block)} chars")
                add("workflow block non-empty", len(block) >= 50 and "cc-Harness" in block,
                    f"{len(block)} chars" + ("" if "cc-Harness" in block else "; cc-Harness marker text missing"))

        # --- installed tools callable through the normal entry ---
        gateway = os.path.join(target, "tools", "gateway.py")
        registry = os.path.join(target, "tools", "registry.json")
        add("tools installed", os.path.exists(gateway) and os.path.exists(registry),
            f"gateway={os.path.exists(gateway)} registry={os.path.exists(registry)}")
        if os.path.exists(gateway):
            code, out = run([PY, gateway, "list"], target, env)
            add("gateway entry works", code == 0, out.strip().splitlines()[-1][:90] if out.strip() else "")
            code, out = run([PY, gateway, "skill", "apply_form", "--limit", "40"], target, env)
            add("installed tool run works", code == 0, out.strip().splitlines()[0][:90] if out.strip() else "")

        # --- skills + index ---
        skills_dir = os.path.join(target, "skills")
        skill_files = []
        if os.path.isdir(skills_dir):
            skill_files = [d for d in os.listdir(skills_dir)
                           if os.path.isfile(os.path.join(skills_dir, d, "SKILL.md"))]
        add("skills installed", bool(skill_files), f"{len(skill_files)} skill(s): {', '.join(sorted(skill_files)[:6])}")
        indexer = os.path.join(target, "tools", "skills_index.py")
        if os.path.exists(indexer):
            code, out = run([PY, indexer, "--check"], target, env)
            add("skill index consistent", code == 0, out.strip()[:110])
        else:
            add("skill index consistent", False, "tools/skills_index.py missing")

        # --- user content preserved ---
        after_hash = sha(agents)
        add("user AGENTS.md content preserved", before_hash == after_hash,
            "" if before_hash == after_hash else "AGENTS.md changed during check")
    finally:
        shutil.rmtree(state, ignore_errors=True)

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"result: {passed}/{len(results)} PASS" + ("  OK" if passed == len(results) else "  FAIL"))
    for name, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if VERBOSE or not ok else ""))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
