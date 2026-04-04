# Notion 任务同步使用说明

本说明文档介绍如何将本地任务数据同步到 Notion 数据库“任务与待办”。

- 数据库页面：<https://www.notion.so/9d64948401c24eb29c6d0501d673660d>
- 数据库 ID（UUID，带短横线）：`9d649484-01c2-4eb2-9c6d-0501d673660d`
- 属性结构：
  - 标题：`任务名称`
  - 复选框：`完成`
  - 日期：`截止日期`

## 环境准备

1. 创建 Notion 集成并将该数据库共享给该集成（可读写）。
2. 获取集成密钥，设置为环境变量：
   - `NOTION_API_TOKEN`：你的 Notion 内部集成密钥。
   - `NOTION_DATABASE_ID`（可选）：数据库 ID，或在命令行通过 `--database-id` 传参。
3. 安装 Python 依赖（需要 `requests`）：

```bash
pip install requests
```

## 快速开始

1. 查看示例数据文件：`tasks_sample.csv`
2. 试运行（不发请求，仅打印将要执行的操作）：

```bash
python notion_sync_tasks.py --file tasks_sample.csv --dry-run
```

3. 实际同步（需要设置好环境变量，或使用 `--database-id` 指定 ID）：

```bash
export NOTION_API_TOKEN="<你的集成密钥>"
python notion_sync_tasks.py --file tasks_sample.csv --database-id 9d649484-01c2-4eb2-9c6d-0501d673660d
```

## 输入格式

脚本支持 CSV 和 JSON：

- CSV（建议）：需要包含列：`任务名称, 截止日期, 完成`，示例见 `tasks_sample.csv`。
- JSON：数组或包含 `tasks`/`items` 数组字段的对象。字段可使用别名：
  - 名称：`任务名称`/`name`/`title`/`任务名`
  - 截止日期：`截止日期`/`due`/`deadline`
  - 完成：`完成`/`done`（true/false/1/0/yes/no 都可识别）

## 行为说明

- Upsert：以 `任务名称` 为键查重；存在则更新，不存在则创建。
- 日期格式：YYYY-MM-DD 或标准 ISO8601 均可。
- 错误处理：遇到请求错误会在终端输出详细信息并停止。

## 常见问题

- 视图筛选/排序：当前 Notion 官方 API 对“视图”的筛选、排序配置支持有限，脚本仅负责写入/更新数据；视图配置建议在 Notion 页面里完成一次，之后会自动应用到后续新增数据。
- 多语言属性：脚本依赖中文属性名（`任务名称`、`完成`、`截止日期`），若你在数据库中改了列名，请对应修改脚本顶部常量。
