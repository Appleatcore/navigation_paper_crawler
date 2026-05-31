# 修改记录

## 1. 过滤与关键词

- 删除 `vla_filter.py`
- 新增 `chemistry_filter.py`
- 用 `is_chemistry_related(...)` 替换原来的导航过滤逻辑
- 提供化学默认关键词 `DEFAULT_CHEMISTRY_KEYWORDS`

## 2. 主流程

- 更新 `paper_crawler.py`
- 导入新的化学过滤模块
- 默认关键词从导航词表改为化学词表
- 新增 `chemistry_domain`、`target_websites`、`source_preferences`、`exclude_keywords` 配置读取
- arXiv 和 Semantic Scholar 的默认标签改为 `Chemistry`
- 大模型评分提示词从导航评审标准改为化学评审标准
- 默认配置文件路径改为 `config.local.json`

## 3. 配置与入口

- 更新 `config.template.json`
- 替换导航关键词为化学关键词
- 增加 `chemistry_domain`、`target_websites`、`source_preferences`、`exclude_keywords`
- 将当前研究方向更新为塑料降解，关键词更新为离子液体、塑料降解、高值化回收、W 催化、PET/PC/PLA 相关词
- 更新 `README.md`
- 更新 `run.sh`
- 更新 `plan.md`，去掉旧领域残留表述
- 删除旧的 `README_NAVIGATION.md`

## 4. 测试

- 删除 `test_vla_filter.py`
- 新增 `test_chemistry_filter.py`
- 已通过 `pytest -q`

## 5. 数据源切换

- 将主抓取源从 `arxiv` 切换为 `x_mol`
- 新增 `XMolCrawler`，直接接入 `https://www.x-mol.net/api/u/paper/search`
- 新增 `OpenAlexCrawler` 和 `CrossrefCrawler` 作为公开接口兜底源
- 主流程默认数据源顺序调整为 `x_mol` -> `openalex` -> `crossref`
- 保留 `semantic_scholar` 为可选补充源，不再默认启用
- 更新 `config.template.json`
- 更新 `README.md`
- 保留 `target_websites` 记录用途，但默认运行逻辑不再依赖 `arxiv`

## 6. 低分论文清理脚本

- 新增 `delete_low_score_papers.py`
- 参考 `navigation_paper_crawler/delete_low_score_papers.py` 实现
- 按 `Recommend Score < 50` 查询 Notion 数据库中的论文
- 默认仅预览，传入 `--execute` 后将页面归档删除
- 支持通过 `--threshold` 自定义清理阈值
