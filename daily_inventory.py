#!/usr/bin/env python3
"""每日盘点"""
import os, json
from datetime import datetime
from scoring import score_one, render_score_card, extract_keywords, extract_summary
from note_api import append_doc, list_notes, create_blank_weekly_note
from config.constants import FOLDER_WEEKLY_ARCHIVE, NOTE_DAILY_LOG, BROKER_MAP

BD = os.path.dirname(os.path.abspath(__file__))
SF = os.path.join(BD, "state", "current_week_note_id")
OD = os.path.join(BD, "outputs")

def get_week():
    if os.path.exists(SF):
        with open(SF) as f: return f.read().strip()
    for n in list_notes(folder_id=FOLDER_WEEKLY_ARCHIVE):
        if "周盘点归档（卡片版）" in n["title"]:
            os.makedirs(os.path.dirname(SF), exist_ok=True)
            open(SF, "w").write(n["note_id"])
            return n["note_id"]
    nid = create_blank_weekly_note(f"{datetime.now():%Y-%m-%d} ~ 待更新", FOLDER_WEEKLY_ARCHIVE)
    if nid:
        os.makedirs(os.path.dirname(SF), exist_ok=True)
        open(SF, "w").write(nid)
    return nid

def parse_fn(fn):
    p = fn.replace(".pdf", "").split("-", 2)
    if len(p) < 3: return "未知券商", fn
    b, t = p[1], p[2]
    for s, f in BROKER_MAP.items():
        if s in b: b = f; break
    return b, t

def process_batch(items, bd=None):
    if not bd: bd = f"{datetime.now():%Y-%m-%d}"
    wid = get_week()
    if not wid: print("无周笔记ID"); return False
    print(f"处理 {bd} | {len(items)} 条")
    cards, sm, ts = [], [], []
    for i, (t, ts_, fn) in enumerate(items, 1):
        br, ct = parse_fn(fn)
        d, tot, r = score_one(t, ts_)
        cards.append(render_score_card(i, ct, br, ts_, extract_keywords(t), extract_summary(t), d, r))
        ts.append(tot); sm.append({"num": i, "title": ct, "tags": ts_, "total": tot})
    append_doc(wid, f"\n## {bd} 批次（{len(items)}条）\n\n---\n\n" + "\n".join(cards))
    avg = round(sum(ts)/len(ts), 2)
    top3 = sorted(sm, key=lambda x: -x["total"])[:3]
    top3t = "、".join([x["title"][:15]+"..." for x in top3])
    append_doc(NOTE_DAILY_LOG, f"\n| {bd} | {len(items)} | {avg} | {max(ts)} | {top3t} |\n")
    os.makedirs(OD, exist_ok=True)
    json.dump({"batch_date": bd, "count": len(items), "avg": avg, "items": sm},
        open(os.path.join(OD, f"evaluation_{bd}.json"), "w"), ensure_ascii=False, indent=2)
    print(f"完成！均分 {avg}")
    return True

if __name__ == "__main__":
    process_batch([
        ("LLM赋能资产配置", ["大模型投研","资产配置"], "20250924-华泰证券-LLM赋能资产配置.pdf"),
        ("如何压缩因子动物园？", ["基本面量化","多因子选股"], "20250929-华安证券-如何压缩因子动物园.pdf"),
    ], "2026-07-23")
