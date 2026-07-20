#!/usr/bin/env python3
"""知识库定时盘点系统 v3.0 — LLM 增强版。支持 daily/weekly/monthly/nightly。"""

import json, os, sys, time, requests, random, re
from datetime import datetime
from statistics import mean

KB_ID = "28RoKuOA8h1pcBxomcac8BUYQF0lqvuxeNQ1X3dtbu0="
DOWNLOADS_FOLDER_ID = "folder_7482703326763920"
DAILY_LOG_NOTE_ID = "7483148258522158"
SYSTEM_STATUS_NOTE_ID = "7483148258537130"
BASE_URL = "https://ima.qq.com"
DEEPSEEK_URL = "https://api.deepseek.com/v1"
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK",
    "https://open.feishu.cn/open-apis/bot/v2/hook/ac6ae40e-9cfd-411d-bda4-44d2d16fbf30")
TODAY = datetime.now().strftime("%Y-%m-%d")
NOW = datetime.now().strftime("%Y-%m-%d %H:%M")
USE_LLM = os.environ.get("USE_LLM_ENHANCE", "").lower() in ("true", "1", "yes")
DS_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

TAG_KW = {
    "大模型投研": ["大模型","LLM","GPT","语言模型","transformer","AI研报","大语言"],
    "基本面量化": ["基本面","财务因子","价值因子","F-Score","质量因子"],
    "多因子选股": ["多因子","选股","因子模型","因子投资","Fama","IC"],
    "量价因子": ["量价","价量","动量","反转","换手率","波动率"],
    "深度学习选股": ["深度学习","神经网络","LSTM","GRU","CNN","RNN","transformer选股"],
    "行业轮动": ["行业轮动","行业配置","板块轮动","行业景气"],
    "风格轮动": ["风格轮动","风格因子","大小盘","价值成长"],
    "择时策略": ["择时","择机","时机选择","市场择时"],
    "ETF策略": ["ETF","指数基金","被动投资"],
    "资产配置": ["资产配置","股债平衡","组合管理","全天候","SAA","TAA"],
    "红利策略": ["红利","股息","高分红","分红策略"],
    "指数增强": ["指数增强","增强指数","Smart Beta"],
    "债券固收": ["债券","固收","利率债","信用债","久期","可转债"],
    "可转债": ["可转债","转债","convertible"],
    "FOF基金": ["FOF","基金配置","基金评价","基金经理"],
    "风险管理": ["风险","回撤","VaR","CVaR","下行风险","尾部风险"],
    "量化综合": ["量化","因子","alpha","对冲","高频","统计套利"],
    "数字货币与DeFi": ["数字货币","比特币","以太坊","区块链","DeFi","加密"],
    "AI编程工具": ["AI编程","Copilot","GPT编程","代码生成"],
    "知识库管理": ["知识库","知识管理","笔记","信息管理"],
}
TAG_BASE = {"FOF基金":7.5,"风险管理":7.5,"深度学习选股":7.5,"大模型投研":7.3,"基本面量化":7.2,"多因子选股":7.2,"量价因子":7.1,"资产配置":7.1,"行业轮动":7.0,"风格轮动":7.0,"择时策略":7.0,"ETF策略":7.0,"红利策略":6.9,"指数增强":6.9,"债券固收":6.9,"可转债":6.8,"量化综合":6.7,"数字货币与DeFi":6.6,"AI编程工具":6.5,"知识库管理":5.5}
BASE = 7.0

# ==================== LLM ====================
def llm_ok(): return USE_LLM and bool(DS_KEY)

def ds_chat(sys_prompt, user_prompt, temp=0.1, max_tk=2000):
    try:
        r = requests.post(f"{DEEPSEEK_URL}/chat/completions",
            headers={"Authorization":f"Bearer {DS_KEY}","Content-Type":"application/json"},
            json={"model":"deepseek-chat","messages":[{"role":"system","content":sys_prompt},{"role":"user","content":user_prompt}],"temperature":temp,"max_tokens":max_tk},
            timeout=30)
        return r.json()["choices"][0]["message"]["content"] if r.status_code==200 else None
    except Exception as e: print(f"  DS API: {e}"); return None

def llm_classify(title, content=""):
    tags = "\n".join(f"- {t}" for t in TAG_KW)
    txt = f"标题：{title}" + (f"\n内容：{content[:2000]}" if content else "")
    r = ds_chat("选1-3个最匹配标签，逗号分隔，只返回标签名", f"标签：\n{tags}\n\n{txt}", max_tk=200)
    if not r: return None
    m = [t for t in TAG_KW if t in r]
    return m or None

