#!/usr/bin/env python3
"""
月汇总脚本（每月最后一天执行）
1. 读取本月所有周卡片笔记内容
2. 生成本月分析总结
3. 汇总到月度笔记
"""
import os
import json
import glob
from datetime import datetime
from statistics import mean, median
from collections import Counter
from note_api import append_doc, list_notes, export_note
from config.constants import FOLDER_MONTHLY_ARCHIVE


def get_this_month_weekly_notes():
    """获取本月所有已封存的周笔记"""
    notes = list_notes(folder_id=FOLDER_MONTHLY_ARCHIVE.replace("monthly", "weekly"))
    this_month = datetime.now().strftime("%Y-%m")
    weekly_notes = []
    
    for n in notes:
        if "周盘点归档（卡片版）" in n["title"] and this_month in n["title"]:
            weekly_notes.append(n)
    
    return sorted(weekly_notes, key=lambda x: x["title"])


def collect_this_month_scores():
    """收集本月所有评分数据"""
    all_items = []
    outputs_dir = "/sandbox/workspace/outputs"
    this_month = datetime.now().strftime("%Y-%m")
    
    for f in sorted(glob.glob(f"{outputs_dir}/evaluation_*.json")):
        if this_month in f:
            with open(f) as fp:
                data = json.load(fp)
                all_items.extend(data["items"])
    
    return all_items


def generate_monthly_analysis(items):
    """生成本月分析"""
    if not items:
        return "本月无数据"
    
    scores = [x["total"] for x in items]
    avg_score = round(mean(scores), 2)
    med_score = round(median(scores), 1)
    max_score = max(scores)
    
    # 标签分布
    all_tags = []
    for item in items:
        all_tags.extend(item["tags"])
    tag_counts = Counter(all_tags)
    top_tags = tag_counts.most_common(5)
    tags_str = "、".join([f"{t}({c})" for t, c in top_tags])
    
    # 高分榜TOP10
    top10 = sorted(items, key=lambda x: -x["total"])[:10]
    top10_rows = ""
    for i, item in enumerate(top10, 1):
        top10_rows += f"| {i} | {item['title'][:30]}... | {'/'.join(item['tags'])} | {item['total']} |\n"
    
    month_name = datetime.now().strftime("%Y年%m月")
    
    analysis = f"""
# 📈 {month_name}分析归档

## 📊 整体概览

| 统计项 | 数值 |
|:-------|-----:|
| 研报总数 | {len(items)}条 |
| 平均分 | {avg_score} |
| 中位数 | {med_score} |
| 最高分 | {max_score} |
| 热门标签TOP5 | {tags_str} |

---

## 🏆 高分榜TOP10

| 排名 | 标题 | 标签 | 评分 |
|:---:|:------|:-----|:----:|
{top10_rows}
---

## 💡 月度洞察

> 本月共收录 {len(items)} 篇研报，平均分 {avg_score}，整体质量{"优秀" if avg_score >= 8.0 else "良好" if avg_score >= 7.5 else "中等"}。

> 热门方向集中在「{top_tags[0][0]}」方向，共 {top_tags[0][1]} 篇相关研报，反映出{top_tags[0][0]}是当前量化领域的热点话题。
"""
    return analysis


def main():
    month_name = datetime.now().strftime("%Y年%m月")
    print(f"📊 开始{month_name}汇总...")
    
    # 1. 收集数据
    items = collect_this_month_scores()
    if not items:
        print("⚠️ 本月无评分数据")
        return False
    
    print(f"📦 本月共 {len(items)} 篇研报")
    
    # 2. 生成月度分析
    analysis = generate_monthly_analysis(items)
    
    # 3. 查找或创建月度笔记
    notes = list_notes(folder_id=FOLDER_MONTHLY_ARCHIVE)
    monthly_note_id = None
    for n in notes:
        if month_name in n["title"]:
            monthly_note_id = n["note_id"]
            break
    
    if monthly_note_id:
        # 追加内容
        result = append_doc(monthly_note_id, analysis)
        if result.get("code") != 0:
            print(f"❌ 追加失败: {result}")
            return False
        print(f"✅ 内容已追加到月度笔记: {monthly_note_id}")
    else:
        print("⚠️ 月度笔记不存在，请先创建空白月度笔记")
        # 这里可以调用 import_doc 创建，但需要额外API支持
        return False
    
    print(f"\n🎉 {month_name}汇总完成！")
    return True


if __name__ == "__main__":
    main()
