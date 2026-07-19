#!/usr/bin/env python3
"""
知识库定时盘点系统 — 核心脚本
支持模式：daily | weekly | monthly | nightly
依赖：requests (pip install requests)
环境变量：IMA_OPENAPI_CLIENTID, IMA_OPENAPI_APIKEY
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from statistics import mean

# ═══════════════════════════════════════════
# 常量
# ═══════════════════════════════════════════

KB_ID = "28RoKuOA8h1pcBxomcac8BUYQF0lqvuxeNQ1X3dtbu0="
DOWNLOADS_FOLDER_ID = "folder_7482703326763920"
NOTEBOOK_FOLDER_ID = "folder59c27fce58bc1de2"
DAILY_LOG_NOTE_ID = "7483148258522158"
SYSTEM_STATUS_NOTE_ID = "7483148258537130"

BASE_URL = "https://ima.qq.com"
FEISHU_WEBHOOK = os.environ.get(
    "FEISHU_WEBHOOK",
    "https://open.feishu.cn/open-apis/bot/v2/hook/ac6ae40e-9cfd-411d-bda4-44d2d16fbf30"
)
TODAY = datetime.now().strftime("%Y-%m-%d")
NOW_STR = datetime.now().strftime("%Y-%m-%d %H:%M")

# 20个标签及其关键词映射
TAG_KEYWORDS = {
    "大模型投研": ["大模型", "LLM", "GPT", "语言模型", "transformer", "AI研报", "大语言"],
    "多因子选股": ["多因子", "因子选股", "Alpha因子", "因子体系", "因子挖掘", "因子模型"],
    "量价因子": ["量价", "成交量", "价格因子", "形态因子", "K线", "筹码分布", "流动性"],
    "择时策略": ["择时", "市场时机", "时机选择", "基差择时"],
    "资产配置": ["资产配置", "宏观因子", "股债", "组合优化"],
    "深度学习选股": ["深度学习", "神经网络", "GRU", "LSTM", "Transformer选股", "时序模型"],
    "风险管理": ["风险因子", "风险控制", "特质风险", "共同风险", "风险管理"],
    "基本面量化": ["基本面", "财务", "财报", "EP因子", "估值因子", "质量因子"],
    "AI编程工具": ["编程", "代码", "编码", "Copilot", "CloudCode", "Cloud Code", "Cloud", "AI工具", "工具教程", "工具分享", "工具介绍", "工具教学", "开源项目", "第二大脑", "Claude", "AI员工", "AI代理", "Agent", "WQ-Alpha", "约束规则"],
    "量化综合": ["量化", "策略", "回测", "因子", "实证"],
    "指数增强": ["指数增强", "增强策略", "跟踪误差"],
    "ETF策略": ["ETF", "交易型开放式"],
    "行业轮动": ["行业轮动", "板块轮动"],
    "可转债": ["可转债", "转债"],
    "债券固收": ["债券", "固收", "利率"],
    "FOF基金": ["FOF", "基金组合", "基金评价"],
    "风格轮动": ["风格轮动", "大小盘"],
    "红利策略": ["红利", "分红", "股息"],
    "数字货币与DeFi": ["数字货", "BTC", "ETH", "DeFi"],
    "知识库管理": ["知识库", "知识管理", "笔记"],
}

# TAG_BASE 基准分（多标签取max）
TAG_BASE = {
    "FOF基金": 7.5, "风险管理": 7.5, "深度学习选股": 7.5,
    "大模型投研": 7.3, "基本面量化": 7.2, "多因子选股": 7.2,
    "量价因子": 7.1, "资产配置": 7.1, "行业轮动": 7.0,
    "风格轮动": 7.0, "择时策略": 7.0, "ETF策略": 7.0,
    "红利策略": 6.9, "指数增强": 6.9, "债券固收": 6.9,
    "可转债": 6.8, "量化综合": 6.7, "数字货币与DeFi": 6.6,
    "AI编程工具": 6.5, "知识库管理": 5.5,
}
BASE = 7.0


# ═══════════════════════════════════════════
# API 调用
# ═══════════════════════════════════════════

def get_credentials():
    client_id = os.environ.get("IMA_OPENAPI_CLIENTID", "")
    api_key = os.environ.get("IMA_OPENAPI_APIKEY", "")
    if not client_id or not api_key:
        print("❌ 缺少 IMA 凭证。设置环境变量 IMA_OPENAPI_CLIENTID 和 IMA_OPENAPI_APIKEY")
        sys.exit(1)
    return client_id, api_key


def ima_api(path, body):
    """通用 IMA API 调用"""
    import requests
    client_id, api_key = get_credentials()
    url = f"{BASE_URL}/{path}"
    headers = {
        "ima-openapi-clientid": client_id,
        "ima-openapi-apikey": api_key,
        "Content-Type": "application/json",
    }
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    data = resp.json()
    if data.get("code") != 0:
        print(f"⚠️ API 错误 [{path}]: {data.get('msg', '未知错误')}")
    return data


def feishu_notify(title, content_lines):
    """发送飞书机器人通知"""
    import requests
    if not FEISHU_WEBHOOK:
        print("⚠️ 未配置飞书 Webhook，跳过通知")
        return

    # 构造飞书富文本消息
    elements = []
    for line in content_lines:
        elements.append({"tag": "div", "text": {"tag": "plain_text", "content": line}})

    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": elements
        }
    }

    try:
        resp = requests.post(FEISHU_WEBHOOK, json=card, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == 0:
                print("✅ 飞书通知已发送")
            else:
                print(f"⚠️ 飞书通知失败: {data.get('msg', '未知错误')}")
        else:
            print(f"⚠️ 飞书通知 HTTP 错误: {resp.status_code}")
    except Exception as e:
        print(f"⚠️ 飞书通知异常: {e}")


# ═══════════════════════════════════════════
# 分类 & 评分
# ═══════════════════════════════════════════

def classify_title(title):
    """根据标题关键词匹配标签，返回匹配的标签列表"""
    title_lower = title.lower()
    
    # 先找出所有匹配的具体标签
    # 排除的"量化综合"作为兜底标签
    specific_tags = {k: v for k, v in TAG_KEYWORDS.items() if k != "量化综合"}
    fallback_tag = TAG_KEYWORDS.get("量化综合", [])
    
    matched = []
    for tag, keywords in specific_tags.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                matched.append(tag)
                break

    # 如果有具体标签匹配，不加"量化综合"
    # 如果没有任何标签匹配，用"量化综合"兜底
    if not matched:
        for kw in fallback_tag:
            if kw.lower() in title_lower:
                matched.append("量化综合")
                break
    
    # 最终兜底
    if not matched:
        matched = ["量化综合"]

    return matched


def score_one(title, tags):
    """五维评分"""
    dims = {"depth": BASE, "data": BASE, "logic": BASE,
            "practical": BASE, "innovation": BASE}

    # 标签加成（取max）
    tag_bonus = max((TAG_BASE.get(t, BASE) - BASE) for t in tags) if tags else 0
    for k in dims:
        dims[k] += tag_bonus

    t = title
    # 标题关键词加成
    if "深度研究" in t or "专题" in t:
        dims["depth"] += 0.4
    if "学海拾珠" in t:
        dims["depth"] += 0.3
        dims["logic"] += 0.3
    if any(kw in t for kw in ["深度学习", "机器学习", "大模型", "AI", "GRU", "神经网络", "图谱"]):
        dims["innovation"] += 0.6
        dims["depth"] += 0.2
    if any(kw in t for kw in ["模型", "框架", "系统", "体系"]):
        dims["logic"] += 0.3
        dims["depth"] += 0.2
    if any(kw in t for kw in ["因子", "策略", "配置", "择时", "选股", "轮动"]):
        dims["practical"] += 0.3
    if any(kw in t for kw in ["回测", "实证", "研究", "应用"]):
        dims["data"] += 0.3
    if any(kw in t for kw in ["系列", "报告"]):
        dims["data"] += 0.2

    for k in dims:
        dims[k] = round(max(1.0, min(10.0, dims[k])), 2)
    total = round(mean(dims.values()), 2)
    return dims, total


# ═══════════════════════════════════════════
# 听脑AI 自动重命名
# ═══════════════════════════════════════════

TINGNAO_WAIT_SECONDS = 15  # 等待听脑AI内容加载的时间（秒）


def is_tingnao_item(title):
    """判断是否为听脑AI自动命名的条目"""
    return "听脑AI" in title


def is_tingnao_new(item):
    """判断是否为新入库的听脑AI条目（标题原始、无标签或标签少）"""
    title = item.get("title", "")
    tags = item.get("tags", [])
    return is_tingnao_item(title) and len(tags) <= 1


def fetch_item_summary(kb_id, media_id):
    """通过 search_knowledge 获取单条内容的摘要"""
    resp = ima_api("openapi/wiki/v1/search_knowledge", {
        "knowledge_base_id": kb_id,
        "query": media_id,
        "cursor": "",
        "limit": 5
    })
    items = resp.get("data", {}).get("knowledge_list", [])
    for item in items:
        if item.get("media_id") == media_id:
            return item.get("summary", "")
    return ""


def generate_real_title(summary, media_id):
    """根据摘要生成真实标题（防重名）"""
    if not summary or len(summary.strip()) < 10:
        return None

    clean = summary.strip()
    for prefix in ["该报告是", "本文是", "该文章", "这篇"]:
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
            break

    # 取第一个句号前的内容
    if "。" in clean:
        title_part = clean.split("。")[0]
    elif "，" in clean:
        title_part = clean.split("，")[0]
    else:
        title_part = clean[:50]

    if len(title_part) > 40:
        title_part = title_part[:40]

    return title_part.strip()


def rename_knowledge_item(kb_id, media_id, new_name):
    """重命名知识库条目"""
    resp = ima_api("openapi/wiki/v1/rename_knowledge", {
        "knowledge_base_id": kb_id,
        "media_id": media_id,
        "name": new_name
    })
    return resp.get("code", -1) == 0


def handle_tingnao_items(kb_items):
    """处理新入库的听脑AI条目：等待内容加载 → 读取摘要 → 自动重命名"""
    tingnao_new = [item for item in kb_items if is_tingnao_new(item)]

    if not tingnao_new:
        return

    print(f"\n🔍 发现 {len(tingnao_new)} 条新听脑AI条目，等待内容加载（{TINGNAO_WAIT_SECONDS}秒）...")

    # 第一轮：立即尝试（有些可能已经加载好了）
    renamed = 0
    pending = []
    for item in tingnao_new:
        media_id = item.get("media_id", "")
        old_title = item.get("title", "")
        summary = item.get("summary", "")

        # 如果 summary 字段为空，尝试通过 search_knowledge 获取
        if not summary:
            summary = fetch_item_summary(KB_ID, media_id)

        new_title = generate_real_title(summary, media_id)
        if new_title and new_title != old_title:
            if rename_knowledge_item(KB_ID, media_id, new_title):
                print(f"  ✅ {new_title[:40]}")
                renamed += 1
            else:
                print(f"  ❌ 重命名失败: {new_title[:40]}")
        else:
            pending.append(item)

    if not pending:
        print(f"  听脑AI重命名完成: {renamed}/{len(tingnao_new)}")
        return

    # 第二轮：等待后重试
    print(f"  ⏳ {len(pending)} 条内容未就绪，等待 {TINGNAO_WAIT_SECONDS} 秒...")
    time.sleep(TINGNAO_WAIT_SECONDS)

    # 重新获取知识库列表（内容可能已加载）
    kb_items_refreshed = get_all_items(KB_ID)
    tingnao_refreshed = {item.get("media_id"): item for item in kb_items_refreshed if is_tingnao_item(item.get("title", ""))}

    for item in pending:
        media_id = item.get("media_id", "")
        old_title = item.get("title", "")

        # 用刷新后的数据
        refreshed = tingnao_refreshed.get(media_id, item)
        summary = refreshed.get("summary", "")
        if not summary:
            summary = fetch_item_summary(KB_ID, media_id)

        new_title = generate_real_title(summary, media_id)
        if new_title and new_title != old_title:
            if rename_knowledge_item(KB_ID, media_id, new_title):
                print(f"  ✅ (延迟) {new_title[:40]}")
                renamed += 1
            else:
                print(f"  ❌ (延迟) 重命名失败: {new_title[:40]}")
        else:
            print(f"  ⏭️ 内容仍未就绪，跳过: {old_title[:30]}...")

    print(f"  听脑AI重命名完成: {renamed}/{len(tingnao_new)}")


# ═══════════════════════════════════════════
# 核心业务逻辑
# ═══════════════════════════════════════════

def get_knowledge_list(kb_id, folder_id="", cursor="", limit=50):
    """获取知识库内容列表"""
    body = {"knowledge_base_id": kb_id, "cursor": cursor, "limit": limit}
    if folder_id:
        body["folder_id"] = folder_id
    data = ima_api("openapi/wiki/v1/get_knowledge_list", body)
    return data.get("data", {})


def get_all_items(kb_id, folder_id=""):
    """翻页获取全部条目（根目录 + 子文件夹）"""
    all_items = []
    cursor = ""
    while True:
        result = get_knowledge_list(kb_id, folder_id, cursor, 50)
        items = result.get("knowledge_list", [])
        all_items.extend(items)
        if result.get("is_end", True):
            break
        cursor = result.get("next_cursor", "")
        time.sleep(0.5)

    # 递归获取子文件夹内容
    subfolders = [item for item in all_items if item.get("media_type") == 99]
    for folder in subfolders:
        sub_items = get_all_items(kb_id, folder.get("media_id", ""))
        all_items.extend(sub_items)

    return all_items


def tag_add(kb_id, item_id, tag_name):
    """给文件打标签"""
    body = {
        "knowledge_base_id": kb_id,
        "item_id": item_id,
        "tag_name": tag_name,
    }
    return ima_api("openapi/wiki/v1/tag_add", body)


def tag_list(kb_id, keyword=""):
    """列出标签"""
    body = {"knowledge_base_id": kb_id, "limit": 100}
    if keyword:
        body["keyword"] = keyword
    data = ima_api("openapi/wiki/v1/tag_list", body)
    return data.get("data", {}).get("items", [])


def append_note(note_id, content):
    """追加内容到笔记"""
    body = {
        "doc_id": note_id,
        "content": content,
        "content_format": 1,
    }
    return ima_api("openapi/note/v1/append_doc", body)


def get_note_content(note_id):
    """获取笔记内容"""
    body = {"doc_id": note_id}
    data = ima_api("openapi/note/v1/get_doc_content", body)
    return data.get("data", {}).get("content", "")


def search_knowledge(kb_id, query):
    """搜索知识库内容"""
    body = {"knowledge_base_id": kb_id, "query": query, "cursor": "", "limit": 50}
    data = ima_api("openapi/wiki/v1/search_knowledge", body)
    return data.get("data", {})


# ═══════════════════════════════════════════
# 每日盘点
# ═══════════════════════════════════════════

def run_daily_inventory():
    """每日盘点：扫描知识库 vs Downloads 文件夹，识别新增并入库"""
    print(f"\n{'='*60}")
    print(f"📋 每日盘点 — {NOW_STR}")
    print(f"{'='*60}")

    # 1. 获取当前系统状态（读取笔记，获取上次处理记录）
    known_items_note = get_note_content(SYSTEM_STATUS_NOTE_ID)

    # 2. 获取知识库全部条目（含文件夹）
    kb_items = get_all_items(KB_ID)

    # 2.5 自动处理听脑AI条目（重命名）
    handle_tingnao_items(kb_items)

    # 重新获取（重命名后刷新）
    kb_items = get_all_items(KB_ID)

    kb_titles = {}
    for item in kb_items:
        mid = item.get("media_id", "")
        title = item.get("title", "")
        tags = item.get("tags", [])
        parent_folder = item.get("parent_folder_id", "")
        media_type = item.get("media_type", 0)
        if mid:
            kb_titles[mid] = {"title": title, "tags": tags, "folder": parent_folder, "media_type": media_type}

    print(f"知识库总条目: {len(kb_titles)}")

    # 3. 获取 Downloads 文件夹内容（研报入库来源）
    dl_items = get_all_items(KB_ID, DOWNLOADS_FOLDER_ID)
    print(f"Downloads 文件夹: {len(dl_items)} 个文件")

    # 4. 识别未处理条目（在知识库中且未打标签，排除文件夹）
    #    策略：找出所有没有标签的条目，它们需要被打标签+评分
    untagged = []
    for mid, info in kb_titles.items():
        if info["media_type"] == 99:  # 跳过文件夹（media_type=99）
            continue
        if not info["tags"]:  # 没有标签 = 未处理
            untagged.append({"media_id": mid, "title": info["title"], "folder": info["folder"]})

    print(f"未处理条目（未打标签）: {len(untagged)}")

    if not untagged:
        summary = f"✅ 每日盘点完成 ({NOW_STR}): 无新增未处理条目。"
        print(summary)
        append_note(DAILY_LOG_NOTE_ID, f"\n## {TODAY} 每日盘点\n\n{summary}\n")
        # 更新状态笔记
        update_status("最后盘点时间", NOW_STR)
        return

    # 5. 逐条处理：分类 → 打标签 → 评分
    results = []
    for item in untagged:
        title = item["title"]
        # 分类
        tags = classify_title(title)
        # 评分
        dims, total = score_one(title, tags)

        results.append({
            "title": title,
            "media_id": item["media_id"],
            "tags": tags,
            "scores": dims,
            "total": total,
        })
        print(f"  📄 {title[:50]}... → {tags[0]} ({total})")

    # 6. 批量打标签（全部完成后统一打，避免中途失败回滚问题）
    print("\n⏳ 开始打标签...")
    tag_count = 0
    for r in results:
        for tag in r["tags"]:
            resp = tag_add(KB_ID, r["media_id"], tag)
            if resp.get("code") == 0:
                tag_count += 1
            time.sleep(0.3)  # 避免频控

    print(f"✅ 打标签完成: {tag_count} 个标签")

    # 7. 按总分排序
    results.sort(key=lambda x: -x["total"])
    avg_score = round(mean(r["total"] for r in results), 2)

    # 8. 写每日盘点日志
    log_content = build_daily_log(results, avg_score)
    append_note(DAILY_LOG_NOTE_ID, log_content)

    # 9. 更新系统状态笔记
    update_status("最后盘点时间", NOW_STR)
    update_status("知识库总条目", str(len(kb_titles)))

    # 10. 打印汇总
    print(f"\n📊 盘点汇总:")
    print(f"  新增处理: {len(results)} 条")
    print(f"  均分: {avg_score}/10")
    print(f"  TOP1: {results[0]['title'][:50]} ({results[0]['total']})")

    # 11. 保存评分档案（GitHub Actions 中存档为 artifact）
    archive = {
        "batch_date": TODAY,
        "count": len(results),
        "avg": avg_score,
        "items": results,
    }
    os.makedirs("outputs", exist_ok=True)
    with open(f"outputs/evaluation_{TODAY}.json", "w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, indent=2)

    print(f"📁 评分档案已保存: outputs/evaluation_{TODAY}.json")

    # 12. 飞书通知
    feishu_lines = [
        f"⏰ 时间: {NOW_STR}",
        f"📊 知识库总条目: {len(kb_titles)}",
        f"🆕 本次新增处理: {len(results)} 条",
        f"🏷️ 打标签: {tag_count} 个",
        f"📈 均分: {avg_score}/10",
        f"🏆 TOP1: {results[0]['title'][:40]} ({results[0]['total']})",
    ]
    feishu_notify("📋 每日盘点完成", feishu_lines)


def build_daily_log(results, avg_score):
    """构建每日盘点日志 markdown"""
    lines = [f"\n## {TODAY} 每日盘点\n"]
    lines.append(f"处理时间: {NOW_STR}")
    lines.append(f"新增处理: {len(results)} 条 | 均分: {avg_score}/10 | 最高: {results[0]['total']} | 最低: {results[-1]['total']}\n")

    lines.append("### 五维评分排序\n")
    lines.append("|#|标题|标签|深度|数据|逻辑|实用|创新|总分|")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(results, 1):
        tags_str = ", ".join(r["tags"])
        title_short = r["title"][:40]
        s = r["scores"]
        lines.append(f"|{i}|{title_short}|{tags_str}|{s['depth']}|{s['data']}|{s['logic']}|{s['practical']}|{s['innovation']}|{r['total']}|")

    # 按标签汇总
    tag_stats = {}
    for r in results:
        for t in r["tags"]:
            if t not in tag_stats:
                tag_stats[t] = []
            tag_stats[t].append(r["total"])
    lines.append("\n### 按标签汇总\n")
    lines.append("|标签|条数|均分|")
    lines.append("|---|---|---|")
    for tag, scores in sorted(tag_stats.items(), key=lambda x: -len(x[1])):
        avg = round(mean(scores), 2)
        lines.append(f"|{tag}|{len(scores)}|{avg}|")

    return "\n".join(lines)


# ═══════════════════════════════════════════
# 周回顾
# ═══════════════════════════════════════════

def run_weekly_review():
    """周回顾：随机推送3条已入库知识做回顾"""
    import random
    print(f"\n{'='*60}")
    print(f"📊 周回顾 — {NOW_STR}")
    print(f"{'='*60}")

    # 获取当前知识库状态
    kb_items = get_all_items(KB_ID)

    # 过滤出有标签的条目（排除文件夹）
    tag_items = []
    for item in kb_items:
        if item.get("media_type") == 99:  # 跳过文件夹
            continue
        tags = item.get("tags", [])
        if tags:
            tag_items.append(item)

    print(f"知识库总条目: {len(kb_items)} | 有标签条目: {len(tag_items)}")

    if not tag_items:
        summary = f"✅ 周回顾完成 ({NOW_STR}): 知识库暂无有标签条目。"
        append_note(DAILY_LOG_NOTE_ID, f"\n## {TODAY} 周回顾\n\n{summary}\n")
        update_status("最后周回顾时间", NOW_STR)
        feishu_notify("📊 周回顾完成", [summary])
        return

    # 随机抽取3条（尽量跨标签）
    random.seed(int(TODAY.replace("-", "")))  # 同一天结果固定，可复现
    if len(tag_items) <= 3:
        selected = tag_items[:]
    else:
        # 尝试跨标签抽取：每条来自不同标签
        tag_groups = {}
        for item in tag_items:
            primary_tag = item.get("tags", ["其他"])[0]
            if primary_tag not in tag_groups:
                tag_groups[primary_tag] = []
            tag_groups[primary_tag].append(item)

        selected = []
        available_tags = list(tag_groups.keys())
        random.shuffle(available_tags)
        for tag in available_tags:
            if len(selected) >= 3:
                break
            items = tag_groups[tag]
            selected.append(random.choice(items))

        # 如果不够3条，从剩余中补
        if len(selected) < 3:
            remaining = [i for i in tag_items if i not in selected]
            if remaining:
                need = 3 - len(selected)
                selected.extend(random.sample(remaining, min(need, len(remaining))))

    print(f"随机抽取 {len(selected)} 条知识做回顾")

    # 构建笔记内容
    lines = [f"\n## {TODAY} 周回顾\n"]
    lines.append(f"回顾时间: {NOW_STR}")
    lines.append(f"知识库总条目: {len(kb_items)} | 有标签: {len(tag_items)}\n")
    lines.append("### 🎯 本周精选回顾（随机抽取 3 条）\n")

    for i, item in enumerate(selected, 1):
        title = item.get("title", "未知标题")
        tags = item.get("tags", [])
        tags_str = " / ".join(tags)
        dims, total = score_one(title, tags)

        # 清洗标题：去掉日期前缀和券商名
        clean_title = title
        for prefix in ["20250", "2024", "2023"]:
            if clean_title.startswith(prefix):
                parts = clean_title.split("-", 2)
                if len(parts) >= 3:
                    clean_title = parts[2]
                    break

        lines.append(f"**{i}. {clean_title}**")
        lines.append(f"   - 标签: {tags_str}")
        lines.append(f"   - 评分: {total}/10 (深度{dims['depth']} 数据{dims['data']} 逻辑{dims['logic']} 实用{dims['practical']} 创新{dims['innovation']})")
        lines.append("")

    content = "\n".join(lines)
    append_note(DAILY_LOG_NOTE_ID, content)
    update_status("最后周回顾时间", NOW_STR)

    print(f"✅ 周回顾完成")

    # 飞书通知
    feishu_lines = [
        f"⏰ 时间: {NOW_STR}",
        f"📊 知识库总条目: {len(kb_items)} | 有标签: {len(tag_items)}",
        "",
        "🎯 本周精选回顾：",
    ]
    for i, item in enumerate(selected, 1):
        title = item.get("title", "")
        tags = item.get("tags", [])
        dims, total = score_one(title, tags)
        # 清洗标题
        clean = title
        for prefix in ["20250", "2024", "2023"]:
            if clean.startswith(prefix):
                parts = clean.split("-", 2)
                if len(parts) >= 3:
                    clean = parts[2]
                    break
        feishu_lines.append(f"{i}. {clean[:40]} ({tags[0]}) ⭐{total}")

    feishu_notify("📊 周回顾 · 本周精选", feishu_lines)


# ═══════════════════════════════════════════
# 月度分析
# ═══════════════════════════════════════════

def run_monthly_analysis():
    """月度分析：随机推送一个大类的知识框架"""
    import random
    print(f"\n{'='*60}")
    print(f"📈 月度分析 — {NOW_STR}")
    print(f"{'='*60}")

    kb_items = get_all_items(KB_ID)

    # 按标签分组（排除文件夹）
    tag_groups = {}
    for item in kb_items:
        if item.get("media_type") == 99:
            continue
        tags = item.get("tags", [])
        for tag in tags:
            if tag not in tag_groups:
                tag_groups[tag] = []
            tag_groups[tag].append(item)

    if not tag_groups:
        summary = f"✅ 月度分析完成 ({NOW_STR}): 知识库暂无有标签条目。"
        append_note(DAILY_LOG_NOTE_ID, f"\n## {TODAY} 月度分析\n\n{summary}\n")
        update_status("最后月度分析时间", NOW_STR)
        feishu_notify("📈 月度分析完成", [summary])
        return

    # 随机选一个大类
    random.seed(int(TODAY.replace("-", "")))
    selected_tag = random.choice(list(tag_groups.keys()))
    selected_items = tag_groups[selected_tag]

    # 按评分排序
    for item in selected_items:
        title = item.get("title", "")
        tags = item.get("tags", [])
        _, total = score_one(title, tags)
        item["_score"] = total
    selected_items.sort(key=lambda x: -x["_score"])

    print(f"随机选中大类: {selected_tag} ({len(selected_items)} 条)")

    # 构建知识框架
    lines = [f"\n## {TODAY} 月度分析\n"]
    lines.append(f"分析时间: {NOW_STR}")
    lines.append(f"知识库总条目: {len(kb_items)} | 标签类别: {len(tag_groups)}\n")

    lines.append(f"### 📚 本月聚焦: {selected_tag}（共 {len(selected_items)} 条）\n")

    # 统计该类均分
    scores = [item["_score"] for item in selected_items]
    avg = round(mean(scores), 2)
    lines.append(f"**类别均分: {avg}/10**\n")

    # 展示框架：按评分分层
    lines.append("#### 知识框架\n")
    lines.append("|#|标题|评分|标签|")
    lines.append("|---|---|---|---|")
    for i, item in enumerate(selected_items[:15], 1):  # 最多展示15条
        title = item.get("title", "")
        tags = " / ".join(item.get("tags", []))
        # 清洗标题
        clean = title
        for prefix in ["20250", "2024", "2023"]:
            if clean.startswith(prefix):
                parts = clean.split("-", 2)
                if len(parts) >= 3:
                    clean = parts[2]
                    break
        lines.append(f"|{i}|{clean[:50]}|{item['_score']}|{tags}|")

    if len(selected_items) > 15:
        lines.append(f"\n> 还有 {len(selected_items) - 15} 条未展示")

    # 核心主题提炼
    lines.append(f"\n#### 核心主题\n")
    titles_clean = []
    for item in selected_items[:10]:
        t = item.get("title", "")
        for prefix in ["20250", "2024", "2023"]:
            if t.startswith(prefix):
                parts = t.split("-", 2)
                if len(parts) >= 3:
                    t = parts[2]
                    break
        titles_clean.append(t)

    # 提取共同关键词
    all_words = " ".join(titles_clean)
    lines.append(f"本类知识覆盖 {len(selected_items)} 篇研报，TOP3 高分:")
    for item in selected_items[:3]:
        t = item.get("title", "")
        for prefix in ["20250", "2024", "2023"]:
            if t.startswith(prefix):
                parts = t.split("-", 2)
                if len(parts) >= 3:
                    t = parts[2]
                    break
        lines.append(f"- {t[:60]}")

    content = "\n".join(lines)
    append_note(DAILY_LOG_NOTE_ID, content)
    update_status("最后月度分析时间", NOW_STR)

    print(f"✅ 月度分析完成")

    # 飞书通知
    feishu_lines = [
        f"⏰ 时间: {NOW_STR}",
        f"📊 知识库总条目: {len(kb_items)} | 标签类别: {len(tag_groups)}",
        "",
        f"📚 本月聚焦: {selected_tag}",
        f"   共 {len(selected_items)} 条 | 均分 {avg}/10",
        "",
        "🏆 TOP3 高分研报：",
    ]
    for i, item in enumerate(selected_items[:3], 1):
        t = item.get("title", "")
        for prefix in ["20250", "2024", "2023"]:
            if t.startswith(prefix):
                parts = t.split("-", 2)
                if len(parts) >= 3:
                    t = parts[2]
                    break
        feishu_lines.append(f"  {i}. {t[:45]} ⭐{item['_score']}")

    feishu_notify("📈 月度分析 · 知识框架", feishu_lines)


# ═══════════════════════════════════════════
# 系统状态更新
# ═══════════════════════════════════════════

def update_status(field, value):
    """更新系统状态笔记中的字段"""
    # 读取当前状态
    content = get_note_content(SYSTEM_STATUS_NOTE_ID)

    # 如果笔记是新/空的，写入初始内容
    if not content.strip():
        content = "# 系统状态文件\n\n"
        append_note(SYSTEM_STATUS_NOTE_ID, content)

    # 追加事件日志
    event_line = f"\n{TODAY} - {field}: {value}"
    append_note(SYSTEM_STATUS_NOTE_ID, event_line)
    print(f"📝 状态更新: {field} = {value}")


# ═══════════════════════════════════════════
# 夜间入库（增量导入）
# ═══════════════════════════════════════════

def run_nightly_import():
    """夜间入库：检查知识库增量"""
    print(f"\n{'='*60}")
    print(f"🌙 夜间入库 — {NOW_STR}")
    print(f"{'='*60}")

    # 与每日盘点逻辑类似，但只做增量扫描和入库
    run_daily_inventory()


# ═══════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(description="知识库定时盘点系统")
    parser.add_argument("mode", choices=["daily", "weekly", "monthly", "nightly"],
                        help="运行模式")
    args = parser.parse_args()

    print(f"🚀 知识库定时盘点系统 v2.0 — GitHub Actions 版")
    print(f"模式: {args.mode}")

    modes = {
        "daily": run_daily_inventory,
        "weekly": run_weekly_review,
        "monthly": run_monthly_analysis,
        "nightly": run_nightly_import,
    }

    modes[args.mode]()

    print(f"\n✅ [{NOW_STR}] {args.mode} 任务执行完毕")


if __name__ == "__main__":
    main()
