# Navigation Paper Crawler

当前仓库已经从旧的 VLA 版本切到 Embodied Navigation 版本。

建议直接阅读：
- [README_NAVIGATION.md](/home/applepie/project_for_papers/navigation_paper_crawler/README_NAVIGATION.md)

最短启动步骤：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp config.template.json config.local.json
export ORCAROUTER_API_KEY="你的 OrcaRouter API Key"
python3 paper_crawler.py config.local.json
```

## 模型平台推荐（可选）

推荐使用 [OrcaRouter](https://api.orcarouter.ai/ref/ref_744ab625079d79508a5b) 平台上的模型，以便更方便地统一接入和切换模型。
Get key at [OrcaRouter](https://api.orcarouter.ai/ref/ref_744ab625079d79508a5b)

公开配置模板中已经提供了可识别的 `orcarouter` provider 配置；API Key 建议通过 `ORCAROUTER_API_KEY` 环境变量提供，不要提交真实密钥。

## Skills 使用示例

本仓库当前提供两个适用于支持 Codex Skills 的 AI agent 的工作流。Skill 是给 agent 的操作规范，不是需要直接执行的 Python 子命令；在对话中使用对应的 `$skill-name` 即可调用。

### 近期导航论文入库

使用 [import-recent-navigation-papers](skills/import-recent-navigation-papers/SKILL.md) 检索近期论文，人工筛选导航相关工作，检查 Notion 重复项，并安全写入论文、中文详情和官方 GitHub 仓库链接。示例提示词：

```text
使用 $import-recent-navigation-papers，检索最近 5 天提交的具身导航论文，
使用 config.local.json，Recommend Score 阈值为 60，最多导入 10 篇。
请人工核验论文内容和官方 GitHub 仓库，不调用项目的外部 LLM API，完成 Notion 写入和回读核验。
```

### 补全已有 Notion 论文

使用 [enrich-notion-papers](skills/enrich-notion-papers/SKILL.md) 处理已有 Notion 记录，补全中文 `Question details` 和经过核验的官方 `source website`。示例提示词：

```text
使用 $enrich-notion-papers，处理 config.local.json 中 Recommend Score >= 85
且 Question details 为空的论文，按评分从高到低处理，核验官方 GitHub 仓库，
并在每次写入后回读 Notion。不要调用外部 LLM API。
```

如果需要手动执行同一工作流的安全写入脚本，可以先生成队列：

```bash
python3 prepare_manual_question_queue.py config.local.json --threshold 85
```

然后使用 `write_manual_source_website.py` 和 `write_manual_question_detail.py` 逐篇写入。两个写入脚本都会拒绝覆盖已有内容，并在写入后回读校验；详细规则见上面的 Skill 文档。

## 代理兜底说明

- 论文源请求目前会先按当前环境代理发起访问。
- 如果检测到设置了 `http_proxy`、`https_proxy` 或 `all_proxy`，且 `arXiv` / `Semantic Scholar` 请求返回 `429`，或出现代理/连接/超时类错误，程序会自动禁用环境代理重试一次。
- `arXiv` 和 `Semantic Scholar` 现在都会以较小分页请求，并在 `429` 时按 `Retry-After` 或保守默认值退避后再重试一次，避免大请求连续触发限流。
- 这个兜底只作用于论文抓取相关请求，不会改动 `Notion`、`LLM`、图床等其他 API 的代理行为。
- 如果禁用代理后仍然失败，程序会继续按原有逻辑报错或跳过对应数据源。

当前主入口：
- [paper_crawler.py](/home/applepie/project_for_papers/navigation_paper_crawler/paper_crawler.py)

运行脚本：
- [run.sh](/home/applepie/project_for_papers/navigation_paper_crawler/run.sh)
