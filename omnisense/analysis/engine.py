"""
Analysis engine for OmniSense
Sentiment analysis, clustering, prediction, and comparison
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from collections import Counter
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from omnisense.config import config
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class SentimentAnalyzer:
    """Sentiment analysis for text content"""

    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load sentiment analysis model"""
        try:
            # Use a lightweight sentiment model
            from transformers import pipeline
            self.model = pipeline(
                "sentiment-analysis",
                model=config.analysis.sentiment_model,
                device=0 if config.matcher.use_gpu else -1
            )
            logger.info("Sentiment analysis model loaded")
        except Exception as e:
            logger.warning(f"Failed to load sentiment model: {e}")
            self.model = None

    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        if not text or not self.model:
            return {'label': 'neutral', 'score': 0.0}

        try:
            result = self.model(text[:512])[0]  # Truncate for model limits
            return {
                'label': result['label'].lower(),
                'score': float(result['score']),
                'polarity': self._map_to_polarity(result['label'])
            }
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return {'label': 'neutral', 'score': 0.0, 'polarity': 0}

    def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Analyze sentiment for multiple texts"""
        return [self.analyze(text) for text in texts]

    def _map_to_polarity(self, label: str) -> int:
        """Map sentiment label to polarity (-1, 0, 1)"""
        label = label.lower()
        if 'positive' in label:
            return 1
        elif 'negative' in label:
            return -1
        return 0

    def aggregate_sentiment(self, sentiments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate multiple sentiment results"""
        if not sentiments:
            return {'average_score': 0.0, 'distribution': {}}

        scores = [s['score'] * s.get('polarity', 0) for s in sentiments]
        labels = [s['label'] for s in sentiments]

        distribution = Counter(labels)

        return {
            'average_score': np.mean(scores) if scores else 0.0,
            'distribution': dict(distribution),
            'positive_ratio': distribution.get('positive', 0) / len(sentiments),
            'negative_ratio': distribution.get('negative', 0) / len(sentiments),
            'neutral_ratio': distribution.get('neutral', 0) / len(sentiments)
        }


class TopicClusterer:
    """Topic clustering for content analysis"""

    def __init__(self, n_clusters: int = 5):
        self.n_clusters = n_clusters
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        self.clusterer = KMeans(n_clusters=n_clusters, random_state=42)

    def cluster(self, texts: List[str]) -> Tuple[np.ndarray, List[str]]:
        """Cluster texts into topics"""
        if len(texts) < self.n_clusters:
            logger.warning(f"Not enough texts ({len(texts)}) for {self.n_clusters} clusters")
            return np.zeros(len(texts)), []

        try:
            # Vectorize texts
            X = self.vectorizer.fit_transform(texts)

            # Cluster
            labels = self.clusterer.fit_predict(X)

            # Extract topic keywords
            topics = self._extract_topic_keywords()

            return labels, topics

        except Exception as e:
            logger.error(f"Clustering error: {e}")
            return np.zeros(len(texts)), []

    def _extract_topic_keywords(self, top_n: int = 5) -> List[str]:
        """Extract top keywords for each cluster"""
        feature_names = self.vectorizer.get_feature_names_out()
        topics = []

        for cluster_center in self.clusterer.cluster_centers_:
            # Get top features for this cluster
            top_indices = cluster_center.argsort()[-top_n:][::-1]
            top_keywords = [feature_names[i] for i in top_indices]
            topics.append(', '.join(top_keywords))

        return topics


class TrendAnalyzer:
    """Trend analysis and prediction"""

    def analyze_trend(self, data: List[Dict[str, Any]],
                     time_field: str = 'publish_time',
                     value_field: str = 'view_count') -> Dict[str, Any]:
        """Analyze trend over time"""
        if not data:
            return {}

        # Sort by time
        sorted_data = sorted(data, key=lambda x: x.get(time_field, 0))

        times = [d.get(time_field) for d in sorted_data]
        values = [d.get(value_field, 0) for d in sorted_data]

        if not values:
            return {}

        # Calculate trend statistics
        trend = {
            'total_items': len(data),
            'time_range': {'start': times[0], 'end': times[-1]} if times else {},
            'value_stats': {
                'min': min(values),
                'max': max(values),
                'mean': np.mean(values),
                'median': np.median(values),
                'std': np.std(values)
            }
        }

        # Simple linear trend
        if len(values) > 1:
            x = np.arange(len(values))
            trend['slope'] = np.polyfit(x, values, 1)[0]
            trend['direction'] = 'up' if trend['slope'] > 0 else 'down'

        return trend


class AnalysisEngine:
    """Main analysis engine coordinating all analyzers"""

    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.topic_clusterer = TopicClusterer()
        self.trend_analyzer = TrendAnalyzer()

    async def analyze(self, data: List[Dict[str, Any]],
                     analysis_types: Optional[List[str]] = None,
                     **kwargs) -> Dict[str, Any]:
        """
        Run analysis on data

        Args:
            data: List of content items
            analysis_types: List of analysis types to run
            **kwargs: Additional parameters

        Returns:
            Analysis results
        """
        if not analysis_types:
            analysis_types = ['sentiment', 'clustering']

        results = {}

        # Extract texts for analysis
        texts = self._extract_texts(data)

        # Sentiment analysis
        if 'sentiment' in analysis_types and texts:
            logger.info("Running sentiment analysis...")
            sentiments = self.sentiment_analyzer.analyze_batch(texts)
            results['sentiment'] = self.sentiment_analyzer.aggregate_sentiment(sentiments)

            # Add sentiment to individual items
            for item, sentiment in zip(data, sentiments):
                item['sentiment'] = sentiment

        # Topic clustering
        if 'clustering' in analysis_types and len(texts) >= 5:
            logger.info("Running topic clustering...")
            labels, topics = self.topic_clusterer.cluster(texts)
            results['clusters'] = {
                'n_clusters': len(topics),
                'topics': topics,
                'distribution': dict(Counter(labels))
            }

            # Add cluster labels to items
            for item, label in zip(data, labels):
                item['cluster'] = int(label)

        # Trend analysis
        if 'trend' in analysis_types:
            logger.info("Running trend analysis...")
            results['trend'] = self.trend_analyzer.analyze_trend(data)

        # Comparison analysis
        if 'comparison' in analysis_types:
            logger.info("Running comparison analysis...")
            results['comparison'] = self._compare_items(data)

        return results

    def _extract_texts(self, data: List[Dict[str, Any]]) -> List[str]:
        """Extract text from content items"""
        texts = []
        for item in data:
            parts = []
            if item.get('title'):
                parts.append(item['title'])
            if item.get('description'):
                parts.append(item['description'])
            texts.append(' '.join(parts) if parts else '')
        return texts

    def _compare_items(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare content items"""
        if len(data) < 2:
            return {}

        # Compare by platform
        by_platform = {}
        for item in data:
            platform = item.get('platform', 'unknown')
            if platform not in by_platform:
                by_platform[platform] = []
            by_platform[platform].append(item)

        platform_stats = {}
        for platform, items in by_platform.items():
            platform_stats[platform] = {
                'count': len(items),
                'avg_engagement': np.mean([
                    item.get('stats', {}).get('likes', 0) +
                    item.get('stats', {}).get('comments', 0)
                    for item in items
                ])
            }

        return {'by_platform': platform_stats}
