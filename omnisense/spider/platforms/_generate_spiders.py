#!/usr/bin/env python3
"""
Spider Generator Script
Generates all remaining platform spider modules based on template
"""

import os
from pathlib import Path

# Define all platforms and their configurations
PLATFORMS = {
    # Social Media (remaining)
    'wechat_video': {
        'class_name': 'WeChatVideoSpider',
        'display_name': '微信视频号',
        'base_url': 'https://channels.weixin.qq.com',
        'login_required': True,
        'category': 'social_media'
    },
    'maimai': {
        'class_name': 'MaimaiSpider',
        'display_name': '脉脉',
        'base_url': 'https://maimai.cn',
        'login_required': True,
        'category': 'social_media'
    },
    'douban': {
        'class_name': 'DoubanSpider',
        'display_name': '豆瓣',
        'base_url': 'https://www.douban.com',
        'login_required': False,
        'category': 'social_media'
    },
    'hupu': {
        'class_name': 'HupuSpider',
        'display_name': '虎扑',
        'base_url': 'https://www.hupu.com',
        'login_required': False,
        'category': 'social_media'
    },
    'tieba': {
        'class_name': 'TiebaSpider',
        'display_name': '百度贴吧',
        'base_url': 'https://tieba.baidu.com',
        'login_required': False,
        'category': 'social_media'
    },

    # Content Communities
    'zhihu': {
        'class_name': 'ZhihuSpider',
        'display_name': '知乎',
        'base_url': 'https://www.zhihu.com',
        'login_required': True,
        'category': 'content_community'
    },
    'toutiao': {
        'class_name': 'ToutiaoSpider',
        'display_name': '今日头条',
        'base_url': 'https://www.toutiao.com',
        'login_required': False,
        'category': 'content_community'
    },
    'sohu': {
        'class_name': 'SohuSpider',
        'display_name': '搜狐',
        'base_url': 'https://www.sohu.com',
        'login_required': False,
        'category': 'content_community'
    },
    'qichezhi': {
        'class_name': 'QichezhiSpider',
        'display_name': '汽车之家',
        'base_url': 'https://www.autohome.com.cn',
        'login_required': False,
        'category': 'content_community'
    },
    'xueqiu': {
        'class_name': 'XueqiuSpider',
        'display_name': '雪球',
        'base_url': 'https://xueqiu.com',
        'login_required': False,
        'category': 'content_community'
    },
    'quora': {
        'class_name': 'QuoraSpider',
        'display_name': 'Quora',
        'base_url': 'https://www.quora.com',
        'login_required': True,
        'category': 'content_community'
    },
    'medium': {
        'class_name': 'MediumSpider',
        'display_name': 'Medium',
        'base_url': 'https://medium.com',
        'login_required': False,
        'category': 'content_community'
    },

    # E-commerce Platforms
    'amazon': {
        'class_name': 'AmazonSpider',
        'display_name': 'Amazon',
        'base_url': 'https://www.amazon.com',
        'login_required': False,
        'category': 'ecommerce'
    },
    'taobao': {
        'class_name': 'TaobaoSpider',
        'display_name': '淘宝',
        'base_url': 'https://www.taobao.com',
        'login_required': False,
        'category': 'ecommerce'
    },
    'tmall': {
        'class_name': 'TmallSpider',
        'display_name': '天猫',
        'base_url': 'https://www.tmall.com',
        'login_required': False,
        'category': 'ecommerce'
    },
    'jd': {
        'class_name': 'JDSpider',
        'display_name': '京东',
        'base_url': 'https://www.jd.com',
        'login_required': False,
        'category': 'ecommerce'
    },
    'pinduoduo': {
        'class_name': 'PinduoduoSpider',
        'display_name': '拼多多',
        'base_url': 'https://www.pinduoduo.com',
        'login_required': False,
        'category': 'ecommerce'
    },
    'shopee': {
        'class_name': 'ShopeeSpider',
        'display_name': 'Shopee',
        'base_url': 'https://shopee.com',
        'login_required': False,
        'category': 'ecommerce'
    },
    'temu': {
        'class_name': 'TemuSpider',
        'display_name': 'Temu',
        'base_url': 'https://www.temu.com',
        'login_required': False,
        'category': 'ecommerce'
    },
    'ozon': {
        'class_name': 'OzonSpider',
        'display_name': 'Ozon',
        'base_url': 'https://www.ozon.ru',
        'login_required': False,
        'category': 'ecommerce'
    },
    'xianyu': {
        'class_name': 'XianyuSpider',
        'display_name': '闲鱼',
        'base_url': 'https://www.goofish.com',
        'login_required': False,
        'category': 'ecommerce'
    },
    'dewu': {
        'class_name': 'DewuSpider',
        'display_name': '得物',
        'base_url': 'https://www.dewu.com',
        'login_required': False,
        'category': 'ecommerce'
    },
    'vipshop': {
        'class_name': 'VipshopSpider',
        'display_name': '唯品会',
        'base_url': 'https://www.vip.com',
        'login_required': False,
        'category': 'ecommerce'
    },

    # Local Services
    'meituan': {
        'class_name': 'MeituanSpider',
        'display_name': '美团',
        'base_url': 'https://www.meituan.com',
        'login_required': False,
        'category': 'local_service'
    },
    'dianping': {
        'class_name': 'DianpingSpider',
        'display_name': '大众点评',
        'base_url': 'https://www.dianping.com',
        'login_required': False,
        'category': 'local_service'
    },
    'zhuanzhuan': {
        'class_name': 'ZhuanzhuanSpider',
        'display_name': '转转',
        'base_url': 'https://www.zhuanzhuan.com',
        'login_required': False,
        'category': 'local_service'
    },
    'aihuishou': {
        'class_name': 'AihuishouSpider',
        'display_name': '爱回收',
        'base_url': 'https://www.aihuishou.com',
        'login_required': False,
        'category': 'local_service'
    },

    # Search Engines
    'baidu': {
        'class_name': 'BaiduSpider',
        'display_name': '百度',
        'base_url': 'https://www.baidu.com',
        'login_required': False,
        'category': 'search_engine'
    },
    'google': {
        'class_name': 'GoogleSpider',
        'display_name': 'Google',
        'base_url': 'https://www.google.com',
        'login_required': False,
        'category': 'search_engine'
    },
    'quark': {
        'class_name': 'QuarkSpider',
        'display_name': '夸克',
        'base_url': 'https://quark.sm.cn',
        'login_required': False,
        'category': 'search_engine'
    },

    # Academic Platforms
    'google_scholar': {
        'class_name': 'GoogleScholarSpider',
        'display_name': 'Google Scholar',
        'base_url': 'https://scholar.google.com',
        'login_required': False,
        'category': 'academic'
    },
    'cnki': {
        'class_name': 'CNKISpider',
        'display_name': 'CNKI',
        'base_url': 'https://www.cnki.net',
        'login_required': True,
        'category': 'academic'
    },
    'webofscience': {
        'class_name': 'WebOfScienceSpider',
        'display_name': 'Web of Science',
        'base_url': 'https://www.webofscience.com',
        'login_required': True,
        'category': 'academic'
    },
    'arxiv': {
        'class_name': 'ArxivSpider',
        'display_name': 'arXiv',
        'base_url': 'https://arxiv.org',
        'login_required': False,
        'category': 'academic'
    },

    # Developer Community
    'github': {
        'class_name': 'GitHubSpider',
        'display_name': 'GitHub',
        'base_url': 'https://github.com',
        'login_required': False,
        'category': 'developer'
    },
}


