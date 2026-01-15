"""
Interaction processing for OmniSense
Handles comments, likes, shares, and other user interactions
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import re

from omnisense.config import config
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class BaseInteractionProcessor:
    """Base class for interaction processing"""

    def __init__(self, platform: str):
        self.platform = platform

    async def process(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process interactions for content

        Args:
            content: Content with raw interaction data

        Returns:
            Content with processed interactions
        """
        interactions = content.get('interactions', [])
        if not interactions:
            return content

        processed = []
        for interaction in interactions:
            processed_interaction = await self.process_single(interaction)
            if processed_interaction:
                processed.append(processed_interaction)

        content['interactions'] = processed
        content['interaction_summary'] = self._generate_summary(processed)

        return content

    async def process_single(self, interaction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single interaction"""
        # Clean text
        if 'text' in interaction:
            interaction['text'] = self._clean_text(interaction['text'])

        # Extract mentions and hashtags
        if 'text' in interaction:
            interaction['mentions'] = self._extract_mentions(interaction['text'])
            interaction['hashtags'] = self._extract_hashtags(interaction['text'])

        # Sentiment analysis (placeholder)
        if 'text' in interaction:
            interaction['sentiment'] = await self._analyze_sentiment(interaction['text'])

        # Extract keywords
        if 'text' in interaction:
            interaction['keywords'] = self._extract_keywords(interaction['text'])

        return interaction

    def _clean_text(self, text: str) -> str:
        """Clean text content"""
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove special characters (keep basic punctuation)
        text = re.sub(r'[^\w\s,.!?;:\-@#]', '', text)
        return text.strip()

    def _extract_mentions(self, text: str) -> List[str]:
        """Extract @mentions from text"""
        return re.findall(r'@(\w+)', text)

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract #hashtags from text"""
        return re.findall(r'#(\w+)', text)

    async def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        # Placeholder for sentiment analysis
        # TODO: Implement with proper NLP model
        return {
            'score': 0.0,
            'label': 'neutral',
            'confidence': 0.0
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction (can be improved with TF-IDF, etc.)
        words = text.lower().split()
        # Filter out common words
        stop_words = {'the', 'is', 'at', 'which', 'on', 'a', 'an', 'as', 'are', 'was', 'were'}
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return list(set(keywords))[:10]  # Top 10 unique keywords

    def _generate_summary(self, interactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for interactions"""
        if not interactions:
            return {}

        total = len(interactions)

        # Count by type
        type_counts = {}
        for interaction in interactions:
            itype = interaction.get('type', 'unknown')
            type_counts[itype] = type_counts.get(itype, 0) + 1

        # Sentiment distribution
        sentiment_dist = {'positive': 0, 'negative': 0, 'neutral': 0}
        for interaction in interactions:
            sentiment = interaction.get('sentiment', {}).get('label', 'neutral')
            sentiment_dist[sentiment] = sentiment_dist.get(sentiment, 0) + 1

        # Top keywords
        all_keywords = []
        for interaction in interactions:
            all_keywords.extend(interaction.get('keywords', []))

        keyword_freq = {}
        for kw in all_keywords:
            keyword_freq[kw] = keyword_freq.get(kw, 0) + 1

        top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:10]

        # Top users by interaction count
        user_counts = {}
        for interaction in interactions:
            user_id = interaction.get('user', {}).get('user_id')
            if user_id:
                user_counts[user_id] = user_counts.get(user_id, 0) + 1

        top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            'total_interactions': total,
            'by_type': type_counts,
            'sentiment_distribution': sentiment_dist,
            'top_keywords': [{'keyword': k, 'count': c} for k, c in top_keywords],
            'top_users': [{'user_id': u, 'count': c} for u, c in top_users]
        }


class CommentProcessor(BaseInteractionProcessor):
    """Specialized processor for comments"""

    async def process(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process comments with threading support"""
        content = await super().process(content)

        # Build comment thread tree
        if 'interactions' in content:
            content['comment_tree'] = self._build_comment_tree(content['interactions'])

        return content

    def _build_comment_tree(self, interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build hierarchical comment tree"""
        # Create lookup dictionary
        comment_dict = {c.get('interaction_id'): c for c in interactions if c.get('type') == 'comment'}

        # Build tree
        root_comments = []
        for comment in interactions:
            if comment.get('type') != 'comment':
                continue

            parent_id = comment.get('parent_id')
            if not parent_id:
                # Root comment
                comment['replies'] = []
                root_comments.append(comment)
            else:
                # Reply to another comment
                parent = comment_dict.get(parent_id)
                if parent:
                    if 'replies' not in parent:
                        parent['replies'] = []
                    parent['replies'].append(comment)

        return root_comments


class InteractionManager:
    """Manager for interaction processing across platforms"""

    def __init__(self):
        self.processors = {}

    def get_processor(self, platform: str) -> BaseInteractionProcessor:
        """Get processor for platform"""
        if platform not in self.processors:
            # Default to comment processor for most platforms
            self.processors[platform] = CommentProcessor(platform)
        return self.processors[platform]

    async def process(self, platform: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process interactions for all content items

        Args:
            platform: Platform name
            data: List of content items with raw interactions

        Returns:
            Content items with processed interactions
        """
        processor = self.get_processor(platform)
        results = []

        for item in data:
            try:
                processed_item = await processor.process(item)
                results.append(processed_item)
            except Exception as e:
                logger.error(f"Error processing interactions for {item.get('content_id')}: {e}")
                results.append(item)  # Return original on error

        logger.info(f"Processed interactions for {len(results)} items on {platform}")
        return results

    def register_processor(self, platform: str, processor: BaseInteractionProcessor):
        """Register custom processor for platform"""
        self.processors[platform] = processor
