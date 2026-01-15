"""
Instagram Spider Usage Examples
演示如何使用Instagram平台爬虫的完整4层架构
"""

import asyncio
from omnisense.spider.platforms.instagram import (
    InstagramSpider,
    MatcherConfig,
    MediaType,
    SearchType,
)


async def example_basic_search():
    """示例1: 基本搜索功能"""
    print("\n=== Example 1: Basic Search ===")

    spider = InstagramSpider(headless=False)

    try:
        await spider.start()

        # 按标签搜索
        results = await spider.search(
            keyword="travel",
            search_type=SearchType.HASHTAG,
            max_results=10
        )

        print(f"Found {len(results)} posts:")
        for i, post in enumerate(results[:5], 1):
            print(f"{i}. {post.get('shortcode')} - {post.get('caption', 'No caption')[:50]}...")

    finally:
        await spider.stop()


async def example_user_profile():
    """示例2: 获取用户资料"""
    print("\n=== Example 2: Get User Profile ===")

    spider = InstagramSpider(headless=False)

    try:
        await spider.start()

        # 获取用户资料
        user = await spider.get_user_profile("instagram")

        if user:
            print(f"Username: {user.username}")
            print(f"Full Name: {user.full_name}")
            print(f"Followers: {user.followers_count:,}")
            print(f"Following: {user.following_count:,}")
            print(f"Posts: {user.posts_count:,}")
            print(f"Verified: {user.is_verified}")
            print(f"Bio: {user.biography[:100]}...")

    finally:
        await spider.stop()


async def example_with_matcher():
    """示例3: 使用内容过滤器"""
    print("\n=== Example 3: Content Filtering ===")

    # 配置过滤条件
    matcher_config = MatcherConfig(
        min_likes=1000,           # 至少1000个赞
        min_comments=50,          # 至少50条评论
        min_followers=10000,      # 用户至少10000粉丝
        required_hashtags=["travel", "photography"],  # 必须包含的标签
        excluded_hashtags=["spam", "ad"],  # 排除的标签
        allowed_media_types=[MediaType.IMAGE, MediaType.CAROUSEL],  # 只要图片和轮播
        verified_only=False,      # 不要求认证用户
        min_engagement_rate=2.0,  # 至少2%互动率
    )

    spider = InstagramSpider(headless=False, matcher_config=matcher_config)

    try:
        await spider.start()

        # 获取用户帖子并应用过滤
        posts = await spider.get_user_posts(
            username="natgeo",
            max_posts=20,
            apply_filter=True  # 启用过滤器
        )

        print(f"Found {len(posts)} posts matching criteria:")
        for i, post in enumerate(posts[:5], 1):
            print(f"{i}. Likes: {post.likes_count:,}, Comments: {post.comments_count:,}")
            print(f"   Hashtags: {', '.join(post.hashtags[:5])}")

    finally:
        await spider.stop()


async def example_post_details():
    """示例4: 获取帖子详情和评论"""
    print("\n=== Example 4: Post Details & Comments ===")

    spider = InstagramSpider(headless=False)

    try:
        await spider.start()

        # 首先搜索获取帖子ID
        results = await spider.search("cats", SearchType.HASHTAG, max_results=3)

        if results:
            shortcode = results[0].get('shortcode')
            print(f"\nAnalyzing post: {shortcode}")

            # 获取详细信息
            post = await spider.get_post_detail(shortcode)

            if post:
                print(f"Caption: {post.caption[:100]}...")
                print(f"Likes: {post.likes_count:,}")
                print(f"Comments: {post.comments_count:,}")
                print(f"Media Type: {post.media_type.value}")
                print(f"Media URLs: {len(post.media_urls)}")

                # 获取评论
                comments = await spider.get_comments(shortcode, max_comments=20)
                print(f"\nTop {len(comments)} comments:")
                for i, comment in enumerate(comments[:5], 1):
                    print(f"{i}. @{comment.owner.get('username')}: {comment.text[:50]}...")

    finally:
        await spider.stop()


