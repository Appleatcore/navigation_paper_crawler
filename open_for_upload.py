#!/usr/bin/env python3
"""
快速上传助手：自动打开Notion页面和本地图片文件夹
"""

import os
import json
import logging
import subprocess
import webbrowser
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def open_file_manager(path: str):
    """打开文件管理器"""
    try:
        dir_path = os.path.dirname(path) if os.path.isfile(path) else path
        
        # 尝试不同的文件管理器
        managers = [
            ['nautilus', dir_path],
            ['dolphin', dir_path],
            ['thunar', dir_path],
            ['xdg-open', dir_path]
        ]
        
        for manager in managers:
            try:
                subprocess.Popen(manager, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except:
                continue
        
        logger.warning("  ⚠️  无法自动打开文件管理器")
        logger.info(f"     请手动打开: {dir_path}")
        return False
                
    except Exception as e:
        logger.error(f"  ❌ 打开文件管理器失败: {e}")
        return False


def open_notion_database(database_id: str):
    """在浏览器中打开Notion数据库"""
    url = f"https://www.notion.so/{database_id}"
    webbrowser.open(url)


def get_paper_images(images_dir: str):
    """获取所有论文图片信息"""
    images_path = Path(images_dir)
    
    if not images_path.exists():
        logger.error(f"❌ 图片目录不存在: {images_dir}")
        return {}
    
    # 按论文标题分组
    paper_images = {}
    for img_file in sorted(images_path.glob("*.png")):
        # 文件名格式: Title_figX_pY_timestamp.png
        name = img_file.stem
        parts = name.split('_fig')
        if len(parts) >= 2:
            title = parts[0]
            fig_info = parts[1].split('_')[0]  # 提取figX中的X
            
            if title not in paper_images:
                paper_images[title] = []
            
            paper_images[title].append({
                'path': str(img_file),
                'fig': fig_info,
                'name': img_file.name
            })
    
    # 为每篇论文选择最佳图片（优先fig1）
    result = {}
    for title, images in paper_images.items():
        # 按fig编号排序
        images.sort(key=lambda x: x['fig'])
        result[title] = {
            'best': images[0],  # fig1或最小编号
            'all': images,
            'count': len(images)
        }
    
    return result


def main():
    # 读取配置
    config_path = "config_lcj.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"❌ 读取配置文件失败: {e}")
        return
    
    database_id = config.get('database_id', '').replace('-', '')
    images_dir = './images'
    
    if not database_id:
        logger.error("❌ 配置文件缺少database_id")
        return
    
    # 打印标题
    logger.info("=" * 70)
    logger.info("🚀 快速上传助手 - 自动打开Notion和图片文件夹")
    logger.info("=" * 70)
    logger.info("")
    
    # 获取图片信息
    paper_images = get_paper_images(images_dir)
    
    if not paper_images:
        logger.info("❌ 未找到任何图片！")
        logger.info(f"   请确认图片目录: {os.path.abspath(images_dir)}")
        return
    
    logger.info(f"📊 找到 {len(paper_images)} 篇论文的图片:")
    logger.info("")
    
    for i, (title, info) in enumerate(paper_images.items(), 1):
        best_img = info['best']
        logger.info(f"[{i}] {title[:60]}")
        logger.info(f"    📁 {info['count']} 张图片")
        logger.info(f"    ⭐ 推荐: {best_img['name']}")
        logger.info("")
    
    logger.info("=" * 70)
    logger.info("🔧 操作步骤:")
    logger.info("=" * 70)
    logger.info("1️⃣  正在打开 Notion 数据库...")
    
    # 打开Notion数据库
    open_notion_database(database_id)
    time.sleep(1)
    
    logger.info("2️⃣  正在打开图片文件夹...")
    
    # 打开图片文件夹
    open_file_manager(images_dir)
    time.sleep(1)
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("💡 手动上传指南:")
    logger.info("=" * 70)
    logger.info("1. Notion数据库已在浏览器中打开")
    logger.info("2. 图片文件夹已打开")
    logger.info("3. 找到对应的论文页面（根据标题匹配）")
    logger.info("4. 拖拽推荐的图片（通常是 *_fig1_*.png）")
    logger.info("5. 放到 'Framework Image' 字段中")
    logger.info("")
    logger.info("📌 提示:")
    logger.info("   • 每篇论文的图片文件名都包含论文标题")
    logger.info("   • 优先上传 fig1，通常是整体框架图")
    logger.info("   • 如果 Framework Image 已有内容，可跳过")
    logger.info("   • 也可以拖拽到页面正文中显示所有图片")
    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ 准备完成！现在可以开始手动上传了")
    logger.info("=" * 70)
    
    # 显示详细的图片列表
    logger.info("")
    logger.info("📋 详细图片列表:")
    logger.info("")
    
    for i, (title, info) in enumerate(paper_images.items(), 1):
        logger.info(f"[{i}] {title}")
        for j, img in enumerate(info['all'], 1):
            marker = "⭐" if j == 1 else "  "
            logger.info(f"    {marker} [{j}] {img['name']}")
        logger.info("")


if __name__ == "__main__":
    main()
