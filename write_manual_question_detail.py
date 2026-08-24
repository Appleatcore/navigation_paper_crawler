#!/usr/bin/env python3
"""安全地为一篇 Notion 文献写入并验证 Question details。"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests

from paper_crawler import (
    NotionClient,
    QUESTION_DETAILS_PROPERTY,
    apply_log_level,
    load_config,
    logger,
)


DEFAULT_QUEUE = Path("output/manual_question_queue.jsonl")
MAX_TEXT_LENGTH = 2000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="只更新一篇论文的 Question details，并在写入后回读验证"
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config.local.json",
        help="配置文件路径，默认 config.local.json",
    )
    parser.add_argument("--page-id", required=True, help="待更新的 Notion 页面 ID")
    content_group = parser.add_mutually_exclusive_group(required=True)
    content_group.add_argument("--text", help="直接提供 Question details 文本")
    content_group.add_argument("--text-file", type=Path, help="从 UTF-8 文本文件读取内容")
    parser.add_argument(
        "--queue",
        type=Path,
        default=DEFAULT_QUEUE,
        help=f"成功后更新状态的 JSONL 队列，默认 {DEFAULT_QUEUE}",
    )
    return parser.parse_args()


def load_answer_text(args: argparse.Namespace) -> str:
    if args.text_file is not None:
        text = args.text_file.read_text(encoding="utf-8")
    else:
        text = args.text or ""
    text = text.strip()
    if not text:
        raise ValueError("Question details 内容不能为空")
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"Question details 不能超过 {MAX_TEXT_LENGTH} 个字符")
    return text


def fetch_page(notion: NotionClient, page_id: str) -> Dict[str, Any]:
    response = requests.get(
        f"{notion.base_url}/pages/{page_id}",
        headers=notion.headers,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def extract_question_details(page: Dict[str, Any]) -> str:
    prop = page.get("properties", {}).get(QUESTION_DETAILS_PROPERTY)
    if not prop or prop.get("type") != "rich_text":
        raise ValueError(
            f"页面缺少 {QUESTION_DETAILS_PROPERTY}，或该属性不是 text/rich_text 类型"
        )
    return "".join(
        item.get("plain_text")
        or item.get("text", {}).get("content", "")
        for item in prop.get("rich_text", [])
    )


def validate_page_database(page: Dict[str, Any], database_id: str) -> None:
    parent_database_id = page.get("parent", {}).get("database_id")

    def normalize(value: Any) -> str:
        return str(value or "").replace("-", "").lower()

    if normalize(parent_database_id) != normalize(database_id):
        raise ValueError("页面不属于 config 中配置的 Notion 数据库，拒绝写入")


def question_details_update(text: str) -> Dict[str, Any]:
    """更新载荷中只包含 Question details。"""
    return {
        QUESTION_DETAILS_PROPERTY: {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": text},
                }
            ]
        }
    }


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    items = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line_number, line in enumerate(file_obj, start=1):
            if not line.strip():
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"队列第 {line_number} 行不是有效 JSON: {exc}") from exc
    return items


def mark_queue_done(queue_path: Path, page_id: str) -> bool:
    if not queue_path.exists():
        logger.warning("队列文件不存在，跳过本地状态更新: %s", queue_path)
        return False

    items = read_jsonl(queue_path)
    found = False
    for item in items:
        if item.get("page_id") == page_id:
            item["status"] = "done"
            found = True
            break

    if not found:
        logger.warning("队列中未找到 page_id，跳过本地状态更新: %s", page_id)
        return False

    temp_path = queue_path.with_suffix(queue_path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file_obj:
        for item in items:
            file_obj.write(json.dumps(item, ensure_ascii=False) + "\n")
    temp_path.replace(queue_path)
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

    try:
        answer_text = load_answer_text(args)
    except (OSError, ValueError) as exc:
        logger.error("读取 Question details 失败: %s", exc)
        return 1

    notion = NotionClient(notion_token, database_id)
    try:
        page_before = fetch_page(notion, args.page_id)
        validate_page_database(page_before, database_id)
        existing_text = extract_question_details(page_before)
    except Exception as exc:
        logger.error("写入前检查失败: %s", exc)
        return 1

    if existing_text.strip():
        logger.error("Question details 已有内容，拒绝覆盖: %s", args.page_id)
        return 1

    updates = question_details_update(answer_text)
    if set(updates) != {QUESTION_DETAILS_PROPERTY}:
        logger.error("更新载荷包含非预期字段，拒绝写入")
        return 1
    if not notion.update_paper_fields(args.page_id, updates):
        return 2

    try:
        page_after = fetch_page(notion, args.page_id)
        written_text = extract_question_details(page_after)
    except Exception as exc:
        logger.error("写入后回读失败: %s", exc)
        return 2

    if written_text != answer_text:
        logger.error("写入后回读内容不一致，页面已修改但验证失败")
        return 2

    logger.info("Question details 已写入并回读验证成功: %s", args.page_id)
    try:
        queue_updated = mark_queue_done(args.queue, args.page_id)
    except (OSError, ValueError) as exc:
        logger.error("Notion 写入已验证，但更新本地队列失败: %s", exc)
        return 2
    if not queue_updated:
        logger.error("Notion 写入已验证，但本地队列状态未更新")
        return 2

    logger.info("本地队列状态已更新为 done: %s", args.queue)
    return 0


if __name__ == "__main__":
    sys.exit(main())
