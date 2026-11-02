# -*- coding: utf-8 -*-
"""生成技能索引（skills/INDEX.md）：把每个 SKILL.md 的用途与触发词提出来，
让模型在冷启动时读一份小文件就能知道"什么时候该加载哪个技能"，不必先猜。

用法：
  python tools/skills_index.py            # 生成/更新 skills/INDEX.md
  python tools/skills_index.py --check    # 只校验是否与 SKILL.md 同步
"""
import sys, io, os, re, glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, "skills")
OUT = os.path.join(SK, "INDEX.md")


def parse(path):
    txt = open(path, encoding="utf-8-sig").read().replace("\\ufeff", "")
    name = os.path.basename(os.path.dirname(path))
    # 标题
    m = re.search(r"^#\s+技能[：:]\s*(.+)$", txt, re.M)
    title = m.group(1).strip() if m else name
    # 触发词：匹配 "触发词：..." 或 "触发词：`x`、`y`"
    m = re.search(r"触发词[：:]\s*(.+?)$", txt, re.M)
    triggers = []
    if m:
        triggers = re.findall(r"[\w\u4e00-\u9fa5（）()]+", m.group(1))
        triggers = [t for t in triggers if t not in ("触发词",)]
    # 首段一句话用途
    body = re.sub(r"^#.*$", "", txt, flags=re.M).strip()
    first = ""
    for line in body.splitlines():
        s = line.strip().lstrip(">").strip()
        if s and not s.startswith("|") and not s.startswith("#") and not s.startswith("触发词"):
            first = re.sub(r"[*`]", "", s)[:60]
            break
    return {"name": name, "title": title, "triggers": triggers[:8], "summary": first}


def build():
    rows = []
    for p in sorted(glob.glob(os.path.join(SK, "*", "SKILL.md"))):
        rows.append(parse(p))
    lines = ["# 技能索引（自动生成，别手改）", "",
             "> 冷启动读这份就够；命中触发词再用 `python tools/gateway.py skill <name>` 加载全文。", "",
             "| 技能 | 用途 | 触发词 | 加载命令 |", "|---|---|---|---|"]
    for r in rows:
        trig = "、".join(r["triggers"]) if r["triggers"] else "-"
        lines.append(f"| **{r['name']}** | {r['title']}：{r['summary']} | {trig} | `gateway.py skill {r['name']}` |")
    lines += ["", "## 使用纪律", "",
              "1. 用户提到上表任一触发词 → **先加载技能再动手**，不许凭记忆做。",
              "2. 加载后按 SKILL.md 的步骤与红线执行；技能里的\"实证坑\"优先于你的直觉。",
              "3. 新技能加进 skills/<name>/SKILL.md 后，跑 `python tools/skills_index.py` 刷新本表。"]
    return "\n".join(lines) + "\n"


def main():
    md = build()
    if "--check" in sys.argv:
        old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if old != md:
            print("STALE: skills/INDEX.md 与 SKILL.md 不同步（跑 python tools/skills_index.py）")
            return 1
        print("OK 技能索引同步")
        return 0
    open(OUT, "w", encoding="utf-8").write(md)
    print(f"已生成 {os.path.relpath(OUT, ROOT)}（{md.count('| **')} 个技能）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
