"""五维评分模块"""
from statistics import mean
from config.constants import TAG_BASE

BASE = 7.0


def score_one(title, tags):
    """
    对单篇研报按五维规则计算评分
    返回: (dims_dict, total_score)
    """
    dims = {"depth": BASE, "data": BASE, "logic": BASE, "practical": BASE, "innovation": BASE}
    
    # 标签加成：多标签取 max
    tag_bonus = max((TAG_BASE.get(t, BASE) - BASE) for t in tags) if tags else 0
    for k in dims:
        dims[k] += tag_bonus

    t = title
    # 标题关键词加成
    if ("深度研究" in t) or ("专题" in t):
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

    # 截断到 [1,10]
    for k in dims:
        dims[k] = round(max(1.0, min(10.0, dims[k])), 1)
    
    total = round(mean(dims.values()), 2)
    return dims, total


def render_score_card(num, title, broker, tags, keywords, dims, summary):
    """生成单篇研报的卡片化Markdown"""
    bars = {k: "█" * int(round(v, 0)) + "░" * (10 - int(round(v, 0))) for k, v in dims.items()}
    total = round(mean(dims.values()), 2)
    
    card = f"""### 📄 №{num} {title}

**券商**：{broker} | **分类**：{' / '.join(tags)}  
**关键词**：{keywords}

| 深度 | 数据 | 逻辑 | 实用 | 创新 | **总分** |
|:---:|:---:|:---:|:---:|:---:|:-------:|
| {dims['depth']} | {dims['data']} | {dims['logic']} | {dims['practical']} | {dims['innovation']} | **{total}** |
| {bars['depth']} | {bars['data']} | {bars['logic']} | {bars['practical']} | {bars['innovation']} | ⭐ |

> **概要**：{summary}

---
"""
    return card


def extract_keywords(title):
    """从标题提取关键词（简单规则）"""
    keywords = []
    kw_list = ["大模型", "LLM", "深度学习", "机器学习", "因子", "策略", "轮动", "选股", 
               "资产配置", "风险管理", "量化", "AI", "NLP", "回测", "框架", "体系",
               "学海拾珠", "事件驱动", "ETF", "组合构建", "Beta"]
    for kw in kw_list:
        if kw in title:
            keywords.append(kw)
    return keywords[:5]


def extract_summary(title):
    """从标题生成一句话概要"""
    if "系列" in title and "之" in title:
        parts = title.split("：")
        return parts[-1] if len(parts) > 1 else title
    return title
