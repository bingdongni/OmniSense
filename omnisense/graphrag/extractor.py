#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entity and Relation Extractor

使用Transformers NER模型进行实体识别和关系抽取
"""

import re
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from loguru import logger

try:
    from transformers import (
        AutoTokenizer,
        AutoModelForTokenClassification,
        AutoModelForSequenceClassification,
        pipeline
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("transformers not installed. Entity extraction will use fallback method.")
    TRANSFORMERS_AVAILABLE = False


@dataclass
class Entity:
    """实体对象"""
    text: str
    type: str  # PERSON, ORG, LOCATION, PRODUCT, etc.
    start: int
    end: int
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "type": self.type,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


@dataclass
class Relation:
    """关系对象"""
    source: str  # Source entity text
    target: str  # Target entity text
    relation_type: str  # WORKS_AT, LOCATED_IN, PRODUCES, etc.
    confidence: float = 0.0
    evidence: str = ""  # Supporting text
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation_type": self.relation_type,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "metadata": self.metadata
        }


class EntityExtractor:
    """实体抽取器"""

    def __init__(
        self,
        model_name: str = "dslim/bert-base-NER",
        use_gpu: bool = False,
        batch_size: int = 16
    ):
        """
        初始化实体抽取器

        Args:
            model_name: Hugging Face模型名称
            use_gpu: 是否使用GPU
            batch_size: 批处理大小
        """
        self.model_name = model_name
        self.use_gpu = use_gpu and TRANSFORMERS_AVAILABLE
        self.batch_size = batch_size
        self.ner_pipeline = None

        if TRANSFORMERS_AVAILABLE:
            self._initialize_model()
        else:
            logger.warning("Using fallback pattern-based entity extraction")

    def _initialize_model(self):
        """初始化NER模型"""
        try:
            device = 0 if self.use_gpu else -1

            self.ner_pipeline = pipeline(
                "ner",
                model=self.model_name,
                tokenizer=self.model_name,
                device=device,
                aggregation_strategy="simple"
            )

            logger.info(f"Initialized NER model: {self.model_name}")

        except Exception as e:
            logger.error(f"Failed to initialize NER model: {e}")
            self.ner_pipeline = None

    def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        min_confidence: float = 0.5
    ) -> List[Entity]:
        """
        从文本中抽取实体

        Args:
            text: 输入文本
            entity_types: 要抽取的实体类型（None表示所有类型）
            min_confidence: 最小置信度阈值

        Returns:
            实体列表
        """
        if not text or not text.strip():
            return []

        # Use transformer model if available
        if self.ner_pipeline:
            return self._extract_with_transformers(text, entity_types, min_confidence)
        else:
            return self._extract_with_patterns(text, entity_types)

    def _extract_with_transformers(
        self,
        text: str,
        entity_types: Optional[List[str]],
        min_confidence: float
    ) -> List[Entity]:
        """使用Transformers模型抽取实体"""
        try:
            # Run NER pipeline
            ner_results = self.ner_pipeline(text)

            entities = []
            for result in ner_results:
                # Filter by confidence
                if result['score'] < min_confidence:
                    continue

                # Normalize entity type
                entity_type = result['entity_group'].upper()

                # Map common NER labels
                type_mapping = {
                    'PER': 'PERSON',
                    'LOC': 'LOCATION',
                    'ORG': 'ORGANIZATION',
                    'MISC': 'MISC'
                }
                entity_type = type_mapping.get(entity_type, entity_type)

                # Filter by entity types if specified
                if entity_types and entity_type not in entity_types:
                    continue

                entity = Entity(
                    text=result['word'].strip(),
                    type=entity_type,
                    start=result['start'],
                    end=result['end'],
                    confidence=result['score']
                )

                entities.append(entity)

            logger.debug(f"Extracted {len(entities)} entities from text (length: {len(text)})")
            return entities

        except Exception as e:
            logger.error(f"Transformer extraction failed: {e}, falling back to patterns")
            return self._extract_with_patterns(text, entity_types)

    def _extract_with_patterns(
        self,
        text: str,
        entity_types: Optional[List[str]]
    ) -> List[Entity]:
        """使用正则模式抽取实体（回退方法）"""
        entities = []

        patterns = {
            'PERSON': [
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b',  # John Doe
                r'\b((?:[A-Z]\.)+\s*[A-Z][a-z]+)\b',  # J. Smith
            ],
            'ORGANIZATION': [
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|Ltd|LLC|Company|Co)\.?)\b',
                r'\b((?:[A-Z]+){2,})\b',  # IBM, NASA
            ],
            'LOCATION': [
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2})\b',  # New York, NY
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b',  # New York
            ],
            'PRODUCT': [
                r'\b([A-Z][a-z]+\s+\d+(?:\.\d+)?)\b',  # iPhone 14
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+[0-9X]+)\b',  # Windows 11
            ],
            'EMAIL': [
                r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
            ],
            'URL': [
                r'(https?://[^\s]+)',
            ],
            'DATE': [
                r'\b(\d{4}-\d{2}-\d{2})\b',  # 2024-01-15
                r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # 1/15/2024
            ]
        }

        # Filter patterns by entity types
        if entity_types:
            patterns = {k: v for k, v in patterns.items() if k in entity_types}

        for entity_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                for match in re.finditer(pattern, text):
                    entity = Entity(
                        text=match.group(1),
                        type=entity_type,
                        start=match.start(1),
                        end=match.end(1),
                        confidence=0.7  # Default confidence for pattern matching
                    )
                    entities.append(entity)

        # Deduplicate overlapping entities
        entities = self._deduplicate_entities(entities)

        logger.debug(f"Extracted {len(entities)} entities using patterns")
        return entities

    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """去除重叠的实体，保留置信度最高的"""
        if not entities:
            return []

        # Sort by start position and confidence
        sorted_entities = sorted(
            entities,
            key=lambda e: (e.start, -e.confidence)
        )

        deduplicated = []
        last_end = -1

        for entity in sorted_entities:
            # Skip overlapping entities
            if entity.start < last_end:
                continue

            deduplicated.append(entity)
            last_end = entity.end

        return deduplicated

    def extract_entity_pairs(
        self,
        text: str,
        max_distance: int = 100
    ) -> List[Tuple[Entity, Entity]]:
        """
        抽取可能存在关系的实体对

        Args:
            text: 输入文本
            max_distance: 实体间最大距离（字符数）

        Returns:
            实体对列表
        """
        entities = self.extract_entities(text)

        pairs = []
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i + 1:]:
                # Check distance
                distance = abs(entity1.start - entity2.start)
                if distance <= max_distance:
                    pairs.append((entity1, entity2))

        logger.debug(f"Extracted {len(pairs)} entity pairs")
        return pairs


class RelationExtractor:
    """关系抽取器"""

    def __init__(
        self,
        llm=None,
        use_patterns: bool = True
    ):
        """
        初始化关系抽取器

        Args:
            llm: LLM实例（用于基于LLM的关系抽取）
            use_patterns: 是否使用模式匹配
        """
        self.llm = llm
        self.use_patterns = use_patterns

        # Define relation patterns
        self.relation_patterns = {
            'WORKS_AT': [
                r'{source}\s+(?:works?|worked|employed)\s+(?:at|for)\s+{target}',
                r'{source}\s+is\s+(?:a|an|the)\s+\w+\s+at\s+{target}',
            ],
            'LOCATED_IN': [
                r'{source}\s+(?:is|are)\s+(?:located|based|situated)\s+in\s+{target}',
                r'{source},\s*{target}',
            ],
            'CEO_OF': [
                r'{source}\s+is\s+(?:the\s+)?CEO\s+of\s+{target}',
                r'{source},\s+CEO\s+of\s+{target}',
            ],
            'FOUNDED_BY': [
                r'{target}\s+(?:was\s+)?founded\s+by\s+{source}',
                r'{source}\s+founded\s+{target}',
            ],
            'ACQUIRED_BY': [
                r'{source}\s+(?:was\s+)?acquired\s+by\s+{target}',
                r'{target}\s+acquired\s+{source}',
            ],
            'PRODUCES': [
                r'{source}\s+(?:makes?|produces?|manufactures?)\s+{target}',
                r'{target}\s+(?:is|are)\s+(?:made|produced|manufactured)\s+by\s+{source}',
            ]
        }

        logger.info("Initialized RelationExtractor")

    def extract_relations(
        self,
        text: str,
        entity_pairs: List[Tuple[Entity, Entity]],
        min_confidence: float = 0.5
    ) -> List[Relation]:
        """
        从文本和实体对中抽取关系

        Args:
            text: 输入文本
            entity_pairs: 实体对列表
            min_confidence: 最小置信度

        Returns:
            关系列表
        """
        relations = []

        # Pattern-based extraction
        if self.use_patterns:
            relations.extend(
                self._extract_with_patterns(text, entity_pairs, min_confidence)
            )

        # LLM-based extraction
        if self.llm and len(entity_pairs) > 0:
            llm_relations = self._extract_with_llm(text, entity_pairs, min_confidence)
            relations.extend(llm_relations)

        # Deduplicate relations
        relations = self._deduplicate_relations(relations)

        logger.debug(f"Extracted {len(relations)} relations")
        return relations

    def _extract_with_patterns(
        self,
        text: str,
        entity_pairs: List[Tuple[Entity, Entity]],
        min_confidence: float
    ) -> List[Relation]:
        """使用模式匹配抽取关系"""
        relations = []

        for entity1, entity2 in entity_pairs:
            # Get text between entities
            start = min(entity1.end, entity2.end)
            end = max(entity1.start, entity2.start)
            context = text[start:end] if start < end else ""

            # Try to match patterns
            for relation_type, patterns in self.relation_patterns.items():
                for pattern_template in patterns:
                    # Replace placeholders
                    pattern = pattern_template.replace('{source}', re.escape(entity1.text))
                    pattern = pattern.replace('{target}', re.escape(entity2.text))

                    if re.search(pattern, text, re.IGNORECASE):
                        relation = Relation(
                            source=entity1.text,
                            target=entity2.text,
                            relation_type=relation_type,
                            confidence=0.8,  # Pattern matching confidence
                            evidence=context,
                            metadata={
                                'source_type': entity1.type,
                                'target_type': entity2.type,
                                'extraction_method': 'pattern'
                            }
                        )
                        relations.append(relation)
                        break

        return relations

    def _extract_with_llm(
        self,
        text: str,
        entity_pairs: List[Tuple[Entity, Entity]],
        min_confidence: float
    ) -> List[Relation]:
        """使用LLM抽取关系"""
        relations = []

        # Limit number of pairs to avoid too many LLM calls
        limited_pairs = entity_pairs[:20]

        for entity1, entity2 in limited_pairs:
            prompt = f"""Analyze the relationship between two entities in the following text.

