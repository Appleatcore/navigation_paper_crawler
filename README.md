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
- `arxiv`
- `semantic_scholar`

`target_websites` 用来记录目标论文网站，例如 `x-mol`、`web_of_science`、`scifinder`。当前版本还没有实现这些网站的抓取器。