def llm_score(title, content=""):
    txt = f"标题：{title}" + (f"\n内容：{content[:3000]}" if content else "")
    r = ds_chat(
        '以JSON评分。格式：{"depth":N,"data":N,"logic":N,"practical":N,"innovation":N,"rationale":"理由"}。1-10分。',
        f"评估研报质量：\n{txt}", temp=0.2, max_tk=500)
    if not r: return None
    try:
        j = json.loads(r[r.find("{"):r.rfind("}")+1])
        d = {k:round(max(1,min(10,float(j.get(k,7)))),2) for k in ["depth","data","logic","practical","innovation"]}
        return d, round(mean(d.values()),2), j.get("rationale","")
    except: return None

def llm_summarize(title, content=""):
    txt = f"标题：{title}" + (f"\n内容：{content[:3000]}" if content else "")
    r = ds_chat("用50-100字概括研报核心观点", f"生成摘要：\n{txt}", temp=0.3, max_tk=300)
    return r.strip() if r else None

# ==================== 规则引擎 ====================
def classify(title):
    tl = title.lower()
    specific = {k:v for k,v in TAG_KW.items() if k!="量化综合"}
    for tag,kws in specific.items():
        if any(kw.lower() in tl for kw in kws): return [tag]
    for kw in TAG_KW.get("量化综合",[]):
        if kw.lower() in tl: return ["量化综合"]
    return ["量化综合"]

def score(title, tags):
    d = dict.fromkeys(["depth","data","logic","practical","innovation"], BASE)
    bonus = max((TAG_BASE.get(t,BASE)-BASE) for t in tags) if tags else 0
    for k in d: d[k] += bonus
    if "深度研究" in title or "专题" in title: d["depth"]+=0.4
    if "学海拾珠" in title: d["depth"]+=0.3; d["logic"]+=0.3
    if any(k in title for k in ["深度学习","机器学习","大模型","AI","GRU","神经网络","图谱"]):
        d["innovation"]+=0.6; d["depth"]+=0.2
    if any(k in title for k in ["模型","框架","系统","体系"]): d["logic"]+=0.3; d["depth"]+=0.2
    if any(k in title for k in ["因子","策略","配置","择时","选股","轮动"]): d["practical"]+=0.3
    if any(k in title for k in ["回测","实证","研究","应用"]): d["data"]+=0.3
    if any(k in title for k in ["系列","报告"]): d["data"]+=0.2
    for k in d: d[k] = round(max(1, min(10, d[k])), 2)
    return d, round(mean(d.values()),2)

# ==================== IMA API ====================
def cred():
    c,k = os.environ.get("IMA_OPENAPI_CLIENTID",""), os.environ.get("IMA_OPENAPI_APIKEY","")
    if not c or not k: print("缺少IMA凭证"); sys.exit(1)
    return c,k

def api(path, body):
    c,k = cred()
    r = requests.post(f"{BASE_URL}/{path}",
        headers={"ima-openapi-clientid":c,"ima-openapi-apikey":k,"Content-Type":"application/json"},
        json=body, timeout=30)
    try:
        data = r.json()
    except:
        print(f"API响应非JSON [{path}]: HTTP {r.status_code}, body={r.text[:200]}")
        return {"code": -1, "msg": "响应非JSON", "data": {}}
    if data.get("code")!=0: print(f"API错误 [{path}]: {data.get('msg','')}")
    return data

def list_items(kb_id, folder_id=""):
    """旧版API：cursor分页"""
    all_items, cursor = [], ""
    while True:
        b = {"knowledge_base_id": kb_id, "cursor": cursor, "limit": 50}
        if folder_id: b["folder_id"] = folder_id
        d = api("openapi/wiki/v1/get_knowledge_list", b).get("data", {})
        items = d.get("knowledge_list", [])
        all_items.extend(items)
        if d.get("is_end", True): break
        cursor = d.get("next_cursor", "")
        time.sleep(0.5)
    return all_items

def tag_add(kb_id, item_id, tag):
    """旧版API：item_id 而非 media_id"""
    api("openapi/wiki/v1/tag_add", {"knowledge_base_id":kb_id,"item_id":item_id,"tag_name":tag})

