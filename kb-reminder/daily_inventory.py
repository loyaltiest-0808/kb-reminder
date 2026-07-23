#!/usr/bin/env python3
"""
每日盘点（新架构）
1. 识别Downloads文件夹新增
2. 打标签、五维评分
3. 直接追加到当前周卡片笔记（而不是本地文件）
4. 更新每日盘点日志（摘要版表格）
5. 飞书通知
"""
import os
import sys
import json
from datetime import datetime
from urllib import request as urllib_request
from scoring import score_one, render_score_card, extract_keywords, extract_summary
from note_api import append_doc, search_note_by_title, list_notes, create_blank_weekly_note
from config.constants import FOLDER_WEEKLY_ARCHIVE, NOTE_DAILY_LOG, BROKER_MAP

STATE_FILE = "state/current_week_note_id"
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "")


def send_feishu_notification(batch_date, count, avg_score, max_score, min_score, top3_titles, scores_summary):
    """发送飞书每日盘点通知（每条研报独立卡片）"""
    if not FEISHU_WEBHOOK:
        return

    # 每条研报单独成卡
    elements = []
    for item in scores_summary:
        num = item["num"]
        title = item["title"]
        tags = " / ".join(item["tags"])
        total = item["total"]
        summary = item.get("summary", title)
        
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**№{num} {title}**　⭐ **{total}**\n🏷️ {tags}"
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
    
    # 汇总行
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**汇总**　共 {count} 条　平均 {avg_score}　最高 {max_score}　最低 {min_score}"
        }
    })
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "note",
        "element": [{"tag": "plain_text", "content": f"📋 三级归档系统 · 每日盘点 · {datetime.now().strftime('%m/%d %H:%M')}"}]
    })

    msg = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"📊 知识库每日盘点 - {batch_date}"},
                "template": "blue"
            },
            "elements": elements
        }
    }
    data = json.dumps(msg).encode("utf-8")
    req = urllib_request.Request(FEISHU_WEBHOOK, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib_request.urlopen(req, timeout=10) as resp:
            print(f"✅ 飞书通知已发送 (status={resp.status})")
    except Exception as e:
        print(f"⚠️ 飞书通知失败: {e}")


def get_current_week_note():
    """获取当前周的卡片笔记ID，不存在则创建"""
    # 先看状态文件
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return f.read().strip()
    
    # 搜索最近的周笔记
    today = datetime.now()
    week_start = today.strftime("%Y-%m-%d")
    notes = list_notes(folder_id=FOLDER_WEEKLY_ARCHIVE)
    
    for n in notes:
        if "周盘点归档（卡片版）" in n["title"]:
            note_id = n["note_id"]
            # 缓存到状态文件
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, "w") as f:
                f.write(note_id)
            return note_id
    
    # 不存在则创建新的
    note_id = create_blank_weekly_note(f"{week_start} ~ 待更新", FOLDER_WEEKLY_ARCHIVE)
    if note_id:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            f.write(note_id)
    return note_id


def parse_filename(filename):
    """解析文件名提取券商和标题"""
    # 格式：20250910-国金证券-标题.pdf
    parts = filename.replace(".pdf", "").split("-", 2)
    if len(parts) < 3:
        return "未知券商", filename
    
    broker = parts[1]
    title = parts[2]
    
    # 简化券商名
    for short, full in BROKER_MAP.items():
        if short in broker:
            broker = full
            break
    
    return broker, title


def process_batch(items, batch_date=None):
    """
    处理一批入库研报
    items: [(title, [tags], filename), ...]
    """
    if batch_date is None:
        batch_date = datetime.now().strftime("%Y-%m-%d")
    
    week_note_id = get_current_week_note()
    if not week_note_id:
        print("❌ 无法获取当前周笔记ID")
        return False
    
    print(f"📅 处理批次: {batch_date}")
    print(f"📝 当前周笔记ID: {week_note_id}")
    print(f"📦 待处理研报: {len(items)}条")
    
    # 评分并生成卡片
    cards = []
    scores_summary = []
    total_scores = []
    
    for i, (title, tags, filename) in enumerate(items, 1):
        broker, clean_title = parse_filename(filename)
        dims, total = score_one(title, tags)
        keywords = extract_keywords(title)
        summary = extract_summary(title, tags)
        
        card = render_score_card(i, clean_title, broker, tags, keywords, dims, summary)
        cards.append(card)
        total_scores.append(total)
        scores_summary.append({
            "num": i, "title": clean_title, "tags": tags, "total": total, "summary": summary
        })
    
    # 追加到周笔记
    batch_header = f"\n## {batch_date} 批次（{len(items)}条）\n\n---\n\n"
    full_content = batch_header + "\n".join(cards)
    
    result = append_doc(week_note_id, full_content)
    if result.get("code") != 0:
        print(f"❌ 追加到周笔记失败: {result}")
        return False
    
    print(f"✅ 已追加 {len(items)} 张卡片到周笔记")
    
    # 更新每日盘点日志（摘要版表格）
    avg_score = round(sum(total_scores) / len(total_scores), 2)
    max_score = max(total_scores)
    min_score = min(total_scores)
    
    top3 = sorted(scores_summary, key=lambda x: -x["total"])[:3]
    top3_titles = "、".join([x["title"][:15] + "..." for x in top3])
    
    daily_row = f"""
| {batch_date} | {len(items)} | {avg_score} | {max_score} | {top3_titles} |
"""
    append_doc(NOTE_DAILY_LOG, daily_row)
    print("✅ 每日盘点日志已更新")
    
    # 保存评分详情到本地（用于月度分析）
    output = {
        "batch_date": batch_date,
        "count": len(items),
        "avg": avg_score,
        "items": scores_summary
    }
    os.makedirs("outputs", exist_ok=True)
    with open(f"outputs/evaluation_{batch_date}.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n🎉 批次处理完成！")
    print(f"   平均分: {avg_score}")
    print(f"   最高分: {max_score}")
    print(f"   最低分: {min_score}")
    
    # 飞书通知
    send_feishu_notification(batch_date, len(items), avg_score, max_score, min_score, top3_titles, scores_summary)
    
    return True


if __name__ == "__main__":
    # 测试用：模拟一批数据
    test_items = [
        ("LLM赋能资产配置，基于新闻数据的AI因子", ["大模型投研", "资产配置"], "20250924-华泰证券-LLM赋能资产配置.pdf"),
        ("如何压缩因子动物园？", ["基本面量化", "多因子选股"], "20250929-华安证券-如何压缩因子动物园.pdf"),
    ]
    process_batch(test_items, "2026-07-23")
