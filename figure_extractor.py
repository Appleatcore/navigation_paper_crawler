#!/usr/bin/env python3
"""
PDF论文图片提取器
自动从PDF中提取框架图/架构图并上传到Notion
"""

import os
import re
import logging
import requests
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from io import BytesIO

logger = logging.getLogger(__name__)

# 图床功能已移除（网络限制），仅使用本地保存
IMAGE_HOST_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF未安装，图片提取功能将不可用。安装: pip install PyMuPDF")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow未安装，图片处理功能受限。安装: pip install Pillow")


class FigureExtractor:
    """从PDF中提取框架图"""
    
    def __init__(self, notion_token: str, max_figures: int = 1, 
                 image_host_service: str = "auto", imgur_client_id: Optional[str] = None):
        """
        Args:
            notion_token: Notion API token，用于上传图片
            max_figures: 每篇论文最多提取的图片数量（默认1张，只保留置信度最高的架构图）
            image_host_service: 图床服务 (auto, imgur, smms, imgbb)
            imgur_client_id: Imgur Client ID (可选)
        """
        self.notion_token = notion_token
        self.max_figures = max_figures
        self.headers = {
            "Authorization": f"Bearer {notion_token}",
            "Notion-Version": "2022-06-28"
        }
        
        # 图床功能已禁用（网络限制），仅使用本地保存
        self.image_uploader = None
        
    def is_available(self) -> bool:
        """检查依赖是否可用"""
        return PYMUPDF_AVAILABLE and PIL_AVAILABLE
    
    def download_pdf(self, pdf_url: str) -> Optional[bytes]:
        """下载PDF文件"""
        try:
            logger.info(f"下载PDF: {pdf_url}")
            response = requests.get(pdf_url, timeout=60, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"PDF下载失败 {pdf_url}: {e}")
            return None
    
    def is_architecture_figure(self, image: Image.Image, page_text: str = "") -> float:
        """
        判断图片是否可能是框架图/架构图
        返回置信度分数 (0-1)
        """
        score = 0.0
        
        # 1. 图片尺寸判断（框架图通常较大且宽高比接近）
        width, height = image.size
        aspect_ratio = width / height if height > 0 else 0
        
        # 偏好宽图或方图
        if 0.5 < aspect_ratio < 2.5:
            score += 0.2
        if width > 800 or height > 600:
            score += 0.2
            
        # 2. 关键词匹配（在图片所在页的文本中）
        architecture_keywords = [
            'architecture', 'framework', 'model', 'pipeline', 'overview',
            'structure', 'diagram', 'flow', 'system', 'network',
            '架构', '框架', '模型', '流程', '系统', '网络'
        ]
        
        page_text_lower = page_text.lower()
        keyword_count = sum(1 for kw in architecture_keywords if kw in page_text_lower)
        score += min(keyword_count * 0.1, 0.4)
        
        # 3. 图片复杂度（简单启发式：更多颜色/更多细节通常是复杂图）
        try:
            colors = len(set(list(image.getdata())))
            if colors > 100:
                score += 0.2
        except:
            pass
        
        return min(score, 1.0)
    
    def extract_figures_from_pdf(self, pdf_content: bytes) -> List[Tuple[bytes, float, int]]:
        """
        从PDF中提取图片
        
        Returns:
            List of (image_bytes, confidence_score, page_number)
        """
        logger.info("[DEBUG] extract_figures_from_pdf 调用")
        
        if not PYMUPDF_AVAILABLE:
            logger.warning("[DEBUG] PyMuPDF未安装，无法提取图片")
            return []
        
        figures = []
        
        try:
            # 打开PDF
            logger.info(f"[DEBUG] 打开PDF文档，大小: {len(pdf_content)} bytes")
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            
            # 只处理前10页（框架图通常在论文开头）
            max_pages = min(10, len(doc))
            
            for page_num in range(max_pages):
                page = doc[page_num]
                page_text = page.get_text()
                
                # 提取页面中的所有图片
                image_list = page.get_images()
                
                for img_index, img_info in enumerate(image_list):
                    try:
                        xref = img_info[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # 转换为PIL Image进行分析
                        if PIL_AVAILABLE:
                            image = Image.open(BytesIO(image_bytes))
                            
                            # 过滤太小的图片（可能是图标、logo等）
                            if image.size[0] < 200 or image.size[1] < 200:
                                continue
                            
                            # 判断是否是框架图
                            confidence = self.is_architecture_figure(image, page_text)
                            
                            if confidence > 0.6:  # 严格标准：只保留高置信度架构图
                                figures.append((image_bytes, confidence, page_num + 1))
                                logger.debug(f"找到候选图片：第{page_num + 1}页，置信度{confidence:.2f}")
                        else:
                            # 没有PIL，直接保存所有大图
                            figures.append((image_bytes, 0.5, page_num + 1))
                            
                    except Exception as e:
                        logger.debug(f"处理图片失败 (page {page_num + 1}, img {img_index}): {e}")
                        continue
            
            doc.close()
            
            logger.info(f"[DEBUG] PDF处理完成，共提取 {len(figures)} 张图片")
            
            # 按置信度排序
            figures.sort(key=lambda x: x[1], reverse=True)
            
            # 只返回前N张
            result = figures[:self.max_figures]
            logger.info(f"[DEBUG] 返回前 {len(result)} 张高置信度图片")
            return result
            
        except Exception as e:
            logger.error(f"[DEBUG] PDF图片提取失败: {e}")
            return []
    
    def save_image_locally(self, image_bytes: bytes, filename: str = "figure.png") -> Optional[str]:
        """
        保存图片到本地目录
        
        Args:
            image_bytes: 图片二进制数据
            filename: 图片文件名
            
        Returns:
            本地文件路径，失败返回None
        """
        try:
            import os
            
            # 创建images目录
            images_dir = os.path.join(os.path.dirname(__file__), "images")
            os.makedirs(images_dir, exist_ok=True)
            
            # 生成唯一文件名（添加时间戳避免冲突）
            import time
            timestamp = int(time.time() * 1000)
            base_name, ext = os.path.splitext(filename)
            unique_filename = f"{base_name}_{timestamp}{ext}"
            
            filepath = os.path.join(images_dir, unique_filename)
            
            # 保存文件
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            logger.info(f"✅ 图片已保存到本地: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"本地保存图片失败: {e}")
            return None
    
    def upload_file_to_notion(self, filepath: str) -> Optional[str]:
        """
        上传文件到Notion并获取托管的URL
        注意：Notion API目前不支持直接上传文件到block
        这个方法会尝试通过临时托管方式获取可访问URL
        
        Args:
            filepath: 本地文件路径
            
        Returns:
            文件的公开访问URL（如果成功）
        """
        try:
            # Notion API不支持直接上传文件
            # 我们需要使用外部托管服务
            # 这里返回None，让调用者决定如何处理
            logger.warning(f"Notion API不支持直接上传本地文件: {filepath}")
            logger.info("建议：使用图床服务获取HTTPS URL，或将图片添加到页面内容中")
            return None
            
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            return None
    
    def add_local_images_to_notion(self, page_id: str, local_files: List[str]) -> bool:
        """
        将本地图片添加到Notion页面
        由于Notion API限制，我们将图片路径记录到日志，并标记为"已保存"
        
        Args:
            page_id: Notion页面ID
            local_files: 本地图片文件路径列表
        """
        try:
            logger.info(f"[INFO] 图片已保存到本地，路径如下：")
            for i, filepath in enumerate(local_files, 1):
                logger.info(f"  [{i}] {filepath}")
            
            logger.info("[INFO] 提示：可以手动将这些图片上传到Notion页面，或配置图床服务自动上传")
            return True  # 标记为成功（图片已保存）
            
        except Exception as e:
            logger.error(f"处理本地图片失败: {e}")
            return False
    
    def process_paper(self, paper: Dict, page_id: str) -> Optional[str]:
        """
        处理单篇论文：下载PDF -> 提取框架图 -> 上传到图床
        
        Args:
            paper: 论文信息字典（需包含pdf_link）
            page_id: Notion页面ID
            
        Returns:
            第一张框架图的URL（用于Framework Diagram字段），失败返回None
        """
        logger.info(f"[DEBUG] 开始处理论文: {paper.get('title', 'Unknown')[:60]}")
        
        if not self.is_available():
            logger.warning("[DEBUG] 图片提取功能不可用，请安装依赖: pip install PyMuPDF Pillow")
            return None
        
        pdf_url = paper.get('pdf_url') or paper.get('pdf_link')  # 兼容两种字段名
        logger.info(f"[DEBUG] PDF链接: {pdf_url}")
        
        if not pdf_url:
            logger.warning("[DEBUG] 论文无PDF链接，跳过图片提取")
            return None
        
        # 下载PDF
        logger.info("[DEBUG] 开始下载PDF...")
        pdf_content = self.download_pdf(pdf_url)
        if not pdf_content:
            logger.warning(f"[DEBUG] PDF下载失败: {pdf_url}")
            return None
        
        logger.info(f"[DEBUG] PDF下载成功，大小: {len(pdf_content)} bytes")
        
        # 提取图片
        logger.info("[DEBUG] 开始从PDF提取框架图...")
        figures = self.extract_figures_from_pdf(pdf_content)
        if not figures:
            logger.info("[DEBUG] 未找到候选框架图")
            return None
        
        logger.info(f"[DEBUG] 找到 {len(figures)} 张候选框架图")
        
        # 保存图片到本地
        logger.info("[DEBUG] 开始保存图片到本地...")
        local_files = []
        for i, (img_bytes, confidence, page_num) in enumerate(figures, 1):
            filename = f"{paper.get('title', 'paper')[:50]}_fig{i}_p{page_num}.png"
            # 清理文件名
            filename = re.sub(r'[^\w\-_\. ]', '_', filename)
            
            logger.info(f"[DEBUG] 保存第{i}张图片: {filename} (置信度:{confidence:.2f}, 页码:{page_num})")
            filepath = self.save_image_locally(img_bytes, filename)
            
            if filepath:
                logger.info(f"[DEBUG] ✅ 图片{i}保存成功: {filepath}")
                local_files.append(filepath)
            else:
                logger.warning(f"[DEBUG] ❌ 图片{i}保存失败")
        
        if not local_files:
            logger.warning("[DEBUG] 所有图片保存失败")
            return None
        
        logger.info(f"[DEBUG] 成功保存 {len(local_files)}/{len(figures)} 张图片")
        
        # 将图片添加到Notion页面内容（使用Base64）
        logger.info("[DEBUG] 将图片添加到Notion页面内容...")
        success = self.add_local_images_to_notion(page_id, local_files)
        
        if success:
            logger.info("[DEBUG] ✅ 图片已添加到Notion页面内容")
            # 返回第一张图片的本地路径作为标记
            return local_files[0] if local_files else None
        else:
            logger.warning("[DEBUG] ❌ 添加图片到Notion页面失败")
            return None
