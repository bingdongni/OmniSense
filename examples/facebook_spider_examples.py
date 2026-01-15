"""
Facebook Spider 快速开始示例
演示如何使用Facebook爬虫的各项功能
"""

import asyncio
import json
from datetime import datetime, timedelta
from omnisense.spider.platforms.facebook import FacebookSpider


# ============================================================================
# 示例1: 基础使用 - 搜索和数据采集
# ============================================================================

async def example_basic_search():
    """基础搜索示例"""
    print("\n" + "="*60)
    print("示例1: 基础搜索和数据采集")
    print("="*60)

    spider = FacebookSpider(headless=False)

    try:
        await spider.start()

        # 登录（首次使用）
        print("\n登录中...")
        login_success = await spider.login(
            username="your_email@example.com",
            password="your_password"
        )

        if not login_success:
            print("登录失败，请检查凭证")
            return

        # 搜索帖子
        print("\n搜索帖子...")
        posts = await spider.search(
            keyword="artificial intelligence",
            max_results=20,
            search_type="posts",
            time_range="week"
        )

        print(f"\n找到 {len(posts)} 条帖子:")
        for i, post in enumerate(posts[:5], 1):
            print(f"\n{i}. 帖子ID: {post.get('id', 'N/A')}")
            print(f"   作者: {post.get('author', 'N/A')}")
            print(f"   内容: {post.get('content', '')[:100]}...")
            print(f"   点赞: {post.get('likes', 0)}")
            print(f"   评论: {post.get('comments', 0)}")
            print(f"   分享: {post.get('shares', 0)}")
            print(f"   类型: {post.get('type', 'text')}")

    finally:
        await spider.stop()


# ============================================================================
# 示例2: Graph API使用
# ============================================================================

async def example_graph_api():
    """Graph API使用示例"""
    print("\n" + "="*60)
    print("示例2: 使用Graph API")
    print("="*60)

    spider = FacebookSpider(headless=True)

    try:
        await spider.start()

        # 配置Graph API凭证
        print("\n配置Graph API...")
        spider.anti_crawl.set_graph_api_credentials(
            app_id="your_app_id",
            app_secret="your_app_secret"
        )

        # 获取访问令牌
        token = await spider.anti_crawl.get_access_token()
        if token:
            print(f"成功获取访问令牌: {token[:20]}...")

            # 使用Graph API获取用户信息
            print("\n获取用户资料...")
            profile = await spider.get_user_profile("zuckerberg")
            print(f"用户名: {profile.get('username', 'N/A')}")
            print(f"粉丝数: {profile.get('followers', 0)}")
            print(f"好友数: {profile.get('friends', 0)}")
            print(f"验证状态: {profile.get('verified', False)}")

            # 获取用户帖子
            print("\n获取用户帖子...")
            posts = await spider.get_user_posts("zuckerberg", max_posts=10)
            print(f"找到 {len(posts)} 条帖子")

            for i, post in enumerate(posts[:3], 1):
                print(f"\n{i}. {post.get('content', '')[:80]}...")
                print(f"   点赞: {post.get('likes', 0)}")
                print(f"   评论: {post.get('comments', 0)}")
        else:
            print("无法获取访问令牌，请检查凭证")

    finally:
        await spider.stop()


# ============================================================================
# 示例3: 使用匹配器过滤数据
# ============================================================================

async def example_with_filters():
    """使用匹配器过滤示例"""
    print("\n" + "="*60)
    print("示例3: 使用匹配器过滤数据")
    print("="*60)

    spider = FacebookSpider(headless=True)

    try:
        await spider.start()
        await spider.login("your_email@example.com", "your_password")

        # 配置多个过滤器
        print("\n配置过滤器:")
        print("- 最小点赞数: 500")
        print("- 最小评论数: 20")
        print("- 帖子类型: 仅视频")
        print("- 关键词包含: AI, technology")
        print("- 关键词排除: spam")

        spider.matcher.set_filter('likes', min=500)
        spider.matcher.set_filter('comments', min=20)
        spider.matcher.set_filter('post_type', types=['video'])
        spider.matcher.set_filter('keywords',
            include=['AI', 'technology'],
            exclude=['spam']
        )

        # 搜索（自动应用过滤器）
        print("\n开始搜索...")
        posts = await spider.search(
            keyword="AI technology",
            max_results=50
        )

        print(f"\n找到 {len(posts)} 条符合条件的帖子:")
        for i, post in enumerate(posts[:5], 1):
            print(f"\n{i}. {post.get('content', '')[:80]}...")
            print(f"   点赞: {post.get('likes', 0)}")
            print(f"   评论: {post.get('comments', 0)}")
            print(f"   类型: {post.get('type', 'N/A')}")

        # 清除过滤器
        spider.matcher.clear_filters()
        print("\n已清除所有过滤器")

    finally:
        await spider.stop()


