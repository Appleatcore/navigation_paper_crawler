#!/usr/bin/env python3
"""按推荐评分从高到低补全高分论文的 Question details。"""

import argparse
import sys
import time
from typing import Any, Dict, List

from paper_crawler import (
    NotionClient,
    QUESTION_DETAILS_PROPERTY,
    QuestionDetailsAnswerer,
    apply_log_level,
    load_config,
    logger,
)


RECOMMEND_SCORE_PROPERTY = "Recommend Score"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="按 Recommend Score 从高到低补全高分论文的 Question details"
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config.local.json",
        help="配置文件路径，默认 config.local.json",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=85.0,
        help="最低推荐评分（包含该分数），默认 85",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="最多处理多少篇，0 表示全部（默认 0）",
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


def select_high_score_missing_details(
    papers: List[Dict[str, Any]], threshold: float = 85.0
) -> List[Dict[str, Any]]:
    """选择达到阈值且详情为空的论文，并按评分降序排列。"""
    selected = []
    for paper in papers:
        if str(paper.get("question_details") or "").strip():
            continue
        try:
            score = float(paper.get("recommend_score"))
        except (TypeError, ValueError):
            continue
        if score >= threshold:
            paper["recommend_score"] = score
            selected.append(paper)

    selected.sort(key=lambda paper: paper["recommend_score"], reverse=True)
    return selected


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


def _validate_database_schema(notion: NotionClient) -> bool:
    try:
        properties = notion._get_database()
    except Exception as exc:
        logger.error("读取 Notion 数据库结构失败: %s", exc)
        return False

    details_schema = properties.get(QUESTION_DETAILS_PROPERTY)
    if not details_schema or details_schema.get("type") != "rich_text":
        logger.error(
            "Notion 属性 %s 必须存在且为 text/rich_text 类型",
            QUESTION_DETAILS_PROPERTY,
        )
        return False

    score_schema = properties.get(RECOMMEND_SCORE_PROPERTY)
    if not score_schema or score_schema.get("type") != "number":
        logger.error(
            "Notion 属性 %s 必须存在且为 number 类型",
            RECOMMEND_SCORE_PROPERTY,
        )
        return False

    return True


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
    if not _validate_database_schema(notion):
        return 1

    papers = notion.fetch_existing_papers(limit=100)
    papers = select_high_score_missing_details(papers, threshold=args.threshold)
    if args.limit > 0:
        papers = papers[:args.limit]

    if not papers:
        logger.info(
            "没有 Recommend Score >= %.2f 且 Question details 为空的论文",
            args.threshold,
        )
        return 0

    delay = args.delay
    if delay is None:
        delay = float(config.get("llm_call_interval_s", 1.0))

    logger.info(
        "找到 %d 篇待处理论文，将按评分从高到低生成（阈值 %.2f，dry-run=%s）",
        len(papers),
        args.threshold,
        args.dry_run,
    )

    success = 0
    failed = 0
    for index, paper in enumerate(papers, start=1):
        title = paper.get("title") or "Untitled"
        score = paper["recommend_score"]
        logger.info("[%d/%d] %.2f | %s", index, len(papers), score, title[:100])
        try:
            answer = answerer.answer_paper(paper)
            if args.dry_run:
                logger.info("Question details 预览 (%s):\n%s", title[:60], answer)
            elif notion.update_paper_fields(paper["page_id"], _question_details_update(answer)):
                logger.info("已写入 Question details: %.2f | %s", score, title[:80])
            else:
                raise RuntimeError("Notion 更新失败")
            success += 1
        except Exception as exc:
            failed += 1
            logger.error("处理失败: %.2f | %s | %s", score, title[:80], exc)

        if index < len(papers):
            time.sleep(max(0.0, delay))

    logger.info("处理完成: %d 成功, %d 失败", success, failed)
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
