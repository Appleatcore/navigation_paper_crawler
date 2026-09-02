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

推荐但不强制使用 [OrcaRouter](https://api.orcarouter.ai/ref/ref_744ab625079d79508a5b) 平台上的模型，以便更方便地统一接入和切换模型。
Get key at [OrcaRouter](https://api.orcarouter.ai/ref/ref_744ab625079d79508a5b)

公开配置模板中已经提供了可识别的 `orcarouter` provider 配置；API Key 建议通过 `ORCAROUTER_API_KEY` 环境变量提供，不要提交真实密钥。

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