async def example_interactions():
    """示例5: 互动操作(需要登录)"""
    print("\n=== Example 5: Interactions ===")

    spider = InstagramSpider(headless=False)

    try:
        await spider.start()

        # 登录
        logged_in = await spider.login(
            username="your_username",
            password="your_password",
            two_factor_code=None  # 如果启用了2FA,提供验证码
        )

        if not logged_in:
            print("Login failed!")
            return

        print("Login successful!")

        # 搜索帖子
        results = await spider.search("photography", SearchType.HASHTAG, max_results=5)

        if results and spider.interaction:
            shortcode = results[0].get('shortcode')

            # 点赞
            await spider.interaction.like_post(shortcode)
            print(f"Liked post: {shortcode}")

            # 发表评论
            await spider.interaction.comment_on_post(
                shortcode,
                "Amazing shot! 📸"
            )
            print(f"Commented on post: {shortcode}")

            # 保存帖子
            await spider.interaction.save_post(shortcode)
            print(f"Saved post: {shortcode}")

            # 获取互动统计
            stats = spider.interaction.get_interaction_stats()
            print(f"\nInteraction stats: {stats}")

    finally:
        await spider.stop()


async def example_stories_and_reels():
    """示例6: 获取Stories和Reels"""
    print("\n=== Example 6: Stories & Reels ===")

    spider = InstagramSpider(headless=False)

    try:
        await spider.start()

        # 登录(Stories通常需要登录)
        logged_in = await spider.login(
            username="your_username",
            password="your_password"
        )

        if logged_in:
            # 获取Stories
            stories = await spider.get_stories("instagram")
            print(f"Found {len(stories)} stories")

            # 获取Reels
            reels = await spider.get_reels("instagram", max_reels=10)
            print(f"Found {len(reels)} reels")

            for i, reel in enumerate(reels[:3], 1):
                print(f"{i}. {reel.get('url')}")

    finally:
        await spider.stop()


async def example_media_download():
    """示例7: 批量下载媒体"""
    print("\n=== Example 7: Media Download ===")

    spider = InstagramSpider(headless=False)

    try:
        await spider.start()

        # 获取帖子
        results = await spider.search("nature", SearchType.HASHTAG, max_results=5)

        media_urls = []
        for result in results:
            shortcode = result.get('shortcode')
            post = await spider.get_post_detail(shortcode)

            if post:
                media_urls.extend(post.media_urls)

        # 批量下载
        print(f"\nDownloading {len(media_urls)} media files...")
        downloaded_files = await spider.download_media(media_urls)

        print(f"Successfully downloaded {len(downloaded_files)} files:")
        for file in downloaded_files[:5]:
            print(f"  - {file.name}")

    finally:
        await spider.stop()


async def example_graph_api():
    """示例8: 使用Graph API"""
    print("\n=== Example 8: Graph API ===")

    spider = InstagramSpider(headless=False)

    try:
        # 设置Graph API令牌
        spider.set_graph_api_token("YOUR_ACCESS_TOKEN_HERE")

        # 使用Graph API获取用户信息
        user_data = await spider.graph_api_get_user("USER_ID")
        if user_data:
            print(f"User: {user_data}")

        # 使用Graph API获取媒体
        media = await spider.graph_api_get_media("USER_ID", limit=10)
        print(f"Found {len(media)} media items via Graph API")

    finally:
        # Graph API不需要启动浏览器
        pass


async def example_anti_crawl_features():
    """示例9: 反爬虫功能演示"""
    print("\n=== Example 9: Anti-Crawl Features ===")

    spider = InstagramSpider(
        headless=False,
        proxy="http://proxy.example.com:8080"  # 使用代理
    )

    try:
        await spider.start()

        # 添加多个代理到池
        spider.anti_crawl.add_proxy("http://proxy1.example.com:8080")
        spider.anti_crawl.add_proxy("http://proxy2.example.com:8080")

        # 生成设备指纹
        fingerprint = spider.anti_crawl.generate_device_fingerprint()
        print(f"Device fingerprint: {fingerprint}")

        # 获取API请求头
        headers = spider.anti_crawl.get_api_headers()
        print(f"API headers: {list(headers.keys())}")

        # 搜索时自动应用rate limit
        results = await spider.search("test", SearchType.HASHTAG, max_results=5)

        print(f"\nRequests made: {spider.anti_crawl._request_count}")
        print(f"Rate limit: {spider.anti_crawl._rate_limit_per_hour} requests/hour")

    finally:
        await spider.stop()


