#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document IR Schema定义

定义报告中间表示的数据结构
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator


class BlockType(str, Enum):
    """块类型枚举"""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    CHART = "chart"
    CODE = "code"
    QUOTE = "quote"
    DIVIDER = "divider"


class MarkType(str, Enum):
    """标记类型枚举"""
    BOLD = "bold"
    ITALIC = "italic"
    CODE = "code"
    LINK = "link"
    HIGHLIGHT = "highlight"


class MarkIR(BaseModel):
    """文本标记"""
    type: MarkType
    attrs: Optional[Dict[str, Any]] = None


class TextIR(BaseModel):
    """文本节点"""
    text: str
    marks: List[MarkIR] = Field(default_factory=list)


class ChartIR(BaseModel):
    """图表IR"""
    type: str = Field(..., description="图表类型: bar, line, pie, scatter等")
    data: Dict[str, Any] = Field(..., description="图表数据")
    layout: Optional[Dict[str, Any]] = Field(default=None, description="图表布局配置")
    config: Optional[Dict[str, Any]] = Field(default=None, description="图表配置")

    @validator('type')
    def validate_chart_type(cls, v):
        """验证图表类型"""
        valid_types = ['bar', 'line', 'pie', 'scatter', 'heatmap', 'box',
                      'histogram', 'radar', 'funnel', 'sankey', 'treemap']
        if v not in valid_types:
            raise ValueError(f"Unsupported chart type: {v}. Valid types: {valid_types}")
        return v

    @validator('data')
    def validate_chart_data(cls, v):
        """验证图表数据结构"""
        if not isinstance(v, dict):
            raise ValueError("Chart data must be a dictionary")

        # 基本验证：至少要有数据
        if 'x' not in v and 'values' not in v and 'labels' not in v:
            raise ValueError("Chart data must contain 'x', 'values', or 'labels'")

        return v


class BlockIR(BaseModel):
    """块级元素IR"""
    type: BlockType
    content: Optional[List[Union[TextIR, 'BlockIR', ChartIR]]] = Field(default_factory=list)
    attrs: Optional[Dict[str, Any]] = Field(default=None)

    @validator('attrs')
    def validate_attrs(cls, v, values):
        """验证属性"""
        block_type = values.get('type')

        if block_type == BlockType.HEADING:
            if v is None or 'level' not in v:
                raise ValueError("Heading block must have 'level' attribute")
            if not (1 <= v['level'] <= 6):
                raise ValueError("Heading level must be between 1 and 6")

        if block_type == BlockType.LIST:
            if v is None or 'ordered' not in v:
                raise ValueError("List block must have 'ordered' attribute")

        if block_type == BlockType.TABLE:
            if v is None or 'headers' not in v:
                raise ValueError("Table block must have 'headers' attribute")

        return v

    class Config:
        """Pydantic配置"""
        arbitrary_types_allowed = True