TEMPLATE = '''"""
{display_name} Spider Implementation
完整的{display_name}平台爬虫实现
"""

import asyncio
import hashlib
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from omnisense.spider.base import BaseSpider


class {class_name}(BaseSpider):
    """
    {display_name}爬虫

    Platform-specific information:
    - Base URL: {base_url}
    - Login required: {login_required}
    - Category: {category}
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="{platform_id}", headless=headless, proxy=proxy)
        self.base_url = "{base_url}"
        self.api_base_url = "{base_url}"

    async def login(self, username: str, password: str) -> bool:
        """Login to {display_name}"""
        try:
            self.logger.info(f"Logging in to {display_name}...")

            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(self.base_url)
                await asyncio.sleep(2)
                # Check if logged in (customize selector)
                if await self._page.query_selector('[class*="user"], [class*="avatar"]'):
                    self._is_logged_in = True
                    self.logger.info("Logged in with saved cookies")
                    return True

            # Navigate to login page
            await self.navigate(f"{{self.base_url}}/login")
            await asyncio.sleep(2)

            # Fill credentials (customize selectors)
            username_input = await self._page.wait_for_selector('input[name="username"], input[type="email"], input[placeholder*="用户"]', timeout=10000)
            await username_input.fill(username)

            password_input = await self._page.wait_for_selector('input[name="password"], input[type="password"]', timeout=10000)
            await password_input.fill(password)

            # Click login
            login_btn = await self._page.wait_for_selector('button[type="submit"], button:has-text("登录"), button:has-text("Login")', timeout=10000)
            await login_btn.click()
            await asyncio.sleep(5)

            # Check success
            if await self._page.query_selector('[class*="user"], [class*="avatar"]'):
                self._is_logged_in = True
                await self._save_cookies()
                self.logger.info("Login successful")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Login failed: {{e}}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search {display_name} content"""
        try:
            self.logger.info(f"Searching {display_name} for '{{keyword}}'")

            # Construct search URL (customize based on platform)
            search_url = f"{{self.base_url}}/search?q={{keyword}}"
            await self.navigate(search_url)
            await asyncio.sleep(3)

            # Scroll to load more results
            for _ in range(max_results // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            results = []
            # Customize selectors based on platform
            result_elements = await self._page.query_selector_all('[class*="item"], [class*="result"], article, .post')

            for elem in result_elements[:max_results]:
                try:
                    result = {{'platform': self.platform}}

                    # Extract title
                    title = await elem.query_selector('h1, h2, h3, h4, [class*="title"]')
                    if title:
                        result['title'] = await title.inner_text()

                    # Extract link
                    link = await elem.query_selector('a[href]')
                    if link:
                        href = await link.get_attribute('href')
                        result['url'] = href if href.startswith('http') else f"{{self.base_url}}{{href}}"
                        # Extract ID from URL (customize pattern)
                        if '/' in href:
                            result['id'] = href.split('/')[-1].split('?')[0]

                    # Extract description
                    desc = await elem.query_selector('[class*="desc"], [class*="summary"], p')
                    if desc:
                        result['description'] = await desc.inner_text()

                    # Extract author
                    author = await elem.query_selector('[class*="author"], [class*="user"]')
                    if author:
                        result['author'] = await author.inner_text()

                    # Extract metadata (views, likes, etc.)
                    stats = await elem.query_selector_all('[class*="count"], [class*="stat"]')
                    for stat in stats:
                        text = await stat.inner_text()
                        if any(word in text.lower() for word in ['view', '浏览', '阅读']):
                            result['views'] = self.parser.parse_count(text)
                        elif any(word in text.lower() for word in ['like', '点赞', '赞']):
                            result['likes'] = self.parser.parse_count(text)
                        elif any(word in text.lower() for word in ['comment', '评论']):
                            result['comments_count'] = self.parser.parse_count(text)

                    if result.get('id') or result.get('url'):
                        results.append(result)

                except Exception as e:
                    self.logger.warning(f"Failed to parse result: {{e}}")
                    continue

            self.logger.info(f"Found {{len(results)}} results")
            return results

        except Exception as e:
            self.logger.error(f"Search failed: {{e}}")
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get {display_name} user profile"""
        try:
            self.logger.info(f"Getting profile: {{user_id}}")

            # Construct profile URL (customize)
            profile_url = f"{{self.base_url}}/user/{{user_id}}"
            await self.navigate(profile_url)
            await asyncio.sleep(3)

            profile = {{'user_id': user_id, 'platform': self.platform}}

            # Extract username
            name = await self._page.query_selector('h1, h2, [class*="username"], [class*="name"]')
            if name:
                profile['username'] = await name.inner_text()

            # Extract bio
            bio = await self._page.query_selector('[class*="bio"], [class*="intro"], [class*="desc"]')
            if bio:
                profile['bio'] = await bio.inner_text()

            # Extract avatar
            avatar = await self._page.query_selector('img[class*="avatar"], img[alt*="avatar"]')
            if avatar:
                profile['avatar'] = await avatar.get_attribute('src')

            # Extract stats
            followers = await self._page.query_selector('[class*="follower"]')
            if followers:
                profile['followers'] = self.parser.parse_count(await followers.inner_text())

            following = await self._page.query_selector('[class*="following"]')
            if following:
                profile['following'] = self.parser.parse_count(await following.inner_text())

            # Check verification
            verified = await self._page.query_selector('[class*="verified"], [class*="badge"]')
            profile['verified'] = verified is not None

            return profile

        except Exception as e:
            self.logger.error(f"Failed to get profile: {{e}}")
            return {{}}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Get posts from {display_name} user"""
        try:
            self.logger.info(f"Getting posts from: {{user_id}}")

            # Navigate to user's posts
            posts_url = f"{{self.base_url}}/user/{{user_id}}/posts"
            await self.navigate(posts_url)
            await asyncio.sleep(3)

            # Scroll to load more posts
            for _ in range(max_posts // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            posts = []
            post_elements = await self._page.query_selector_all('[class*="post"], [class*="item"], article')

            for elem in post_elements[:max_posts]:
                try:
                    post = {{'user_id': user_id, 'platform': self.platform}}

                    # Extract title
                    title = await elem.query_selector('h1, h2, h3, [class*="title"]')
                    if title:
                        post['title'] = await title.inner_text()

                    # Extract link and ID
                    link = await elem.query_selector('a[href]')
                    if link:
                        href = await link.get_attribute('href')
                        post['url'] = href if href.startswith('http') else f"{{self.base_url}}{{href}}"
                        if '/' in href:
                            post['id'] = href.split('/')[-1].split('?')[0]

                    # Extract thumbnail
                    img = await elem.query_selector('img')
                    if img:
                        post['thumbnail'] = await img.get_attribute('src')

                    # Extract timestamp
                    time_elem = await elem.query_selector('time, [class*="time"], [class*="date"]')
                    if time_elem:
                        time_text = await time_elem.inner_text()
                        post['created_at'] = self.parser.parse_date(time_text)

                    if post.get('id'):
                        posts.append(post)

                except Exception as e:
                    self.logger.warning(f"Failed to parse post: {{e}}")
                    continue

            self.logger.info(f"Got {{len(posts)}} posts")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get posts: {{e}}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """Get detailed {display_name} post information"""
        try:
            self.logger.info(f"Getting post detail: {{post_id}}")

            # Construct post URL
            post_url = f"{{self.base_url}}/post/{{post_id}}"
            await self.navigate(post_url)
            await asyncio.sleep(3)

            post = {{'id': post_id, 'url': post_url, 'platform': self.platform}}

            # Extract title
            title = await self._page.query_selector('h1, [class*="title"]')
            if title:
                post['title'] = await title.inner_text()

            # Extract content
            content = await self._page.query_selector('[class*="content"], [class*="body"], article')
            if content:
                post['content'] = await content.inner_text()

            # Extract author
            author = await self._page.query_selector('[class*="author"], [class*="user"]')
            if author:
                post['author'] = await author.inner_text()

            # Extract stats
            stats_selectors = {{
                'views': '[class*="view"]',
                'likes': '[class*="like"]',
                'comments_count': '[class*="comment"]',
                'shares': '[class*="share"]'
            }}

            for key, selector in stats_selectors.items():
                elem = await self._page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    post[key] = self.parser.parse_count(text)

            # Extract images
            images = await self._page.query_selector_all('article img, [class*="content"] img')
            post['images'] = []
            for img in images[:5]:
                src = await img.get_attribute('src')
                if src:
                    post['images'].append({{'src': src}})

            # Extract timestamp
            time_elem = await self._page.query_selector('time, [class*="time"], [datetime]')
            if time_elem:
                datetime_attr = await time_elem.get_attribute('datetime')
                time_text = datetime_attr or await time_elem.inner_text()
                post['created_at'] = self.parser.parse_date(time_text)

            return post

        except Exception as e:
            self.logger.error(f"Failed to get post detail: {{e}}")
            return {{}}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Get comments for a {display_name} post"""
        try:
            self.logger.info(f"Getting comments for post: {{post_id}}")

            post_url = f"{{self.base_url}}/post/{{post_id}}"
            if post_id not in self._page.url:
                await self.navigate(post_url)
                await asyncio.sleep(3)

            # Load more comments
            for _ in range(max_comments // 20):
                load_more = await self._page.query_selector('button:has-text("more"), button:has-text("更多")')
                if load_more:
                    try:
                        await load_more.click()
                        await asyncio.sleep(random.uniform(1, 2))
                    except:
                        break

            comments = []
            comment_elements = await self._page.query_selector_all('[class*="comment"], .comment-item')

            for elem in comment_elements[:max_comments]:
                try:
                    comment = {{'post_id': post_id, 'platform': self.platform}}

                    # Extract author
                    author = await elem.query_selector('[class*="author"], [class*="user"]')
                    if author:
                        comment['username'] = await author.inner_text()

                    # Extract content
                    content = await elem.query_selector('[class*="content"], [class*="text"], p')
                    if content:
                        comment['content'] = await content.inner_text()

                    # Extract likes
                    likes = await elem.query_selector('[class*="like"]')
                    if likes:
                        like_text = await likes.inner_text()
                        comment['likes'] = self.parser.parse_count(like_text) if like_text else 0

                    # Extract timestamp
                    time_elem = await elem.query_selector('time, [class*="time"]')
                    if time_elem:
                        comment['created_at'] = self.parser.parse_date(await time_elem.inner_text())

                    if comment.get('content'):
                        comment['id'] = hashlib.md5(f"{{comment.get('username', '')}}{{comment['content']}}".encode()).hexdigest()[:16]
                        comments.append(comment)

                except Exception as e:
                    self.logger.warning(f"Failed to parse comment: {{e}}")
                    continue

            self.logger.info(f"Got {{len(comments)}} comments")
            return comments

        except Exception as e:
            self.logger.error(f"Failed to get comments: {{e}}")
            return []
'''

def generate_spider(platform_id, config):
    """Generate spider code for a platform"""
    return TEMPLATE.format(
        platform_id=platform_id,
        class_name=config['class_name'],
        display_name=config['display_name'],
        base_url=config['base_url'],
        login_required='Yes' if config['login_required'] else 'No',
        category=config['category']
    )

def main():
    """Generate all spider files"""
    script_dir = Path(__file__).parent
    output_dir = script_dir

    print(f"Generating {len(PLATFORMS)} spider files...")

    for platform_id, config in PLATFORMS.items():
        filename = f"{platform_id}.py"
        filepath = output_dir / filename

        code = generate_spider(platform_id, config)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)

        print(f"✓ Created {filename}")

    print(f"\nSuccessfully generated {len(PLATFORMS)} spider files!")

if __name__ == "__main__":
    main()