def append_note(nid, content):
    """旧版API：openapi/note/v1/append_doc + doc_id + content_format"""
    api("openapi/note/v1/append_doc", {"doc_id":nid,"content":content,"content_format":1})

def rename_item(kb_id, mid, name):
    api("openapi/wiki/v1/rename_knowledge", {"knowledge_base_id":kb_id,"media_id":mid,"name":name})

def fetch_content(kb_id, media_id):
    try:
        r = api("openapi/wiki/v1/search_knowledge", {"knowledge_base_id":kb_id,"query":"","cursor":"","limit":50})
        return r.get("data",{}).get("summary","") or ""
    except: pass
    return ""

def search_item(kb_id, keyword):
    """旧版搜索API"""
    return api("openapi/wiki/v1/search_knowledge", {"knowledge_base_id":kb_id,"query":keyword,"cursor":"","limit":50})

# ==================== 通知 ====================
def feishu(title, lines):
    try:
        r = requests.post(FEISHU_WEBHOOK, json={"msg_type":"interactive","card":{"header":{"title":{"tag":"plain_text","content":title},"template":"blue"},"elements":[{"tag":"div","text":{"tag":"plain_text","content":l}} for l in lines]}}, timeout=10)
        if r.status_code==200:
            print(f"飞书通知已发送: {title}")
        else:
            print(f"飞书通知失败: HTTP {r.status_code}")
    except Exception as e:
        print(f"飞书通知异常: {e}")

def update_status(f, v):
    append_note(SYSTEM_STATUS_NOTE_ID, f"\n{TODAY} - {f}: {v}")
    print(f"状态: {f} = {v}")

# ==================== 听脑AI ====================
def handle_tingnao(items):
    new = [i for i in items if any(k in i.get("title","").lower() for k in ["听脑ai","tingnao","脑听"]) and re.search(r"\d{4}[-/]\d", i.get("title",""))]
    if not new: return
    print(f"听脑AI: {len(new)}条待重命名")
    for i in new:
        mid, old = i.get("media_id",""), i.get("title","")
        sm = i.get("summary","") or fetch_content(KB_ID, mid)
        if not sm or len(sm.strip())<5: continue
        if llm_ok():
            new_t = ds_chat("提炼10-25字标题，只返回标题", f"摘要：\n{sm[:1000]}", max_tk=100)
            new_t = new_t.strip()[:50] if new_t and len(new_t.strip())>5 else sm.strip()[:20]
        else:
            new_t = sm.strip().replace("\n"," ")[:20]
        if new_t and new_t!=old:
            rename_item(KB_ID, mid, new_t); print(f"  {new_t[:40]}")

# ==================== 核心入库 ====================
def build_log(results, avg, llm_on):
    l = [f"\n## {TODAY} 每日盘点\n", f"时间: {NOW} | 模式: {'LLM' if llm_on else '规则'}", f"新增: {len(results)}条 | 均分: {avg}/10\n"]
    l.append("| # | 标题 | 标签 | 深度 | 数据 | 逻辑 | 实用 | 创新 | 总分 | 摘要 |")
    l.append("|---|------|------|------|------|------|------|------|------|------|")
    for i,r in enumerate(results,1):
        s=r["scores"]; sm=(r.get("summary","")[:30]+"...") if r.get("summary") else ""
        l.append(f"| {i} | {r['title'][:40]} | {'/'.join(r['tags'][:3])} | {s['depth']} | {s['data']} | {s['logic']} | {s['practical']} | {s['innovation']} | {r['total']} | {sm} |")
    return "\n".join(l)

