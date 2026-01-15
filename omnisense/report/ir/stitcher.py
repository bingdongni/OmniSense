#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document IR Stitcher (装订器)

负责将生成的章节装订成完整文档，补齐锚点和元数据
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .schema import DocumentIR, ChapterIR, BlockIR, BlockType


class IRStitcher:
    """IR装订器"""

    def __init__(self):
        """初始化装订器"""
        self.chapter_counter = 0

    def stitch_document(
        self,
        chapters: List[ChapterIR],
        title: str,
        subtitle: Optional[str] = None,
        authors: Optional[List[str]] = None,
        template: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentIR:
        """
        装订章节为完整文档

        Args:
            chapters: 章节列表
            title: 文档标题
            subtitle: 副标题
            authors: 作者列表
            template: 模板名称
            metadata: 元数据

        Returns:
            完整的DocumentIR
        """
        if not chapters:
            raise ValueError("Cannot stitch empty chapter list")

        logger.info(f"Stitching {len(chapters)} chapters into document: {title}")

        # 重置计数器
        self.chapter_counter = 0

        # 修复章节ID和锚点
        fixed_chapters = []
        for i, chapter in enumerate(chapters, 1):
            fixed_chapter = self._fix_chapter_ids(chapter, str(i))
            fixed_chapters.append(fixed_chapter)

        # 创建文档
        doc = DocumentIR(
            title=title,
            subtitle=subtitle,
            authors=authors or ["OmniSense AI"],
            date=datetime.now().strftime("%Y-%m-%d"),
            template=template,
            chapters=fixed_chapters,
            metadata=metadata or {},
        )

        # 生成目录
        doc.generate_toc()

        # 添加统计信息到元数据
        if doc.metadata is None:
            doc.metadata = {}

        doc.metadata.update({
            'total_chapters': len(fixed_chapters),
            'total_words': doc.count_total_words(),
            'total_charts': len(doc.get_all_charts()),
            'generated_at': datetime.now().isoformat(),
        })

        logger.success(
            f"Document stitched: {len(fixed_chapters)} chapters, "
            f"{doc.metadata['total_words']} words, "
            f"{doc.metadata['total_charts']} charts"
        )

        return doc

    def _fix_chapter_ids(self, chapter: ChapterIR, number: str) -> ChapterIR:
        """
        修复章节ID和锚点

        Args:
            chapter: 章节
            number: 章节编号 (如 "1", "1.1", "2.3.1")

        Returns:
            修复后的章节
        """
        # 生成标准ID
        chapter_id = f"chapter-{number.replace('.', '-')}"

        # 修复子章节
        fixed_children = []
        for i, child in enumerate(chapter.children, 1):
            child_number = f"{number}.{i}"
            fixed_child = self._fix_chapter_ids(child, child_number)
            fixed_children.append(fixed_child)

        # 为内容块添加锚点
        fixed_content = self._add_block_anchors(chapter.content, chapter_id)

        # 更新元数据
        if chapter.metadata is None:
            chapter.metadata = {}

        chapter.metadata.update({
            'number': number,
            'anchor': chapter_id,
            'word_count': chapter.count_words(),
        })

        # 创建新章节（保持不可变性）
        return ChapterIR(
            id=chapter_id,
            title=chapter.title,
            level=chapter.level,
            content=fixed_content,
            children=fixed_children,
            metadata=chapter.metadata,
        )

    def _add_block_anchors(
        self,
        blocks: List[BlockIR],
        chapter_id: str
    ) -> List[BlockIR]:
        """为块添加锚点"""
        fixed_blocks = []

        for i, block in enumerate(blocks):
            # 为标题块添加锚点
            if block.type == BlockType.HEADING:
                if block.attrs is None:
                    block.attrs = {}

                # 生成锚点ID
                anchor = f"{chapter_id}-heading-{i}"
                block.attrs['id'] = anchor

            # 为图表块添加锚点
            elif block.type == BlockType.CHART:
                if block.attrs is None:
                    block.attrs = {}

                anchor = f"{chapter_id}-chart-{i}"
                block.attrs['id'] = anchor

            # 为表格块添加锚点
            elif block.type == BlockType.TABLE:
                if block.attrs is None:
                    block.attrs = {}

                anchor = f"{chapter_id}-table-{i}"
                block.attrs['id'] = anchor

            # 递归处理嵌套块
            if block.content and isinstance(block.content, list):
                nested_fixed = []
                for item in block.content:
                    if isinstance(item, BlockIR):
                        nested_fixed.extend(
                            self._add_block_anchors([item], chapter_id)
                        )
                    else:
                        nested_fixed.append(item)
                block.content = nested_fixed

            fixed_blocks.append(block)

        return fixed_blocks

    def merge_chapters(
        self,
        chapters: List[ChapterIR],
        merge_level: int = 2
    ) -> List[ChapterIR]:
        """
        合并章节（将低层级章节合并到父章节）

        Args:
            chapters: 章节列表
            merge_level: 合并层级，低于此层级的章节将被合并

        Returns:
            合并后的章节列表
        """
        merged = []

        for chapter in chapters:
            if chapter.level < merge_level:
                # 保持当前章节，递归合并子章节
                merged_children = self.merge_chapters(chapter.children, merge_level)
                merged.append(
                    ChapterIR(
                        id=chapter.id,
                        title=chapter.title,
                        level=chapter.level,
                        content=chapter.content,
                        children=merged_children,
                        metadata=chapter.metadata,
                    )
                )
            else:
                # 合并到内容中
                # 将标题添加为heading块
                title_block = BlockIR(
                    type=BlockType.HEADING,
                    content=[],
                    attrs={'level': min(chapter.level + 1, 6)}
                )

                # 合并内容
                merged_content = [title_block] + chapter.content

                # 递归处理子章节
                for child in chapter.children:
                    merged_content.extend(child.content)

                # 如果merged为空，创建新章节
                if not merged:
                    merged.append(chapter)
                else:
                    # 将内容添加到最后一个章节
                    last_chapter = merged[-1]
                    last_chapter.content.extend(merged_content)

        return merged

    def split_long_chapter(
        self,
        chapter: ChapterIR,
        max_words: int = 5000
    ) -> List[ChapterIR]:
        """
        拆分过长的章节

        Args:
            chapter: 章节
            max_words: 最大字数

        Returns:
            拆分后的章节列表
        """
        word_count = chapter.count_words()

        if word_count <= max_words:
            return [chapter]

        logger.warning(
            f"Chapter '{chapter.title}' too long ({word_count} words), "
            f"splitting..."
        )

        # 简单策略：按块拆分
        split_chapters = []
        current_content = []
        current_words = 0
        part_number = 1

        for block in chapter.content:
            block_words = self._count_block_words(block)

            if current_words + block_words > max_words and current_content:
                # 创建新章节
                split_chapter = ChapterIR(
                    id=f"{chapter.id}-part{part_number}",
                    title=f"{chapter.title} (Part {part_number})",
                    level=chapter.level,
                    content=current_content,
                    children=[],
                    metadata=chapter.metadata.copy() if chapter.metadata else {}
                )
                split_chapters.append(split_chapter)

                # 重置
                current_content = [block]
                current_words = block_words
                part_number += 1
            else:
                current_content.append(block)
                current_words += block_words

        # 添加最后一部分
        if current_content:
            split_chapter = ChapterIR(
                id=f"{chapter.id}-part{part_number}",
                title=f"{chapter.title} (Part {part_number})",
                level=chapter.level,
                content=current_content,
                children=[],
                metadata=chapter.metadata.copy() if chapter.metadata else {}
            )
            split_chapters.append(split_chapter)

        logger.info(f"Split into {len(split_chapters)} parts")
        return split_chapters

    def _count_block_words(self, block: BlockIR) -> int:
        """统计块字数"""
        word_count = 0

        if block.content:
            for item in block.content:
                if hasattr(item, 'text'):
                    text = item.text
                    # 中文字符数 + 英文单词数
                    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
                    english_words = len([w for w in text.split() if w.isalpha()])
                    word_count += chinese_chars + english_words
                elif isinstance(item, BlockIR):
                    word_count += self._count_block_words(item)

        return word_count

    def add_cross_references(self, doc: DocumentIR) -> DocumentIR:
        """
        添加交叉引用（章节引用、图表引用）

        Args:
            doc: 文档IR

        Returns:
            添加交叉引用后的文档
        """
        # 构建锚点映射
        anchor_map = {}

        def collect_anchors(chapters: List[ChapterIR]):
            for chapter in chapters:
                anchor_map[chapter.id] = {
                    'title': chapter.title,
                    'type': 'chapter'
                }

                # 收集块锚点
                for block in chapter.content:
                    if block.attrs and 'id' in block.attrs:
                        anchor_map[block.attrs['id']] = {
                            'title': f"{chapter.title} - {block.type.value}",
                            'type': block.type.value,
                            'chapter': chapter.id
                        }

                # 递归
                collect_anchors(chapter.children)

        collect_anchors(doc.chapters)

        # 将锚点映射保存到元数据
        if doc.metadata is None:
            doc.metadata = {}

        doc.metadata['anchor_map'] = anchor_map
        logger.info(f"Added {len(anchor_map)} cross-references")

        return doc
