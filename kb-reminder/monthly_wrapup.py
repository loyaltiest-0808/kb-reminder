#!/usr/bin/env python3
"""
月汇总脚本（每月最后一天执行）
1. 读取本月所有周卡片笔记内容
2. 生成本月分析总结
3. 汇总到月度笔记
4. 飞书通知：TOP5卡片 + 其余精简 + 热门研究方向
"""
import os
import json
import glob
from datetime import datetime
from statistics import mean, median
from collections import Counter
from urllib import request as urllib_request
from note_api import append_doc, list_notes, export_note
from config.constants import FOLDER_MONTHLY_ARCHIVE

FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


def fetch_hot_research_directions(tags):
    """调用DeepSeek API根据热门标签生成当前研究方向"""
    if not DEEPSEEK_API_KEY:
        return ""
    
    tag_names = [t for t, _ in tags]
    prompt = f"""你是一位量化金融研究员。基于以下本月最热门的5个研究标签：
{'、'.join(tag_names)}

请从专业研报和财经新闻视角，列出当前这些方向下的3-5个热门研究课题/方向。
每个方向用一句话描述（30字以内）。
格式要求：序号+方向名称+简短说明，每行一条。
无需开头语和结尾语。"""

    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
        "temperature": 0.3
    }).encode("utf-8")

    req = urllib_request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        },
        method="POST"
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"].strip()
            print("✅ 热门研究方向已生成")
            return content
    except Exception as e:
        print(f"⚠️ 研究方向生成失败: {e}")
        return ""


def send_feishu_monthly(month, count, avg, top5_tags, top5_items, rest_items, hot_directions):
    """发送飞书月报通知（TOP5卡片 + 其余精简 + 热门研究方向）"""
    if not FEISHU_WEBHOOK:
        return
    tags_str = "、".join([f"{t}({c})" for t, c in top5_tags])
    
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**📦 研报总数:** {count} 条　**📈 平均分:** {avg}"
            }
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**🏷️ 热门标签TOP5**\n{tags_str}"
            }
        },
        {"tag": "hr"}
    ]
    
    # TOP5完整卡片
    for i, item in enumerate(top5_items, 1):
        title = item["title"]
        total = item["total"]
        tags = " / ".join(item["tags"])
        summary = item.get("summary", title)
        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"{medal} **№{i} {title}**　⭐ **{total}**\n🏷️ {tags}"
            }
        })
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"> {summary}"
            }
        })
        elements.append({"tag": "hr"})
    
    # 其余精简展示
    if rest_items:
        rest_text = "**📋 其他研报**\n"
        for item in rest_items:
            tags = " / ".join(item["tags"])
            rest_text += f"• **{item['title']}** ⭐ {item['total']}　🏷️ {tags}\n"
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": rest_text}
        })
        elements.append({"tag": "hr"})
    
    # 热门研究方向
    if hot_directions:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**🔬 当前市场热门研究方向**\n{hot_directions}"
            }
        })
        elements.append({"tag": "hr"})
    
    elements.append({
        "tag": "note",
        "element": [{"tag": "plain_text", "content": f"📋 三级归档系统 · 月度分析 · {datetime.now().strftime('%m/%d %H:%M')}"}]
    })
    
    msg = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"📊 {month}月度研报分析"},
                "template": "green"
            },
            "elements": elements
        }
    }
    data = json.dumps(msg).encode("utf-8")
    req = urllib_request.Request(FEISHU_WEBHOOK, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib_request.urlopen(req, timeout=10) as resp:
            print(f"✅ 飞书月报已发送 (status={resp.status})")
    except Exception as e:
        print(f"⚠️ 飞书月报失败: {e}")


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
    outputs_dir = "outputs"
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
    
    # 飞书通知
    scores = [x["total"] for x in items]
    avg_score = round(mean(scores), 2)
    all_tags = [t for item in items for t in item["tags"]]
    top5_tags = Counter(all_tags).most_common(5)
    sorted_items = sorted(items, key=lambda x: -x["total"])
    top5_items = sorted_items[:5]
    rest_items = sorted_items[5:]
    
    # 生成热门研究方向
    hot_directions = fetch_hot_research_directions(top5_tags)
    
    send_feishu_monthly(month_name, len(items), avg_score, top5_tags, top5_items, rest_items, hot_directions)
    
    return True


if __name__ == "__main__":
    main()