Text: {text[:500]}

Entity 1: {entity1.text} (Type: {entity1.type})
Entity 2: {entity2.text} (Type: {entity2.type})

What is the relationship between Entity 1 and Entity 2? Choose from:
- WORKS_AT
- LOCATED_IN
- CEO_OF
- FOUNDED_BY
- ACQUIRED_BY
- PRODUCES
- RELATED_TO (generic)
- NO_RELATION

Respond with only the relationship type, or NO_RELATION if no clear relationship exists.
"""

            try:
                if hasattr(self.llm, 'invoke'):
                    response = self.llm.invoke(prompt)
                else:
                    response = str(self.llm(prompt))

                # Extract relation type
                response_text = response.content if hasattr(response, 'content') else str(response)
                relation_type = response_text.strip().upper()

                if relation_type != 'NO_RELATION' and relation_type in [
                    'WORKS_AT', 'LOCATED_IN', 'CEO_OF', 'FOUNDED_BY',
                    'ACQUIRED_BY', 'PRODUCES', 'RELATED_TO'
                ]:
                    relation = Relation(
                        source=entity1.text,
                        target=entity2.text,
                        relation_type=relation_type,
                        confidence=0.7,  # LLM confidence
                        evidence=text[:200],
                        metadata={
                            'source_type': entity1.type,
                            'target_type': entity2.type,
                            'extraction_method': 'llm'
                        }
                    )
                    relations.append(relation)

            except Exception as e:
                logger.warning(f"LLM relation extraction failed: {e}")
                continue

        return relations

    def _deduplicate_relations(self, relations: List[Relation]) -> List[Relation]:
        """去重关系"""
        seen = set()
        deduplicated = []

        for relation in relations:
            # Create unique key
            key = (relation.source, relation.target, relation.relation_type)

            if key not in seen:
                seen.add(key)
                deduplicated.append(relation)

        return deduplicated