async def example_comprehensive_workflow():
    """示例10: 综合工作流"""
    print("\n=== Example 10: Comprehensive Workflow ===")

    # 配置过滤器
    matcher_config = MatcherConfig(
        min_likes=500,
        min_engagement_rate=1.5,
        required_hashtags=["travel"],
        allowed_media_types=[MediaType.IMAGE, MediaType.CAROUSEL]
    )

    spider = InstagramSpider(
        headless=False,
        matcher_config=matcher_config
    )

    try:
        await spider.start()

        # 1. 登录
        print("Step 1: Login...")
        logged_in = await spider.login("username", "password")

        if logged_in:
            # 2. 搜索目标用户
            print("\nStep 2: Search target users...")
            search_results = await spider.search(
                "travel",
                SearchType.HASHTAG,
                max_results=10
            )

            # 3. 分析用户资料
            print("\nStep 3: Analyze user profiles...")
            target_users = set()
            for result in search_results[:5]:
                shortcode = result.get('shortcode')
                post = await spider.get_post_detail(shortcode)
                if post:
                    username = post.owner.get('username')
                    if username:
                        target_users.add(username)

            # 4. 获取并过滤帖子
            print("\nStep 4: Get and filter posts...")
            all_posts = []
            for username in list(target_users)[:3]:
                posts = await spider.get_user_posts(
                    username,
                    max_posts=10,
                    apply_filter=True
                )
                all_posts.extend(posts)

            print(f"Found {len(all_posts)} qualifying posts")

            # 5. 互动(点赞/评论)
            print("\nStep 5: Engage with posts...")
            for post in all_posts[:3]:
                if spider.interaction:
                    # 点赞
                    await spider.interaction.like_post(post.shortcode)

                    # 随机评论
                    comments_pool = [
                        "Great shot!",
                        "Amazing!",
                        "Love this! 😍",
                    ]
                    import random
                    comment = random.choice(comments_pool)
                    await spider.interaction.comment_on_post(post.shortcode, comment)

                await asyncio.sleep(5)  # 避免操作过快

            # 6. 下载优质内容
            print("\nStep 6: Download quality content...")
            download_urls = []
            for post in all_posts[:5]:
                download_urls.extend(post.media_urls)

            downloaded = await spider.download_media(download_urls)
            print(f"Downloaded {len(downloaded)} files")

            # 7. 生成统计报告
            print("\nStep 7: Generate stats...")
            stats = spider.get_stats()
            print(f"Final stats: {stats}")

    finally:
        await spider.stop()


async def main():
    """运行所有示例"""
    print("Instagram Spider - 4 Layer Architecture Examples")
    print("=" * 60)

    # 选择要运行的示例
    examples = [
        ("Basic Search", example_basic_search),
        ("User Profile", example_user_profile),
        ("Content Filtering", example_with_matcher),
        ("Post Details & Comments", example_post_details),
        ("Interactions (Login Required)", example_interactions),
        ("Stories & Reels (Login Required)", example_stories_and_reels),
        ("Media Download", example_media_download),
        ("Graph API", example_graph_api),
        ("Anti-Crawl Features", example_anti_crawl_features),
        ("Comprehensive Workflow", example_comprehensive_workflow),
    ]

    print("\nAvailable Examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")

    print("\nNote: Examples 5 and 6 require login credentials.")
    print("Edit the code to add your credentials before running.")

    # 运行示例1-4(不需要登录)
    print("\n" + "=" * 60)
    print("Running examples that don't require login...")
    print("=" * 60)

    # await example_basic_search()
    # await example_user_profile()
    # await example_with_matcher()
    # await example_post_details()

    print("\nTo run other examples, uncomment the desired function calls in main().")


if __name__ == "__main__":
    asyncio.run(main())
