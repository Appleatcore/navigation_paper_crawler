#!/usr/bin/env python3
"""安全地为一篇 Notion 文献写入并验证官方 GitHub 链接。"""

import argparse
import sys
from typing import Any, Dict
from urllib.parse import urlparse

from paper_crawler import NotionClient, apply_log_level, load_config, logger
from write_manual_question_detail import fetch_page, validate_page_database


SOURCE_WEBSITE_PROPERTY = "source website"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="只更新一篇论文的 source website，并在写入后回读验证"
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config.local.json",
        help="配置文件路径，默认 config.local.json",
    )
    parser.add_argument("--page-id", required=True, help="待更新的 Notion 页面 ID")
    parser.add_argument("--url", required=True, help="论文作者或项目的官方 GitHub 仓库链接")
    return parser.parse_args()


def validate_github_url(value: str) -> str:
    url = value.strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError("source website 必须是 https://github.com/ 下的官方仓库链接")
    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) < 2:
        raise ValueError("GitHub 链接必须指向具体仓库（至少包含 owner/repository）")
    return url


def extract_source_website(page: Dict[str, Any]) -> str:
    prop = page.get("properties", {}).get(SOURCE_WEBSITE_PROPERTY)
    if not prop or prop.get("type") != "url":
        raise ValueError(f"页面缺少 {SOURCE_WEBSITE_PROPERTY}，或该属性不是 URL 类型")
    return prop.get("url") or ""


def source_website_update(url: str) -> Dict[str, Any]:
    """更新载荷中只包含 source website。"""
    return {SOURCE_WEBSITE_PROPERTY: {"url": url}}


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
        source_url = validate_github_url(args.url)
    except ValueError as exc:
        logger.error("GitHub 链接无效: %s", exc)
        return 1

    notion = NotionClient(notion_token, database_id)
    try:
        page_before = fetch_page(notion, args.page_id)
        validate_page_database(page_before, database_id)
        existing_url = extract_source_website(page_before)
    except Exception as exc:
        logger.error("写入前检查失败: %s", exc)
        return 1

    if existing_url.strip():
        logger.error("source website 已有内容，拒绝覆盖: %s", args.page_id)
        return 1

    updates = source_website_update(source_url)
    if set(updates) != {SOURCE_WEBSITE_PROPERTY}:
        logger.error("更新载荷包含非预期字段，拒绝写入")
        return 1
    if not notion.update_paper_fields(args.page_id, updates):
        return 2

    try:
        page_after = fetch_page(notion, args.page_id)
        written_url = extract_source_website(page_after)
    except Exception as exc:
        logger.error("写入后回读失败: %s", exc)
        return 2

    if written_url != source_url:
        logger.error("写入后回读链接不一致，页面已修改但验证失败")
        return 2

    logger.info("source website 已写入并回读验证成功: %s", args.page_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
