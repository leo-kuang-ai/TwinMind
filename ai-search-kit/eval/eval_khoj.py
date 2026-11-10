#!/usr/bin/env python3
"""khoj 检索质量评测：对黄金集逐题调 /api/search，算 Recall@5 与 MRR。
用法: python3 eval_khoj.py --label <名称>   # 结果写 eval-<label>-<日期>.md
换向量模型 / 调阈值 / 升级 khoj 前后各跑一次对比，防止检索质量回归。"""
import json, subprocess, sys, time, datetime, pathlib

SET = json.load(open(pathlib.Path(__file__).parent / "golden_set.json"))
API = "http://127.0.0.1:42110/api/search"
TOPK = 5

def search(q, topk=TOPK):
    out = subprocess.run(
        ["curl", "-s", "--max-time", "30", "-G", API,
         "--data-urlencode", f"q={q}", "-d", "client=web", "-d", f"max_results={topk}"],
        capture_output=True, text=True).stdout
    try: return json.loads(out)
    except Exception: return []

hits, rr, rows = 0, 0.0, []
for c in SET["cases"]:
    results = search(c["q"])
    files = [(r.get("additional") or {}).get("file", "") for r in results]
    rank = next((i + 1 for i, f in enumerate(files) if c["expect"] in f), None)
    ok = rank is not None
    hits += ok; rr += 1.0 / rank if ok else 0.0
    rows.append((c["id"], c["q"], c["expect"], ok, rank, files[0] if files else "(空)"))
    time.sleep(0.3)

n = len(SET["cases"]); recal5, mrr = hits / n, rr / n
label = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else "run"
today = datetime.date.today().isoformat()
report = pathlib.Path(__file__).parent / f"eval-{label}-{today}.md"
lines = [f"# khoj 检索评测: {label} ({today})", "",
         f"- **Recall@{TOPK}: {recal5:.2%}** ({hits}/{n})  |  **MRR: {mrr:.3f}**", "",
         "| # | 问题 | 期望 | 命中 | 排名 |", "|---|---|---|---|---|"]
for rid, q, exp, ok, rank, _ in rows:
    lines.append(f"| {rid} | {q} | {exp} | {'✅' if ok else '❌'} | {rank or '-'} |")
report.write_text("\n".join(lines), encoding="utf-8")
print(f"Recall@{TOPK}: {recal5:.2%} ({hits}/{n})  MRR: {mrr:.3f}  -> {report}")