# ============================================================================
# 示例4: 互动操作
# ============================================================================

async def example_interactions():
    """互动操作示例"""
    print("\n" + "="*60)
    print("示例4: 互动操作（点赞、评论、分享）")
    print("="*60)

    spider = FacebookSpider(headless=False)

    try:
        await spider.start()
        await spider.login("your_email@example.com", "your_password")

        # 搜索帖子
        print("\n搜索帖子...")
        posts = await spider.search("tech news", max_results=5)

        if posts:
            post_id = posts[0].get('id')
            print(f"\n对帖子 {post_id} 进行互动:")

            # 点赞
            print("- 点赞...")
            success = await spider.interaction.like_post(
                post_id,
                reaction_type="love"
            )
            print(f"  {'成功' if success else '失败'}")

            # 评论
            print("- 评论...")
            success = await spider.interaction.comment_on_post(
                post_id,
                "Very interesting! Thanks for sharing."
            )
            print(f"  {'成功' if success else '失败'}")

            # 分享
            print("- 分享...")
            success = await spider.interaction.share_post(
                post_id,
                share_type="timeline",
                message="Must read!"
            )
            print(f"  {'成功' if success else '失败'}")

        # 其他互动
        print("\n其他互动操作:")

        # 关注页面
        print("- 关注页面...")
        success = await spider.interaction.follow_page("techcrunch")
        print(f"  {'成功' if success else '失败'}")

        # 加入群组
        print("- 加入群组...")
        success = await spider.interaction.join_group("ai.developers")
        print(f"  {'成功' if success else '失败'}")

    finally:
        await spider.stop()


# ============================================================================
# 示例5: 完整数据采集流程
# ============================================================================

