"""五维评分模块 — 规则引擎 + LLM评分（降级链）"""
import os, json, requests
from statistics import mean
from config.constants import TAG_BASE

BASE = 7.0
DEEPSEEK_API_KEY = ***"DEEPSEEK_API_KEY", "")
USE_LLM = os.environ.get("USE_LLM_ENHANCE", "false").lower() == "true"
LLM_URL = "https://api.deepseek.com/v1/chat/completions"
PROMPT = """你是金融研报评分专家。对研报按五维打分(1-10)并给理由。
标题：{title}  分类：{tags}
维度：depth(深度) data(数据) logic(逻辑) practical(实用) innovation(创新)
返回JSON：{{"depth":7.5,"data":7.0,"logic":8.0,"practical":7.5,"innovation":6.5,"reason":"理由"}}"""

def score_one_llm(t, ts):
    if not USE_LLM or not DEEPSEEK_API_KEY:
        *** None
    try:
        r = requests.post(LLM_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": PROMPT.format(title=t, tags="、".join(ts) if ts else "未分类")}], "temperature": 0.3, "max_tokens": 300},
            timeout=30)
        r.raise_for_status()
        c = r.json()["choices"][0]["message"]["content"].strip()
        if "```" in c: c = c.split("```")[1]
        if c.startswith("json"): c = c[4:]
        d = json.loads(c.strip())
        dims = {k: round(max(1.0, min(10.0, float(d[k]))), 1) for k in ["depth","data","logic","practical","innovation"]}
        return dims, round(mean(dims.values()), 2), d.get("reason", "")
    except Exception as e:
        print(f"LLM失败，降级规则引擎: {e}")
        *** None

def score_one_rule(t, ts):
    dims = {"depth": BASE, "data": BASE, "logic": BASE, "practical": BASE, "innovation": BASE}
    tb = max((TAG_BASE.get(x, BASE) - BASE) for x in ts) if ts else 0
    for k in dims: dims[k] += tb
    if "深度研究" in t or "专题" in t: dims["depth"] += 0.4
    if "学海拾珠" in t: dims["depth"] += 0.3; dims["logic"] += 0.3
    if any(w in t for w in ["深度学习","机器学习","大模型","AI","GRU","神经网络","图谱"]): dims["innovation"] += 0.6; dims["depth"] += 0.2
    if any(w in t for w in ["模型","框架","系统","体系"]): dims["logic"] += 0.3; dims["depth"] += 0.2
    if any(w in t for w in ["因子","策略","配置","择时","选股","轮动"]): dims["practical"] += 0.3
    if any(w in t for w in ["回测","实证","研究","应用"]): dims["data"] += 0.3
    if any(w in t for w in ["系列","报告"]): dims["data"] += 0.2
    for k in dims: dims[k] = round(max(1.0, min(10.0, dims[k])), 1)
    return dims, round(mean(dims.values()), 2), ""

def score_one(t, ts):
    r = score_one_llm(t, ts)
    return r if r is not None else score_one_rule(t, ts)

def render_score_card(num, title, broker, tags, keywords, dims, summary, reason=""):
    bars = {k: "█" * int(round(v, 0)) + "░" * (10 - int(round(v, 0))) for k, v in dims.items()}
    total = round(mean(dims.values()), 2)
    rl = f"\n> **评语**：{reason}" if reason else ""
    return f"""### 📄 №{num} {title}

**券商**：{broker}　|　**分类**：{' / '.join(tags)}
**关键词**：{keywords}

| 深度 | 数据 | 逻辑 | 实用 | 创新 | **总分** |
|:---:|:---:|:---:|:---:|:---:|:-------:|
| {dims['depth']} | {dims['data']} | {dims['logic']} | {dims['practical']} | {dims['innovation']} | **{total}** |
| {bars['depth']} | {bars['data']} | {bars['logic']} | {bars['practical']} | {bars['innovation']} | ⭐ |

> **概要**：{summary}{rl}

---
"""

def extract_keywords(title):
    kw = ["大模型","LLM","深度学习","机器学习","因子","策略","轮动","选股","资产配置","风险管理","量化","AI","NLP","回测","框架","体系","学海拾珠","事件驱动","ETF","组合构建","Beta"]
    return [w for w in kw if w in title][:5]

def extract_summary(title):
    if "系列" in title and "之" in title:
        p = title.split("：")
        return p[-1] if len(p) > 1 else title
    return title
