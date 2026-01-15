"""
Visualization renderer for OmniSense
Creates charts, wordclouds, and network graphs
"""

from typing import Any, Dict, List, Optional
from collections import Counter
import base64
from io import BytesIO

from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class VisualizationRenderer:
    """Renders visualizations for analysis results"""

    def __init__(self):
        pass

    def render(self, data: Dict[str, Any],
              chart_types: Optional[List[str]] = None,
              output: Optional[str] = None,
              **kwargs) -> Dict[str, Any]:
        """
        Render visualizations

        Args:
            data: Analysis data
            chart_types: Types of charts to generate
            output: Output file path (optional)
            **kwargs: Additional parameters

        Returns:
            Dictionary of chart objects/files
        """
        if not chart_types:
            chart_types = ['bar', 'wordcloud']

        charts = {}

        for chart_type in chart_types:
            try:
                if chart_type == 'bar':
                    charts['bar'] = self._create_bar_chart(data)
                elif chart_type == 'line':
                    charts['line'] = self._create_line_chart(data)
                elif chart_type == 'pie':
                    charts['pie'] = self._create_pie_chart(data)
                elif chart_type == 'wordcloud':
                    charts['wordcloud'] = self._create_wordcloud(data)
                elif chart_type == 'network':
                    charts['network'] = self._create_network_graph(data)
            except Exception as e:
                logger.error(f"Error creating {chart_type} chart: {e}")

        return charts

    def _create_bar_chart(self, data: Dict[str, Any]) -> str:
        """Create bar chart"""
        try:
            import plotly.graph_objects as go

            # Extract data for bar chart
            if 'sentiment' in data and 'distribution' in data['sentiment']:
                dist = data['sentiment']['distribution']
                fig = go.Figure(data=[
                    go.Bar(x=list(dist.keys()), y=list(dist.values()))
                ])
                fig.update_layout(
                    title='Sentiment Distribution',
                    xaxis_title='Sentiment',
                    yaxis_title='Count'
                )
                return fig.to_html()

            return ""

        except Exception as e:
            logger.error(f"Bar chart error: {e}")
            return ""

    def _create_line_chart(self, data: Dict[str, Any]) -> str:
        """Create line chart for trends"""
        try:
            import plotly.graph_objects as go

            if 'trend' in data:
                # Placeholder - need time series data
                fig = go.Figure()
                fig.update_layout(title='Trend Over Time')
                return fig.to_html()

            return ""

        except Exception as e:
            logger.error(f"Line chart error: {e}")
            return ""

    def _create_pie_chart(self, data: Dict[str, Any]) -> str:
        """Create pie chart"""
        try:
            import plotly.graph_objects as go

            if 'clusters' in data and 'distribution' in data['clusters']:
                dist = data['clusters']['distribution']
                fig = go.Figure(data=[
                    go.Pie(labels=list(dist.keys()), values=list(dist.values()))
                ])
                fig.update_layout(title='Topic Distribution')
                return fig.to_html()

            return ""

        except Exception as e:
            logger.error(f"Pie chart error: {e}")
            return ""

    def _create_wordcloud(self, data: Dict[str, Any]) -> str:
        """Create word cloud"""
        try:
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt

            # Extract text data
            texts = []
            if isinstance(data, dict):
                if 'content' in data:
                    for item in data['content']:
                        if isinstance(item, dict):
                            texts.append(item.get('title', ''))
                            texts.append(item.get('description', ''))

            if not texts:
                return ""

            text = ' '.join(texts)

            # Generate word cloud
            wordcloud = WordCloud(
                width=800,
                height=400,
                background_color='white',
                max_words=100
            ).generate(text)

            # Save to bytes
            plt.figure(figsize=(10, 5))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')

            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plt.close()

            # Convert to base64
            img_base64 = base64.b64encode(buf.read()).decode()
            return f'<img src="data:image/png;base64,{img_base64}"/>'

        except Exception as e:
            logger.error(f"Word cloud error: {e}")
            return ""

    def _create_network_graph(self, data: Dict[str, Any]) -> str:
        """Create network graph for relationships"""
        try:
            import networkx as nx
            import plotly.graph_objects as go

            G = nx.Graph()

            # Build graph from data
            # Placeholder - need relationship data
            if 'interactions' in data:
                # Add nodes and edges based on interactions
                pass

            # Create plotly figure
            pos = nx.spring_layout(G)

            edge_trace = go.Scatter(
                x=[],
                y=[],
                line=dict(width=0.5, color='#888'),
                hoverinfo='none',
                mode='lines')

            node_trace = go.Scatter(
                x=[],
                y=[],
                text=[],
                mode='markers+text',
                hoverinfo='text',
                marker=dict(
                    showscale=True,
                    colorscale='YlGnBu',
                    size=10,
                    colorbar=dict(
                        thickness=15,
                        title='Node Connections',
                        xanchor='left',
                        titleside='right'
                    )
                ))

            fig = go.Figure(data=[edge_trace, node_trace],
                          layout=go.Layout(
                              title='Network Graph',
                              showlegend=False,
                              hovermode='closest'
                          ))

            return fig.to_html()

        except Exception as e:
            logger.error(f"Network graph error: {e}")
            return ""
