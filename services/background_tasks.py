"""Background Tasks - 定时爬虫和推荐生成"""

import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime as _dt

from data import calendar_db
from services.content_crawler import arxiv_crawler, github_crawler, huggingface_crawler
from services.recommendation_engine import recommendation_engine
from services.report_generator import generate_reports_for_all_users
from services.profile_extractor import profile_extractor

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """后台任务管理器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._running = False

    def start(self):
        """启动后台任务"""
        if self._running:
            logger.warning("后台任务已在运行")
            return

        self.scheduler.add_job(
            self.run_crawlers,
            IntervalTrigger(hours=6),
            id="periodic_crawl",
            name="Periodic Content Crawl",
            replace_existing=True,
            next_run_time=_dt.now()  # run immediately on startup
        )

        self.scheduler.add_job(
            self.generate_recommendations_for_all_users,
            "date",
            run_date=_dt.now(),
            id="startup_recommendations",
            name="Startup Recommendations",
            replace_existing=True
        )

        self.scheduler.add_job(
            self.generate_recommendations_for_all_users,
            IntervalTrigger(hours=1),
            id="periodic_recommendations",
            name="Generate Recommendations",
            replace_existing=True
        )

        self.scheduler.add_job(
            self.generate_daily_reports,
            IntervalTrigger(hours=24),
            id="daily_reports",
            name="Generate Daily Reports",
            replace_existing=True
        )

        self.scheduler.add_job(
            self.extract_interests_from_chats,
            CronTrigger(hour=2, minute=0),
            id="daily_interest_extraction",
            name="Extract Interests from Chats",
            replace_existing=True
        )

        self.scheduler.start()
        self._running = True
        logger.info("后台任务已启动")

    def shutdown(self):
        """关闭后台任务"""
        if self._running:
            self.scheduler.shutdown()
            self._running = False
            logger.info("后台任务已停止")

    async def run_crawlers(self):
        """运行所有爬虫"""
        logger.info("开始运行爬虫任务")
        
        start_time = datetime.now()
        
        await self._run_arxiv_crawler()

        await self._run_github_crawler()

        await self._run_huggingface_crawler()

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"爬虫任务完成，耗时 {duration:.2f} 秒")

    async def _run_arxiv_crawler(self):
        """运行 arXiv 爬虫，关键词融合用户兴趣"""
        try:
            import json as _json
            base_keywords = ["machine learning", "deep learning", "neural networks",
                             "AI", "large language model", "LLM", "agent", "transformer"]
            base_categories = ["cs.AI", "cs.LG", "cs.CV", "cs.CL"]

            # 从用户兴趣中提取英文关键词补充搜索
            try:
                all_interests = calendar_db.get_user_interests("")
                for interest in all_interests:
                    raw_kw = interest.get("keywords", [])
                    if isinstance(raw_kw, str):
                        try:
                            raw_kw = _json.loads(raw_kw)
                        except Exception:
                            raw_kw = []
                    for kw in raw_kw:
                        if kw and any(c.isascii() and c.isalpha() for c in str(kw)):
                            for part in str(kw).replace(";", ",").split(","):
                                part = part.strip()
                                if part and len(part) > 1:
                                    base_keywords.append(part)
            except Exception:
                pass

            keywords = list(dict.fromkeys(base_keywords))
            categories = base_categories

            papers = await arxiv_crawler.search(
                keywords,
                categories=categories,
                days=7,
                limit=100
            )
            
            saved_count = 0
            for paper in papers:
                result = calendar_db.create_or_update_content(
                    source=paper["source"],
                    source_id=paper["source_id"],
                    title=paper["title"],
                    description=paper["description"],
                    url=paper["url"],
                    author=paper["author"],
                    published_date=paper["published_date"],
                    content_type=paper["content_type"],
                    tags=paper.get("tags", []),
                    stars=paper.get("stars", 0)
                )
                if result:
                    saved_count += 1
            
            calendar_db.log_crawler_run(
                source="arxiv",
                status="success",
                items_found=len(papers),
                items_saved=saved_count
            )
            
            logger.info(f"arXiv: 找到 {len(papers)} 篇论文，保存 {saved_count} 篇")
            
        except Exception as e:
            logger.error(f"arXiv 爬虫错误: {e}")
            calendar_db.log_crawler_run(
                source="arxiv",
                status="failed",
                items_found=0,
                items_saved=0,
                error_message=str(e)
            )

    async def _run_github_crawler(self):
        """运行 GitHub 爬虫"""
        try:
            keywords = ["pytorch", "tensorflow", "machine-learning", "deep-learning"]
            
            repos = await github_crawler.search(
                keywords,
                language="Python",
                days=7,
                limit=50
            )
            
            saved_count = 0
            for repo in repos:
                result = calendar_db.create_or_update_content(
                    source=repo["source"],
                    source_id=repo["source_id"],
                    title=repo["title"],
                    description=repo["description"],
                    url=repo["url"],
                    author=repo["author"],
                    published_date=repo["published_date"],
                    content_type=repo["content_type"],
                    tags=repo.get("tags", []),
                    stars=repo.get("stars", 0)
                )
                if result:
                    saved_count += 1
            
            calendar_db.log_crawler_run(
                source="github",
                status="success",
                items_found=len(repos),
                items_saved=saved_count
            )
            
            logger.info(f"GitHub: 找到 {len(repos)} 个仓库，保存 {saved_count} 个")
            
        except Exception as e:
            logger.error(f"GitHub 爬虫错误: {e}")
            calendar_db.log_crawler_run(
                source="github",
                status="failed",
                items_found=0,
                items_saved=0,
                error_message=str(e)
            )

    async def generate_recommendations_for_all_users(self):
        """为所有用户生成推荐"""
        logger.info("开始生成推荐")
        
        try:
            all_interests = calendar_db.get_user_interests("")
            user_ids = set(i["user_id"] for i in all_interests)
            
            total_recommendations = 0
            for user_id in user_ids:
                stats = await recommendation_engine.generate_recommendations(user_id)
                total_recommendations += stats.get("recommendations_created", 0)
            
            logger.info(f"推荐生成完成，共生成 {total_recommendations} 条推荐")
            
        except Exception as e:
            logger.error(f"推荐生成错误: {e}")

    async def generate_daily_reports(self):
        """为所有用户生成日报"""
        logger.info("开始生成日报")
        
        try:
            stats = await generate_reports_for_all_users()
            logger.info(f"日报生成完成: {stats}")
            
        except Exception as e:
            logger.error(f"日报生成错误: {e}")

    async def extract_interests_from_chats(self):
        """每天凌晨从聊天记录中提取用户兴趣"""
        logger.info("开始从聊天记录提取用户兴趣")
        
        try:
            yesterday = datetime.now().strftime("%Y-%m-%d")
            
            stats = await profile_extractor.extract_interests_from_all_chat_sessions(yesterday)
            logger.info(f"兴趣提取完成: {stats}")
            
        except Exception as e:
            logger.error(f"兴趣提取错误: {e}")

    async def run_once(self):
        """手动触发一次爬虫和推荐"""
        await self.run_crawlers()
        await self.generate_recommendations_for_all_users()
        await self.generate_daily_reports()
        await self.extract_interests_from_chats()


background_manager = BackgroundTaskManager()
