"""
Tests for database operations
Tests DatabaseManager class, CRUD operations, and queries
"""

import pytest
import asyncio
import sqlite3
from pathlib import Path
from datetime import datetime

from omnisense.storage.database import DatabaseManager


class TestDatabaseInitialization:
    """Test database initialization"""

    def test_database_creation(self, temp_dir):
        """Test database file creation"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        assert Path(config.database.sqlite_path).exists()

        config.database.sqlite_path = original_path

    def test_schema_creation(self, temp_dir):
        """Test that tables are created"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        db_path = temp_dir / "test.db"
        config.database.sqlite_path = str(db_path)
        db = DatabaseManager()

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]

        assert "collections" in tables
        assert "content" in tables
        assert "interactions" in tables
        assert "creators" in tables
        assert "analysis_results" in tables

        conn.close()
        config.database.sqlite_path = original_path

    def test_indexes_creation(self, temp_dir):
        """Test that indexes are created"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        db_path = temp_dir / "test.db"
        config.database.sqlite_path = str(db_path)
        db = DatabaseManager()

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indexes = [row[0] for row in cursor.fetchall()]

        assert any("idx_content_platform" in idx for idx in indexes)
        assert any("idx_content_collection" in idx for idx in indexes)

        conn.close()
        config.database.sqlite_path = original_path


class TestCollectionOperations:
    """Test collection operations"""

    @pytest.mark.asyncio
    async def test_save_collection(self, temp_dir, sample_content_data):
        """Test saving a collection"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        collection_id = await db.save_collection(
            platform="douyin",
            data=sample_content_data,
            keyword="test",
        )

        assert collection_id is not None
        assert "douyin" in collection_id

        config.database.sqlite_path = original_path

    @pytest.mark.asyncio
    async def test_get_collection(self, temp_dir, sample_content_data):
        """Test retrieving a collection"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        # Save collection
        collection_id = await db.save_collection(
            platform="douyin",
            data=sample_content_data,
        )

        # Retrieve collection
        result = await db.get_collection(collection_id)

        assert result is not None
        assert result["collection"]["collection_id"] == collection_id
        assert result["count"] == len(sample_content_data)

        config.database.sqlite_path = original_path

    @pytest.mark.asyncio
    async def test_collection_not_found(self, temp_dir):
        """Test retrieving non-existent collection"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        with pytest.raises(ValueError):
            await db.get_collection("nonexistent_id")

        config.database.sqlite_path = original_path


class TestContentOperations:
    """Test content operations"""

    @pytest.mark.asyncio
    async def test_save_content(self, temp_dir, sample_content_data):
        """Test saving content"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        collection_id = await db.save_collection(
            platform="douyin",
            data=sample_content_data,
        )

        # Verify content was saved
        result = await db.get_collection(collection_id)
        assert len(result["content"]) == len(sample_content_data)

        config.database.sqlite_path = original_path

    @pytest.mark.asyncio
    async def test_duplicate_content(self, temp_dir, sample_content_data):
        """Test handling duplicate content"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        # Save same content twice
        await db.save_collection(
            platform="douyin",
            data=sample_content_data,
            collection_id="test_collection_1",
        )

        await db.save_collection(
            platform="douyin",
            data=sample_content_data,
            collection_id="test_collection_2",
        )

        # Should not create duplicates (INSERT OR REPLACE)
        result = await db.search_content(platform="douyin")
        assert len(result) == len(sample_content_data)

        config.database.sqlite_path = original_path

    @pytest.mark.asyncio
    async def test_search_content(self, temp_dir, sample_content_data):
        """Test searching content"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        await db.save_collection(
            platform="douyin",
            data=sample_content_data,
        )

        # Search by platform
        results = await db.search_content(platform="douyin")
        assert len(results) > 0

        # Search by keyword
        results = await db.search_content(keyword="test")
        assert len(results) > 0

        config.database.sqlite_path = original_path

    @pytest.mark.asyncio
    async def test_search_with_limit(self, temp_dir, sample_content_data):
        """Test search with limit"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        await db.save_collection(
            platform="douyin",
            data=sample_content_data,
        )

        results = await db.search_content(limit=1)
        assert len(results) == 1

        config.database.sqlite_path = original_path


