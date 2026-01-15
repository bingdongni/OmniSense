"""
Douyin Spider Example Script
演示如何使用抖音爬虫的各项功能

Usage:
    python examples/douyin_example.py
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from omnisense.spider.platforms import DouyinSpider, search_douyin_videos


async def example_1_basic_search():
    """示例1: 基础视频搜索"""
    print("\n" + "="*50)
    print("Example 1: Basic Video Search")
    print("="*50)

    spider = DouyinSpider(headless=True)

    async with spider.session():
        videos = await spider.search(
            keyword="人工智能",
            max_results=5
        )

        print(f"\nFound {len(videos)} videos:")
        for i, video in enumerate(videos, 1):
            print(f"\n{i}. {video.get('title', 'N/A')}")
            print(f"   Author: {video.get('author', {}).get('nickname', 'N/A')}")
            print(f"   Likes: {video.get('like_count', 0):,}")
            print(f"   Views: {video.get('view_count', 0):,}")
            print(f"   Comments: {video.get('comment_count', 0):,}")
            print(f"   URL: {video.get('url', 'N/A')}")


async def example_2_search_with_criteria():
    """示例2: 带条件的搜索"""
    print("\n" + "="*50)
    print("Example 2: Search with Filtering Criteria")
    print("="*50)

    spider = DouyinSpider(headless=True)

    # 定义筛选条件
    criteria = {
        'keywords': ['Python', '编程', '教程'],
        'min_likes': 1000,
        'min_views': 10000,
        'match_threshold': 0.3
    }

    async with spider.session():
        videos = await spider.search(
            keyword="Python教程",
            max_results=10,
            criteria=criteria
        )

        print(f"\nFound {len(videos)} videos matching criteria:")
        for i, video in enumerate(videos, 1):
            print(f"\n{i}. {video.get('title', 'N/A')}")
            print(f"   Match Score: {video.get('match_score', 0):.2f}")
            print(f"   Likes: {video.get('like_count', 0):,}")
            print(f"   Hashtags: {', '.join(video.get('hashtags', []))}")


async def example_3_get_user_videos():
    """示例3: 获取用户视频"""
    print("\n" + "="*50)
    print("Example 3: Get User Videos")
    print("="*50)

    spider = DouyinSpider(headless=True)

    # 注意: 替换为真实的用户ID
    user_id = "MS4wLjABAAAA..."

    async with spider.session():
        # 获取用户资料
        profile = await spider.get_user_profile(user_id)

        print(f"\nUser Profile:")
        print(f"  Nickname: {profile.get('nickname', 'N/A')}")
        print(f"  Douyin ID: {profile.get('douyin_id', 'N/A')}")
        print(f"  Followers: {profile.get('follower_count', 0):,}")
        print(f"  Following: {profile.get('following_count', 0):,}")
        print(f"  Total Likes: {profile.get('total_likes', 0):,}")
        print(f"  Videos: {profile.get('video_count', 0)}")

        # 获取用户视频
        videos = await spider.get_user_posts(
            user_id=user_id,
            max_posts=5
        )

        print(f"\nLatest {len(videos)} videos:")
        for i, video in enumerate(videos, 1):
            print(f"\n{i}. {video.get('title', 'N/A')}")
            print(f"   Published: {video.get('publish_time', 'N/A')}")
            print(f"   Likes: {video.get('like_count', 0):,}")


async def example_4_get_comments():
    """示例4: 获取视频评论"""
    print("\n" + "="*50)
    print("Example 4: Get Video Comments")
    print("="*50)

    spider = DouyinSpider(headless=True)

    async with spider.session():
        # 先搜索一个视频
        videos = await spider.search("AI", max_results=1)

        if not videos:
            print("No videos found")
            return

        video = videos[0]
        video_id = video.get('content_id')

        print(f"\nVideo: {video.get('title')}")
        print(f"Comments: {video.get('comment_count', 0):,}")

        # 获取评论
        comments = await spider.get_comments(
            post_id=video_id,
            max_comments=20,
            include_replies=True
        )

        print(f"\nCollected {len(comments)} comments:")
        for i, comment in enumerate(comments[:5], 1):  # 只显示前5条
            print(f"\n{i}. {comment.get('user', {}).get('nickname', 'Anonymous')}")
            print(f"   {comment.get('text', '')}")
            print(f"   ❤️ {comment.get('like_count', 0)}")

            # 显示回复
            replies = comment.get('replies', [])
            if replies:
                print(f"   📝 {len(replies)} replies:")
                for reply in replies[:2]:  # 只显示前2条回复
                    print(f"      └─ {reply.get('user', {}).get('nickname')}: {reply.get('text')}")


async def example_5_topic_videos():
    """示例5: 获取话题视频"""
    print("\n" + "="*50)
    print("Example 5: Get Topic Videos")
    print("="*50)

    spider = DouyinSpider(headless=True)

    async with spider.session():
        videos = await spider.get_topic_videos(
            topic="人工智能",
            max_videos=5
        )

        print(f"\nFound {len(videos)} videos for #人工智能:")
        for i, video in enumerate(videos, 1):
            print(f"\n{i}. {video.get('title', 'N/A')}")
            print(f"   Hashtags: {', '.join(video.get('hashtags', []))}")
            print(f"   Likes: {video.get('like_count', 0):,}")


async def example_6_download_video():
    """示例6: 下载视频"""
    print("\n" + "="*50)
    print("Example 6: Download Video")
    print("="*50)

    spider = DouyinSpider(headless=True)

    async with spider.session():
        # 搜索视频
        videos = await spider.search("Python", max_results=1)

        if not videos:
            print("No videos found")
            return

        video = videos[0]
        print(f"\nVideo: {video.get('title')}")

        # 下载视频
        if video.get('video_url'):
            download_path = await spider.download_video(
                video_url=video['video_url'],
                save_path=f"downloads/{video['content_id']}.mp4"
            )

            if download_path:
                print(f"✅ Downloaded to: {download_path}")
            else:
                print("❌ Download failed")
        else:
            print("❌ No video URL available")


async def example_7_convenience_functions():
    """示例7: 使用便捷函数"""
    print("\n" + "="*50)
    print("Example 7: Using Convenience Functions")
    print("="*50)

    # 使用便捷函数搜索
    videos = await search_douyin_videos(
        keyword="机器学习",
        max_results=5,
        headless=True,
        criteria={'min_likes': 500}
    )

    print(f"\nFound {len(videos)} videos using convenience function:")
    for i, video in enumerate(videos, 1):
        print(f"{i}. {video.get('title')}")


async def example_8_save_to_json():
    """示例8: 保存结果到JSON"""
    print("\n" + "="*50)
    print("Example 8: Save Results to JSON")
    print("="*50)

    spider = DouyinSpider(headless=True)

    async with spider.session():
        videos = await spider.search("AI编程", max_results=5)

        # 转换datetime为字符串
        for video in videos:
            if isinstance(video.get('publish_time'), datetime):
                video['publish_time'] = video['publish_time'].isoformat()
            if isinstance(video.get('collected_at'), datetime):
                video['collected_at'] = video['collected_at'].isoformat()

        # 保存到JSON
        output_file = Path("output") / "douyin_videos.json"
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(videos, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Saved {len(videos)} videos to {output_file}")


async def run_all_examples():
    """运行所有示例"""
    examples = [
        ("Basic Search", example_1_basic_search),
        ("Search with Criteria", example_2_search_with_criteria),
        # ("Get User Videos", example_3_get_user_videos),  # 需要真实用户ID
        ("Get Comments", example_4_get_comments),
        ("Topic Videos", example_5_topic_videos),
        # ("Download Video", example_6_download_video),  # 可能较慢
        ("Convenience Functions", example_7_convenience_functions),
        ("Save to JSON", example_8_save_to_json),
    ]

    print("\n" + "="*60)
    print("Douyin Spider Examples")
    print("="*60)

    for name, example_func in examples:
        try:
            print(f"\nRunning: {name}")
            await example_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")

        # 延迟避免请求过快
        await asyncio.sleep(2)

    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60)


def main():
    """主函数"""
    import sys

    if len(sys.argv) > 1:
        example_num = sys.argv[1]

        examples_map = {
            '1': example_1_basic_search,
            '2': example_2_search_with_criteria,
            '3': example_3_get_user_videos,
            '4': example_4_get_comments,
            '5': example_5_topic_videos,
            '6': example_6_download_video,
            '7': example_7_convenience_functions,
            '8': example_8_save_to_json,
        }

        if example_num in examples_map:
            asyncio.run(examples_map[example_num]())
        elif example_num == 'all':
            asyncio.run(run_all_examples())
        else:
            print(f"Unknown example: {example_num}")
            print("Available examples: 1-8, or 'all'")
    else:
        # 默认运行所有示例
        print("Usage: python examples/douyin_example.py [example_number]")
        print("Examples: 1-8, or 'all'")
        print("\nRunning all examples...")
        asyncio.run(run_all_examples())


if __name__ == "__main__":
    main()
