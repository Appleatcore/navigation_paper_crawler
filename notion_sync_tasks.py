#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notion 任务同步脚本

功能
- 从 CSV/JSON 导入任务并同步到 Notion 数据库
- 字段映射：
  - 任务名称 -> Notion 标题属性 "任务名称"
  - 完成 -> Notion 复选框属性 "完成" (true/false)
  - 截止日期 -> Notion 日期属性 "截止日期" (YYYY-MM-DD 或 ISO8601)

使用
  环境变量：
    - NOTION_API_TOKEN: Notion 集成密钥（必填）
    - NOTION_DATABASE_ID: 数据库 ID（可选，亦可通过 --database-id 传入）

  示例：
    python notion_sync_tasks.py --file tasks_sample.csv --database-id 9d649484-01c2-4eb2-9c6d-0501d673660d
    python notion_sync_tasks.py --file tasks.json --dry-run

说明
- 脚本支持 upsert（按“任务名称”查重，存在则更新，不存在则创建）。
- 无网络/无 Token 时可使用 --dry-run 查看将要同步的内容。
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


TITLE_FIELD = "任务名称"
DONE_FIELD = "完成"
DUE_FIELD = "截止日期"


def eprint(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)


def _coerce_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"1", "true", "t", "y", "yes", "on"}:
        return True
    if s in {"0", "false", "f", "n", "no", "off"}:
        return False
    return None


@dataclass
class Task:
    name: str
    due: Optional[str] = None  # YYYY-MM-DD or ISO8601
    done: Optional[bool] = None

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Task":
        # 兼容 name/标题字段别名
        name = (
            d.get(TITLE_FIELD)
            or d.get("name")
            or d.get("title")
            or d.get("任务名")
        )
        if not name:
            raise ValueError("缺少任务名称（name/任务名称）")
        due = d.get(DUE_FIELD) or d.get("due") or d.get("deadline")
        done = _coerce_bool(d.get(DONE_FIELD) or d.get("done") or d.get("完成"))
        return Task(name=str(name), due=(str(due) if due else None), done=done)


def read_tasks_from_csv(path: str) -> List[Task]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        tasks = [Task.from_dict(row) for row in reader]
    return tasks


def read_tasks_from_json(path: str) -> List[Task]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("tasks") or data.get("items") or []
    if not isinstance(data, list):
        raise ValueError("JSON 顶层应为数组或包含 tasks/items 的对象")
    return [Task.from_dict(it) for it in data]


def read_tasks(path: str) -> List[Task]:
    if path.lower().endswith(".csv"):
        return read_tasks_from_csv(path)
    if path.lower().endswith(".json"):
        return read_tasks_from_json(path)
    raise ValueError("仅支持 CSV 或 JSON 文件")


class NotionClient:
    def __init__(self, token: str) -> None:
        self.token = token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
        # 延迟导入，避免 --help/无网时硬依赖 requests
        import requests  # type: ignore

        resp = requests.request(method, url, headers=self._headers(), timeout=30, **kwargs)
        if resp.status_code >= 400:
            raise RuntimeError(f"Notion API {method} {url} -> {resp.status_code}: {resp.text}")
        return resp.json() if resp.text else {}

    def query_by_title(self, database_id: str, title: str) -> Optional[str]:
        """返回匹配 title 的 page_id（若存在）"""
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        payload = {
            "filter": {
                "property": TITLE_FIELD,
                "title": {"equals": title},
            },
            "page_size": 1,
        }
        data = self._request("POST", url, json=payload)
        results = data.get("results", [])
        if results:
            return results[0]["id"]
        return None

    def create_task(self, database_id: str, task: Task) -> str:
        url = "https://api.notion.com/v1/pages"
        props: Dict[str, Any] = {
            TITLE_FIELD: {
                "title": [
                    {"type": "text", "text": {"content": task.name}},
                ]
            }
        }
        if task.done is not None:
            props[DONE_FIELD] = {"checkbox": bool(task.done)}
        if task.due:
            props[DUE_FIELD] = {"date": {"start": task.due}}

        payload = {
            "parent": {"database_id": database_id},
            "properties": props,
        }
        data = self._request("POST", url, json=payload)
        pid = data.get("id")
        if not isinstance(pid, str):
            raise RuntimeError(f"未从 Notion 返回有效的页面 ID: {pid!r}")
        return pid

    def update_task(self, page_id: str, task: Task) -> None:
        url = f"https://api.notion.com/v1/pages/{page_id}"
        props: Dict[str, Any] = {
            TITLE_FIELD: {
                "title": [
                    {"type": "text", "text": {"content": task.name}},
                ]
            }
        }
        if task.done is not None:
            props[DONE_FIELD] = {"checkbox": bool(task.done)}
        if task.due:
            props[DUE_FIELD] = {"date": {"start": task.due}}

        payload = {"properties": props}
        self._request("PATCH", url, json=payload)


def upsert_tasks(database_id: str, tasks: Iterable[Task], token: str, dry_run: bool = False) -> None:
    client = NotionClient(token)
    for t in tasks:
        if dry_run:
            print(f"[DRY-RUN] UPSERT -> name={t.name!r}, due={t.due!r}, done={t.done!r}")
            continue
        page_id = client.query_by_title(database_id, t.name)
        if page_id:
            client.update_task(page_id, t)
            print(f"Updated: {t.name}")
        else:
            new_id = client.create_task(database_id, t)
            print(f"Created: {t.name} -> {new_id}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="同步 CSV/JSON 任务到 Notion 数据库")
    p.add_argument("--file", required=True, help="输入 CSV 或 JSON 文件路径")
    p.add_argument("--database-id", default=os.getenv("NOTION_DATABASE_ID"), help="Notion 数据库 ID（带短横线的 UUID，如 9d649484-...）")
    p.add_argument("--dry-run", action="store_true", help="仅打印将要同步的内容，不访问网络")
    return p.parse_args(argv)


def main() -> int:
    args = parse_args()
    token = os.getenv("NOTION_API_TOKEN")
    if not token and not args.dry_run:
        eprint("缺少 NOTION_API_TOKEN 环境变量；或使用 --dry-run 进行试运行")
        return 2
    if not args.database_id and not args.dry_run:
        eprint("缺少数据库 ID（--database-id 或 NOTION_DATABASE_ID）")
        return 2

    try:
        tasks = read_tasks(args.file)
    except Exception as e:
        eprint(f"读取任务失败: {e}")
        return 2

    if args.dry_run:
        upsert_tasks(args.database_id or "unknown", tasks, token or "", dry_run=True)
        return 0

    try:
        # 此处 token/database_id 根据前置校验都已非 None
        assert args.database_id is not None
        assert token is not None
        upsert_tasks(args.database_id, tasks, token, dry_run=False)
    except Exception as e:
        eprint(f"同步失败: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