def daily():
    print(f"\n{'='*60}\n每日盘点 — {NOW} [{'LLM' if llm_ok() else '规则'}]\n{'='*60}")
    items = list_items(KB_ID)
    handle_tingnao(items)
    items = list_items(KB_ID)
    
    # 获取 Downloads 文件夹条目（研报入库来源）
    dl_items = list_items(KB_ID, DOWNLOADS_FOLDER_ID)
    print(f"根目录: {len(items)} | Downloads: {len(dl_items)}")
    
    # 合并根目录 + Downloads 文件夹条目，去重
    all_items = items + dl_items
    titles = {}
    dup = 0
    for i in all_items:
        mid = i.get("media_id","")
        if mid:
            if mid in titles: dup += 1
            titles[mid] = {"title":i.get("title",""),"tags":i.get("tags",[]),"mt":i.get("media_type",0)}
    print(f"去重后总条目: {len(titles)} (去除{dup}条重复)")
    untagged = [{"media_id":m,"title":v["title"]} for m,v in titles.items() if v["mt"]!=99 and not v["tags"]]
    print(f"未处理: {len(untagged)}")
    if not untagged:
        print("无新增")
        update_status("最后盘点时间",NOW)
        feishu("📋 每日盘点", [f"⏰ {NOW}", f"🤖 {'LLM' if llm_ok() else '规则'}模式", f"📊 总: {len(titles)}", "✅ 无新增未处理条目"])
        return

    results, tc = [], 0
    llm_on = llm_ok()
    for idx,item in enumerate(untagged):
        print(f"\n  [{idx+1}/{len(untagged)}] {item['title'][:60]}")
        content = fetch_content(KB_ID, item["media_id"]) if llm_on else ""
        if content: print(f"    content ({len(content)}c)")

        if llm_on:
            lt = llm_classify(item["title"], content)
            tags = lt if lt else classify(item["title"])
            print(f"    tags: {'LLM' if lt else '规则降级'} {tags}")
        else:
            tags = classify(item["title"])
            print(f"    tags: 规则 {tags}")

        if llm_on:
            ls = llm_score(item["title"], content)
            if ls: dims,total,_ = ls; print(f"    score: LLM {total}")
            else: dims,total = score(item["title"], tags); print(f"    score: 规则降级 {total}")
        else:
            dims,total = score(item["title"], tags)
            print(f"    score: 规则 {total}")

        sm = llm_summarize(item["title"], content) if llm_on else ""
        if sm: print(f"    summary: {sm[:60]}...")
        results.append({"title":item["title"],"media_id":item["media_id"],"tags":tags,"scores":dims,"total":total,"summary":sm})
        time.sleep(0.2)

    print("\n打标签...")
    for r in results:
        for t in r["tags"]:
            tag_add(KB_ID, r["media_id"], t); tc+=1; time.sleep(0.3)
    print(f"标签: {tc}")

    results.sort(key=lambda x:-x["total"])
    avg = round(mean(r["total"] for r in results),2)
    append_note(DAILY_LOG_NOTE_ID, build_log(results, avg, llm_on))
    update_status("最后盘点时间",NOW); update_status("知识库总条目",str(len(titles)))
    os.makedirs("outputs",exist_ok=True)
    with open(f"outputs/evaluation_{TODAY}.json","w",encoding="utf-8") as f:
        json.dump({"date":TODAY,"mode":"llm" if llm_on else "rule","count":len(results),"avg":avg,"items":results}, f, ensure_ascii=False, indent=2)
    fl = [f"⏰ {NOW}", f"{'LLM' if llm_on else '规则'}模式", f"总: {len(titles)}", f"新增: {len(results)}", f"均分: {avg}"]
    if results: fl.append(f"TOP1: {results[0]['title'][:40]} ⭐{results[0]['total']}" + (f"\n📝{results[0].get('summary','')[:60]}" if results[0].get('summary') else ""))
    feishu("每日盘点完成", fl)

def run_nightly(): print(f"夜间入库 — {NOW}"); daily()
def run_weekly():
    print(f"\n{'='*60}\n周回顾 — {NOW} [{'LLM' if llm_ok() else '规则'}]\n{'='*60}")
    kb=list_items(KB_ID); tg=[i for i in kb if i.get("media_type")!=99 and i.get("tags")]
    print(f"总: {len(kb)} | 有标签: {len(tg)}")
    if not tg: return
    sel = random.sample(tg, min(3,len(tg)))
    l=[f"\n## {TODAY} 周回顾\n时间: {NOW} | 模式: {'LLM' if llm_ok() else '规则'}\n总: {len(kb)} | 有标签: {len(tg)}\n"]
    llm_on = llm_ok()
    for i,s in enumerate(sel,1):
        title = s.get("title",""); tags = s.get("tags",[])
        if llm_on:
            content = fetch_content(KB_ID, s.get("media_id",""))
            ls = llm_score(title, content)
            if ls: dims, total, rationale = ls
            else: dims, total = score(title, tags)
        else:
            dims, total = score(title, tags)
        sm = llm_summarize(title, fetch_content(KB_ID, s.get("media_id",""))) if llm_on else ""
        l.append(f"**{i}. {title[:50]}**\n   标签: {'/'.join(tags)} | 评分: {total}/10 (深度{dims['depth']} 数据{dims['data']} 逻辑{dims['logic']} 实用{dims['practical']} 创新{dims['innovation']})" + (f"\n   📝 {sm[:60]}" if sm else "") + "\n")
    append_note(DAILY_LOG_NOTE_ID, "\n".join(l))
    update_status("最后周回顾时间",NOW)
    fl = [f"⏰ {NOW}", f"{'LLM' if llm_on else '规则'}模式", f"📊 总: {len(kb)} | 有标签: {len(tg)}"]
    for i,s in enumerate(sel,1):
        title = s.get("title","")[:40]
        tags = s.get("tags",[])
        _, sc = llm_score(title, "") if llm_on else (None, 0)
        if not _: _, sc = score(title, tags)
        fl.append(f"{i}. {title} ⭐{sc}")
    feishu("📊 周回顾", fl)

