"""IMA笔记API封装"""
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
