"""
Database management for OmniSense
SQLite for structured data, with async support
"""

import sqlite3
import aiosqlite
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import json

from omnisense.config import config
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Database manager for OmniSense using SQLite"""

    def __init__(self):
        self.db_path = Path(config.database.sqlite_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()

            # Collections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    collection_id TEXT UNIQUE NOT NULL,
                    keyword TEXT,
                    user_id TEXT,
                    url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    metadata TEXT
                )
            """)

            # Content table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    content_type TEXT,
                    title TEXT,
                    description TEXT,
                    author_id TEXT,
                    author_name TEXT,
                    publish_time TIMESTAMP,
                    view_count INTEGER DEFAULT 0,
                    like_count INTEGER DEFAULT 0,
                    comment_count INTEGER DEFAULT 0,
                    share_count INTEGER DEFAULT 0,
                    collect_count INTEGER DEFAULT 0,
                    media_urls TEXT,
                    tags TEXT,
                    sentiment_score REAL,
                    matched BOOLEAN DEFAULT 0,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform, content_id)
                )
            """)

            # Comments/Interactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    interaction_id TEXT NOT NULL,
                    interaction_type TEXT,
                    user_id TEXT,
                    user_name TEXT,
                    text TEXT,
                    timestamp TIMESTAMP,
                    like_count INTEGER DEFAULT 0,
                    reply_count INTEGER DEFAULT 0,
                    parent_id TEXT,
                    sentiment_score REAL,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform, interaction_id)
                )
            """)

            # Users/Creators table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT,
                    display_name TEXT,
                    bio TEXT,
                    follower_count INTEGER DEFAULT 0,
                    following_count INTEGER DEFAULT 0,
                    content_count INTEGER DEFAULT 0,
                    verified BOOLEAN DEFAULT 0,
                    profile_url TEXT,
                    avatar_url TEXT,
                    tags TEXT,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform, user_id)
                )
            """)

            # Analysis results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_id TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    results TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_platform ON content(platform)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_collection ON content(collection_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_content ON interactions(content_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_creators_platform ON creators(platform)")

            conn.commit()
            logger.info("Database initialized successfully")

    async def save_collection(self, platform: str, data: List[Dict[str, Any]],
                             collection_id: Optional[str] = None, **metadata) -> str:
        """Save collection data to database"""
        if not collection_id:
            collection_id = f"{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        async with aiosqlite.connect(str(self.db_path)) as db:
            # Insert collection record
            await db.execute("""
                INSERT OR REPLACE INTO collections
                (platform, collection_id, keyword, user_id, url, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                platform,
                collection_id,
                metadata.get('keyword'),
                metadata.get('user_id'),
                metadata.get('url'),
                json.dumps(metadata)
            ))

            # Insert content records
            for item in data:
                await self._save_content(db, collection_id, platform, item)

            await db.commit()
            logger.info(f"Saved {len(data)} items for collection {collection_id}")

        return collection_id

    async def _save_content(self, db: aiosqlite.Connection, collection_id: str,
                           platform: str, item: Dict[str, Any]):
        """Save content item to database"""
        await db.execute("""
            INSERT OR REPLACE INTO content
            (collection_id, platform, content_id, content_type, title, description,
             author_id, author_name, publish_time, view_count, like_count,
             comment_count, share_count, collect_count, media_urls, tags,
             sentiment_score, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            collection_id,
            platform,
            item.get('content_id'),
            item.get('content_type'),
            item.get('title'),
            item.get('description'),
            item.get('author', {}).get('user_id'),
            item.get('author', {}).get('name'),
            item.get('publish_time'),
            item.get('stats', {}).get('views', 0),
            item.get('stats', {}).get('likes', 0),
            item.get('stats', {}).get('comments', 0),
            item.get('stats', {}).get('shares', 0),
            item.get('stats', {}).get('collects', 0),
            json.dumps(item.get('media_urls', [])),
            json.dumps(item.get('tags', [])),
            item.get('sentiment_score'),
            json.dumps(item)
        ))

        # Save interactions if present
        interactions = item.get('interactions', [])
        for interaction in interactions:
            await self._save_interaction(db, item.get('content_id'), platform, interaction)

    async def _save_interaction(self, db: aiosqlite.Connection, content_id: str,
                                platform: str, interaction: Dict[str, Any]):
        """Save interaction/comment to database"""
        await db.execute("""
            INSERT OR REPLACE INTO interactions
            (content_id, platform, interaction_id, interaction_type, user_id,
             user_name, text, timestamp, like_count, reply_count, parent_id,
             sentiment_score, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            content_id,
            platform,
            interaction.get('interaction_id'),
            interaction.get('type'),
            interaction.get('user', {}).get('user_id'),
            interaction.get('user', {}).get('name'),
            interaction.get('text'),
            interaction.get('timestamp'),
            interaction.get('like_count', 0),
            interaction.get('reply_count', 0),
            interaction.get('parent_id'),
            interaction.get('sentiment_score'),
            json.dumps(interaction)
        ))

    async def get_collection(self, collection_id: str) -> Dict[str, Any]:
        """Retrieve collection data"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row

            # Get collection metadata
            async with db.execute(
                "SELECT * FROM collections WHERE collection_id = ?",
                (collection_id,)
            ) as cursor:
                collection = await cursor.fetchone()
                if not collection:
                    raise ValueError(f"Collection {collection_id} not found")

            # Get content
            async with db.execute(
                "SELECT * FROM content WHERE collection_id = ?",
                (collection_id,)
            ) as cursor:
                content = await cursor.fetchall()

            return {
                'collection': dict(collection),
                'content': [dict(row) for row in content],
                'count': len(content)
            }

    async def search_content(self, platform: Optional[str] = None,
                            keyword: Optional[str] = None,
                            limit: int = 100) -> List[Dict[str, Any]]:
        """Search content in database"""
        query = "SELECT * FROM content WHERE 1=1"
        params = []

        if platform:
            query += " AND platform = ?"
            params.append(platform)

        if keyword:
            query += " AND (title LIKE ? OR description LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                results = await cursor.fetchall()
                return [dict(row) for row in results]

    async def get_statistics(self, platform: Optional[str] = None) -> Dict[str, Any]:
        """Get database statistics"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            stats = {}

            # Content stats
            query = "SELECT COUNT(*) FROM content"
            params = []
            if platform:
                query += " WHERE platform = ?"
                params.append(platform)

            async with db.execute(query, params) as cursor:
                stats['total_content'] = (await cursor.fetchone())[0]

            # Interactions stats
            query = "SELECT COUNT(*) FROM interactions"
            if platform:
                query += " WHERE platform = ?"

            async with db.execute(query, params) as cursor:
                stats['total_interactions'] = (await cursor.fetchone())[0]

            # Collections stats
            query = "SELECT COUNT(*) FROM collections"
            if platform:
                query += " WHERE platform = ?"

            async with db.execute(query, params) as cursor:
                stats['total_collections'] = (await cursor.fetchone())[0]

            return stats

    async def close(self):
        """Close database connections"""
        logger.info("Database connections closed")
