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


def extract_summary(title, tags=None):
    """从标题和标签生成50-80字段落式概要"""
    if tags is None:
        tags = []
    
    tag_str = "、".join(tags) if tags else "金融"
    t = title
    
    # 尝试解析标题结构
    # 格式：XXX，基于YYY 或 XXX ——基于YYY
    main_part = t
    method_part = ""
    if "，" in t:
        parts = t.split("，", 1)
        main_part = parts[0]
        method_part = parts[1]
    elif "——" in t:
        parts = t.split("——", 1)
        main_part = parts[0]
        method_part = parts[1]
    elif "—" in t:
        parts = t.split("—", 1)
        main_part = parts[0]
        method_part = parts[1]
    
    # 构建概要
    if "基于" in t:
        # 标题含"基于"：本文围绕[方向]，基于[方法]进行系统性研究...
        if "，" in t and "基于" in t.split("，")[0]:
            prefix = t.split("基于", 1)[0]
        else:
            prefix = t.split("基于", 1)[0]
        core = t.split("基于", 1)[1]
        summary = f"本文围绕{prefix}方向，基于{core}方法进行系统性研究。从{tag_str}角度出发，为相关投资决策提供了定量分析支持与实证参考。"
    
    elif "如何" in t:
        summary = f"本文聚焦「{t}」这一核心问题，从{tag_str}维度进行了系统性探讨。通过构建量化分析框架，为实际投资场景提供了可落地的解决方案。"
    
    elif "研究" in t or "分析" in t:
        target = t.replace("研究", "").replace("分析", "")
        summary = f"本文对{target}领域进行了深入研究，综合运用{tag_str}方法论。通过系统性的实证检验，揭示了关键规律并提出了具操作性的投资策略建议。"
    
    elif "应用" in t or "实践" in t:
        summary = f"本文聚焦{t}方向，探讨了{tag_str}在实际金融场景中的应用方法与效果。通过案例与数据分析，验证了相关策略的有效性与局限性。"
    
    else:
        # 通用模板
        summary = f"本文属于{tag_str}方向的最新研究成果，系统探讨了{t}。通过多维度的定量分析与方法创新，为投资决策提供了富有价值的参考框架。"
    
    # 截断到50-80字
    if len(summary) < 50:
        summary += f"研究内容涵盖{tag_str}核心领域，具有较好的理论与实践参考价值。"
    if len(summary) > 80:
        # 找到第75个字左右的句号位置截断
        cut = 75
        while cut < len(summary) and cut < 82:
            if summary[cut] in "。！？":
                summary = summary[:cut+1]
                break
            cut += 1
        if len(summary) > 82:
            summary = summary[:78] + "。"
    
    return summary
