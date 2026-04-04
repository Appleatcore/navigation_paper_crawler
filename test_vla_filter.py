#!/usr/bin/env python3
"""
测试具身导航过滤逻辑
"""

from vla_filter import is_navigation_related


TEST_CASES = [
    ("Embodied Navigation with Vision-Language Planning", "", True),
    ("Robot Path Planning for Indoor Navigation with Multimodal Instructions", "", True),
    ("ObjectNav with Semantic Memory for Mobile Robots", "", True),
    ("Vision-and-Language Navigation with Hierarchical Memory", "", True),
    ("", "We study robot navigation in indoor 3D scenes with language instructions.", True),
    ("Social Navigation via Goal-conditioned Policies", "", True),
    ("Motion Planning for Robotic Exploration in Indoor Scenes", "", True),
    ("Large Vision-Language Models for Visual Understanding", "", False),
    ("Autonomous Driving with Vision-Language-Action Models", "", False),
    ("Multimodal Learning for Robotics", "", False),
    ("Trajectory Prediction for Highway Driving", "", False),
    ("Point cloud registration for mapping", "", False),
]


print("=" * 80)
print("测试具身导航严格过滤逻辑")
print("=" * 80)

passed = 0
failed = 0

for title, abstract, expected in TEST_CASES:
    result = is_navigation_related(title, abstract)
    status = "✅ PASS" if result == expected else "❌ FAIL"
    if result == expected:
        passed += 1
    else:
        failed += 1

    display = title if title else abstract[:60]
    print(f"{status} | {display}")
    if result != expected:
        print(f"       Expected: {expected}, Got: {result}")

print("=" * 80)
print(f"测试结果: {passed} 通过, {failed} 失败")
print("=" * 80)
