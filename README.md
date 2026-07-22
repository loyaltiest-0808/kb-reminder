# 📚 知识库三级归档系统（新架构）

## 架构概览

```
┌─────────────┐     实时追加      ┌──────────────┐
│  每日入库   │ ───────────────▶  │  周卡片笔记   │  ← 日常实时追加
└─────────────┘                    └──────────────┘
                                              ↓
                                    周收尾（周日晚）
                                              ↓
                                    ┌──────────────┐
                                    │  已封存周归档  │
                                    └──────────────┘
                                              ↓
                                    月汇总（月底）
                                              ↓
                                    ┌──────────────┐
                                    │  月度分析笔记  │
                                    └──────────────┘
```

## 核心改变

**旧架构**：每日盘点 → 本地文件 → 周汇总转换 → 推送笔记  
**新架构**：每日盘点 → **直接追加到周卡片笔记** → 周收尾补统计 → 月汇总

优势：
1. ✅ 数据流转更简单，无中间冗余文件
2. ✅ 周归档实时可见，无需等待周底转换
3. ✅ 定时任务只做"收尾统计"，不做"内容转换"
4. ✅ 代码量减少 60%，维护成本低

## 文件说明

| 文件 | 职责 | 执行时机 |
|:-----|:-----|:---------|
| `daily_inventory.py` | 新研报入库 → 五维评分 → 追加周卡片 → 更新每日日志 | 每日 20:50 |
| `weekly_wrapup.py` | 补周汇总统计 → 标注封存 → 创建下周空白笔记 | 每周日 23:00 |
| `monthly_wrapup.py` | 汇总本月所有周卡片 → 生成月度分析 | 每月最后一天 23:00 |
| `scoring.py` | 五维评分算法、卡片渲染 | 库模块 |
| `note_api.py` | IMA笔记API封装 | 库模块 |
| `config/constants.py` | ID常量、标签基准分 | 配置 |
| `state/current_week_note_id` | 当前周笔记ID缓存 | 状态文件 |

## 定时任务配置

```bash
# crontab
50 20 * * * cd /sandbox/workspace/kb-reminder && python3 daily_inventory.py
0 23 * * 0 cd /sandbox/workspace/kb-reminder && python3 weekly_wrapup.py
0 23 28-31 * * [ "$(date +\%d -d tomorrow)" = "01" ] && cd /sandbox/workspace/kb-reminder && python3 monthly_wrapup.py
```

## 使用方法

```bash
# 1. 每日入库（在研报识别脚本中调用）
python3 -c "
from daily_inventory import process_batch
items = [('标题', ['标签1', '标签2'], '文件名.pdf')]
process_batch(items, '2026-07-22')
"

# 2. 手动触发周收尾
python3 weekly_wrapup.py

# 3. 手动触发月汇总
python3 monthly_wrapup.py
```

## 沙箱重置后恢复

```bash
# 1. 恢复评分逻辑（来自笔记 7483572432682694）
# 2. 恢复配置文件中的ID常量
# 3. 删除 state/current_week_note_id（会自动重新发现）
# 4. 测试 API 连接正常
```