def run_monthly():
    print(f"\n{'='*60}\n月度分析 — {NOW} [{'LLM' if llm_ok() else '规则'}]\n{'='*60}")
    kb=list_items(KB_ID)
    # 合并 Downloads
    dl = list_items(KB_ID, DOWNLOADS_FOLDER_ID)
    all_i = {}
    for i in kb + dl:
        mid = i.get("media_id","")
        if mid: all_i[mid] = i
    all_i = list(all_i.values())
    
    # 按标签分组
    grp = {}
    for i in all_i:
        if i.get("media_type")==99: continue
        for t in i.get("tags",[]):
            if t not in grp: grp[t]=[]
            d=dict(i)
            if llm_ok():
                content = fetch_content(KB_ID, i.get("media_id",""))
                ls = llm_score(i.get("title",""), content)
                sc = ls[1] if ls else score(i.get("title",""),[t])[1]
            else:
                sc = score(i.get("title",""),[t])[1]
            d["_s"]=sc; grp[t].append(d)
    if not grp: return
    
    # 标签分布 TOP5
    tag_counts = sorted([(t,len(v)) for t,v in grp.items()], key=lambda x:-x[1])[:5]
    # 均分 TOP5
    tag_avgs = sorted([(t,round(mean(i["_s"] for i in v),2)) for t,v in grp.items()], key=lambda x:-x[1])[:5]
    
    # 随机标签（保留）
    tag=random.choice(list(grp))
    its=sorted(grp[tag], key=lambda x:-x["_s"])
    av=round(mean(i["_s"] for i in its),2)
    print(f"选中: {tag} ({len(its)}条, 均分{av})")
    
    l=[f"\n## {TODAY} 月度分析\n时间: {NOW} | 模式: {'LLM' if llm_ok() else '规则'}\n总条目: {len(all_i)} | 标签类别: {len(grp)}\n"]
    
    l.append("\n### 📊 标签分布 TOP5\n")
    for t,c in tag_counts: l.append(f"- {t}: {c}条")
    
    l.append("\n### ⭐ 均分 TOP5 标签\n")
    for t,sc in tag_avgs: l.append(f"- {t}: {sc}/10")
    
    l.append(f"\n### 🎲 随机选中: {tag}（共{len(its)}条, 均分{av}）\n")
    for i in its[:5]: l.append(f"- {i['title'][:60]} ⭐{i['_s']}")
    
    append_note(DAILY_LOG_NOTE_ID, "\n".join(l))
    update_status("最后月度分析时间",NOW)
    
    fl = [f"⏰ {NOW}", f"{'LLM' if llm_ok() else '规则'}模式", f"📊 总: {len(all_i)} | 标签: {len(grp)}类", ""]
    fl.append("📊 标签分布TOP5:")
    for t,c in tag_counts: fl.append(f"  {t}: {c}条")
    fl.append("")
    fl.append("⭐ 均分TOP5:")
    for t,sc in tag_avgs: fl.append(f"  {t}: {sc}")
    fl.append("")
    fl.append(f"🎲 随机聚焦: {tag} ({av})")
    for i in its[:2]: fl.append(f"  {i['title'][:40]} ⭐{i['_s']}")
    feishu("📈 月度分析", fl)

if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "daily"
    print(f"v3.0 {'🤖LLM' if llm_ok() else '⚙️规则'}: {mode}")
    {"daily":daily,"weekly":run_weekly,"monthly":run_monthly,"nightly":run_nightly}[mode]()
    print(f"✅ [{NOW}] 完成")
