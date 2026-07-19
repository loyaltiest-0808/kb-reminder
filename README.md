# 知识库定时盘点系统

基于 GitHub Actions + IMA OpenAPI 的自动化知识库管理工具。

## 4 个定时任务

| 任务 | 调度时间 | 说明 |
|------|---------|------|
| 每日盘点 | 每天 21:00 | 扫描新增条目 → 分类打标签 → 五维评分 → 写入日志 |
| 周回顾 | 每周五 20:00 | 本周知识库概况与标签分布统计 |
| 月度分析 | 月末周六 20:00 | 全量条目评分汇总与趋势分析 |
| 夜间入库 | 每天 00:10 | 增量导入与预处理 |

## 部署步骤

### 第一步：获取 IMA API 凭证

1. 打开 https://ima.qq.com/agent-interface
2. 登录你的 ima 账号
3. 获取 **Client ID** 和 **API Key**

### 第二步：创建 GitHub 仓库

1. 在 GitHub 上创建一个新仓库（私有/公开均可）
2. 把本目录所有文件推送到仓库

```bash
cd kb-reminder
git init
git add .
git commit -m "初始化知识库定时盘点系统"
git remote add origin 你的仓库地址
git push -u origin main
```

### 第三步：配置 GitHub Secrets

在仓库设置 → Secrets and variables → Actions 中添加：

| Secret 名称 | 值 |
|------------|-----|
| `IMA_OPENAPI_CLIENTID` | 你的 Client ID |
| `IMA_OPENAPI_APIKEY` | 你的 API Key |

### 第四步：激活工作流

推送代码后，GitHub Actions 会自动识别 `.github/workflows/` 下的 4 个 workflow 文件。你可以在 Actions 标签页中手动触发测试。

## 关键 ID（请勿修改）

- 知识库 kb_id: `28RoKuOA8h1pcBxomcac8BUYQF0lqvuxeNQ1X3dtbu0=`
- 每日盘点日志笔记: `7483148258522158`
- 系统状态笔记: `7483148258537130`
- Downloads 文件夹: `folder_7482703326763920`

## 本地测试

```bash
export IMA_OPENAPI_CLIENTID="你的client_id"
export IMA_OPENAPI_APIKEY="你的api_key"
pip install -r requirements.txt
python kb_reminder.py daily    # 测试每日盘点
python kb_reminder.py weekly   # 测试周回顾
python kb_reminder.py monthly  # 测试月度分析
python kb_reminder.py nightly  # 测试夜间入库
```
