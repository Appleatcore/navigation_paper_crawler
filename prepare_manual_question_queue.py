#!/usr/bin/env python3
"""从 Notion 导出高分且缺少 Question details 的人工处理队列。"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from paper_crawler import (
    NotionClient,
    QUESTION_DETAILS_PROPERTY,
    apply_log_level,
    load_config,
    logger,
)


RECOMMEND_SCORE_PROPERTY = "Recommend Score"
DEFAULT_OUTPUT = Path("output/manual_question_queue.jsonl")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="导出 Recommend Score >= 阈值且 Question details 为空的论文队列"
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
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"输出 JSONL 路径，默认 {DEFAULT_OUTPUT}",
    )
    return parser.parse_args()


def select_queue_papers(
    papers: List[Dict[str, Any]], threshold: float = 85.0
) -> List[Dict[str, Any]]:
    """筛选待处理论文，并按评分降序、标题升序排列。"""
    selected = []
    for paper in papers:
        if str(paper.get("question_details") or "").strip():
            continue
        try:
            score = float(paper.get("recommend_score"))
        except (TypeError, ValueError):
            continue
        if score >= threshold:
            selected.append({**paper, "recommend_score": score})

    selected.sort(
        key=lambda paper: (
            -paper["recommend_score"],
            str(paper.get("title") or "").lower(),
        )
    )
    return selected


def build_queue_items(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """只保留人工处理需要的字段。"""
    return [
        {
            "page_id": paper["page_id"],
            "title": paper.get("title") or "Untitled",
            "recommend_score": paper["recommend_score"],
            "pdf_url": paper.get("pdf_url"),
            "abstract": paper.get("abstract") or "",
            "status": "pending",
        }
        for paper in papers
    ]


def write_jsonl_atomic(output_path: Path, items: List[Dict[str, Any]]) -> None:
    """原子写入 JSONL，避免中途中断留下半个文件。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file_obj:
        for item in items:
            file_obj.write(json.dumps(item, ensure_ascii=False) + "\n")
    temp_path.replace(output_path)


def validate_database_schema(notion: NotionClient) -> bool:
    try:
        properties = notion._get_database()
    except Exception as exc:
        logger.error("读取 Notion 数据库结构失败: %s", exc)
        return False

    score_schema = properties.get(RECOMMEND_SCORE_PROPERTY)
    details_schema = properties.get(QUESTION_DETAILS_PROPERTY)
    if not score_schema or score_schema.get("type") != "number":
        logger.error("Notion 属性 %s 必须存在且为 number 类型", RECOMMEND_SCORE_PROPERTY)
        return False
    if not details_schema or details_schema.get("type") != "rich_text":
        logger.error("Notion 属性 %s 必须存在且为 text/rich_text 类型", QUESTION_DETAILS_PROPERTY)
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

    notion = NotionClient(notion_token, database_id)
    if not validate_database_schema(notion):
        return 1

    papers = notion.fetch_existing_papers(limit=100)
    selected = select_queue_papers(papers, threshold=args.threshold)
    items = build_queue_items(selected)
    write_jsonl_atomic(args.output, items)

    logger.info(
        "已导出 %d 篇论文到 %s（评分 >= %.2f，按分数降序）",
        len(items),
        args.output,
        args.threshold,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
