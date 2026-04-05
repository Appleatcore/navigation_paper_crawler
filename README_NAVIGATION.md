# Navigation Paper Crawler

这份文档对应 2026-04-04 之后的导航版本，用来替代仓库里仍然残留的部分 VLA 文案。

当前版本的目标是：
- 检索 Embodied Navigation 相关论文
- 支持 planning 相关导航论文检索
- 可选使用 Qwen 进行推荐评分
- 将结果写入 Notion
- 尝试补充作者机构信息

## 主要改动

本次修改将仓库从偏 VLA 的逻辑，最小化改成了 Embodied Navigation 版本：

- arXiv 查询不再写死 VLA 词，而是直接读取配置中的 `keywords`
- 默认关键词已切换为 navigation，并加入 planning 相关词
- 过滤逻辑改为 `is_navigation_related(...)`
- 评分提示词改为导航论文评审标准，不再按 VLA 标准评分
- 写入 Notion 的标签改为 `Embodied Navigation`
- 日志默认改回 `INFO`，并压低了 `urllib3` / `requests` 的调试输出

当前默认关键词包括：

```json
[
  "embodied navigation",
  "vision-language navigation",
  "robot navigation",
  "object navigation",
  "navigation planning",
  "robot path planning"
]
```

## 环境要求

- `Python 3.9+`
- 可访问：
  - `export.arxiv.org`
  - `api.semanticscholar.org`
  - `api.notion.com`
  - `dashscope.aliyuncs.com`

## 安装步骤

在新电脑上建议直接按下面执行：

```bash
git clone <your-repo-url> navigation_paper_crawler
cd navigation_paper_crawler

python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

如果你不想用虚拟环境，也可以直接：

```bash
python3 -m pip install -r requirements.txt
```

## 配置步骤

先复制模板：

```bash
cp config.template.json config.local.json
```

然后编辑 `config.local.json`，至少填这几项：

```json
{
  "notion_token": "你的 Notion integration token",
  "database_id": "你的 Notion database id",
  "llm_provider": "openai-compatible",
  "llm_model": "qwen-plus",
  "llm_api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "llm_api_key": "你的百炼 API Key"
}
```

## Notion 数据库要求

数据库至少需要这些字段：

- `Name`：title
- `Status`：select
- `Venue`：select
- `Date`：date
- `Added`：date
- `Authors`：rich_text
- `Year`：number
- `Abstract`：rich_text
- `userDefined:URL`：url
- `PDF Link`：url
- `DOI`：rich_text
- `Tags`：multi_select
- `Institutions`：multi_select

另外要把该数据库共享给你的 Notion integration。

## 快速启动

正式运行：

```bash
cd /path/to/navigation_paper_crawler
python3 paper_crawler.py config.local.json
```

也可以用仓库自带脚本：

```bash
cd /path/to/navigation_paper_crawler
./run.sh config.local.json
```

查看日志：

```bash
tail -f paper_crawler.log
```

## 推荐的首次测试配置

首次部署建议先用偏保守的配置，确认链路通了再放大：

```json
{
  "days_back": 7,
  "max_papers": 10,
  "arxiv_max_results": 30,
  "semantic_scholar_max_results": 15,
  "use_semantic_scholar": true,
  "enrich_institutions": true,
  "recommend_score_enabled": true,
  "llm_recommend_score_enabled": true,
  "llm_max_papers": 5,
  "log_level": "INFO"
}
```

这组参数的意义是：

- 最近 7 天内检索
- 最多写入 10 篇到 Notion
- 最多给 5 篇调用 Qwen 评分
- 先控制 API 成本和日志量

## 如果想多搜几篇

主要调整这几个参数：

- `days_back`
  - 从 `7` 调到 `14` 或 `30`
- `arxiv_max_results`
  - 从 `30` 调到 `50` 或 `100`
- `semantic_scholar_max_results`
  - 从 `15` 调到 `30` 或 `50`
- `max_papers`
  - 控制最终写入 Notion 的上限
- `llm_max_papers`
  - 控制有多少篇会调用大模型评分

一个更激进的例子：

```json
{
  "keywords": [
    "embodied navigation",
    "vision-language navigation",
    "robot navigation",
    "object navigation",
    "navigation planning",
    "robot path planning",
    "mobile robot planning",
    "goal-conditioned navigation"
  ],
  "days_back": 30,
  "arxiv_max_results": 80,
  "semantic_scholar_max_results": 40,
  "max_papers": 30,
  "llm_max_papers": 10
}
```

## 只做检索预览，不写 Notion

如果你想先看今天能抓到哪些标题，而不写数据库，可以用：

```bash
python3 -c 'from paper_crawler import ArxivCrawler; keywords=["embodied navigation","vision-language navigation","robot navigation","object navigation","navigation planning","robot path planning"]; papers=ArxivCrawler(keywords, 30).search(20); print("count", len(papers)); [print("- " + p["title"]) for p in papers[:20]]'
```

## 常见问题

### 1. 为什么机构信息经常补不出来？

当前机构补全依赖 Semantic Scholar，常见原因有：

- `429` 限流
- arXiv 新论文尚未被 Semantic Scholar 索引
- 部分 `arXiv:xxxxv1` 会返回 `404`
- 即使论文能查到，作者 `affiliations` 也可能为空

所以“抓取成功但 institutions 为空”在当前版本里是正常现象。

### 2. 为什么有些论文只用了规则打分？

因为 `llm_max_papers` 控制了最多多少篇会调用 Qwen。超出的部分会回退到规则打分。

### 3. 为什么日志比之前安静？

因为当前版本默认：

- `log_level = INFO`
- `urllib3` / `requests` 的底层连接日志被压到了 `WARNING`

这样终端不会再刷大量 `connectionpool DEBUG`。

## 部署后最常用的命令

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

启动：

```bash
python3 paper_crawler.py config.local.json
```

查看日志：

```bash
tail -f paper_crawler.log
```

## 备注

- `config.local.json` 不要提交到 Git
- 不要把真实的 `notion_token`、`database_id`、`llm_api_key` 写进公共文档
- 如果 API key 曾经暴露过，建议立刻旋转