class TestStatistics:
    """Test statistics operations"""

    @pytest.mark.asyncio
    async def test_get_statistics(self, temp_dir, sample_content_data):
        """Test getting database statistics"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        # Save some data
        await db.save_collection(
            platform="douyin",
            data=sample_content_data,
        )

        # Get statistics
        stats = await db.get_statistics()

        assert "total_content" in stats
        assert "total_interactions" in stats
        assert "total_collections" in stats
        assert stats["total_content"] == len(sample_content_data)

        config.database.sqlite_path = original_path

    @pytest.mark.asyncio
    async def test_platform_statistics(self, temp_dir, sample_content_data):
        """Test platform-specific statistics"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        await db.save_collection(
            platform="douyin",
            data=sample_content_data,
        )

        stats = await db.get_statistics(platform="douyin")
        assert stats["total_content"] == len(sample_content_data)

        # Test with different platform
        stats = await db.get_statistics(platform="weibo")
        assert stats["total_content"] == 0

        config.database.sqlite_path = original_path


class TestInteractions:
    """Test interaction operations"""

    @pytest.mark.asyncio
    async def test_save_interactions(self, temp_dir, sample_interactions):
        """Test saving interactions"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        # Create content with interactions
        content_data = [
            {
                "content_id": "test_001",
                "platform": "douyin",
                "title": "Test",
                "interactions": sample_interactions,
            }
        ]

        await db.save_collection(
            platform="douyin",
            data=content_data,
        )

        # Verify interactions were saved
        stats = await db.get_statistics()
        assert stats["total_interactions"] == len(sample_interactions)

        config.database.sqlite_path = original_path


class TestDatabasePerformance:
    """Test database performance"""

    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, temp_dir, performance_tracker):
        """Test bulk insert performance"""
        from omnisense.config import config
        from tests.conftest import generate_mock_content

        original_path = config.database.sqlite_path
        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        # Generate large dataset
        large_dataset = generate_mock_content(100, "douyin")

        performance_tracker.start()
        await db.save_collection(
            platform="douyin",
            data=large_dataset,
        )
        elapsed = performance_tracker.stop()

        assert elapsed < 5.0, f"Bulk insert took {elapsed}s for 100 items"

        config.database.sqlite_path = original_path

    @pytest.mark.asyncio
    async def test_search_performance(self, temp_dir, performance_tracker):
        """Test search performance"""
        from omnisense.config import config
        from tests.conftest import generate_mock_content

        original_path = config.database.sqlite_path
        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        # Insert data
        large_dataset = generate_mock_content(100, "douyin")
        await db.save_collection(
            platform="douyin",
            data=large_dataset,
        )

        # Test search performance
        performance_tracker.start()
        for _ in range(10):
            await db.search_content(platform="douyin", limit=10)
        elapsed = performance_tracker.stop()

        assert elapsed < 1.0, f"10 searches took {elapsed}s"

        config.database.sqlite_path = original_path


class TestDatabaseEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_empty_collection(self, temp_dir):
        """Test saving empty collection"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        collection_id = await db.save_collection(
            platform="douyin",
            data=[],
        )

        assert collection_id is not None

        config.database.sqlite_path = original_path

    @pytest.mark.asyncio
    async def test_malformed_data(self, temp_dir):
        """Test handling malformed data"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        # Missing required fields
        malformed_data = [{"content_id": "test_001"}]

        # Should not crash
        await db.save_collection(
            platform="douyin",
            data=malformed_data,
        )

        config.database.sqlite_path = original_path

    @pytest.mark.asyncio
    async def test_unicode_content(self, temp_dir):
        """Test handling Unicode content"""
        from omnisense.config import config
        original_path = config.database.sqlite_path

        config.database.sqlite_path = str(temp_dir / "test.db")
        db = DatabaseManager()

        unicode_data = [
            {
                "content_id": "test_001",
                "platform": "douyin",
                "title": "测试标题 🎉",
                "description": "描述内容 with émojis 😀",
            }
        ]

        collection_id = await db.save_collection(
            platform="douyin",
            data=unicode_data,
        )

        result = await db.get_collection(collection_id)
        assert "测试标题" in result["content"][0]["title"]

        config.database.sqlite_path = original_path
