"""
Ecommerce Agent - Product and Market Analysis
负责电商产品分析、市场分析和竞争分析
"""

from typing import Any, Dict, List, Optional
from loguru import logger

from .base import BaseAgent, AgentConfig, AgentRole, AgentResponse, AgentState


class EcommerceAgent(BaseAgent):
    """
    Ecommerce agent for product and market analysis

    Capabilities:
    - Product analysis and comparison
    - Price analysis and trends
    - Review and rating analysis
    - Competitor analysis
    - Market positioning
    - Purchase recommendations
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="Ecommerce",
                role=AgentRole.ECOMMERCE,
                system_prompt=self._get_system_prompt()
            )
        super().__init__(config)

    def _get_system_prompt(self) -> str:
        return """You are an Ecommerce Agent specialized in product and market analysis.

Your role:
1. Analyze products across multiple platforms
2. Compare prices, features, and specifications
3. Analyze customer reviews and ratings
4. Identify market trends and opportunities
5. Evaluate competitive positioning
6. Provide purchase recommendations

Approach:
- Consider both quantitative and qualitative factors
- Focus on value proposition and differentiation
- Analyze customer sentiment and satisfaction
- Track pricing dynamics and promotions
- Identify quality indicators
- Consider platform-specific factors

Output format:
Always provide structured analysis with:
{
  "product_analysis": {...},
  "price_analysis": {...},
  "review_analysis": {...},
  "competitive_position": "...",
  "recommendation": "...",
  "confidence_score": 0-100
}
"""

    def _setup_chains(self):
        """Setup LangChain chains for ecommerce operations"""
        # Product analysis chain
        self._create_chain(
            name="product_analysis",
            template="""
Analyze the following product:

Product: {product_name}
Platform: {platform}
Details: {product_details}
Reviews: {reviews}

Provide comprehensive analysis:
1. Product overview and key features
2. Strengths and weaknesses
3. Value proposition
4. Quality indicators
5. Target audience fit
6. Unique selling points

Analysis:
""",
            input_variables=["product_name", "platform", "product_details", "reviews"]
        )

        # Price analysis chain
        self._create_chain(
            name="price_analysis",
            template="""
Analyze pricing for the product:

Product: {product_name}
Current Price: {current_price}
Historical Prices: {price_history}
Competitor Prices: {competitor_prices}

Provide:
1. Price positioning (premium/mid/budget)
2. Price trend analysis
3. Value for money assessment
4. Price comparison with competitors
5. Promotion opportunities
6. Price recommendation

Price Analysis:
""",
            input_variables=["product_name", "current_price", "price_history", "competitor_prices"]
        )

        # Review analysis chain
        self._create_chain(
            name="review_analysis",
            template="""
Analyze customer reviews:

Product: {product_name}
Reviews: {reviews}
Rating: {rating}

Extract:
1. Common praise points
2. Common complaints
3. Quality issues
4. Feature feedback
5. Customer satisfaction drivers
6. Improvement suggestions

Review Insights:
""",
            input_variables=["product_name", "reviews", "rating"]
        )

        # Competitive analysis chain
        self._create_chain(
            name="competitive_analysis",
            template="""
Analyze competitive landscape:

Target Product: {target_product}
Competitors: {competitors}
Market Context: {market_context}

Provide:
1. Competitive positioning
2. Competitive advantages
3. Competitive disadvantages
4. Market differentiation
5. Market share insights
6. Strategic recommendations

