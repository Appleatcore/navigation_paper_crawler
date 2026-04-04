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
python3 paper_crawler.py config.local.json
```

当前主入口：
- [paper_crawler.py](/home/applepie/project_for_papers/navigation_paper_crawler/paper_crawler.py)

运行脚本：
- [run.sh](/home/applepie/project_for_papers/navigation_paper_crawler/run.sh)