async def example_full_scraping():
    """完整数据采集示例"""
    print("\n" + "="*60)
    print("示例5: 完整数据采集流程")
    print("="*60)

    spider = FacebookSpider(headless=True)

    try:
        await spider.start()
        await spider.login("your_email@example.com", "your_password")

        # 配置代理池（可选）
        print("\n配置代理池...")
        # spider.anti_crawl.add_proxy_to_pool("http://proxy1:8080")
        # spider.anti_crawl.add_proxy_to_pool("http://proxy2:8080")

        # 配置时间范围过滤器
        print("配置过滤器...")
        spider.matcher.set_filter('time_range',
            start=datetime.now() - timedelta(days=7),
            end=datetime.now()
        )
        spider.matcher.set_filter('likes', min=100)

        # 搜索用户
        print("\n搜索用户...")
        users = await spider.search(
            keyword="AI researcher",
            search_type="people",
            max_results=5
        )

        all_data = []

        # 采集每个用户的数据
        for i, user in enumerate(users, 1):
            user_id = user.get('user_id')
            print(f"\n处理用户 {i}/{len(users)}: {user_id}")

            # 获取用户资料
            print("  - 获取用户资料...")
            profile = await spider.get_user_profile(user_id)

            # 获取用户帖子
            print("  - 获取用户帖子...")
            posts = await spider.get_user_posts(user_id, max_posts=10)

            user_data = {
                'profile': profile,
                'posts': []
            }

            # 获取每个帖子的详情
            for j, post in enumerate(posts[:3], 1):
                post_id = post.get('id')
                print(f"    - 处理帖子 {j}/{min(len(posts), 3)}")

                # 帖子详情
                detail = await spider.get_post_detail(post_id)

                # 评论
                comments = await spider.get_comments(post_id, max_comments=20)
                detail['comments_data'] = comments

                user_data['posts'].append(detail)

            all_data.append(user_data)

            # IP轮换（如果配置了代理池）
            # await spider.anti_crawl.rotate_ip()

        # 保存数据
        output_file = 'facebook_data.json'
        print(f"\n保存数据到 {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)

        print(f"\n采集完成!")
        print(f"- 用户数: {len(users)}")
        print(f"- 总帖子数: {sum(len(u['posts']) for u in all_data)}")
        print(f"- 数据文件: {output_file}")

    finally:
        await spider.stop()


# ============================================================================
# 示例6: 群组和页面监控
# ============================================================================

async def example_monitor():
    """群组和页面监控示例"""
    print("\n" + "="*60)
    print("示例6: 群组和页面监控")
    print("="*60)

    spider = FacebookSpider(headless=True)

    try:
        await spider.start()
        await spider.login("your_email@example.com", "your_password")

        # 监控群组
        print("\n监控群组:")
        group_ids = ["ai.developers", "machine.learning", "tech.news"]

        for group_id in group_ids[:2]:  # 监控前2个群组
            print(f"\n群组: {group_id}")

            # 获取群组帖子
            posts = await spider.get_group_posts(group_id, max_posts=10)
            print(f"  找到 {len(posts)} 条帖子")

            # 统计热门帖子
            hot_posts = [p for p in posts if p.get('likes', 0) > 100]
            print(f"  热门帖子: {len(hot_posts)}")

            # 对热门帖子进行互动
            for post in hot_posts[:2]:
                await spider.interaction.like_post(post['id'])
                print(f"  已点赞帖子: {post['id']}")

        # 监控页面
        print("\n监控页面:")
        page_ids = ["techcrunch", "wired", "theverge"]

        for page_id in page_ids:
            print(f"\n页面: {page_id}")

            # 获取页面信息
            page_info = await spider.get_page_info(page_id)
            print(f"  名称: {page_info.get('name', 'N/A')}")
            print(f"  关注数: {page_info.get('followers', 0)}")
            print(f"  分类: {page_info.get('category', 'N/A')}")

            # 关注页面
            await spider.interaction.follow_page(page_id)
            print(f"  已关注页面")

            # 获取最新帖子
            posts = await spider.get_user_posts(page_id, max_posts=5)
            print(f"  最新 {len(posts)} 条帖子:")
            for i, post in enumerate(posts[:3], 1):
                print(f"    {i}. {post.get('content', '')[:60]}...")
                print(f"       点赞: {post.get('likes', 0)}")

    finally:
        await spider.stop()


# ============================================================================
# 示例7: 评论和回复分析
# ============================================================================

async def example_comment_analysis():
    """评论和回复分析示例"""
    print("\n" + "="*60)
    print("示例7: 评论和回复分析")
    print("="*60)

    spider = FacebookSpider(headless=True)

    try:
        await spider.start()
        await spider.login("your_email@example.com", "your_password")

        # 搜索热门帖子
        print("\n搜索热门帖子...")
        spider.matcher.set_filter('likes', min=1000)
        posts = await spider.search("technology", max_results=5)

        for i, post in enumerate(posts[:2], 1):
            post_id = post.get('id')
            print(f"\n分析帖子 {i}: {post_id}")
            print(f"内容: {post.get('content', '')[:100]}...")

            # 获取评论
            comments = await spider.get_comments(post_id, max_comments=100)
            print(f"评论数: {len(comments)}")

            # 统计分析
            total_likes = sum(c.get('likes', 0) for c in comments)
            avg_likes = total_likes / len(comments) if comments else 0

            print(f"\n评论统计:")
            print(f"- 总评论数: {len(comments)}")
            print(f"- 总点赞数: {total_likes}")
            print(f"- 平均点赞: {avg_likes:.2f}")

            # 找出热门评论
            hot_comments = sorted(
                comments,
                key=lambda x: x.get('likes', 0),
                reverse=True
            )[:5]

            print(f"\n热门评论 Top 5:")
            for j, comment in enumerate(hot_comments, 1):
                print(f"{j}. {comment.get('username', 'N/A')}")
                print(f"   内容: {comment.get('content', '')[:80]}...")
                print(f"   点赞: {comment.get('likes', 0)}")

    finally:
        await spider.stop()


# ============================================================================
# 主函数 - 运行所有示例
# ============================================================================

async def main():
    """运行所有示例"""
    print("\n" + "="*60)
    print("Facebook Spider 示例程序")
    print("="*60)

    examples = {
        "1": ("基础搜索", example_basic_search),
        "2": ("Graph API使用", example_graph_api),
        "3": ("使用匹配器", example_with_filters),
        "4": ("互动操作", example_interactions),
        "5": ("完整采集流程", example_full_scraping),
        "6": ("群组和页面监控", example_monitor),
        "7": ("评论分析", example_comment_analysis),
    }

    print("\n可用示例:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print("  0. 运行所有示例")

    choice = input("\n请选择要运行的示例 (0-7): ").strip()

    if choice == "0":
        # 运行所有示例
        for key, (name, func) in examples.items():
            try:
                await func()
            except Exception as e:
                print(f"\n示例 {key} 运行出错: {e}")
                import traceback
                traceback.print_exc()
            print("\n" + "-"*60)
    elif choice in examples:
        # 运行单个示例
        name, func = examples[choice]
        try:
            await func()
        except Exception as e:
            print(f"\n示例运行出错: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("无效选择")


if __name__ == "__main__":
    print("\n注意:")
    print("1. 请先修改代码中的登录凭证（邮箱和密码）")
    print("2. 如果使用Graph API，请配置App ID和Secret")
    print("3. 首次运行建议使用 headless=False 查看浏览器操作")
    print("4. 请遵守Facebook服务条款，合理使用")

    input("\n按Enter键继续...")

    asyncio.run(main())
