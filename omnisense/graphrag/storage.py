#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo4j Storage Layer

知识图谱的Neo4j存储实现
"""

from typing import List, Dict, Any, Optional, Set
from loguru import logger

try:
    from neo4j import GraphDatabase, basic_auth
    NEO4J_AVAILABLE = True
except ImportError:
    logger.warning("neo4j-driver not installed. Graph storage will not be available.")
    NEO4J_AVAILABLE = False


class Neo4jStorage:
    """Neo4j存储层"""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "password",
        database: str = "neo4j"
    ):
        """
        初始化Neo4j连接

        Args:
            uri: Neo4j URI
            username: 用户名
            password: 密码
            database: 数据库名
        """
        if not NEO4J_AVAILABLE:
            raise RuntimeError("neo4j-driver is not installed. Run: pip install neo4j")

        self.uri = uri
        self.username = username
        self.database = database
        self.driver = None

        try:
            self.driver = GraphDatabase.driver(
                uri,
                auth=basic_auth(username, password)
            )
            # Test connection
            with self.driver.session(database=database) as session:
                session.run("RETURN 1")

            logger.info(f"Connected to Neo4j at {uri}")

        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def create_node(
        self,
        label: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        创建节点

        Args:
            label: 节点标签
            properties: 节点属性

        Returns:
            创建的节点信息
        """
        query = f"""
        CREATE (n:{label} $props)
        RETURN n
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, props=properties)
            record = result.single()

            if record:
                node = dict(record["n"])
                logger.debug(f"Created node: {label} with {len(properties)} properties")
                return node

        return {}

    def create_or_update_node(
        self,
        label: str,
        key_property: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        创建或更新节点（基于唯一键）

        Args:
            label: 节点标签
            key_property: 唯一键属性名
            properties: 节点属性

        Returns:
            节点信息
        """
        if key_property not in properties:
            raise ValueError(f"Key property '{key_property}' not in properties")

        query = f"""
        MERGE (n:{label} {{{key_property}: $key_value}})
        ON CREATE SET n = $props
        ON MATCH SET n += $props
        RETURN n
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                key_value=properties[key_property],
                props=properties
            )
            record = result.single()

            if record:
                node = dict(record["n"])
                logger.debug(f"Created/Updated node: {label}[{key_property}={properties[key_property]}]")
                return node

        return {}

    def create_relationship(
        self,
        source_label: str,
        source_key: str,
        source_value: Any,
        target_label: str,
        target_key: str,
        target_value: Any,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建关系

        Args:
            source_label: 源节点标签
            source_key: 源节点键属性
            source_value: 源节点键值
            target_label: 目标节点标签
            target_key: 目标节点键属性
            target_value: 目标节点键值
            relationship_type: 关系类型
            properties: 关系属性

        Returns:
            关系信息
        """
        properties = properties or {}

        query = f"""
        MATCH (source:{source_label} {{{source_key}: $source_value}})
        MATCH (target:{target_label} {{{target_key}: $target_value}})
        MERGE (source)-[r:{relationship_type}]->(target)
        ON CREATE SET r = $props
        ON MATCH SET r += $props
        RETURN r
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                source_value=source_value,
                target_value=target_value,
                props=properties
            )
            record = result.single()

            if record:
                relationship = dict(record["r"])
                logger.debug(f"Created relationship: {relationship_type}")
                return relationship

        return {}

    def find_nodes(
        self,
        label: str,
        properties: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查找节点

        Args:
            label: 节点标签
            properties: 筛选属性
            limit: 结果数量限制

        Returns:
            节点列表
        """
        properties = properties or {}

        if properties:
            where_clause = " AND ".join([f"n.{k} = ${k}" for k in properties.keys()])
            query = f"""
            MATCH (n:{label})
            WHERE {where_clause}
            RETURN n
            LIMIT {limit}
            """
        else:
            query = f"""
            MATCH (n:{label})
            RETURN n
            LIMIT {limit}
            """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, **properties)
            nodes = [dict(record["n"]) for record in result]

            logger.debug(f"Found {len(nodes)} nodes with label {label}")
            return nodes

    def find_node_by_property(
        self,
        label: str,
        key: str,
        value: Any
    ) -> Optional[Dict[str, Any]]:
        """
        根据属性查找单个节点

        Args:
            label: 节点标签
            key: 属性键
            value: 属性值

        Returns:
            节点信息或None
        """
        query = f"""
        MATCH (n:{label} {{{key}: $value}})
        RETURN n
        LIMIT 1
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, value=value)
            record = result.single()

            if record:
                return dict(record["n"])

        return None

    def find_relationships(
        self,
        source_label: Optional[str] = None,
        target_label: Optional[str] = None,
        relationship_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查找关系

        Args:
            source_label: 源节点标签
            target_label: 目标节点标签
            relationship_type: 关系类型
            limit: 结果数量限制

        Returns:
            关系列表（包含源节点和目标节点）
        """
        # Build query dynamically
        source_pattern = f"(source:{source_label})" if source_label else "(source)"
        target_pattern = f"(target:{target_label})" if target_label else "(target)"
        rel_pattern = f"[r:{relationship_type}]" if relationship_type else "[r]"

        query = f"""
        MATCH {source_pattern}-{rel_pattern}->{target_pattern}
        RETURN source, r, target
        LIMIT {limit}
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query)
            relationships = []

            for record in result:
                relationships.append({
                    "source": dict(record["source"]),
                    "relationship": dict(record["r"]),
                    "target": dict(record["target"])
                })

            logger.debug(f"Found {len(relationships)} relationships")
            return relationships

    def find_neighbors(
        self,
        node_label: str,
        node_key: str,
        node_value: Any,
        direction: str = "both",  # "outgoing", "incoming", "both"
        relationship_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        查找邻居节点

        Args:
            node_label: 节点标签
            node_key: 节点键属性
            node_value: 节点键值
            direction: 关系方向
            relationship_type: 关系类型
            limit: 结果数量限制

        Returns:
            邻居节点列表（包含关系信息）
        """
        rel_pattern = f"[r:{relationship_type}]" if relationship_type else "[r]"

        if direction == "outgoing":
            query = f"""
            MATCH (n:{node_label} {{{node_key}: $value}})-{rel_pattern}->(neighbor)
            RETURN neighbor, r
            LIMIT {limit}
            """
        elif direction == "incoming":
            query = f"""
            MATCH (n:{node_label} {{{node_key}: $value}})<-{rel_pattern}-(neighbor)
            RETURN neighbor, r
            LIMIT {limit}
            """
        else:  # both
            query = f"""
            MATCH (n:{node_label} {{{node_key}: $value}})-{rel_pattern}-(neighbor)
            RETURN neighbor, r
            LIMIT {limit}
            """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, value=node_value)
            neighbors = []

            for record in result:
                neighbors.append({
                    "node": dict(record["neighbor"]),
                    "relationship": dict(record["r"])
                })

            logger.debug(f"Found {len(neighbors)} neighbors")
            return neighbors

    def find_path(
        self,
        source_label: str,
        source_key: str,
        source_value: Any,
        target_label: str,
        target_key: str,
        target_value: Any,
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """
        查找两个节点之间的路径

        Args:
            source_label: 源节点标签
            source_key: 源节点键
            source_value: 源节点值
            target_label: 目标节点标签
            target_key: 目标节点键
            target_value: 目标节点值
            max_depth: 最大路径深度

        Returns:
            路径列表
        """
        query = f"""
        MATCH path = (source:{source_label} {{{source_key}: $source_value}})-[*1..{max_depth}]->
                     (target:{target_label} {{{target_key}: $target_value}})
        RETURN path
        LIMIT 10
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                source_value=source_value,
                target_value=target_value
            )

            paths = []
            for record in result:
                path = record["path"]
                paths.append({
                    "nodes": [dict(node) for node in path.nodes],
                    "relationships": [dict(rel) for rel in path.relationships],
                    "length": len(path)
                })

            logger.debug(f"Found {len(paths)} paths")
            return paths

    def execute_cypher(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行自定义Cypher查询

        Args:
            query: Cypher查询语句
            parameters: 查询参数

        Returns:
            查询结果
        """
        parameters = parameters or {}

        with self.driver.session(database=self.database) as session:
            result = session.run(query, **parameters)
            records = [dict(record) for record in result]

            logger.debug(f"Executed custom query, returned {len(records)} records")
            return records

    def delete_node(self, label: str, key: str, value: Any):
        """
        删除节点及其关系

        Args:
            label: 节点标签
            key: 节点键
            value: 节点值
        """
        query = f"""
        MATCH (n:{label} {{{key}: $value}})
        DETACH DELETE n
        """

        with self.driver.session(database=self.database) as session:
            session.run(query, value=value)
            logger.debug(f"Deleted node: {label}[{key}={value}]")

    def delete_relationship(
        self,
        source_label: str,
        source_key: str,
        source_value: Any,
        target_label: str,
        target_key: str,
        target_value: Any,
        relationship_type: str
    ):
        """
        删除关系

        Args:
            source_label: 源节点标签
            source_key: 源节点键
            source_value: 源节点值
            target_label: 目标节点标签
            target_key: 目标节点键
            target_value: 目标节点值
            relationship_type: 关系类型
        """
        query = f"""
        MATCH (source:{source_label} {{{source_key}: $source_value}})-[r:{relationship_type}]->
              (target:{target_label} {{{target_key}: $target_value}})
        DELETE r
        """

        with self.driver.session(database=self.database) as session:
            session.run(
                query,
                source_value=source_value,
                target_value=target_value
            )
            logger.debug(f"Deleted relationship: {relationship_type}")

    def clear_database(self):
        """清空数据库（谨慎使用！）"""
        query = "MATCH (n) DETACH DELETE n"

        with self.driver.session(database=self.database) as session:
            session.run(query)
            logger.warning("Database cleared!")

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取图谱统计信息

        Returns:
            统计信息字典
        """
        queries = {
            "total_nodes": "MATCH (n) RETURN count(n) as count",
            "total_relationships": "MATCH ()-[r]->() RETURN count(r) as count",
            "node_labels": "CALL db.labels() YIELD label RETURN collect(label) as labels",
            "relationship_types": "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as types"
        }

        stats = {}

        with self.driver.session(database=self.database) as session:
            for key, query in queries.items():
                try:
                    result = session.run(query)
                    record = result.single()

                    if key in ["total_nodes", "total_relationships"]:
                        stats[key] = record["count"]
                    elif key == "node_labels":
                        stats[key] = record["labels"]
                    elif key == "relationship_types":
                        stats[key] = record["types"]

                except Exception as e:
                    logger.warning(f"Failed to get {key}: {e}")
                    stats[key] = None

        logger.info(f"Graph statistics: {stats}")
        return stats

    def create_indexes(self, label: str, properties: List[str]):
        """
        创建索引以提高查询性能

        Args:
            label: 节点标签
            properties: 属性列表
        """
        with self.driver.session(database=self.database) as session:
            for prop in properties:
                try:
                    query = f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.{prop})"
                    session.run(query)
                    logger.info(f"Created index on {label}.{prop}")
                except Exception as e:
                    logger.warning(f"Failed to create index on {label}.{prop}: {e}")
