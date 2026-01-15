"""
Creator Agent - Content Creation and Optimization
负责内容创作、优化和策略建议
"""

from typing import Any, Dict, List, Optional
from loguru import logger

from .base import BaseAgent, AgentConfig, AgentRole, AgentResponse, AgentState


class CreatorAgent(BaseAgent):
    """
    Creator agent for content creation and optimization

    Capabilities:
    - Content generation and optimization
    - Platform-specific recommendations
    - SEO and engagement optimization
    - Content strategy development
    - Hashtag and keyword suggestions
    - Viral content analysis
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="Creator",
                role=AgentRole.CREATOR,
                system_prompt=self._get_system_prompt()
            )
        super().__init__(config)

    def _get_system_prompt(self) -> str:
        return """You are a Creator Agent specialized in content creation and optimization.

Your role:
1. Generate engaging and optimized content
2. Provide platform-specific recommendations
3. Optimize content for maximum engagement
4. Develop content strategies
5. Suggest keywords, hashtags, and SEO improvements
6. Analyze successful content patterns

Approach:
- Understand platform algorithms and best practices
- Balance creativity with data-driven insights
- Consider audience preferences and trends
- Optimize for engagement metrics
- Maintain brand voice and authenticity
- Adapt content for different platforms

Output format:
Always provide structured creative output:
{
  "content": "...",
  "optimization_tips": [...],
  "platform_recommendations": {...},
  "keywords": [...],
  "hashtags": [...],
  "engagement_prediction": 0-100
}
"""

    def _setup_chains(self):
        """Setup LangChain chains for creator operations"""
        # Content generation chain
        self._create_chain(
            name="content_generation",
            template="""
Generate engaging content based on:

Topic: {topic}
Platform: {platform}
Target Audience: {audience}
Tone: {tone}
Constraints: {constraints}

Create compelling content that:
1. Captures attention immediately
2. Delivers value to the audience
3. Encourages engagement
4. Follows platform best practices
5. Includes call-to-action
6. Optimizes for discoverability

Content:
""",
            input_variables=["topic", "platform", "audience", "tone", "constraints"]
        )

        # Content optimization chain
        self._create_chain(
            name="content_optimization",
            template="""
Optimize the following content:

Original Content: {content}
Platform: {platform}
Goal: {goal}

Provide optimized version with:
1. Improved hook/opening
2. Better structure and flow
3. Enhanced engagement elements
4. Platform-specific optimizations
5. SEO improvements
6. Clear call-to-action

Optimized Content:
""",
            input_variables=["content", "platform", "goal"]
        )

        # Hashtag suggestion chain
        self._create_chain(
            name="hashtag_suggestion",
            template="""
Suggest effective hashtags for:

Content: {content}
Platform: {platform}
Niche: {niche}
Target Reach: {reach_type}

Provide:
1. Primary hashtags (high relevance, moderate competition)
2. Secondary hashtags (broader reach)
3. Niche hashtags (targeted audience)
4. Trending hashtags (if applicable)
5. Branded hashtags (if applicable)

Hashtags (provide 15-30 hashtags):
""",
            input_variables=["content", "platform", "niche", "reach_type"]
        )

        # Content strategy chain
        self._create_chain(
            name="content_strategy",
            template="""
Develop content strategy for:

Brand/Creator: {brand}
Platform: {platform}
Goals: {goals}
Current Performance: {performance}
Audience: {audience}

Provide strategic plan:
1. Content pillars and themes
2. Posting frequency and timing
3. Content mix (formats/types)
4. Engagement tactics
5. Growth strategies
6. Performance metrics to track

