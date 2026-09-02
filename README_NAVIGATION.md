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
cp .env.example .env
```

在 `.env` 中填写 `ORCAROUTER_API_KEY`，或在执行前直接 `export ORCAROUTER_API_KEY="你的 OrcaRouter API Key"`。

然后编辑 `config.local.json`，至少填这几项：

```json
{
  "notion_token": "你的 Notion integration token",
  "database_id": "你的 Notion database id",
  "llm_provider": "orcarouter",
  "llm_model": "qwen/qwen3-vl-235b-a22b-thinking",
  "llm_api_base": "https://api.orcarouter.ai/v1",
  "llm_api_key": ""
}
```

当 `llm_provider` 为 `orcarouter` 且 `llm_api_key` 为空时，程序会从 `ORCAROUTER_API_KEY` 环境变量读取密钥。也可以将 `llm_provider`、模型、API 地址和密钥改为其他兼容服务；OrcaRouter 不是强制选项。

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

## 批量回答论文细节问题

先在 Notion 文献数据库中创建名为 `Question details` 的 text 属性，然后运行：

```bash
python3 answer_question_details.py config.local.json
```

脚本会优先读取 PDF 全文，PDF 不可用时回退到摘要和元数据，并写入以下内容：主要问题、方法概述、导航类型和分类依据。导航类型为 `VLN`、`VN`、`Point Navigation` 或 `Other/Unclear`。

正常运行主爬虫时也会自动为准备入库的新论文生成并写入该字段：

```bash
python3 paper_crawler.py config.local.json
```

此行为由 `question_details_enabled` 控制，默认启用。主爬虫会先过滤低分论文并应用 `max_papers` 上限，再调用大模型生成详情。

默认跳过已经填写过 `Question details` 的论文。常用选项：

```bash
# 只处理一篇并预览答案，不写数据库
python3 answer_question_details.py config.local.json --limit 1 --dry-run

# 重新回答并覆盖已有内容
python3 answer_question_details.py config.local.json --overwrite

# 只根据摘要和元数据回答，不下载 PDF
python3 answer_question_details.py config.local.json --abstract-only
```

只补全 `Recommend Score >= 85` 且 `Question details` 为空的论文，并按评分从高到低处理：

```bash
python3 answer_high_score_question_details.py config.local.json
```

建议先预览一篇：

```bash
python3 answer_high_score_question_details.py config.local.json --limit 1 --dry-run
```

可以通过 `--threshold` 修改阈值，例如 `--threshold 90`。

## 人工逐篇总结工作流

生成评分不低于 85、且尚未填写 `Question details` 的人工处理队列：

```bash
python3 prepare_manual_question_queue.py config.local.json
```

队列默认保存到 `output/manual_question_queue.jsonl`，包含 `page_id`、标题、评分、PDF 链接、摘要和处理状态，并按评分从高到低排列。该脚本只调用 Notion API，不调用大模型 API。

准备好一篇论文的中文总结后，将内容保存为 UTF-8 文本文件，再安全写入单个页面：

```bash
python3 write_manual_question_detail.py config.local.json \
  --page-id "从队列中复制的 page_id" \
  --text-file output/question_detail.txt
```

写入工具会拒绝覆盖已有内容，只提交 `Question details` 字段，写入后回读核对，并把对应队列项的 `status` 更新为 `done`。

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
  "min_recommend_score": 60,
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
- 爬虫内部会把 `arXiv` / `Semantic Scholar` 的单次请求拆成更小分页，并在 `429` 时退避后再重试一次

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
- `min_recommend_score`
  - 控制论文写入 Notion 的最低推荐评分，默认 `60`；低于该分数的论文会被跳过
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