Competitive Analysis:
""",
            input_variables=["target_product", "competitors", "market_context"]
        )

    async def process(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process ecommerce task

        Task types:
        - product_analysis: Analyze a product
        - price_analysis: Analyze pricing
        - review_analysis: Analyze reviews
        - competitive_analysis: Competitive analysis
        - market_analysis: Market analysis
        - purchase_recommendation: Purchase recommendation
        """
        self.state = AgentState.WORKING
        context = context or {}

        try:
            task_type = task.get("type", "product_analysis")

            if task_type == "product_analysis":
                result = await self._product_analysis(task, context)
            elif task_type == "price_analysis":
                result = await self._price_analysis(task, context)
            elif task_type == "review_analysis":
                result = await self._review_analysis(task, context)
            elif task_type == "competitive_analysis":
                result = await self._competitive_analysis(task, context)
            elif task_type == "market_analysis":
                result = await self._market_analysis(task, context)
            elif task_type == "purchase_recommendation":
                result = await self._purchase_recommendation(task, context)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            return result

        except Exception as e:
            logger.error(f"Ecommerce processing failed: {e}")
            return AgentResponse(
                agent_name=self.name,
                agent_role=self.role,
                success=False,
                error=str(e)
            )
        finally:
            self.state = AgentState.IDLE

    async def _product_analysis(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Analyze a product"""
        product_name = task.get("product_name", "")
        platform = task.get("platform", "")
        product_details = task.get("details", {})
        reviews = task.get("reviews", [])

        reasoning = await self.think(
            f"Analyze product {product_name} from {platform}",
            {"has_reviews": len(reviews) > 0}
        )

        # Run product analysis chain
        chain_result = await self._execute_with_retry(
            self.chains["product_analysis"].ainvoke,
            {
                "product_name": product_name,
                "platform": platform,
                "product_details": str(product_details)[:2000],
                "reviews": str(reviews[:10])[:2000]
            }
        )

        # Parse analysis
        analysis = self._parse_product_analysis(chain_result["text"])

        # Calculate product score
        product_score = self._calculate_product_score(product_details, reviews)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "product_name": product_name,
                "platform": platform,
                "analysis": analysis,
                "product_score": product_score,
                "review_count": len(reviews)
            },
            message=f"Product analysis complete for {product_name} (score: {product_score}/100)",
            reasoning=reasoning,
            confidence=0.85,
            metadata={
                "task_type": "product_analysis",
                "platform": platform
            }
        )

    async def _price_analysis(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Analyze product pricing"""
        product_name = task.get("product_name", "")
        current_price = task.get("current_price", 0)
        price_history = task.get("price_history", [])
        competitor_prices = task.get("competitor_prices", [])

        reasoning = await self.think(
            f"Analyze pricing for {product_name}",
            {"current_price": current_price, "competitors": len(competitor_prices)}
        )

        # Run price analysis chain
        chain_result = await self._execute_with_retry(
            self.chains["price_analysis"].ainvoke,
            {
                "product_name": product_name,
                "current_price": str(current_price),
                "price_history": str(price_history),
                "competitor_prices": str(competitor_prices)
            }
        )

        # Parse price analysis
        price_analysis = self._parse_price_analysis(chain_result["text"])

        # Calculate price metrics
        price_metrics = self._calculate_price_metrics(
            current_price,
            price_history,
            competitor_prices
        )

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "product_name": product_name,
                "current_price": current_price,
                "price_analysis": price_analysis,
                "price_metrics": price_metrics
            },
            message=f"Price analysis: {price_analysis.get('positioning', 'mid-range')} "
                    f"({price_metrics.get('value_score', 50)}/100 value)",
            reasoning=reasoning,
            confidence=0.8,
            metadata={
                "task_type": "price_analysis"
            }
        )

    async def _review_analysis(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Analyze product reviews"""
        product_name = task.get("product_name", "")
        reviews = task.get("reviews", [])
        rating = task.get("rating", 0)

        reasoning = await self.think(
            f"Analyze {len(reviews)} reviews for {product_name}",
            {"avg_rating": rating}
        )

        # Run review analysis chain
        chain_result = await self._execute_with_retry(
            self.chains["review_analysis"].ainvoke,
            {
                "product_name": product_name,
                "reviews": str(reviews[:20])[:3000],
                "rating": str(rating)
            }
        )

        # Parse review insights
        review_insights = self._parse_review_insights(chain_result["text"])

        # Calculate review metrics
        review_metrics = self._calculate_review_metrics(reviews, rating)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "product_name": product_name,
                "review_count": len(reviews),
                "avg_rating": rating,
                "insights": review_insights,
                "metrics": review_metrics
            },
            message=f"Analyzed {len(reviews)} reviews (avg rating: {rating:.1f}/5)",
            reasoning=reasoning,
            confidence=0.82,
            metadata={
                "task_type": "review_analysis"
            }
        )

    async def _competitive_analysis(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Perform competitive analysis"""
        target_product = task.get("target_product", {})
        competitors = task.get("competitors", [])
        market_context = task.get("market_context", {})

        reasoning = await self.think(
            f"Analyze {len(competitors)} competitors",
            {"target": target_product.get("name", "unknown")}
        )

        # Run competitive analysis chain
        chain_result = await self._execute_with_retry(
            self.chains["competitive_analysis"].ainvoke,
            {
                "target_product": str(target_product)[:2000],
                "competitors": str(competitors)[:3000],
                "market_context": str(market_context)[:1000]
            }
        )

        # Parse competitive analysis
        competitive_analysis = self._parse_competitive_analysis(chain_result["text"])

        # Calculate competitive score
        competitive_score = self._calculate_competitive_score(
            target_product,
            competitors
        )

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "target_product": target_product.get("name", "unknown"),
                "competitor_count": len(competitors),
                "analysis": competitive_analysis,
                "competitive_score": competitive_score
            },
            message=f"Competitive analysis complete (score: {competitive_score}/100)",
            reasoning=reasoning,
            confidence=0.78,
            metadata={
                "task_type": "competitive_analysis",
                "competitor_count": len(competitors)
            }
        )

    async def _market_analysis(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Analyze market conditions"""
        category = task.get("category", "")
        products = task.get("products", [])

        reasoning = await self.think(
            f"Analyze {category} market",
            {"product_count": len(products)}
        )

        # Market metrics
        market_metrics = self._calculate_market_metrics(products)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "category": category,
                "market_metrics": market_metrics,
                "product_count": len(products)
            },
            message=f"Market analysis for {category} completed",
            reasoning=reasoning,
            confidence=0.75,
            metadata={
                "task_type": "market_analysis",
                "category": category
            }
        )

    async def _purchase_recommendation(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Generate purchase recommendation"""
        products = task.get("products", [])
        user_preferences = task.get("preferences", {})
        budget = task.get("budget", None)

        reasoning = await self.think(
            f"Generate recommendation from {len(products)} products",
            {"budget": budget, "preferences": user_preferences}
        )

        # Score and rank products
        scored_products = self._score_products(products, user_preferences, budget)

        # Select top recommendation
        top_product = scored_products[0] if scored_products else None

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            success=True,
            data={
                "recommendation": top_product,
                "alternatives": scored_products[1:4] if len(scored_products) > 1 else [],
                "total_evaluated": len(products)
            },
            message=f"Recommended: {top_product.get('name', 'N/A') if top_product else 'No match found'}",
            reasoning=reasoning,
            confidence=0.85 if top_product else 0.3,
            metadata={
                "task_type": "purchase_recommendation",
                "evaluated_count": len(products)
            }
        )

    def _parse_product_analysis(self, text: str) -> Dict[str, Any]:
        """Parse product analysis results"""
        analysis = {
            "strengths": [],
            "weaknesses": [],
            "value_proposition": ""
        }

        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            line_lower = line.lower()
            if "strength" in line_lower or "pros" in line_lower:
                current_section = "strengths"
            elif "weakness" in line_lower or "cons" in line_lower:
                current_section = "weaknesses"
            elif "value" in line_lower:
                current_section = "value_proposition"
            elif current_section and (line[0].isdigit() or line.startswith(('-', '•'))):
                content = line.lstrip('0123456789.-• ').strip()
                if content:
                    if current_section in ["strengths", "weaknesses"]:
                        analysis[current_section].append(content)
                    else:
                        analysis[current_section] = content

        return analysis

    def _parse_price_analysis(self, text: str) -> Dict[str, Any]:
        """Parse price analysis results"""
        analysis = {
            "positioning": "mid-range",
            "value_assessment": "fair"
        }

        text_lower = text.lower()
        if "premium" in text_lower or "high-end" in text_lower:
            analysis["positioning"] = "premium"
        elif "budget" in text_lower or "low-cost" in text_lower:
            analysis["positioning"] = "budget"

        if "excellent value" in text_lower or "great value" in text_lower:
            analysis["value_assessment"] = "excellent"
        elif "poor value" in text_lower or "overpriced" in text_lower:
            analysis["value_assessment"] = "poor"

        return analysis

    def _parse_review_insights(self, text: str) -> Dict[str, List[str]]:
        """Parse review insights"""
        insights = {
            "praise_points": [],
            "complaints": []
        }

        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            line_lower = line.lower()
            if "praise" in line_lower or "positive" in line_lower:
                current_section = "praise_points"
            elif "complaint" in line_lower or "negative" in line_lower:
                current_section = "complaints"
            elif current_section and (line[0].isdigit() or line.startswith(('-', '•'))):
                content = line.lstrip('0123456789.-• ').strip()
                if content:
                    insights[current_section].append(content)

        return insights

    def _parse_competitive_analysis(self, text: str) -> Dict[str, Any]:
        """Parse competitive analysis results"""
        analysis = {
            "advantages": [],
            "disadvantages": [],
            "positioning": "competitive"
        }

        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            line_lower = line.lower()
            if "advantage" in line_lower:
                current_section = "advantages"
            elif "disadvantage" in line_lower:
                current_section = "disadvantages"
            elif current_section and (line[0].isdigit() or line.startswith(('-', '•'))):
                content = line.lstrip('0123456789.-• ').strip()
                if content:
                    analysis[current_section].append(content)

        return analysis

    def _calculate_product_score(
        self,
        details: Dict[str, Any],
        reviews: List[Any]
    ) -> int:
        """Calculate overall product score"""
        score = 50  # Base score

        # Rating contribution (0-40 points)
        if "rating" in details:
            rating = float(details["rating"])
            score += int((rating / 5.0) * 40)

        # Review count contribution (0-10 points)
        review_count = len(reviews)
        score += min(10, review_count // 10)

        return min(100, score)

    def _calculate_price_metrics(
        self,
        current_price: float,
        price_history: List[float],
        competitor_prices: List[float]
    ) -> Dict[str, Any]:
        """Calculate price metrics"""
        metrics = {
            "current_price": current_price,
            "value_score": 50
        }

        if price_history:
            metrics["avg_historical_price"] = sum(price_history) / len(price_history)
            metrics["price_trend"] = "stable"
            if current_price < metrics["avg_historical_price"] * 0.9:
                metrics["price_trend"] = "decreasing"
            elif current_price > metrics["avg_historical_price"] * 1.1:
                metrics["price_trend"] = "increasing"

        if competitor_prices:
            metrics["avg_competitor_price"] = sum(competitor_prices) / len(competitor_prices)
            if current_price < metrics["avg_competitor_price"]:
                metrics["value_score"] = 75
            elif current_price > metrics["avg_competitor_price"] * 1.2:
                metrics["value_score"] = 35

        return metrics

    def _calculate_review_metrics(
        self,
        reviews: List[Any],
        rating: float
    ) -> Dict[str, Any]:
        """Calculate review metrics"""
        return {
            "review_count": len(reviews),
            "avg_rating": rating,
            "rating_grade": "A" if rating >= 4.5 else "B" if rating >= 4.0 else "C" if rating >= 3.5 else "D",
            "review_density": "high" if len(reviews) > 100 else "medium" if len(reviews) > 20 else "low"
        }

    def _calculate_competitive_score(
        self,
        target: Dict[str, Any],
        competitors: List[Dict[str, Any]]
    ) -> int:
        """Calculate competitive score"""
        if not competitors:
            return 50

        target_price = target.get("price", 0)
        target_rating = target.get("rating", 0)

        # Compare with competitors
        better_price = sum(1 for c in competitors if target_price < c.get("price", 999999))
        better_rating = sum(1 for c in competitors if target_rating > c.get("rating", 0))

        score = 50
        score += int((better_price / len(competitors)) * 25)
        score += int((better_rating / len(competitors)) * 25)

        return min(100, score)

    def _calculate_market_metrics(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate market metrics"""
        if not products:
            return {}

        prices = [p.get("price", 0) for p in products if p.get("price")]
        ratings = [p.get("rating", 0) for p in products if p.get("rating")]

        metrics = {
            "product_count": len(products)
        }

        if prices:
            metrics.update({
                "avg_price": sum(prices) / len(prices),
                "min_price": min(prices),
                "max_price": max(prices),
                "price_range": max(prices) - min(prices)
            })

        if ratings:
            metrics["avg_rating"] = sum(ratings) / len(ratings)

        return metrics

    def _score_products(
        self,
        products: List[Dict[str, Any]],
        preferences: Dict[str, Any],
        budget: Optional[float]
    ) -> List[Dict[str, Any]]:
        """Score and rank products"""
        scored_products = []

        for product in products:
            score = 0
            price = product.get("price", 0)
            rating = product.get("rating", 0)

            # Budget constraint
            if budget and price > budget:
                continue

            # Rating score (0-50 points)
            score += int((rating / 5.0) * 50)

            # Price score (0-30 points)
            if budget:
                price_ratio = price / budget
                score += int((1 - min(price_ratio, 1)) * 30)

            # Feature matching (0-20 points)
            if preferences:
                # Simple feature matching
                feature_match = 0
                for key, value in preferences.items():
                    if key in product and product[key] == value:
                        feature_match += 5
                score += min(20, feature_match)

            scored_products.append({
                **product,
                "match_score": score
            })

        # Sort by score
        scored_products.sort(key=lambda p: p["match_score"], reverse=True)

        return scored_products
