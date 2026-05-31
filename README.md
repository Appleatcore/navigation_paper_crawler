# Chemistry Paper Crawler

当前仓库已经切到化学论文抓取方向。

建议直接阅读：
- [paper_crawler.py](/home/applepie/project_for_papers/chemical_paper_crawler/paper_crawler.py)
- [chemistry_filter.py](/home/applepie/project_for_papers/chemical_paper_crawler/chemistry_filter.py)
- [run.sh](/home/applepie/project_for_papers/chemical_paper_crawler/run.sh)
- [config.template.json](/home/applepie/project_for_papers/chemical_paper_crawler/config.template.json)

最短启动步骤：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp config.template.json config.local.json
python3 paper_crawler.py config.local.json
```

当前最小配置项：
- `notion_token`
- `database_id`
- `llm_api_base`
- `llm_api_key`
- `chemistry_domain`
- `target_websites`
- `keywords`
- `exclude_keywords`
- `source_preferences`

当前代码支持的数据源：
- `x_mol`
- `openalex`
- `crossref`
- `semantic_scholar`

`target_websites` 用来记录目标论文网站，例如 `x-mol`、`web_of_science`、`scifinder`。

当前默认抓取顺序：
- `x_mol` 作为主数据源
- `openalex`、`crossref` 作为公开接口兜底
- `semantic_scholar` 保持可选，不默认启用

维护脚本：

```bash
# 预览 Recommend Score < 50 的论文，不实际删除
python3 delete_low_score_papers.py config.local.json

# 实际归档删除 Recommend Score < 50 的论文
python3 delete_low_score_papers.py config.local.json --execute

# 自定义阈值
python3 delete_low_score_papers.py config.local.json --threshold 40 --execute
```

说明：
- Notion 不支持硬删除页面，脚本实际执行的是 `archived=true`
- 默认是预览模式，只有传入 `--execute` 才会归档
