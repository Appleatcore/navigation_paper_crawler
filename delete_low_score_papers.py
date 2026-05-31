#!/usr/bin/env python3
"""
归档删除 Notion 数据库中评分低于阈值的论文。

默认只预览，不执行实际删除；传入 --execute 后才会把页面 archived=true。
Notion API 不支持真正硬删除页面，这里采用归档方式，相当于从数据库中移除。
"""

import argparse
import sys
import time
from typing import Any, Dict, List

import requests

from paper_crawler import NotionClient, apply_log_level, load_config, logger


def fetch_low_score_papers(notion: NotionClient, threshold: float, page_size: int = 100) -> List[Dict[str, Any]]:
    """查询评分低于阈值的论文页面。"""
    papers: List[Dict[str, Any]] = []
    has_more = True
    start_cursor = None

    while has_more:
        query_body: Dict[str, Any] = {
            "page_size": min(page_size, 100),
            "filter": {
                "property": "Recommend Score",
                "number": {"less_than": threshold}
            }
        }
        if start_cursor:
            query_body["start_cursor"] = start_cursor

        response = requests.post(
            f"{notion.base_url}/databases/{notion.database_id}/query",
            headers=notion.headers,
            json=query_body,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        for page in data.get("results", []):
            properties = page.get("properties", {})
            title = ""
            title_prop = properties.get("Name", {})
            if title_prop.get("type") == "title":
                title = "".join(
                    item.get("plain_text", "")
                    for item in title_prop.get("title", [])
                ).strip()

            score = None
            score_prop = properties.get("Recommend Score", {})
            if score_prop.get("type") == "number":
                score = score_prop.get("number")

            papers.append({
                "page_id": page["id"],
                "title": title or "Untitled",
                "recommend_score": score,
            })

        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")
        if has_more:
            time.sleep(0.3)

    return papers


def archive_page(notion: NotionClient, page_id: str) -> None:
    """归档页面。"""
    response = requests.patch(
        f"{notion.base_url}/pages/{page_id}",
        headers=notion.headers,
        json={"archived": True},
        timeout=15
    )
    response.raise_for_status()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="归档删除 Notion 数据库中评分低于阈值的论文")
    parser.add_argument("config", nargs="?", default="config.local.json", help="配置文件路径，默认 config.local.json")
    parser.add_argument("--threshold", type=float, default=50.0, help="删除阈值，默认 50")
    parser.add_argument("--execute", action="store_true", help="实际执行归档删除；默认仅预览")
    parser.add_argument("--delay", type=float, default=0.3, help="每次归档之间的等待秒数，默认 0.3")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    apply_log_level(config.get("log_level", "INFO"))

    notion_token = config.get("notion_token")
    database_id = config.get("database_id")
    if not notion_token or not database_id:
        logger.error("配置文件缺少 notion_token 或 database_id")
        return 1

    notion = NotionClient(notion_token, database_id)

    logger.info("开始查询 Recommend Score < %.2f 的论文", args.threshold)
    try:
        papers = fetch_low_score_papers(notion, threshold=args.threshold)
    except Exception as exc:
        logger.error("查询低分论文失败: %s", exc)
        return 1

    if not papers:
        logger.info("未找到评分低于 %.2f 的论文", args.threshold)
        return 0

    logger.info("共找到 %d 篇评分低于 %.2f 的论文", len(papers), args.threshold)
    for idx, paper in enumerate(papers, start=1):
        logger.info("%d. %.2f | %s", idx, float(paper.get("recommend_score") or 0.0), paper["title"])

    if not args.execute:
        logger.info("当前为预览模式，未执行删除。添加 --execute 后会归档这些页面。")
        return 0

    success = 0
    failed = 0
    for paper in papers:
        try:
            archive_page(notion, paper["page_id"])
            success += 1
            logger.info("已归档: %.2f | %s", float(paper.get("recommend_score") or 0.0), paper["title"])
        except Exception as exc:
            failed += 1
            logger.error("归档失败: %s | %s", paper["title"], exc)
        time.sleep(max(0.0, args.delay))

    logger.info("归档完成: %d 成功, %d 失败", success, failed)
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
