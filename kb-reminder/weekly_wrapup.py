#!/usr/bin/env python3
"""
周收尾脚本（每周日晚执行）
1. 读取本周所有评分结果
2. 生成本周汇总统计表并追加到周笔记
3. 更新周笔记标题的日期区间
4. 标注「已封存」
5. 创建下一周的空白周卡片笔记
6. 清除状态文件 current_week_note_id
"""
import os
import json
import glob
from datetime import datetime, timedelta
from statistics import mean, median
from urllib import request as urllib_request
from note_api import append_doc, rename_note, create_blank_weekly_note, list_notes
from config.constants import FOLDER_WEEKLY_ARCHIVE

STATE_FILE = "state/current_week_note_id"
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "")


def send_feishu_weekly(start, end, count, avg, med, count_8_plus, top_tag, all_items):
    """发送飞书周报通知（8分+全卡片，其余标题+评分+标签）"""
    if not FEISHU_WEBHOOK:
        return
    
    all_sorted = sorted(all_items, key=lambda x: -x["total"])
    high_score_items = [x for x in all_sorted if x["total"] >= 8.0]
    low_score_items = [x for x in all_sorted if x["total"] < 8.0]
    
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**📊 本周概览**\n研报总数: {count} 条　平均分: {avg}　中位数: {med}\n8分+优质研报: {count_8_plus} 条　最佳标签: {top_tag[0]} ({top_tag[1]})"
            }
        },
        {"tag": "hr"}
    ]
    
    # 8分+：完整卡片
    if high_score_items:
        for item in high_score_items:
            title = item["title"]
            total = item["total"]
            tags = " / ".join(item["tags"])
            summary = item.get("summary", title)
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**⭐ {total} {title}**\n🏷️ {tags}"
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
    
    # 8分以下：标题+评分+标签（无概要）
    if low_score_items:
        rest_text = "**📋 其他研报**\n"
        for item in low_score_items:
            tags = " / ".join(item["tags"])
            rest_text += f"• **{item['title']}** ⭐ {item['total']}　🏷️ {tags}\n"
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": rest_text}
        })
        elements.append({"tag": "hr"})
    
    elements.append({
        "tag": "note",
        "element": [{"tag": "plain_text", "content": f"📋 三级归档系统 · 周度盘点 · {datetime.now().strftime('%m/%d %H:%M')}"}]
    })
    
    msg = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"📈 周度研报盘点 - {start} ~ {end}"},
                "template": "purple"
            },
            "elements": elements
        }
    }
    data = json.dumps(msg).encode("utf-8")
    req = urllib_request.Request(FEISHU_WEBHOOK, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib_request.urlopen(req, timeout=10) as resp:
            print(f"✅ 飞书周报已发送 (status={resp.status})")
    except Exception as e:
        print(f"⚠️ 飞书周报失败: {e}")


def get_this_week_dates():
    """获取本周的起止日期（周一到周日）"""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


def collect_this_week_scores():
    """收集本周所有批次的评分"""
    all_items = []
    # 读取本周的所有 evaluation_*.json
    outputs_dir = "outputs"
    for f in glob.glob(f"{outputs_dir}/evaluation_*.json"):
        with open(f) as fp:
            data = json.load(fp)
            all_items.extend(data["items"])
    return all_items


def generate_summary_table(items):
    """生成周汇总统计表"""
    if not items:
        return "无数据"
    
    scores = [x["total"] for x in items]
    avg_score = round(mean(scores), 2)
    med_score = round(median(scores), 1)
    max_score = max(scores)
    min_score = min(scores)
    count_8_plus = sum(1 for s in scores if s >= 8.0)
    
    # 统计平均分最高的标签
    tag_scores = {}
    for item in items:
        for tag in item["tags"]:
            if tag not in tag_scores:
                tag_scores[tag] = []
            tag_scores[tag].append(item["total"])
    
    tag_avg = {t: round(mean(vs), 2) for t, vs in tag_scores.items()}
    top_tag = max(tag_avg.items(), key=lambda x: x[1]) if tag_avg else ("", 0)
    
    table = f"""
## 📈 本周汇总统计

| 统计项 | 数值 |
|:-------|-----:|
| 研报总数 | {len(items)}条 |
| 平均分 | {avg_score} |
| 中位数 | {med_score} |
| 8分+数量 | {count_8_plus}条 |
| 平均分最高标签 | {top_tag[0]} ({top_tag[1]}) |

---

### 🔒 本周已封存
下一周内容将追加到新的周归档笔记中。
"""
    return table


def main():
    print("📊 开始周收尾处理...")
    
    # 1. 获取当前周笔记ID
    current_note_id = None
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            current_note_id = f.read().strip()
    else:
        # 搜索周归档笔记本中的最新笔记
        notes = list_notes(folder_id=FOLDER_WEEKLY_ARCHIVE)
        for n in notes:
            if "周盘点归档（卡片版）" in n["title"] and "已封存" not in n["title"]:
                current_note_id = n["note_id"]
                break
    
    if not current_note_id:
        print("❌ 找不到当前周笔记")
        return False
    
    print(f"📝 当前周笔记ID: {current_note_id}")
    
    # 2. 收集本周评分并生成汇总
    items = collect_this_week_scores()
    if not items:
        print("⚠️ 本周无评分数据")
        summary = "\n## 📈 本周汇总统计\n\n无新增研报\n\n---\n\n### 🔒 本周已封存"
    else:
        summary = generate_summary_table(items)
        print(f"📦 汇总 {len(items)} 条研报")
    
    # 3. 追加汇总表到周笔记
    result = append_doc(current_note_id, summary)
    if result.get("code") != 0:
        print(f"❌ 追加汇总失败: {result}")
        return False
    print("✅ 周汇总表已追加")
    
    # 4. 更新笔记标题（加上日期区间和已封存标记）
    start, end = get_this_week_dates()
    new_title = f"📊 周盘点归档（卡片版）| {start} ~ {end} [已封存]"
    result = rename_note(current_note_id, new_title)
    if result.get("code") != 0:
        print(f"❌ 重命名失败: {result}")
    else:
        print(f"✅ 笔记标题已更新: {new_title}")
    
    # 5. 创建下一周的空白笔记
    next_start = (datetime.now() + timedelta(days=7 - datetime.now().weekday())).strftime("%Y-%m-%d")
    next_week_range = f"{next_start} ~ 待更新"
    next_note_id = create_blank_weekly_note(next_week_range, FOLDER_WEEKLY_ARCHIVE)
    
    if next_note_id:
        print(f"✅ 下周空白笔记已创建: {next_note_id}")
        # 更新状态文件
        with open(STATE_FILE, "w") as f:
            f.write(next_note_id)
    else:
        print("⚠️ 下周空白笔记创建失败")
    
    print("\n🎉 周收尾完成！")
    
    # 飞书通知
    if items:
        scores = [x["total"] for x in items]
        avg_score = round(mean(scores), 2)
        med_score = round(median(scores), 1)
        count_8_plus = sum(1 for s in scores if s >= 8.0)
        tag_scores = {}
        for item in items:
            for tag in item["tags"]:
                if tag not in tag_scores:
                    tag_scores[tag] = []
                tag_scores[tag].append(item["total"])
        top_tag = max({t: round(mean(vs), 2) for t, vs in tag_scores.items()}.items(), key=lambda x: x[1])
        send_feishu_weekly(start, end, len(items), avg_score, med_score, count_8_plus, top_tag, items)
    else:
        send_feishu_weekly(start, end, 0, 0, 0, 0, ("", 0), [])
    
    return True


if __name__ == "__main__":
    main()
