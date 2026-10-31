# -*- coding: utf-8 -*-
"""AI 味检测器：给一段回复打分，抓"客服腔 / 满篇表格 / 秒跪认错 / 零观点"。

用法：
  python tools/detect_ai_smell.py --file out/draft.md
  python tools/detect_ai_smell.py --text "你的回复内容"
  echo "..." | python tools/detect_ai_smell.py --stdin
输出：AI 味分数（0-100，越低越像人）+ 命中项清单
"""
import sys, io, os, re, argparse, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 客服腔/机器腔禁词（Brain 认定）
BANNED = ["收到", "遵命", "为您服务", "请您查收", "作为一个AI", "根据您的要求", "综上所述",
          "好的呢", "我来帮您", "如有疑问请", "感谢您的", "希望对您有帮助"]
# 秒跪认错模式
KOWTOW = [r"我错了[，,。]", r"非常抱歉", r"深表歉意", r"我深刻检讨", r"我保证下次"]
# 观点标记（有观点加分/缺观点扣分）
OPINION = [r"我建议", r"我倾向", r"我看[好不]", r"我觉得", r"我不同意", r"我担心", r"说实话", r"按我的判断"]
# 情绪/温度标记
WARMTH = [r"别急", r"睡吧", r"辛苦了", r"这块我没底", r"我有点", r"你别慌", r"陪你", r"放心"]


def score(text):
    t = text.strip()
    hits = []
    n = len(t)
    # 1) 客服腔
    banned_hits = [w for w in BANNED if w in t]
    if banned_hits:
        hits.append(("客服腔", banned_hits, 30))
    # 2) 秒跪认错
    kw = [p for p in KOWTOW if re.search(p, t)]
    if kw:
        hits.append(("秒跪认错", kw, 15))
    # 3) 满篇表格/清单（表格行占比 / 列表项密度）
    table_rows = len([l for l in t.splitlines() if l.strip().startswith("|")])
    bullet_rows = len([l for l in t.splitlines() if re.match(r"^\s*([-*]|\d+\.)\s", l)])
    total_lines = max(1, len([l for l in t.splitlines() if l.strip()]))
    ratio = (table_rows + bullet_rows) / total_lines
    if ratio > 0.6 and total_lines >= 5:
        hits.append(("满篇结构化", f"结构化行占比 {ratio:.0%}", 20))
    elif ratio > 0.4 and total_lines >= 5:
        hits.append(("结构化偏多", f"{ratio:.0%}", 8))
    # 4) 零观点
    if n > 120 and not any(re.search(p, t) for p in OPINION):
        hits.append(("零观点", "通篇无主观判断", 15))
    # 5) 零温度
    if n > 200 and not any(re.search(p, t) for p in WARMTH):
        hits.append(("零温度", "无任何人情味表达", 10))
    # 6) 过长（短问长答）
    if n > 900:
        hits.append(("过长", f"{n} 字", 5))

    penalty = sum(h[2] for h in hits)
    ai_score = max(0, min(100, 100 - penalty + (10 if any(re.search(p, t) for p in OPINION) else 0)))
    return ai_score, hits, {"chars": n, "structured_ratio": round(ratio, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="")
    ap.add_argument("--text", default="")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.file:
        text = open(a.file, encoding="utf-8", errors="replace").read()
    elif a.text:
        text = a.text
    elif a.stdin:
        text = sys.stdin.read()
    else:
        print("need --file/--text/--stdin"); return 2
    s, hits, meta = score(text)
    if a.json:
        print(json.dumps({"ai_score": s, "hits": [{"type": h[0], "detail": str(h[1])} for h in hits], "meta": meta}, ensure_ascii=False, indent=1))
    else:
        verdict = "像人 ✅" if s >= 80 else ("还行" if s >= 60 else "机器味重 ❌")
        print(f"AI 味评分: {s}/100（{verdict}） | 字数 {meta['chars']} | 结构化占比 {meta['structured_ratio']:.0%}")
        for typ, detail, pen in hits:
            print(f"  - {typ}: {detail}（-{pen}）")
        if not hits:
            print("  （无命中项，克制、有观点、有人情味）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