class ChapterIR(BaseModel):
    """章节IR"""
    id: str = Field(..., description="章节唯一标识")
    title: str = Field(..., description="章节标题")
    level: int = Field(1, ge=1, le=3, description="章节层级 (1-3)")
    content: List[BlockIR] = Field(default_factory=list, description="章节内容块")
    children: List['ChapterIR'] = Field(default_factory=list, description="子章节")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="章节元数据")

    @validator('id')
    def validate_id(cls, v):
        """验证章节ID"""
        if not v or not v.strip():
            raise ValueError("Chapter ID cannot be empty")
        # ID格式：chapter-1, chapter-1-1, chapter-1-2-1等
        parts = v.split('-')
        if len(parts) < 2 or parts[0] != 'chapter':
            raise ValueError("Chapter ID must follow format: chapter-{number}")
        return v

    @validator('title')
    def validate_title(cls, v):
        """验证标题"""
        if not v or not v.strip():
            raise ValueError("Chapter title cannot be empty")
        if len(v) > 200:
            raise ValueError("Chapter title too long (max 200 characters)")
        return v.strip()

    def get_all_charts(self) -> List[ChartIR]:
        """递归获取所有图表"""
        charts = []

        def extract_charts(blocks: List[BlockIR]):
            for block in blocks:
                if block.type == BlockType.CHART and isinstance(block.content, list):
                    for item in block.content:
                        if isinstance(item, ChartIR):
                            charts.append(item)
                if isinstance(block.content, list):
                    extract_charts(block.content)

        extract_charts(self.content)

        # 递归处理子章节
        for child in self.children:
            charts.extend(child.get_all_charts())

        return charts

    def count_words(self) -> int:
        """统计字数"""
        word_count = 0

        def count_text(blocks: List[BlockIR]):
            nonlocal word_count
            for block in blocks:
                if isinstance(block.content, list):
                    for item in block.content:
                        if isinstance(item, TextIR):
                            # 中文按字符数，英文按单词数
                            text = item.text
                            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
                            english_words = len([w for w in text.split() if w.isalpha()])
                            word_count += chinese_chars + english_words
                    count_text(block.content)

        count_text(self.content)

        # 递归处理子章节
        for child in self.children:
            word_count += child.count_words()

        return word_count


class DocumentIR(BaseModel):
    """文档IR（完整报告）"""
    title: str = Field(..., description="文档标题")
    subtitle: Optional[str] = Field(None, description="副标题")
    authors: List[str] = Field(default_factory=list, description="作者列表")
    date: Optional[str] = Field(None, description="生成日期")
    template: str = Field("default", description="使用的模板名称")
    chapters: List[ChapterIR] = Field(default_factory=list, description="章节列表")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="文档元数据")
    toc: Optional[List[Dict[str, Any]]] = Field(default=None, description="目录结构")

    @validator('title')
    def validate_title(cls, v):
        """验证文档标题"""
        if not v or not v.strip():
            raise ValueError("Document title cannot be empty")
        if len(v) > 300:
            raise ValueError("Document title too long (max 300 characters)")
        return v.strip()

    @validator('chapters')
    def validate_chapters(cls, v):
        """验证章节列表"""
        if not v:
            raise ValueError("Document must have at least one chapter")

        # 验证章节ID唯一性
        chapter_ids = set()

        def check_ids(chapters: List[ChapterIR]):
            for chapter in chapters:
                if chapter.id in chapter_ids:
                    raise ValueError(f"Duplicate chapter ID: {chapter.id}")
                chapter_ids.add(chapter.id)
                if chapter.children:
                    check_ids(chapter.children)

        check_ids(v)
        return v

    def generate_toc(self) -> List[Dict[str, Any]]:
        """生成目录"""
        toc = []

        def build_toc(chapters: List[ChapterIR], parent_number: str = ""):
            for i, chapter in enumerate(chapters, 1):
                number = f"{parent_number}{i}" if parent_number else str(i)
                toc_item = {
                    "id": chapter.id,
                    "number": number,
                    "title": chapter.title,
                    "level": chapter.level,
                    "word_count": chapter.count_words(),
                }

                if chapter.children:
                    toc_item["children"] = []
                    build_toc(chapter.children, f"{number}.")

                toc.append(toc_item)

        build_toc(self.chapters)
        self.toc = toc
        return toc

    def get_all_charts(self) -> List[ChartIR]:
        """获取所有图表"""
        charts = []
        for chapter in self.chapters:
            charts.extend(chapter.get_all_charts())
        return charts

    def count_total_words(self) -> int:
        """统计总字数"""
        return sum(chapter.count_words() for chapter in self.chapters)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict(exclude_none=True)

    def to_json(self, **kwargs) -> str:
        """转换为JSON"""
        return self.json(exclude_none=True, ensure_ascii=False, **kwargs)


# 更新forward references
ChapterIR.update_forward_refs()
BlockIR.update_forward_refs()
