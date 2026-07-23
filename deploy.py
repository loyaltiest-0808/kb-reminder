#!/usr/bin/env python3
"""一键部署 - 在kb-reminder仓库根目录运行 python deploy.py"""
import os, shutil
from datetime import datetime

B = os.getcwd()
bd = os.path.join(B, f"_backup_{datetime.now():%Y%m%d}")
os.makedirs(bd, exist_ok=True)
for f in ["daily_inventory.py","weekly_wrapup.py","monthly_wrapup.py","scoring.py","note_api.py"]:
    if os.path.exists(os.path.join(B,f)): shutil.copy2(os.path.join(B,f), os.path.join(bd,f))
for d in ["config",".github"]:
    s=os.path.join(B,d)
    if os.path.isdir(s): shutil.copytree(s, os.path.join(bd,d), dirs_exist_ok=True)
old=os.path.join(B,".github","workflows","nightly-import.yml")
if os.path.exists(old): os.remove(old); print("deleted nightly-import.yml")
for d in ["config","state","outputs",".github/workflows"]: os.makedirs(os.path.join(B,d), exist_ok=True)

F = {}

F["requirements.txt"] = "requests\n"
F["config/__init__.py"] = ""

F["config/constants.py"] = r'''# ID常量
KB_ID = "28RoKuOA8h1pcBxomcac8BUYQF0lqvuxeNQ1X3dtbu0="
FOLDER_AUTO = "folder59c27fce58bc1de2"
NOTE_DAILY_LOG = "7483148258522158"
NOTE_SYSTEM_STATUS = "7483148258537130"
FOLDER_WEEKLY_ARCHIVE = "folder4b8b0b46f60f7f3a"
FOLDER_MONTHLY_ARCHIVE = "folder735278f31abee357"

TAG_BASE = {
    "FOF基金": 7.5, "风险管理": 7.5, "深度学习选股": 7.5,
    "大模型投研": 7.3, "基本面量化": 7.2, "多因子选股": 7.2,
    "量价因子": 7.1, "资产配置": 7.1, "行业轮动": 7.0,
    "风格轮动": 7.0, "择时策略": 7.0, "ETF策略": 7.0,
    "红利策略": 6.9, "指数增强": 6.9, "债券固收": 6.9,
    "可转债": 6.8, "量化综合": 6.7, "数字货币与DeFi": 6.6,
    "AI编程工具": 6.5, "知识库管理": 5.5,
}

BROKER_MAP = {
    "国金": "国金证券", "华泰": "华泰证券", "华安": "华安证券",
    "招商": "招商证券", "中信建投": "中信建投", "国盛": "国盛证券",
    "广发": "广发证券", "长江": "长江证券", "东北": "东北证券",
    "兴业": "兴业证券", "财通": "财通证券", "东吴": "东吴证券",
    "天风": "天风证券", "申万": "申万宏源", "海通": "海通证券",
    "中信": "中信证券", "国君": "国泰君安", "安信": "安信证券",
    "银河": "银河证券", "中金": "中金公司",
}
'''

F["scoring.py"] = r'''"""五维评分模块 — 规则引擎 + LLM评分（降级链）"""
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
'''

F["note_api.py"] = r'''"""IMA笔记API封装"""
import os, json, subprocess

API = "https://ima.qq.com/openapi/note/v1"
H = {
    "ima-openapi-clientid": os.environ.get("IMA_OPENAPI_CLIENTID", ""),
    "ima-openapi-apikey": os.environ.get("IMA_OPENAPI_APIKEY", ""),
    "Content-Type": "application/json",
}

def _c(ep, d):
    cmd = ["curl", "-s", "-X", "POST", f"{API}/{ep}"]
    for k, v in H.items(): cmd.extend(["-H", f"{k}: {v}"])
    cmd.extend(["-d", json.dumps(d)])
    return json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)

def search_note_by_title(kw):
    r = _c("search_note", {"search_type": 0, "query_info": {"title": kw}, "start": 0, "end": 20})
    return r.get("data", {}).get("search_note_infos", []) if r.get("code") == 0 else []

def append_doc(nid, c):
    return _c("append_doc", {"note_id": nid, "content_format": 1, "content": c})

def push_note(note_id=None, content=None, content_cos_key=None):
    d = {"note_id": note_id}
    if content: d["content"] = content
    if content_cos_key: d["content_cos_key"] = content_cos_key
    return _c("push_note", d)

def rename_note(nid, t):
    return _c("rename_note", {"note_id": nid, "title": t})

def export_note(nid, format=1):
    r = _c("export_note", {"note_id": nid, "target_content_format": format})
    return r.get("data", {}).get("content_url") if r.get("code") == 0 else None

def list_notes(folder_id="", limit=20):
    r = _c("list_note", {"folder_id": folder_id, "cursor": "", "limit": limit})
    return r.get("data", {}).get("note_book_list", []) if r.get("code") == 0 else []

def create_blank_weekly_note(wr, fid):
    content = f"# 📊 周盘点归档（卡片版）| {wr}\n\n> 全量归集·卡片化展示\n\n**统计**：共 0 条 | 待更新\n"
    r = _c("import_doc", {"content_format": 1, "content": content, "folder_id": fid})
    return r.get("data", {}).get("note_id") if r.get("code") == 0 else None
'''

