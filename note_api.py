"""IMA笔记API封装"""
import os
import json
import subprocess
import uuid

API_BASE = "https://ima.qq.com/openapi/note/v1"
HEADERS = {
    "ima-openapi-clientid": os.environ.get("IMA_OPENAPI_CLIENTID", ""),
    "ima-openapi-apikey": os.environ.get("IMA_OPENAPI_APIKEY", ""),
    "Content-Type": "application/json",
}


def _curl(endpoint, data):
    """通用curl请求"""
    cmd = [
        "curl", "-s", "-X", "POST", f"{API_BASE}/{endpoint}",
    ]
    for k, v in HEADERS.items():
        cmd.extend(["-H", f"{k}: {v}"])
    cmd.extend(["-d", json.dumps(data)])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)


def search_note_by_title(title_keyword):
    """按标题搜索笔记"""
    data = {
        "search_type": 0,
        "query_info": {"title": title_keyword},
        "start": 0,
        "end": 20,
    }
    result = _curl("search_note", data)
    if result.get("code") == 0:
        return result.get("data", {}).get("search_note_infos", [])
    return []


def append_doc(note_id, content):
    """短内容追加"""
    data = {
        "note_id": note_id,
        "content_format": 1,
        "content": content,
    }
    return _curl("append_doc", data)


def push_note(note_id=None, content=None, content_cos_key=None):
    """智能推送（新建或追加）"""
    data = {"note_id": note_id}
    if content:
        data["content"] = content
    if content_cos_key:
        data["content_cos_key"] = content_cos_key
    return _curl("push_note", data)


def rename_note(note_id, title):
    """重命名笔记"""
    data = {"note_id": note_id, "title": title}
    return _curl("rename_note", data)


def export_note(note_id, format=1):
    """导出笔记内容，返回下载链接"""
    data = {"note_id": note_id, "target_content_format": format}
    result = _curl("export_note", data)
    if result.get("code") == 0:
        return result.get("data", {}).get("content_url")
    return None


def list_notes(folder_id="", limit=20):
    """列出笔记"""
    data = {"folder_id": folder_id, "cursor": "", "limit": limit}
    result = _curl("list_note", data)
    if result.get("code") == 0:
        return result.get("data", {}).get("note_book_list", [])
    return []


def create_blank_weekly_note(week_range, folder_id):
    """创建空白周卡片笔记"""
    content = f"""# 📊 周盘点归档（卡片版）| {week_range}

> 每周知识点（五维评分明细）全量归集 · 卡片化展示

**统计概览**：共 0 条 | 待更新
"""
    data = {
        "content_format": 1,
        "content": content,
        "folder_id": folder_id,
    }
    result = _curl("import_doc", data)
    if result.get("code") == 0:
        return result.get("data", {}).get("note_id")
    return None


def upload_to_cos(filepath):
    """上传文件到COS，返回cosKey"""
    result = subprocess.run(
        ["ima_cos_util", "-f", filepath],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()
