#!/usr/bin/env python3
"""周收尾"""
import os, json, glob
from datetime import datetime, timedelta
from statistics import mean, median
from note_api import append_doc, rename_note, create_blank_weekly_note, list_notes
from config.constants import FOLDER_WEEKLY_ARCHIVE

BD = os.path.dirname(os.path.abspath(__file__))
SF = os.path.join(BD, "state", "current_week_note_id")
OD = os.path.join(BD, "outputs")

def main():
    print("周收尾...")
    nid = None
    if os.path.exists(SF): nid = open(SF).read().strip()
    else:
        for n in list_notes(folder_id=FOLDER_WEEKLY_ARCHIVE):
            if "周盘点归档（卡片版）" in n["title"] and "已封存" not in n["title"]:
                nid = n["note_id"]; break
    if not nid: print("找不到周笔记"); return
    items = []
    for f in glob.glob(os.path.join(OD, "evaluation_*.json")):
        items.extend(json.load(open(f))["items"])
    if not items:
        s = "\n## 📈 本周汇总\n\n无新增\n\n---\n\n### 🔒 已封存"
    else:
        sc = [x["total"] for x in items]
        ts = {}
        for it in items:
            for t in it["tags"]: ts.setdefault(t, []).append(it["total"])
        tt = max({t: round(mean(v),2) for t,v in ts.items()}.items(), key=lambda x: x[1]) if ts else ("",0)
        s = f"\n## 📈 本周汇总\n\n| 项 | 值 |\n|:---|---:|\n| 总数 | {len(items)} |\n| 均分 | {round(mean(sc),2)} |\n| 中位 | {round(median(sc),1)} |\n| 8分+ | {sum(1 for x in sc if x>=8)} |\n| 最佳 | {tt[0]}({tt[1]}) |\n\n---\n\n### 🔒 已封存\n"
    append_doc(nid, s)
    now = datetime.now()
    mon = now - timedelta(days=now.weekday())
    sun = mon + timedelta(days=6)
    rename_note(nid, f"📊 周盘点归档（卡片版）| {mon:%Y-%m-%d} ~ {sun:%Y-%m-%d} [已封存]")
    nxt = (now + timedelta(days=7 - now.weekday())).strftime("%Y-%m-%d")
    new_id = create_blank_weekly_note(f"{nxt} ~ 待更新", FOLDER_WEEKLY_ARCHIVE)
    if new_id:
        os.makedirs(os.path.dirname(SF), exist_ok=True)
        open(SF, "w").write(new_id)
    print("周收尾完成！")

if __name__ == "__main__": main()
