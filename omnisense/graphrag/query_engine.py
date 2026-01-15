#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Query Engine

知识图谱查询引擎，支持自然语言查询和Cypher查询
"""

from typing import List, Dict, Any, Optional
from loguru import logger

from .storage import Neo4jStorage


class QueryEngine:
    """知识图谱查询引擎"""

    def __init__(
        self,
        storage: Neo4jStorage,
        llm=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化查询引擎

        Args:
            storage: Neo4j存储实例
            llm: LLM实例用于自然语言查询
            config: 配置
        """
        self.storage = storage
        self.llm = llm
        self.config = config or {}

        logger.info("Initialized QueryEngine")

    def query_entity(
        self,
        entity_name: str,
        include_neighbors: bool = True,
        max_neighbors: int = 20
    ) -> Dict[str, Any]:
        """
        查询实体及其相关信息

        Args:
            entity_name: 实体名称
            include_neighbors: 是否包含邻居节点
            max_neighbors: 最大邻居数量

        Returns:
            实体信息
        """
        # Find entity
        entity = self.storage.find_node_by_property(
            label="Entity",
            key="name",
            value=entity_name
        )

        if not entity:
            logger.warning(f"Entity not found: {entity_name}")
            return {"found": False, "entity_name": entity_name}

        result = {
            "found": True,
            "entity": entity,
            "neighbors": []
        }

        # Get neighbors if requested
        if include_neighbors:
            neighbors = self.storage.find_neighbors(
                node_label="Entity",
                node_key="name",
                node_value=entity_name,
                direction="both",
                limit=max_neighbors
            )
            result["neighbors"] = neighbors

        logger.debug(f"Queried entity: {entity_name}, found {len(result.get('neighbors', []))} neighbors")
        return result

    def query_relation(
        self,
        source: str,
        target: str,
        relation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        查询两个实体之间的关系

        Args:
            source: 源实体名称
            target: 目标实体名称
            relation_type: 关系类型（可选）

        Returns:
            关系列表
        """
        if relation_type:
            query = """
            MATCH (source:Entity {name: $source})-[r:%s]->(target:Entity {name: $target})
            RETURN r
            """ % relation_type
        else:
            query = """
            MATCH (source:Entity {name: $source})-[r]->(target:Entity {name: $target})
            RETURN r, type(r) as relation_type
            """

        results = self.storage.execute_cypher(
            query,
            {"source": source, "target": target}
        )

        logger.debug(f"Found {len(results)} relations between {source} and {target}")
        return results

    def find_path(
        self,
        source: str,
        target: str,
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """
        查找两个实体之间的路径

        Args:
            source: 源实体名称
            target: 目标实体名称
            max_depth: 最大路径深度

        Returns:
            路径列表
        """
        paths = self.storage.find_path(
            source_label="Entity",
            source_key="name",
            source_value=source,
            target_label="Entity",
            target_key="name",
            target_value=target,
            max_depth=max_depth
        )

        logger.debug(f"Found {len(paths)} paths from {source} to {target}")
        return paths

    def search_entities(
        self,
        entity_type: Optional[str] = None,
        name_pattern: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        搜索实体

        Args:
            entity_type: 实体类型
            name_pattern: 名称模式（支持通配符）
            limit: 结果数量限制

        Returns:
            实体列表
        """
        conditions = []
        params = {}

        if entity_type:
            conditions.append("n.type = $entity_type")
            params["entity_type"] = entity_type

        if name_pattern:
            conditions.append("n.name =~ $pattern")
            # Convert simple wildcard to regex
            pattern = name_pattern.replace('*', '.*')
            params["pattern"] = f"(?i).*{pattern}.*"

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
        MATCH (n:Entity)
        WHERE {where_clause}
        RETURN n
        LIMIT {limit}
        """

        result = self.storage.execute_cypher(query, params)
        entities = [record.get('n', {}) for record in result]

        logger.debug(f"Search found {len(entities)} entities")
        return entities

    def query_with_cypher(
        self,
        cypher_query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        使用Cypher查询图谱

        Args:
            cypher_query: Cypher查询语句
            parameters: 查询参数

        Returns:
            查询结果
        """
        results = self.storage.execute_cypher(cypher_query, parameters)
        logger.debug(f"Cypher query returned {len(results)} results")
        return results

    def query_with_natural_language(
        self,
        question: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        使用自然语言查询图谱

        Args:
            question: 自然语言问题
            max_results: 最大结果数量

        Returns:
            查询结果
        """
        if not self.llm:
            logger.warning("LLM not available for natural language query")
            return {
                "success": False,
                "error": "LLM not configured"
            }

        logger.info(f"Natural language query: {question}")

        try:
            # Generate Cypher query using LLM
            cypher_query = self._generate_cypher_from_nl(question)

            if not cypher_query:
                return {
                    "success": False,
                    "error": "Failed to generate Cypher query"
                }

            # Execute query
            results = self.storage.execute_cypher(cypher_query)

            # Limit results
            if len(results) > max_results:
                results = results[:max_results]

            # Generate natural language answer
            answer = self._generate_answer_from_results(question, results)

            return {
                "success": True,
                "question": question,
                "cypher_query": cypher_query,
                "results": results,
                "answer": answer
            }

        except Exception as e:
            logger.error(f"Natural language query failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question
            }

    def _generate_cypher_from_nl(self, question: str) -> Optional[str]:
        """
        使用LLM将自然语言转换为Cypher查询

        Args:
            question: 自然语言问题

        Returns:
            Cypher查询语句
        """
        # Get graph schema
        stats = self.storage.get_statistics()

        prompt = f"""Convert the following natural language question into a Cypher query for Neo4j.

Graph Schema:
- Node labels: {stats.get('node_labels', [])}
- Relationship types: {stats.get('relationship_types', [])}
- Entity nodes have properties: name, type, confidence, document_id

Question: {question}

Provide ONLY the Cypher query, without any explanation or markdown formatting.
Example:
MATCH (e:Entity {{name: "Apple"}}) RETURN e

Cypher query:
"""

        try:
            if hasattr(self.llm, 'invoke'):
                response = self.llm.invoke(prompt)
            else:
                response = str(self.llm(prompt))

            # Extract query
            cypher = response.content if hasattr(response, 'content') else str(response)
            cypher = cypher.strip()

            # Remove markdown code blocks if present
            if cypher.startswith('```'):
                lines = cypher.split('\n')
                cypher = '\n'.join(lines[1:-1])

            logger.debug(f"Generated Cypher: {cypher}")
            return cypher

        except Exception as e:
            logger.error(f"Failed to generate Cypher: {e}")
            return None

    def _generate_answer_from_results(
        self,
        question: str,
        results: List[Dict[str, Any]]
    ) -> str:
        """
        使用LLM从查询结果生成自然语言答案

        Args:
            question: 原始问题
            results: 查询结果

        Returns:
            自然语言答案
        """
        if not results:
            return "No results found for your question."

        # Format results
        results_text = ""
        for i, record in enumerate(results[:5], 1):  # Limit to 5 for prompt
            results_text += f"{i}. {record}\n"

        prompt = f"""Based on the following query results, provide a natural language answer to the question.

Question: {question}

Query Results:
{results_text}

Provide a concise, natural language answer (2-3 sentences):
"""

        try:
            if hasattr(self.llm, 'invoke'):
                response = self.llm.invoke(prompt)
            else:
                response = str(self.llm(prompt))

            answer = response.content if hasattr(response, 'content') else str(response)
            return answer.strip()

        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            return "Failed to generate answer from results."

    def get_subgraph(
        self,
        entity_name: str,
        depth: int = 2,
        max_nodes: int = 50
    ) -> Dict[str, Any]:
        """
        获取以某个实体为中心的子图

        Args:
            entity_name: 中心实体名称
            depth: 扩展深度
            max_nodes: 最大节点数

        Returns:
            子图数据（节点和边）
        """
        query = f"""
        MATCH path = (center:Entity {{name: $entity_name}})-[*1..{depth}]-(node:Entity)
        WITH collect(path) as paths, collect(DISTINCT node) as nodes
        UNWIND paths as p
        WITH nodes + [center] as allNodes,
             [r in relationships(p) | {{source: startNode(r).name, target: endNode(r).name, type: type(r)}}] as rels
        RETURN
            [n in allNodes | {{name: n.name, type: n.type}}] as nodes,
            rels as relationships
        LIMIT 1
        """

        results = self.storage.execute_cypher(query, {"entity_name": entity_name})

        if not results:
            return {"nodes": [], "relationships": []}

        subgraph = results[0]

        # Limit nodes if too many
        nodes = subgraph.get('nodes', [])
        if len(nodes) > max_nodes:
            nodes = nodes[:max_nodes]

        logger.debug(f"Extracted subgraph: {len(nodes)} nodes")

        return {
            "center": entity_name,
            "nodes": nodes,
            "relationships": subgraph.get('relationships', [])
        }

    def get_entity_statistics(self) -> Dict[str, Any]:
        """
        获取实体统计信息

        Returns:
            统计信息
        """
        queries = {
            "entity_type_distribution": """
                MATCH (e:Entity)
                RETURN e.type as type, count(e) as count
                ORDER BY count DESC
            """,
            "relation_type_distribution": """
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """,
            "most_connected_entities": """
                MATCH (e:Entity)-[r]-()
                RETURN e.name as entity, count(r) as connections
                ORDER BY connections DESC
                LIMIT 10
            """
        }

        stats = {}
        for key, query in queries.items():
            try:
                results = self.storage.execute_cypher(query)
                stats[key] = results
            except Exception as e:
                logger.warning(f"Failed to get {key}: {e}")
                stats[key] = []

        return stats

    def recommend_related_entities(
        self,
        entity_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        推荐相关实体

        Args:
            entity_name: 实体名称
            limit: 推荐数量

        Returns:
            推荐实体列表
        """
        # Find entities connected through common neighbors
        query = """
        MATCH (e:Entity {name: $entity_name})-[]-(common)-[]-(related:Entity)
        WHERE e <> related
        WITH related, count(DISTINCT common) as commonality
        RETURN related.name as entity,
               related.type as type,
               commonality
        ORDER BY commonality DESC
        LIMIT $limit
        """

        results = self.storage.execute_cypher(
            query,
            {"entity_name": entity_name, "limit": limit}
        )

        logger.debug(f"Recommended {len(results)} related entities for {entity_name}")
        return results