F["daily_inventory.py"] = r'''#!/usr/bin/env python3
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
'''

F["weekly_wrapup.py"] = r'''#!/usr/bin/env python3
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
'''

F["monthly_wrapup.py"] = r'''#!/usr/bin/env python3
"""月汇总"""
import os, json, glob
from datetime import datetime
from statistics import mean, median
from collections import Counter
from note_api import append_doc, list_notes
from config.constants import FOLDER_MONTHLY_ARCHIVE

BD = os.path.dirname(os.path.abspath(__file__))
OD = os.path.join(BD, "outputs")

def main():
    m = f"{datetime.now():%Y年%m月}"
    print(f"{m}汇总...")
    items = []
    tm = f"{datetime.now():%Y-%m}"
    for f in sorted(glob.glob(os.path.join(OD, "evaluation_*.json"))):
        if tm in f: items.extend(json.load(open(f))["items"])
    if not items: print("无数据"); return
    sc = [x["total"] for x in items]
    at = [t for it in items for t in it["tags"]]
    tc = Counter(at).most_common(5)
    ts = "、".join(f"{t}({c})" for t,c in tc)
    top = sorted(items, key=lambda x: -x["total"])[:10]
    rows = "\n".join(f"| {i} | {it['title'][:30]}... | {'/'.join(it['tags'])} | {it['total']} |" for i,it in enumerate(top,1))
    avg = round(mean(sc), 2)
    a = f"\n# 📈 {m}分析\n\n| 项 | 值 |\n|:---|---:|\n| 总数 | {len(items)} |\n| 均分 | {avg} |\n| 中位 | {round(median(sc),1)} |\n| 最高 | {max(sc)} |\n| 热门 | {ts} |\n\n## TOP10\n\n| # | 标题 | 标签 | 分 |\n|:---:|:---|:---|:---:|\n{rows}\n"
    for n in list_notes(folder_id=FOLDER_MONTHLY_ARCHIVE):
        if m in n["title"]:
            append_doc(n["note_id"], a)
            print(f"{m}完成！")
            return
    print("月度笔记不存在")

if __name__ == "__main__": main()
'''

F[".github/workflows/daily-inventory.yml"] = """name: 每日盘点
on:
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:
jobs:
  daily-inventory:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - name: 执行
        env:
          IMA_OPENAPI_CLIENTID: ${{ secrets.IMA_OPENAPI_CLIENTID }}
          IMA_OPENAPI_APIKEY: *** secrets.IMA_OPENAPI_APIKEY }}
          DEEPSEEK_API_KEY: *** secrets.DEEPSEEK_API_KEY }}
          USE_LLM_ENHANCE: ${{ vars.USE_LLM_ENHANCE }}
        run: python3 daily_inventory.py
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: eval-${{ github.run_id }}
          path: outputs/
"""

F[".github/workflows/weekly-review.yml"] = """name: 周收尾封存
on:
  schedule:
    - cron: '0 15 * * 0'
  workflow_dispatch:
jobs:
  weekly-wrapup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install -r requirements.txt
      - name: 执行
        env:
          IMA_OPENAPI_CLIENTID: ${{ secrets.IMA_OPENAPI_CLIENTID }}
          IMA_OPENAPI_APIKEY: *** secrets.IMA_OPENAPI_APIKEY }}
          DEEPSEEK_API_KEY: *** secrets.DEEPSEEK_API_KEY }}
          USE_LLM_ENHANCE: ${{ vars.USE_LLM_ENHANCE }}
        run: python3 weekly_wrapup.py
"""

F[".github/workflows/monthly-analysis.yml"] = """name: 月度汇总分析
on:
  schedule:
    - cron: '0 15 28-31 * *'
  workflow_dispatch:
jobs:
  monthly-wrapup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install -r requirements.txt
      - name: 执行
        env:
          IMA_OPENAPI_CLIENTID: ${{ secrets.IMA_OPENAPI_CLIENTID }}
          IMA_OPENAPI_APIKEY: *** secrets.IMA_OPENAPI_APIKEY }}
          DEEPSEEK_API_KEY: *** secrets.DEEPSEEK_API_KEY }}
          USE_LLM_ENHANCE: ${{ vars.USE_LLM_ENHANCE }}
        run: python3 monthly_wrapup.py
"""

# ============ 写入文件 ============
for rp, ct in F.items():
    fp = os.path.join(B, rp)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, "w", encoding="utf-8").write(ct)
    print(f"  ✅ {rp}")

for d in ["state", "outputs"]:
    gk = os.path.join(B, d, ".gitkeep")
    if not os.path.exists(gk): open(gk, "w").write("")

print(f"\n🎉 部署完成！共写入 {len(F)} 个文件")
print(f"💾 备份在: {bd}")
print(f"\n下一步：")
print(f"  git add -A")
print(f"  git commit -m 'v2.0: 三级归档 + LLM评分 + 路径修复'")
print(f"  git push origin main")