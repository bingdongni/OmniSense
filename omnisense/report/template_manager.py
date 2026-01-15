#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report Template Manager

负责管理报告模板的加载、解析和选择
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger


class TemplateSection:
    """模板章节"""

    def __init__(
        self,
        level: int,
        title: str,
        content: str = "",
        children: Optional[List['TemplateSection']] = None
    ):
        self.level = level
        self.title = title
        self.content = content
        self.children = children or []

    def __repr__(self):
        return f"<TemplateSection level={self.level} title='{self.title}'>"


class ReportTemplate:
    """报告模板"""

    def __init__(
        self,
        name: str,
        title: str,
        description: str,
        sections: List[TemplateSection],
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.title = title
        self.description = description
        self.sections = sections
        self.metadata = metadata or {}

    def __repr__(self):
        return f"<ReportTemplate name='{self.name}' sections={len(self.sections)}>"

    def get_section_count(self) -> int:
        """获取章节总数（包括子章节）"""
        def count_sections(sections: List[TemplateSection]) -> int:
            count = len(sections)
            for section in sections:
                count += count_sections(section.children)
            return count

        return count_sections(self.sections)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        def section_to_dict(section: TemplateSection) -> Dict[str, Any]:
            return {
                'level': section.level,
                'title': section.title,
                'content': section.content,
                'children': [section_to_dict(child) for child in section.children]
            }

        return {
            'name': self.name,
            'title': self.title,
            'description': self.description,
            'sections': [section_to_dict(s) for s in self.sections],
            'metadata': self.metadata,
        }


class TemplateManager:
    """模板管理器"""

    def __init__(self, template_dir: Optional[Path] = None):
        """
        初始化模板管理器

        Args:
            template_dir: 模板目录路径
        """
        if template_dir is None:
            # 默认模板目录
            current_file = Path(__file__)
            self.template_dir = current_file.parent / "templates"
        else:
            self.template_dir = Path(template_dir)

        self.templates: Dict[str, ReportTemplate] = {}
        self._load_templates()

    def _load_templates(self):
        """加载所有模板"""
        if not self.template_dir.exists():
            logger.warning(f"Template directory not found: {self.template_dir}")
            return

        md_files = list(self.template_dir.glob("*.md"))
        logger.info(f"Found {len(md_files)} template files in {self.template_dir}")

        for md_file in md_files:
            try:
                template = self._parse_template(md_file)
                self.templates[template.name] = template
                logger.success(f"Loaded template: {template.name}")
            except Exception as e:
                logger.error(f"Failed to load template {md_file.name}: {e}")

    def _parse_template(self, md_file: Path) -> ReportTemplate:
        """
        解析Markdown模板文件

        Args:
            md_file: Markdown文件路径

        Returns:
            ReportTemplate对象
        """
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取标题（第一个# heading）
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else md_file.stem

        # 解析章节结构
        sections = self._parse_sections(content)

        # 生成描述
        description = self._generate_description(sections)

        template = ReportTemplate(
            name=md_file.stem,
            title=title,
            description=description,
            sections=sections,
            metadata={
                'source_file': str(md_file),
                'section_count': len(sections),
            }
        )

        return template

    def _parse_sections(self, content: str) -> List[TemplateSection]:
        """
        解析Markdown内容为章节树

        Args:
            content: Markdown内容

        Returns:
            章节列表
        """
        # 分割为行
        lines = content.split('\n')

        # 解析所有标题行
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
        sections_flat = []

        current_content = []
        for line in lines:
            match = heading_pattern.match(line)
            if match:
                # 保存前一个章节的内容
                if sections_flat:
                    sections_flat[-1]['content'] = '\n'.join(current_content).strip()
                    current_content = []

                # 添加新章节
                level = len(match.group(1))
                title = match.group(2).strip()

                sections_flat.append({
                    'level': level,
                    'title': title,
                    'content': '',
                })
            else:
                current_content.append(line)

        # 保存最后一个章节的内容
        if sections_flat:
            sections_flat[-1]['content'] = '\n'.join(current_content).strip()

        # 构建层级结构
        sections_tree = self._build_section_tree(sections_flat)

        return sections_tree

    def _build_section_tree(
        self,
        sections_flat: List[Dict[str, Any]]
    ) -> List[TemplateSection]:
        """
        将扁平章节列表构建为树形结构

        Args:
            sections_flat: 扁平章节列表

        Returns:
            树形章节列表
        """
        if not sections_flat:
            return []

        root_sections = []
        stack: List[TemplateSection] = []

        for section_data in sections_flat:
            section = TemplateSection(
                level=section_data['level'],
                title=section_data['title'],
                content=section_data['content'],
            )

            # 找到正确的父节点
            while stack and stack[-1].level >= section.level:
                stack.pop()

            if not stack:
                # 顶层章节
                root_sections.append(section)
            else:
                # 添加为子章节
                stack[-1].children.append(section)

            stack.append(section)

        return root_sections

    def _generate_description(self, sections: List[TemplateSection]) -> str:
        """
        生成模板描述

        Args:
            sections: 章节列表

        Returns:
            描述文本
        """
        section_titles = []

        def collect_titles(secs: List[TemplateSection]):
            for sec in secs:
                section_titles.append(sec.title)
                collect_titles(sec.children)

        collect_titles(sections)

        # 取前5个标题
        main_sections = section_titles[:5]
        description = "包含：" + "、".join(main_sections)

        if len(section_titles) > 5:
            description += f" 等{len(section_titles)}个章节"

        return description

    def get_template(self, name: str) -> Optional[ReportTemplate]:
        """
        获取模板

        Args:
            name: 模板名称

        Returns:
            模板对象，如果不存在返回None
        """
        return self.templates.get(name)

    def list_templates(self) -> List[Dict[str, str]]:
        """
        列出所有模板

        Returns:
            模板列表（包括name, title, description）
        """
        return [
            {
                'name': template.name,
                'title': template.title,
                'description': template.description,
                'section_count': template.get_section_count(),
            }
            for template in self.templates.values()
        ]

    def select_template(
        self,
        query: str,
        data_summary: Optional[Dict[str, Any]] = None,
        llm_provider: Optional[Any] = None
    ) -> str:
        """
        智能选择模板

        Args:
            query: 用户查询/需求
            data_summary: 数据摘要
            llm_provider: LLM提供者（用于智能选择）

        Returns:
            选择的模板名称
        """
        # 基于关键词的简单匹配
        query_lower = query.lower()

        # 电商相关
        if any(keyword in query_lower for keyword in [
            '电商', '淘宝', '天猫', '京东', '拼多多', 'amazon',
            '商品', '购物', '销量', '价格'
        ]):
            return 'ecommerce_analysis'

        # 社交媒体相关
        if any(keyword in query_lower for keyword in [
            '社交', '微博', '抖音', '小红书', 'twitter', 'facebook',
            '舆情', '声量', '传播', 'kol'
        ]):
            return 'social_media_report'

        # 学术相关
        if any(keyword in query_lower for keyword in [
            '学术', '论文', '文献', '综述', 'scholar', 'research',
            '研究', '期刊', '引用'
        ]):
            return 'academic_review'

        # 品牌声誉相关
        if any(keyword in query_lower for keyword in [
            '品牌', '声誉', '口碑', '形象', '危机',
            '监测', '负面', '正面'
        ]):
            return 'brand_reputation'

        # 默认模板
        logger.info(f"No specific template matched for query: {query}, using default")
        return 'default'

    async def select_template_with_llm(
        self,
        query: str,
        data_summary: Dict[str, Any],
        llm
    ) -> Tuple[str, str]:
        """
        使用LLM智能选择模板

        Args:
            query: 用户查询
            data_summary: 数据摘要
            llm: LLM实例

        Returns:
            (模板名称, 选择理由)
        """
        # 构建提示
        template_list = self.list_templates()
        templates_desc = "\n".join([
            f"{i + 1}. {t['name']}: {t['title']} - {t['description']}"
            for i, t in enumerate(template_list)
        ])

        prompt = f"""根据用户需求和数据摘要，选择最合适的报告模板。

用户需求：{query}

数据摘要：
{data_summary}

可用模板：
{templates_desc}

请选择最合适的模板，并说明理由。只返回模板名称和理由，格式如下：
模板：<template_name>
理由：<reason>
"""

        try:
            response = await llm.apredict(prompt)

            # 解析响应
            template_match = re.search(r'模板[：:]\s*(\w+)', response)
            reason_match = re.search(r'理由[：:]\s*(.+)', response, re.DOTALL)

            if template_match:
                template_name = template_match.group(1)
                reason = reason_match.group(1).strip() if reason_match else "LLM选择"

                # 验证模板存在
                if template_name in self.templates:
                    logger.info(f"LLM selected template: {template_name}")
                    return template_name, reason
                else:
                    logger.warning(f"LLM selected invalid template: {template_name}")

        except Exception as e:
            logger.error(f"LLM template selection failed: {e}")

        # 降级到基于规则的选择
        template_name = self.select_template(query, data_summary)
        return template_name, "基于规则的自动选择"

    def get_section_outline(self, template_name: str) -> List[Dict[str, Any]]:
        """
        获取模板的章节大纲

        Args:
            template_name: 模板名称

        Returns:
            章节大纲列表
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        outline = []

        def build_outline(
            sections: List[TemplateSection],
            parent_number: str = ""
        ):
            for i, section in enumerate(sections, 1):
                number = f"{parent_number}{i}" if parent_number else str(i)
                outline.append({
                    'number': number,
                    'level': section.level,
                    'title': section.title,
                    'content_hint': section.content[:100] if section.content else "",
                })

                if section.children:
                    build_outline(section.children, f"{number}.")

        build_outline(template.sections)
        return outline

    def customize_template(
        self,
        template_name: str,
        customizations: Dict[str, Any]
    ) -> ReportTemplate:
        """
        自定义模板

        Args:
            template_name: 基础模板名称
            customizations: 自定义配置

        Returns:
            自定义后的模板
        """
        base_template = self.get_template(template_name)
        if not base_template:
            raise ValueError(f"Template not found: {template_name}")

        # 创建副本
        custom_template = ReportTemplate(
            name=f"{template_name}_custom",
            title=customizations.get('title', base_template.title),
            description=customizations.get('description', base_template.description),
            sections=base_template.sections,  # 可以进一步自定义章节
            metadata=base_template.metadata.copy()
        )

        custom_template.metadata['customized'] = True
        custom_template.metadata['base_template'] = template_name

        return custom_template
