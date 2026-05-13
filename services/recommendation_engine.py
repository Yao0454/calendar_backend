"""Recommendation Engine - 多因子综合评分推荐引擎"""

import logging
import math
from datetime import datetime
from typing import List, Dict

from data import calendar_db

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """多因子综合评分推荐引擎
    
    综合考虑以下因子：
    1. 相关度分数（关键词匹配）
    2. 时间新鲜度（指数衰减）
    3. 流行度分数
    4. 多样性惩罚
    """

    def __init__(self):
        self.min_relevance_score = 0.3
        self.freshness_half_life = 30  # 30天半衰期

    def calculate_relevance(
        self,
        user_interests: List[Dict],
        content: Dict
    ) -> float:
        """计算内容与用户兴趣的相关度
        
        Args:
            user_interests: 用户的兴趣列表
            content: 内容对象
            
        Returns:
            相关度分数 0-1
        """
        if not user_interests:
            return 0.0

        content_text = (
            (content.get("title") or "") + " " +
            (content.get("description") or "")
        ).lower()

        total_score = 0.0
        max_weight = 0.0

        for interest in user_interests:
            weight = interest.get("weight", 1.0)
            max_weight += weight

            keywords = interest.get("keywords", [])
            interest_score = 0.0

            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in content_text:
                    count = content_text.count(keyword_lower)
                    interest_score += min(count * 0.2, 1.0)

            if keywords:
                interest_score = min(interest_score / len(keywords), 1.0)

            total_score += interest_score * weight

        if max_weight > 0:
            return min(total_score / max_weight, 1.0)

        return 0.0

    def calculate_freshness(self, published_date: str | None) -> float:
        """计算时间新鲜度分数（指数衰减）
        
        Args:
            published_date: 发布日期 (YYYY-MM-DD)
            
        Returns:
            新鲜度分数 0-1
        """
        if not published_date:
            return 0.5

        try:
            pub_date = datetime.strptime(published_date, "%Y-%m-%d")
            days_old = (datetime.now() - pub_date).days
            
            freshness = math.exp(-days_old / self.freshness_half_life)
            return max(freshness, 0.0)
        except Exception:
            return 0.5

    def calculate_popularity(self, content: Dict) -> float:
        """计算流行度分数
        
        Args:
            content: 内容对象
            
        Returns:
            流行度分数 0-1
        """
        source = content.get("source", "")
        
        if source == "github":
            stars = content.get("stars", 0)
            return min(math.log10(stars + 1) / 5, 1.0)
        
        elif source == "arxiv":
            return 0.5
        
        return 0.5

    def calculate_diversity(
        self,
        content: Dict,
        recent_recommendations: List[Dict]
    ) -> float:
        """计算多样性分数（惩罚相似内容）
        
        Args:
            content: 当前内容
            recent_recommendations: 最近的推荐列表
            
        Returns:
            多样性分数 0-1
        """
        if not recent_recommendations:
            return 1.0

        similarities = []
        for recent in recent_recommendations[-10:]:
            sim = self._calculate_content_similarity(content, recent)
            similarities.append(sim)

        avg_similarity = sum(similarities) / len(similarities)
        return 1.0 - avg_similarity

    def _calculate_content_similarity(
        self,
        content1: Dict,
        content2: Dict
    ) -> float:
        """计算两个内容的相似度
        
        Args:
            content1: 内容1
            content2: 内容2
            
        Returns:
            相似度 0-1
        """
        tags1 = set(content1.get("tags", []))
        tags2 = set(content2.get("tags", []))
        
        if not tags1 or not tags2:
            return 0.0

        intersection = len(tags1 & tags2)
        union = len(tags1 | tags2)
        
        if union == 0:
            return 0.0

        return intersection / union

    def calculate_final_score(
        self,
        user_interests: List[Dict],
        content: Dict,
        recent_recommendations: List[Dict]
    ) -> float:
        """计算综合评分
        
        综合评分 = 相关度×0.4 + 新鲜度×0.2 + 流行度×0.2 + 多样性×0.2
        
        Args:
            user_interests: 用户兴趣列表
            content: 内容对象
            recent_recommendations: 最近推荐列表
            
        Returns:
            综合评分 0-1
        """
        relevance = self.calculate_relevance(user_interests, content)
        freshness = self.calculate_freshness(content.get("published_date"))
        popularity = self.calculate_popularity(content)
        diversity = self.calculate_diversity(content, recent_recommendations)

        final_score = (
            relevance * 0.4 +
            freshness * 0.2 +
            popularity * 0.2 +
            diversity * 0.2
        )

        return final_score

    def rank_content(
        self,
        user_id: str,
        content_list: List[Dict],
        limit: int = 20
    ) -> List[Dict]:
        """为用户排序和筛选内容
        
        Args:
            user_id: 用户 ID
            content_list: 内容列表
            limit: 返回的最大结果数
            
        Returns:
            排序后的推荐内容列表
        """
        user_interests = calendar_db.get_user_interests(user_id)
        if not user_interests:
            logger.warning(f"用户 {user_id} 没有设置兴趣")
            return []

        existing_recommendations = calendar_db.get_user_recommendations(user_id)
        recent_recommendations = existing_recommendations[:20]

        scored_content = []
        for content in content_list:
            score = self.calculate_final_score(
                user_interests,
                content,
                recent_recommendations
            )
            
            if score >= self.min_relevance_score:
                content_copy = content.copy()
                content_copy["recommendation_score"] = score
                scored_content.append(content_copy)

        scored_content.sort(key=lambda x: x["recommendation_score"], reverse=True)

        return scored_content[:limit]

    async def generate_recommendations(
        self,
        user_id: str
    ) -> Dict:
        """为用户生成推荐
        
        Args:
            user_id: 用户 ID
            
        Returns:
            生成的推荐统计
        """
        user_interests = calendar_db.get_user_interests(user_id)
        if not user_interests:
            return {"status": "skipped", "reason": "用户未设置兴趣"}

        stats = {
            "total_processed": 0,
            "recommendations_created": 0,
            "sources": {}
        }

        sources = ["arxiv", "github"]

        for source in sources:
            all_content = calendar_db.get_content_items(source=source, limit=1000)

            existing = calendar_db.get_user_recommendations(user_id)
            existing_ids = {r.get("content_id") for r in existing}

            new_content = [
                c for c in all_content
                if c["id"] not in existing_ids
            ]

            ranked = self.rank_content(user_id, new_content, limit=50)

            source_count = 0
            for content in ranked:
                score = content.get("recommendation_score", 0.0)
                result = calendar_db.create_recommendation(user_id, content["id"], score)
                if result:
                    source_count += 1

            stats["total_processed"] += len(all_content)
            stats["recommendations_created"] += source_count
            stats["sources"][source] = source_count

        logger.info(f"为用户 {user_id} 生成 {stats['recommendations_created']} 条推荐")
        return stats


recommendation_engine = RecommendationEngine()
