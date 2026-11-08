# -*- coding: utf-8 -*-
"""Generate or validate the workspace skill index from SKILL.md files."""
import sys, io, os, re, glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, "skills")
OUT = os.path.join(SK, "INDEX.md")


def parse(path):
    txt = open(path, encoding="utf-8-sig").read().replace("\\ufeff", "")
    name = os.path.basename(os.path.dirname(path))
    # 标题
    m = re.search(r"^#\s+(?:Skill|技能)[：:]\s*(.+)$", txt, re.M)
    title = m.group(1).strip() if m else name
    # 触发词：匹配 "触发词：..." 或 "触发词：`x`、`y`"
    m = re.search(r"(?:Triggers|触发词)[：:]\s*(.+?)$", txt, re.M)
    triggers = []
    if m:
        triggers = [item.strip(" `。") for item in re.split(r"[,，、]", m.group(1))]
        triggers = [item for item in triggers if item]
    # 首段一句话用途
    body = re.sub(r"^#.*$", "", txt, flags=re.M).strip()
    first = ""
    for line in body.splitlines():
        s = line.strip().lstrip(">").strip()
        if s and not s.startswith("|") and not s.startswith("#") and not s.startswith(("Triggers:", "触发词")):
            first = re.sub(r"[*`]", "", s)[:60]
            break
    return {"name": name, "title": title, "triggers": triggers, "summary": first}


def build():
    rows = []
    for p in sorted(glob.glob(os.path.join(SK, "*", "SKILL.md"))):
        rows.append(parse(p))
    lines = ["# Skill index (generated)", "",
             "> Read this index at startup. Load matching skills with `python tools/gateway.py skill <name>`.", "",
             "| Skill | Purpose | Triggers | Load command |", "|---|---|---|---|"]
    for r in rows:
        trig = " / ".join(r["triggers"]) if r["triggers"] else "-"
        lines.append(f"| **{r['name']}** | {r['title']}: {r['summary']} | {trig} | `python tools/gateway.py skill {r['name']}` |")
    lines += ["", "## Usage", "",
              "1. Load the matching skill before acting.",
              "2. Follow the steps and constraints in its SKILL.md.",
              "3. Run `python tools/skills_index.py` after editing a skill."]
    return "\n".join(lines) + "\n"


def main():
    md = build()
    if "--check" in sys.argv:
        old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if old != md:
            print("STALE: Run python tools/skills_index.py to refresh skills/INDEX.md")
            return 1
        print("OK: Skill index is up to date")
        return 0
    open(OUT, "w", encoding="utf-8").write(md)
    print(f"Generated {os.path.relpath(OUT, ROOT)}（{md.count('| **')} skills）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
