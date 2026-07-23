#!/usr/bin/env python3
"""月汇总"""
import os, json, glob
from datetime import datetime
from statistics import mean, median
from collections import Counter
from note_api import append_doc, list_notes
from config.constants import FOLDER_MONTHLY_ARCHIVE

BD = os.path.dirname(os.path.abspath(__file__))
OD = os.path.join(BD, "outputs")

def main():
    m = f"{datetime.now():%Y年%m月}"
    print(f"{m}汇总...")
    items = []
    tm = f"{datetime.now():%Y-%m}"
    for f in sorted(glob.glob(os.path.join(OD, "evaluation_*.json"))):
        if tm in f: items.extend(json.load(open(f))["items"])
    if not items: print("无数据"); return
    sc = [x["total"] for x in items]
    at = [t for it in items for t in it["tags"]]
    tc = Counter(at).most_common(5)
    ts = "、".join(f"{t}({c})" for t,c in tc)
    top = sorted(items, key=lambda x: -x["total"])[:10]
    rows = "\n".join(f"| {i} | {it['title'][:30]}... | {'/'.join(it['tags'])} | {it['total']} |" for i,it in enumerate(top,1))
    avg = round(mean(sc), 2)
    a = f"\n# 📈 {m}分析\n\n| 项 | 值 |\n|:---|---:|\n| 总数 | {len(items)} |\n| 均分 | {avg} |\n| 中位 | {round(median(sc),1)} |\n| 最高 | {max(sc)} |\n| 热门 | {ts} |\n\n## TOP10\n\n| # | 标题 | 标签 | 分 |\n|:---:|:---|:---|:---:|\n{rows}\n"
    for n in list_notes(folder_id=FOLDER_MONTHLY_ARCHIVE):
        if m in n["title"]:
            append_doc(n["note_id"], a)
            print(f"{m}完成！")
            return
    print("月度笔记不存在")

if __name__ == "__main__": main()