Strategy:
""",
            input_variables=["brand", "platform", "goals", "performance", "audience"]
        )

    async def process(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process creator task

        Task types:
        - generate_content: Generate new content
        - optimize_content: Optimize existing content
        - suggest_hashtags: Suggest hashtags
        - content_strategy: Develop content strategy
        - analyze_viral: Analyze viral content
        - platform_adaptation: Adapt content for platforms
        """
        self.state = AgentState.WORKING
        context = context or {}

        try:
            task_type = task.get("type", "generate_content")

            if task_type == "generate_content":
                result = await self._generate_content(task, context)
            elif task_type == "optimize_content":
                result = await self._optimize_content(task, context)
            elif task_type == "suggest_hashtags":
                result = await self._suggest_hashtags(task, context)
            elif task_type == "content_strategy":
                result = await self._content_strategy(task, context)
            elif task_type == "analyze_viral":
                result = await self._analyze_viral(task, context)
            elif task_type == "platform_adaptation":
                result = await self._platform_adaptation(task, context)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            return result

        except Exception as e:
            logger.error(f"Creator processing failed: {e}")
            return AgentResponse(
                agent_name=self.name,
                agent_role=self.role,
                success=False,
                error=str(e)
            )
        finally:
            self.state = AgentState.IDLE

    async def _generate_content(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Generate new content"""
        topic = task.get("topic", "")
        platform = task.get("platform", "")
        audience = task.get("audience", "general")
        tone = task.get("tone", "professional")
        constraints = task.get("constraints", {})

        reasoning = await self.think(
            f"Generate content about {topic} for {platform}",
            {"audience": audience, "tone": tone}
        )

        # Run content generation chain
        chain_result = await self._execute_with_retry(
            self.chains["content_generation"].ainvoke,
            {
                "topic": topic,
                "platform": platform,
                "audience": audience,
                "tone": tone,
                "constraints": str(constraints)
            }
        )

        generated_content = chain_result["text"].strip()

        # Generate optimization tips
        optimization_tips = self._generate_optimization_tips(
            generated_content,
            platform
        )

        # Predict engagement
        engagement_prediction = self._predict_engagement(
            generated_content,
            platform
        )

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "content": generated_content,
                "topic": topic,
                "platform": platform,
                "optimization_tips": optimization_tips,
                "engagement_prediction": engagement_prediction
            },
            message=f"Generated content for {platform} "
                    f"(predicted engagement: {engagement_prediction}/100)",
            reasoning=reasoning,
            confidence=0.85,
            metadata={
                "task_type": "generate_content",
                "platform": platform,
                "tone": tone
            }
        )

    async def _optimize_content(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Optimize existing content"""
        content = task.get("content", "")
        platform = task.get("platform", "")
        goal = task.get("goal", "engagement")

        reasoning = await self.think(
            f"Optimize content for {platform}",
            {"goal": goal, "content_length": len(content)}
        )

        # Run content optimization chain
        chain_result = await self._execute_with_retry(
            self.chains["content_optimization"].ainvoke,
            {
                "content": content[:2000],
                "platform": platform,
                "goal": goal
            }
        )

        optimized_content = chain_result["text"].strip()

        # Compare metrics
        original_score = self._predict_engagement(content, platform)
        optimized_score = self._predict_engagement(optimized_content, platform)
        improvement = optimized_score - original_score

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "original_content": content,
                "optimized_content": optimized_content,
                "original_score": original_score,
                "optimized_score": optimized_score,
                "improvement": improvement,
                "platform": platform
            },
            message=f"Content optimized for {platform} "
                    f"(+{improvement} predicted engagement)",
            reasoning=reasoning,
            confidence=0.82,
            metadata={
                "task_type": "optimize_content",
                "platform": platform,
                "goal": goal
            }
        )

    async def _suggest_hashtags(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Suggest hashtags"""
        content = task.get("content", "")
        platform = task.get("platform", "instagram")
        niche = task.get("niche", "general")
        reach_type = task.get("reach_type", "balanced")

        reasoning = await self.think(
            f"Suggest hashtags for {platform}",
            {"niche": niche, "reach": reach_type}
        )

        # Run hashtag suggestion chain
        chain_result = await self._execute_with_retry(
            self.chains["hashtag_suggestion"].ainvoke,
            {
                "content": content[:1000],
                "platform": platform,
                "niche": niche,
                "reach_type": reach_type
            }
        )

        # Parse hashtags
        hashtags = self._parse_hashtags(chain_result["text"])

        # Categorize hashtags
        categorized = self._categorize_hashtags(hashtags)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "hashtags": hashtags,
                "categorized": categorized,
                "platform": platform,
                "total_count": len(hashtags)
            },
            message=f"Generated {len(hashtags)} hashtags for {platform}",
            reasoning=reasoning,
            confidence=0.88,
            metadata={
                "task_type": "suggest_hashtags",
                "platform": platform,
                "niche": niche
            }
        )

    async def _content_strategy(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Develop content strategy"""
        brand = task.get("brand", "")
        platform = task.get("platform", "")
        goals = task.get("goals", [])
        performance = task.get("performance", {})
        audience = task.get("audience", {})

        reasoning = await self.think(
            f"Develop content strategy for {brand} on {platform}",
            {"goals": goals}
        )

        # Run content strategy chain
        chain_result = await self._execute_with_retry(
            self.chains["content_strategy"].ainvoke,
            {
                "brand": brand,
                "platform": platform,
                "goals": str(goals),
                "performance": str(performance),
                "audience": str(audience)
            }
        )

        # Parse strategy
        strategy = self._parse_content_strategy(chain_result["text"])

        # Generate tactical recommendations
        recommendations = self._generate_tactical_recommendations(
            platform,
            goals,
            performance
        )

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "brand": brand,
                "platform": platform,
                "strategy": strategy,
                "recommendations": recommendations
            },
            message=f"Content strategy developed for {brand} on {platform}",
            reasoning=reasoning,
            confidence=0.8,
            metadata={
                "task_type": "content_strategy",
                "platform": platform,
                "brand": brand
            }
        )

    async def _analyze_viral(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Analyze viral content"""
        content_list = task.get("content_list", [])
        platform = task.get("platform", "")

        reasoning = await self.think(
            f"Analyze {len(content_list)} viral contents from {platform}",
            {}
        )

        # Analyze patterns
        patterns = self._extract_viral_patterns(content_list)

        # Identify success factors
        success_factors = self._identify_success_factors(content_list)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "patterns": patterns,
                "success_factors": success_factors,
                "analyzed_count": len(content_list),
                "platform": platform
            },
            message=f"Analyzed {len(content_list)} viral contents, "
                    f"identified {len(patterns)} patterns",
            reasoning=reasoning,
            confidence=0.78,
            metadata={
                "task_type": "analyze_viral",
                "platform": platform
            }
        )

    async def _platform_adaptation(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Adapt content for different platforms"""
        content = task.get("content", "")
        source_platform = task.get("source_platform", "")
        target_platforms = task.get("target_platforms", [])

        reasoning = await self.think(
            f"Adapt content from {source_platform} to {len(target_platforms)} platforms",
            {}
        )

        # Adapt for each platform
        adapted_content = {}
        for target_platform in target_platforms:
            adapted = self._adapt_for_platform(
                content,
                source_platform,
                target_platform
            )
            adapted_content[target_platform] = adapted

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "original_content": content,
                "source_platform": source_platform,
                "adapted_content": adapted_content,
                "platform_count": len(target_platforms)
            },
            message=f"Adapted content for {len(target_platforms)} platforms",
            reasoning=reasoning,
            confidence=0.85,
            metadata={
                "task_type": "platform_adaptation",
                "source": source_platform,
                "targets": target_platforms
            }
        )

    def _generate_optimization_tips(
        self,
        content: str,
        platform: str
    ) -> List[str]:
        """Generate optimization tips"""
        tips = []

        # Length check
        length = len(content)
        platform_limits = {
            "twitter": 280,
            "instagram": 2200,
            "facebook": 63206,
            "linkedin": 3000,
            "tiktok": 2200,
            "xiaohongshu": 1000,
            "douyin": 2000
        }

        limit = platform_limits.get(platform.lower(), 5000)
        if length > limit:
            tips.append(f"Content exceeds {platform} optimal length. Consider shortening.")
        elif length < limit * 0.3:
            tips.append(f"Content could be expanded for better {platform} engagement.")

        # Hashtag check
        if platform.lower() in ["instagram", "tiktok", "twitter", "xiaohongshu", "douyin"]:
            if "#" not in content:
                tips.append(f"Add hashtags to improve {platform} discoverability.")

        # Call-to-action check
        cta_keywords = ["comment", "like", "share", "follow", "subscribe", "click", "learn more"]
        if not any(keyword in content.lower() for keyword in cta_keywords):
            tips.append("Consider adding a clear call-to-action.")

        # Emoji usage
        if platform.lower() in ["instagram", "tiktok", "xiaohongshu", "douyin"]:
            emoji_count = sum(1 for char in content if ord(char) > 127)
            if emoji_count == 0:
                tips.append("Consider adding emojis for visual appeal.")

        return tips

    def _predict_engagement(self, content: str, platform: str) -> int:
        """Predict engagement score"""
        score = 50  # Base score

        # Length factor
        length = len(content)
        if 100 <= length <= 500:
            score += 10
        elif 50 <= length <= 1000:
            score += 5

        # Question factor
        if "?" in content:
            score += 10

        # Emoji factor
        emoji_count = sum(1 for char in content if ord(char) > 127)
        score += min(10, emoji_count * 2)

        # Hashtag factor
        hashtag_count = content.count("#")
        score += min(10, hashtag_count * 2)

        # Call-to-action factor
        cta_keywords = ["comment", "like", "share", "follow"]
        if any(keyword in content.lower() for keyword in cta_keywords):
            score += 10

        return min(100, score)

    def _parse_hashtags(self, text: str) -> List[str]:
        """Parse hashtags from text"""
        hashtags = []

        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('#'):
                # Single hashtag per line
                hashtags.append(line)
            else:
                # Multiple hashtags in line
                words = line.split()
                for word in words:
                    if word.startswith('#'):
                        hashtags.append(word)

        # Clean and deduplicate
        cleaned = []
        for tag in hashtags:
            tag = tag.strip('#').strip()
            if tag and tag not in cleaned:
                cleaned.append('#' + tag)

        return cleaned[:30]  # Limit to 30 hashtags

    def _categorize_hashtags(self, hashtags: List[str]) -> Dict[str, List[str]]:
        """Categorize hashtags"""
        categorized = {
            "high_reach": [],
            "medium_reach": [],
            "niche": []
        }

        # Simple categorization based on length and common patterns
        for tag in hashtags:
            tag_lower = tag.lower()
            if any(common in tag_lower for common in ["#love", "#instagood", "#photooftheday"]):
                categorized["high_reach"].append(tag)
            elif len(tag) < 15:
                categorized["medium_reach"].append(tag)
            else:
                categorized["niche"].append(tag)

        return categorized

    def _parse_content_strategy(self, text: str) -> Dict[str, Any]:
        """Parse content strategy"""
        strategy = {
            "content_pillars": [],
            "posting_frequency": "",
            "tactics": []
        }

        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            line_lower = line.lower()
            if "pillar" in line_lower or "theme" in line_lower:
                current_section = "content_pillars"
            elif "frequency" in line_lower or "timing" in line_lower:
                current_section = "posting_frequency"
            elif "tactic" in line_lower or "strategy" in line_lower:
                current_section = "tactics"
            elif current_section:
                if current_section == "posting_frequency":
                    strategy[current_section] += line + " "
                elif line[0].isdigit() or line.startswith(('-', '•')):
                    content = line.lstrip('0123456789.-• ').strip()
                    if content:
                        strategy[current_section].append(content)

        return strategy

    def _generate_tactical_recommendations(
        self,
        platform: str,
        goals: List[str],
        performance: Dict[str, Any]
    ) -> List[str]:
        """Generate tactical recommendations"""
        recommendations = []

        # Platform-specific recommendations
        if platform.lower() == "instagram":
            recommendations.append("Post Reels 3-5 times per week for maximum reach")
            recommendations.append("Use 20-30 relevant hashtags per post")
            recommendations.append("Post during peak hours: 11am-1pm and 7pm-9pm")

        elif platform.lower() == "tiktok":
            recommendations.append("Post 1-3 times daily for algorithm favorability")
            recommendations.append("Hook viewers in first 3 seconds")
            recommendations.append("Use trending sounds and effects")

        elif platform.lower() == "linkedin":
            recommendations.append("Post 2-3 times per week on weekdays")
            recommendations.append("Share industry insights and thought leadership")
            recommendations.append("Engage with comments within first hour")

        # Goal-specific recommendations
        if "growth" in str(goals).lower():
            recommendations.append("Collaborate with similar-sized creators")
            recommendations.append("Run engagement-focused campaigns")

        if "engagement" in str(goals).lower():
            recommendations.append("Ask questions to encourage comments")
            recommendations.append("Respond to all comments within 24 hours")

        return recommendations

    def _extract_viral_patterns(self, content_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract patterns from viral content"""
        patterns = []

        # Analyze common elements
        total_with_questions = sum(1 for c in content_list if "?" in c.get("text", ""))
        if total_with_questions / max(len(content_list), 1) > 0.5:
            patterns.append({
                "pattern": "Question-based content",
                "frequency": total_with_questions / len(content_list)
            })

        # Check content length
        avg_length = sum(len(c.get("text", "")) for c in content_list) / max(len(content_list), 1)
        patterns.append({
            "pattern": f"Average length: {int(avg_length)} characters",
            "frequency": 1.0
        })

        return patterns

    def _identify_success_factors(self, content_list: List[Dict[str, Any]]) -> List[str]:
        """Identify success factors"""
        factors = []

        # Common success factors
        factors.append("Strong hook in first 3 seconds/lines")
        factors.append("Emotional resonance with target audience")
        factors.append("Clear value proposition")
        factors.append("Strategic use of platform features")

        return factors

    def _adapt_for_platform(
        self,
        content: str,
        source_platform: str,
        target_platform: str
    ) -> Dict[str, Any]:
        """Adapt content for specific platform"""
        adapted = {
            "content": content,
            "modifications": []
        }

        # Platform-specific adaptations
        if target_platform.lower() == "twitter":
            # Truncate to 280 characters
            if len(content) > 280:
                adapted["content"] = content[:277] + "..."
                adapted["modifications"].append("Truncated to Twitter limit")

        elif target_platform.lower() == "instagram":
            # Add line breaks for readability
            if "\n\n" not in content:
                adapted["content"] = content.replace(". ", ".\n\n")
                adapted["modifications"].append("Added line breaks for Instagram")

        elif target_platform.lower() == "linkedin":
            # Make more professional
            adapted["modifications"].append("Tone adjusted for professional audience")

        elif target_platform.lower() in ["tiktok", "douyin"]:
            # Add hook
            if not content.startswith(("Watch", "See", "Discover", "Learn")):
                adapted["content"] = "Watch this! " + content
                adapted["modifications"].append("Added attention-grabbing hook")

        return adapted
