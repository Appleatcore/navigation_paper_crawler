#!/usr/bin/env python3
"""
Embodied Navigation 论文过滤模块
提供通用的具身导航相关性检查函数
"""

import re


STRONG_NAVIGATION_PATTERNS = [
    "embodied navigation",
    "vision-language navigation",
    "vision language navigation",
    "vision-and-language navigation",
    "visual navigation",
    "language navigation",
    "robot navigation",
    "mobile robot navigation",
    "object navigation",
    "objectnav",
    "goal navigation",
    "goalnav",
    "pointnav",
    "point-goal navigation",
    "point goal navigation",
    "social navigation",
    "instruction following navigation",
    "navigation planning",
    "robot navigation planning",
    "mobile robot planning",
    "robot path planning",
]

NAVIGATION_TERMS = [
    "navigation",
    "navigate",
    "path planning",
    "motion planning",
    "trajectory planning",
    "waypoint",
    "route planning",
    "goal reaching",
    "goal-directed",
    "long-horizon planning",
    "exploration planning",
]

EMBODIMENT_TERMS = [
    "embodied",
    "robot",
    "robotic",
    "mobile robot",
    "agent",
    "indoor",
    "3d scene",
    "vision-language",
    "vision language",
    "object goal",
    "point goal",
    "social",
    "agentic",
    "locomotion",
    "indoor scene",
]


def is_navigation_related(title: str, abstract: str) -> bool:
    """严格检查论文是否真正与具身导航相关。"""
    text = f" {title} {abstract} ".lower()

    if any(pattern in text for pattern in STRONG_NAVIGATION_PATTERNS):
        return True

    if re.search(r"\bvln\b", text):
        return True

    has_navigation_signal = any(term in text for term in NAVIGATION_TERMS)
    has_embodiment_signal = any(term in text for term in EMBODIMENT_TERMS)
    return has_navigation_signal and has_embodiment_signal


def is_vla_related(title: str, abstract: str) -> bool:
    """Backward-compatible alias retained for older imports."""
    return is_navigation_related(title, abstract)
