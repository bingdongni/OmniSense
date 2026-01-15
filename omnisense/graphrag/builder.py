#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Knowledge Graph Builder

知识图谱构建器，整合实体抽取和图谱存储
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .extractor import EntityExtractor, RelationExtractor, Entity, Relation
from .storage import Neo4jStorage


class KnowledgeGraphBuilder:
    """知识图谱构建器"""

    def __init__(
        self,
        storage: Neo4jStorage,
        entity_extractor: Optional[EntityExtractor] = None,
        relation_extractor: Optional[RelationExtractor] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化构建器

        Args:
            storage: Neo4j存储实例
            entity_extractor: 实体抽取器
            relation_extractor: 关系抽取器
            config: 配置
        """
        self.storage = storage
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.relation_extractor = relation_extractor or RelationExtractor()
        self.config = config or {}

        # Statistics
        self.stats = {
            "documents_processed": 0,
            "entities_extracted": 0,
            "relations_extracted": 0,
            "entities_stored": 0,
            "relations_stored": 0
        }

        logger.info("Initialized KnowledgeGraphBuilder")

    def build_from_text(
        self,
        text: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        从文本构建知识图谱

        Args:
            text: 输入文本
            document_id: 文档ID
            metadata: 元数据

        Returns:
            构建结果统计
        """
        if not text or not text.strip():
            logger.warning("Empty text provided")
            return {"success": False, "error": "Empty text"}

        document_id = document_id or f"doc_{int(datetime.now().timestamp())}"
        metadata = metadata or {}

        logger.info(f"Building knowledge graph from document: {document_id}")

        try:
            # Extract entities
            entities = self.entity_extractor.extract_entities(text)
            self.stats["entities_extracted"] += len(entities)

            if not entities:
                logger.warning("No entities extracted")
                return {
                    "success": True,
                    "document_id": document_id,
                    "entities": 0,
                    "relations": 0
                }

            # Store entities
            entity_map = {}  # Map entity text to node info
            for entity in entities:
                node = self._store_entity(entity, document_id, metadata)
                if node:
                    entity_map[entity.text] = node
                    self.stats["entities_stored"] += 1

            # Extract entity pairs
            entity_pairs = self.entity_extractor.extract_entity_pairs(text)

            # Extract relations
            relations = self.relation_extractor.extract_relations(
                text,
                entity_pairs
            )
            self.stats["relations_extracted"] += len(relations)

            # Store relations
            for relation in relations:
                success = self._store_relation(relation, document_id, metadata)
                if success:
                    self.stats["relations_stored"] += 1

            self.stats["documents_processed"] += 1

            result = {
                "success": True,
                "document_id": document_id,
                "entities": len(entities),
                "relations": len(relations),
                "entity_types": list(set(e.type for e in entities)),
                "relation_types": list(set(r.relation_type for r in relations))
            }

            logger.info(f"Built graph: {len(entities)} entities, {len(relations)} relations")
            return result

        except Exception as e:
            logger.error(f"Failed to build graph: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }

    def build_from_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        从多个文档批量构建知识图谱

        Args:
            documents: 文档列表，每个文档包含 'text', 'id', 'metadata'
            batch_size: 批处理大小

        Returns:
            批量构建结果
        """
        logger.info(f"Building graph from {len(documents)} documents")

        results = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]

            for doc in batch:
                result = self.build_from_text(
                    text=doc.get('text', ''),
                    document_id=doc.get('id'),
                    metadata=doc.get('metadata', {})
                )
                results.append(result)

            logger.info(f"Processed batch {i // batch_size + 1}/{(len(documents) + batch_size - 1) // batch_size}")

        successful = sum(1 for r in results if r.get('success'))
        total_entities = sum(r.get('entities', 0) for r in results)
        total_relations = sum(r.get('relations', 0) for r in results)

        summary = {
            "total_documents": len(documents),
            "successful": successful,
            "failed": len(documents) - successful,
            "total_entities": total_entities,
            "total_relations": total_relations,
            "results": results
        }

        logger.info(f"Batch build complete: {successful}/{len(documents)} successful")
        return summary

    def _store_entity(
        self,
        entity: Entity,
        document_id: str,
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        存储实体到Neo4j

        Args:
            entity: 实体对象
            document_id: 文档ID
            metadata: 元数据

        Returns:
            节点信息
        """
        try:
            # Prepare node properties
            properties = {
                "name": entity.text,
                "type": entity.type,
                "confidence": entity.confidence,
                "document_id": document_id,
                "created_at": datetime.now().isoformat(),
                **entity.metadata
            }

            # Merge any additional metadata
            properties.update(metadata)

            # Create or update node
            node = self.storage.create_or_update_node(
                label="Entity",
                key_property="name",
                properties=properties
            )

            return node

        except Exception as e:
            logger.error(f"Failed to store entity {entity.text}: {e}")
            return None

    def _store_relation(
        self,
        relation: Relation,
        document_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        存储关系到Neo4j

        Args:
            relation: 关系对象
            document_id: 文档ID
            metadata: 元数据

        Returns:
            是否成功
        """
        try:
            # Prepare relationship properties
            properties = {
                "confidence": relation.confidence,
                "evidence": relation.evidence,
                "document_id": document_id,
                "created_at": datetime.now().isoformat(),
                **relation.metadata
            }

            # Create relationship
            self.storage.create_relationship(
                source_label="Entity",
                source_key="name",
                source_value=relation.source,
                target_label="Entity",
                target_key="name",
                target_value=relation.target,
                relationship_type=relation.relation_type,
                properties=properties
            )

            return True

        except Exception as e:
            logger.error(f"Failed to store relation {relation.source} -> {relation.target}: {e}")
            return False

    async def build_from_text_async(
        self,
        text: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        异步从文本构建知识图谱

        Args:
            text: 输入文本
            document_id: 文档ID
            metadata: 元数据

        Returns:
            构建结果
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.build_from_text,
            text,
            document_id,
            metadata
        )
        return result

    async def build_from_documents_async(
        self,
        documents: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        异步批量构建知识图谱

        Args:
            documents: 文档列表
            max_concurrent: 最大并发数

        Returns:
            批量构建结果
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def build_with_semaphore(doc):
            async with semaphore:
                return await self.build_from_text_async(
                    text=doc.get('text', ''),
                    document_id=doc.get('id'),
                    metadata=doc.get('metadata', {})
                )

        results = await asyncio.gather(*[
            build_with_semaphore(doc) for doc in documents
        ])

        successful = sum(1 for r in results if r.get('success'))
        total_entities = sum(r.get('entities', 0) for r in results)
        total_relations = sum(r.get('relations', 0) for r in results)

        summary = {
            "total_documents": len(documents),
            "successful": successful,
            "failed": len(documents) - successful,
            "total_entities": total_entities,
            "total_relations": total_relations,
            "results": results
        }

        logger.info(f"Async batch build complete: {successful}/{len(documents)} successful")
        return summary

    def enrich_graph(
        self,
        llm=None,
        inference_rules: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        增强图谱（推断新关系、聚类等）

        Args:
            llm: LLM实例用于推断
            inference_rules: 推断规则

        Returns:
            增强结果
        """
        logger.info("Enriching knowledge graph...")

        enrichment_stats = {
            "inferred_relations": 0,
            "merged_entities": 0
        }

        # Apply inference rules
        if inference_rules:
            for rule in inference_rules:
                try:
                    self._apply_inference_rule(rule)
                    enrichment_stats["inferred_relations"] += 1
                except Exception as e:
                    logger.error(f"Failed to apply inference rule: {e}")

        # Merge similar entities (basic implementation)
        merged = self._merge_similar_entities()
        enrichment_stats["merged_entities"] = merged

        logger.info(f"Graph enrichment complete: {enrichment_stats}")
        return enrichment_stats

    def _apply_inference_rule(self, rule: Dict[str, Any]):
        """
        应用推断规则

        Args:
            rule: 推断规则（Cypher查询）
        """
        query = rule.get('query')
        if not query:
            return

        self.storage.execute_cypher(query)
        logger.debug(f"Applied inference rule: {rule.get('name', 'unnamed')}")

    def _merge_similar_entities(self) -> int:
        """
        合并相似实体

        Returns:
            合并的实体数量
        """
        # Simple implementation: merge entities with same name but different cases
        query = """
        MATCH (e1:Entity), (e2:Entity)
        WHERE toLower(e1.name) = toLower(e2.name)
          AND id(e1) < id(e2)
        WITH e1, e2
        CALL apoc.refactor.mergeNodes([e1, e2], {properties: 'combine'})
        YIELD node
        RETURN count(node) as merged
        """

        try:
            result = self.storage.execute_cypher(query)
            if result:
                merged = result[0].get('merged', 0)
                logger.info(f"Merged {merged} similar entities")
                return merged
        except Exception as e:
            logger.warning(f"Entity merging failed (APOC may not be available): {e}")

        return 0

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取构建统计信息

        Returns:
            统计信息
        """
        graph_stats = self.storage.get_statistics()

        return {
            "builder_stats": self.stats,
            "graph_stats": graph_stats
        }

    def reset_statistics(self):
        """重置统计信息"""
        self.stats = {
            "documents_processed": 0,
            "entities_extracted": 0,
            "relations_extracted": 0,
            "entities_stored": 0,
            "relations_stored": 0
        }
        logger.info("Statistics reset")

    def create_indexes(self):
        """创建常用索引以提高性能"""
        self.storage.create_indexes("Entity", ["name", "type", "document_id"])
        logger.info("Created indexes for Entity nodes")
