"""
Content matcher for OmniSense
Semantic matching, deduplication, and relevance scoring
"""

import hashlib
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

from omnisense.config import config
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class BaseMatcher:
    """Base class for content matching"""

    def __init__(self):
        self.model = None
        self.index = None
        self._load_model()

    def _load_model(self):
        """Load BERT model for semantic matching"""
        try:
            self.model = SentenceTransformer(config.matcher.bert_model)
            if config.matcher.use_gpu:
                self.model = self.model.to('cuda')
            logger.info(f"Loaded model: {config.matcher.bert_model}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity between two texts"""
        try:
            embeddings = self.model.encode([text1, text2])
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return float(similarity)
        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0

    def compute_hash(self, text: str) -> str:
        """Compute hash for deduplication"""
        return hashlib.md5(text.encode()).hexdigest()

    def match(self, content: Dict[str, Any], criteria: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Match content against criteria

        Returns:
            (is_match, score)
        """
        raise NotImplementedError


class TextMatcher(BaseMatcher):
    """Text-based content matcher"""

    def match(self, content: Dict[str, Any], criteria: Dict[str, Any]) -> Tuple[bool, float]:
        """Match text content against criteria"""
        text = self._extract_text(content)
        if not text:
            return False, 0.0

        score = 0.0

        # Keyword matching
        if 'keywords' in criteria:
            keyword_score = self._match_keywords(text, criteria['keywords'])
            score += keyword_score * 0.4

        # Semantic matching
        if 'semantic_query' in criteria:
            semantic_score = self.compute_similarity(text, criteria['semantic_query'])
            score += semantic_score * 0.6

        is_match = score >= config.matcher.similarity_threshold
        return is_match, score

    def _extract_text(self, content: Dict[str, Any]) -> str:
        """Extract text from content"""
        parts = []
        if content.get('title'):
            parts.append(content['title'])
        if content.get('description'):
            parts.append(content['description'])
        if content.get('text'):
            parts.append(content['text'])
        return ' '.join(parts)

    def _match_keywords(self, text: str, keywords: List[str]) -> float:
        """Match keywords in text"""
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        return matches / len(keywords) if keywords else 0.0


class MultiModalMatcher(BaseMatcher):
    """Multi-modal content matcher (text + image + video)"""

    def match(self, content: Dict[str, Any], criteria: Dict[str, Any]) -> Tuple[bool, float]:
        """Match multi-modal content"""
        scores = []

        # Text matching
        if 'text' in content or 'title' in content or 'description' in content:
            text_matcher = TextMatcher()
            _, text_score = text_matcher.match(content, criteria)
            scores.append(text_score)

        # Image matching (if available)
        if content.get('images') and criteria.get('visual_query'):
            image_score = self._match_images(content['images'], criteria['visual_query'])
            scores.append(image_score)

        # Video matching (if available)
        if content.get('videos') and criteria.get('video_query'):
            video_score = self._match_videos(content['videos'], criteria['video_query'])
            scores.append(video_score)

        final_score = np.mean(scores) if scores else 0.0
        is_match = final_score >= config.matcher.similarity_threshold
        return is_match, final_score

    def _match_images(self, images: List[str], query: str) -> float:
        """Match images against query (placeholder for vision model)"""
        # TODO: Implement with vision model (CLIP, etc.)
        logger.debug("Image matching not fully implemented yet")
        return 0.5

    def _match_videos(self, videos: List[str], query: str) -> float:
        """Match videos against query (placeholder for video model)"""
        # TODO: Implement with video understanding model
        logger.debug("Video matching not fully implemented yet")
        return 0.5


class Deduplicator:
    """Content deduplication"""

    def __init__(self):
        self.seen_hashes = set()
        self.vector_index = None
        self.vectors = []

    def is_duplicate(self, content: Dict[str, Any], threshold: float = 0.95) -> bool:
        """Check if content is duplicate"""
        # Hash-based deduplication
        content_hash = self._compute_content_hash(content)
        if content_hash in self.seen_hashes:
            return True

        # Vector-based deduplication
        if self.vectors:
            is_dup = self._check_vector_duplicate(content, threshold)
            if is_dup:
                return True

        # Not duplicate, add to seen
        self.seen_hashes.add(content_hash)
        return False

    def _compute_content_hash(self, content: Dict[str, Any]) -> str:
        """Compute content hash for deduplication"""
        # Combine key fields
        text = f"{content.get('title', '')}{content.get('description', '')}"
        return hashlib.md5(text.encode()).hexdigest()

    def _check_vector_duplicate(self, content: Dict[str, Any], threshold: float) -> bool:
        """Check for near-duplicates using vector similarity"""
        # TODO: Implement vector-based deduplication with FAISS
        return False

    def add_content(self, content: Dict[str, Any], vector: Optional[np.ndarray] = None):
        """Add content to deduplication index"""
        content_hash = self._compute_content_hash(content)
        self.seen_hashes.add(content_hash)
        if vector is not None:
            self.vectors.append(vector)

    def reset(self):
        """Reset deduplication state"""
        self.seen_hashes.clear()
        self.vectors.clear()
        self.vector_index = None


class MatcherManager:
    """Manager for content matching across platforms"""

    def __init__(self):
        self.matchers = {}
        self.deduplicator = Deduplicator()

    def get_matcher(self, platform: str) -> BaseMatcher:
        """Get matcher for platform"""
        if platform not in self.matchers:
            # Default to multi-modal matcher
            self.matchers[platform] = MultiModalMatcher()
        return self.matchers[platform]

    async def match(self, platform: str, data: List[Dict[str, Any]],
                   criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Match and filter content

        Args:
            platform: Platform name
            data: List of content items
            criteria: Matching criteria

        Returns:
            Filtered and scored content
        """
        matcher = self.get_matcher(platform)
        results = []

        for item in data:
            # Check for duplicates
            if self.deduplicator.is_duplicate(item):
                logger.debug(f"Skipping duplicate: {item.get('content_id')}")
                continue

            # Match against criteria
            if criteria:
                is_match, score = matcher.match(item, criteria)
                if not is_match:
                    continue
                item['match_score'] = score

            results.append(item)
            self.deduplicator.add_content(item)

        logger.info(f"Matched {len(results)}/{len(data)} items for {platform}")
        return results

    def reset(self):
        """Reset matching state"""
        self.deduplicator.reset()
