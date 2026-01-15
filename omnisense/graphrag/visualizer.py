#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Graph Visualizer

知识图谱可视化工具，使用Pyvis生成交互式图谱
"""

import os
from typing import List, Dict, Any, Optional
from loguru import logger

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    logger.warning("pyvis not installed. Graph visualization will not be available.")
    PYVIS_AVAILABLE = False

from .storage import Neo4jStorage
from .query_engine import QueryEngine


class GraphVisualizer:
    """知识图谱可视化器"""

    def __init__(
        self,
        storage: Neo4jStorage,
        query_engine: Optional[QueryEngine] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化可视化器

        Args:
            storage: Neo4j存储实例
            query_engine: 查询引擎（可选）
            config: 配置
        """
        if not PYVIS_AVAILABLE:
            raise RuntimeError("pyvis is not installed. Run: pip install pyvis")

        self.storage = storage
        self.query_engine = query_engine or QueryEngine(storage)
        self.config = config or {}

        # Visualization settings
        self.default_height = self.config.get('height', '750px')
        self.default_width = self.config.get('width', '100%')
        self.physics_enabled = self.config.get('physics', True)

        # Color mapping for entity types
        self.entity_colors = {
            'PERSON': '#FF6B6B',
            'ORGANIZATION': '#4ECDC4',
            'LOCATION': '#45B7D1',
            'PRODUCT': '#FFA07A',
            'EMAIL': '#98D8C8',
            'URL': '#C7CEEA',
            'DATE': '#FFEAA7',
            'MISC': '#DFE6E9'
        }

        logger.info("Initialized GraphVisualizer")

    def visualize_entity(
        self,
        entity_name: str,
        depth: int = 2,
        output_path: str = "entity_graph.html",
        max_nodes: int = 50
    ) -> str:
        """
        可视化实体及其周边关系

        Args:
            entity_name: 实体名称
            depth: 扩展深度
            output_path: 输出HTML文件路径
            max_nodes: 最大节点数

        Returns:
            生成的HTML文件路径
        """
        logger.info(f"Visualizing entity: {entity_name}")

        # Get subgraph
        subgraph = self.query_engine.get_subgraph(
            entity_name=entity_name,
            depth=depth,
            max_nodes=max_nodes
        )

        if not subgraph.get('nodes'):
            logger.warning(f"No data found for entity: {entity_name}")
            return ""

        # Create network
        net = self._create_network(f"Knowledge Graph: {entity_name}")

        # Add nodes and edges
        self._add_nodes_and_edges(net, subgraph['nodes'], subgraph['relationships'])

        # Highlight center node
        center_node_id = entity_name
        for node in net.nodes:
            if node['id'] == center_node_id:
                node['size'] = 30
                node['borderWidth'] = 3
                node['color'] = '#E74C3C'
                break

        # Save to HTML
        net.save_graph(output_path)
        logger.info(f"Saved visualization to {output_path}")

        return output_path

    def visualize_subgraph(
        self,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        output_path: str = "subgraph.html",
        title: str = "Knowledge Subgraph"
    ) -> str:
        """
        可视化自定义子图

        Args:
            nodes: 节点列表
            relationships: 关系列表
            output_path: 输出HTML文件路径
            title: 图谱标题

        Returns:
            生成的HTML文件路径
        """
        logger.info(f"Visualizing subgraph: {len(nodes)} nodes, {len(relationships)} edges")

        net = self._create_network(title)
        self._add_nodes_and_edges(net, nodes, relationships)

        net.save_graph(output_path)
        logger.info(f"Saved visualization to {output_path}")

        return output_path

    def visualize_path(
        self,
        source: str,
        target: str,
        output_path: str = "path.html",
        max_depth: int = 5
    ) -> str:
        """
        可视化两个实体之间的路径

        Args:
            source: 源实体名称
            target: 目标实体名称
            output_path: 输出HTML文件路径
            max_depth: 最大路径深度

        Returns:
            生成的HTML文件路径
        """
        logger.info(f"Visualizing path: {source} -> {target}")

        # Find paths
        paths = self.query_engine.find_path(source, target, max_depth)

        if not paths:
            logger.warning(f"No path found between {source} and {target}")
            return ""

        # Use the first (shortest) path
        path = paths[0]

        # Create network
        net = self._create_network(f"Path: {source} → {target}")

        # Add nodes from path
        nodes = []
        for node_data in path['nodes']:
            nodes.append({
                'name': node_data.get('name', 'Unknown'),
                'type': node_data.get('type', 'MISC')
            })

        # Add relationships from path
        relationships = []
        for rel_data in path['relationships']:
            relationships.append({
                'source': rel_data.get('source', ''),
                'target': rel_data.get('target', ''),
                'type': rel_data.get('type', 'RELATED')
            })

        self._add_nodes_and_edges(net, nodes, relationships)

        # Highlight source and target
        for node in net.nodes:
            if node['id'] == source:
                node['color'] = '#2ECC71'  # Green for source
                node['size'] = 25
            elif node['id'] == target:
                node['color'] = '#E74C3C'  # Red for target
                node['size'] = 25

        net.save_graph(output_path)
        logger.info(f"Saved path visualization to {output_path}")

        return output_path

    def visualize_full_graph(
        self,
        output_path: str = "full_graph.html",
        max_nodes: int = 100,
        entity_type: Optional[str] = None
    ) -> str:
        """
        可视化完整知识图谱（或按类型筛选）

        Args:
            output_path: 输出HTML文件路径
            max_nodes: 最大节点数
            entity_type: 实体类型筛选

        Returns:
            生成的HTML文件路径
        """
        logger.info(f"Visualizing full graph (max {max_nodes} nodes)")

        # Query all entities and relationships
        if entity_type:
            query = f"""
            MATCH (n:Entity {{type: $entity_type}})-[r]-(m:Entity)
            RETURN n, r, m
            LIMIT {max_nodes}
            """
            params = {"entity_type": entity_type}
        else:
            query = f"""
            MATCH (n:Entity)-[r]-(m:Entity)
            RETURN n, r, m
            LIMIT {max_nodes}
            """
            params = {}

        results = self.storage.execute_cypher(query, params)

        if not results:
            logger.warning("No data found for full graph")
            return ""

        # Extract unique nodes and relationships
        nodes_dict = {}
        relationships = []

        for record in results:
            # Source node
            n = record.get('n', {})
            if n and n.get('name'):
                nodes_dict[n['name']] = {
                    'name': n.get('name'),
                    'type': n.get('type', 'MISC')
                }

            # Target node
            m = record.get('m', {})
            if m and m.get('name'):
                nodes_dict[m['name']] = {
                    'name': m.get('name'),
                    'type': m.get('type', 'MISC')
                }

            # Relationship
            r = record.get('r', {})
            if r:
                relationships.append({
                    'source': n.get('name'),
                    'target': m.get('name'),
                    'type': 'RELATED'  # Generic type
                })

        nodes = list(nodes_dict.values())

        # Create network
        net = self._create_network("Full Knowledge Graph")
        self._add_nodes_and_edges(net, nodes, relationships)

        net.save_graph(output_path)
        logger.info(f"Saved full graph visualization to {output_path}")

        return output_path

    def _create_network(self, title: str) -> Network:
        """
        创建Pyvis网络对象

        Args:
            title: 网络标题

        Returns:
            Network对象
        """
        net = Network(
            height=self.default_height,
            width=self.default_width,
            bgcolor="#ffffff",
            font_color="#000000",
            heading=title
        )

        # Configure physics
        if self.physics_enabled:
            net.barnes_hut(
                gravity=-8000,
                central_gravity=0.3,
                spring_length=200,
                spring_strength=0.001,
                damping=0.09
            )
        else:
            net.toggle_physics(False)

        return net

    def _add_nodes_and_edges(
        self,
        net: Network,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ):
        """
        添加节点和边到网络

        Args:
            net: Network对象
            nodes: 节点列表
            relationships: 关系列表
        """
        # Add nodes
        for node in nodes:
            node_name = node.get('name', 'Unknown')
            node_type = node.get('type', 'MISC')
            color = self.entity_colors.get(node_type, '#95A5A6')

            net.add_node(
                node_name,
                label=node_name,
                title=f"Type: {node_type}",
                color=color,
                size=20
            )

        # Add edges
        for rel in relationships:
            source = rel.get('source', '')
            target = rel.get('target', '')
            rel_type = rel.get('type', '')

            if source and target:
                net.add_edge(
                    source,
                    target,
                    title=rel_type,
                    label=rel_type,
                    arrows='to',
                    smooth={'type': 'curvedCW', 'roundness': 0.2}
                )

    def create_legend_html(self) -> str:
        """
        创建图例HTML

        Returns:
            图例HTML字符串
        """
        legend_items = []
        for entity_type, color in self.entity_colors.items():
            legend_items.append(
                f'<div style="display:inline-block; margin: 5px;">'
                f'<span style="display:inline-block; width:15px; height:15px; '
                f'background-color:{color}; border-radius:50%; margin-right:5px;"></span>'
                f'{entity_type}</div>'
            )

        legend_html = f"""
        <div style="position: absolute; top: 10px; right: 10px;
                    background: white; padding: 10px; border: 1px solid #ccc;
                    border-radius: 5px; font-family: Arial, sans-serif;">
            <h4 style="margin-top: 0;">Entity Types</h4>
            {''.join(legend_items)}
        </div>
        """

        return legend_html

    def export_to_json(
        self,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        output_path: str = "graph_data.json"
    ) -> str:
        """
        导出图谱数据为JSON格式

        Args:
            nodes: 节点列表
            relationships: 关系列表
            output_path: 输出JSON文件路径

        Returns:
            生成的JSON文件路径
        """
        import json

        data = {
            "nodes": nodes,
            "relationships": relationships,
            "metadata": {
                "node_count": len(nodes),
                "relationship_count": len(relationships)
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported graph data to {output_path}")
        return output_path
