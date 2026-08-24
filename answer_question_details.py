#!/usr/bin/env python3
"""使用大模型阅读 Notion 文献，并填写 Question details 字段。"""

import argparse
import sys
import time
from typing import Any, Dict

from paper_crawler import (
    NotionClient,
    QUESTION_DETAILS_PROPERTY,
    QuestionDetailsAnswerer,
    apply_log_level,
    load_config,
    logger,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="调用大模型逐篇阅读 Notion 文献并填写 Question details"
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config.local.json",
        help="配置文件路径，默认 config.local.json",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="最多处理多少篇，0 表示全部（默认 0）",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="重新处理已有 Question details 的论文",
    )
    parser.add_argument(
        "--abstract-only",
        action="store_true",
        help="不下载 PDF，只根据摘要和元数据回答",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="调用大模型并显示答案，但不写入 Notion",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="每篇论文处理后的等待秒数；默认使用 llm_call_interval_s",
    )
    return parser.parse_args()


def _question_details_update(answer: str) -> Dict[str, Any]:
    return {
        QUESTION_DETAILS_PROPERTY: {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": answer},
                }
            ]
        }
    }


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    apply_log_level(config.get("log_level", "INFO"))

    notion_token = config.get("notion_token")
    database_id = config.get("database_id")
    if not notion_token or not database_id:
        logger.error("配置文件缺少 notion_token 或 database_id")
        return 1

    answerer = QuestionDetailsAnswerer(config, abstract_only=args.abstract_only)
    if not answerer.api_key:
        logger.error("配置文件缺少 llm_api_key，且环境变量 OPENAI_API_KEY 未设置")
        return 1

    notion = NotionClient(notion_token, database_id)
    try:
        property_schema = notion._get_database().get(QUESTION_DETAILS_PROPERTY)
    except Exception as exc:
        logger.error("读取 Notion 数据库结构失败: %s", exc)
        return 1

    if not property_schema:
        logger.error("Notion 数据库缺少属性: %s", QUESTION_DETAILS_PROPERTY)
        return 1
    if property_schema.get("type") != "rich_text":
        logger.error(
            "Notion 属性 %s 必须是 text/rich_text 类型，当前是 %s",
            QUESTION_DETAILS_PROPERTY,
            property_schema.get("type"),
        )
        return 1

    papers = notion.fetch_existing_papers(limit=100)
    if not args.overwrite:
        papers = [paper for paper in papers if not str(paper.get("question_details") or "").strip()]
    if args.limit > 0:
        papers = papers[:args.limit]

    if not papers:
        logger.info("没有需要填写 Question details 的论文")
        return 0

    delay = args.delay
    if delay is None:
        delay = float(config.get("llm_call_interval_s", 1.0))

    logger.info(
        "开始处理 %d 篇论文（PDF全文=%s，覆盖已有答案=%s，dry-run=%s）",
        len(papers),
        answerer.use_full_pdf,
        args.overwrite,
        args.dry_run,
    )

    success = 0
    failed = 0
    for index, paper in enumerate(papers, start=1):
        title = paper.get("title") or "Untitled"
        logger.info("[%d/%d] 分析: %s", index, len(papers), title[:100])
        try:
            answer = answerer.answer_paper(paper)
            if args.dry_run:
                logger.info("Question details 预览 (%s):\n%s", title[:60], answer)
            elif notion.update_paper_fields(paper["page_id"], _question_details_update(answer)):
                logger.info("已写入 Question details: %s", title[:80])
            else:
                raise RuntimeError("Notion 更新失败")
            success += 1
        except Exception as exc:
            failed += 1
            logger.error("处理失败: %s | %s", title[:80], exc)

        if index < len(papers):
            time.sleep(max(0.0, delay))

    logger.info("处理完成: %d 成功, %d 失败", success, failed)
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
