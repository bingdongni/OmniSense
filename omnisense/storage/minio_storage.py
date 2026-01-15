"""
MinIO object storage management for OmniSense
Handles media files (images, videos, audio)
"""

from minio import Minio
from minio.error import S3Error
from pathlib import Path
from typing import Optional, BinaryIO
import io

from omnisense.config import config
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class MinIOStorage:
    """MinIO object storage manager"""

    def __init__(self):
        self.client = None
        self.bucket_name = config.storage.minio_bucket
        self._connect()
        self._ensure_bucket()

    def _connect(self):
        """Connect to MinIO"""
        try:
            self.client = Minio(
                config.storage.minio_endpoint,
                access_key=config.storage.minio_access_key,
                secret_key=config.storage.minio_secret_key,
                secure=config.storage.minio_secure
            )
            logger.info("MinIO connection established")
        except Exception as e:
            logger.warning(f"MinIO connection failed: {e}")
            self.client = None

    def _ensure_bucket(self):
        """Ensure bucket exists"""
        if not self.client:
            return

        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket: {e}")

    def upload_file(
        self,
        file_path: str,
        object_name: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> Optional[str]:
        """Upload file to MinIO"""
        if not self.client:
            logger.warning("MinIO not available, skipping upload")
            return None

        if not object_name:
            object_name = Path(file_path).name

        try:
            self.client.fput_object(
                self.bucket_name,
                object_name,
                file_path,
                content_type=content_type
            )
            logger.info(f"Uploaded: {object_name}")
            return object_name
        except S3Error as e:
            logger.error(f"Error uploading file: {e}")
            return None

    def upload_data(
        self,
        data: bytes,
        object_name: str,
        content_type: Optional[str] = None
    ) -> Optional[str]:
        """Upload binary data to MinIO"""
        if not self.client:
            return None

        try:
            data_stream = io.BytesIO(data)
            self.client.put_object(
                self.bucket_name,
                object_name,
                data_stream,
                length=len(data),
                content_type=content_type
            )
            logger.info(f"Uploaded data: {object_name}")
            return object_name
        except S3Error as e:
            logger.error(f"Error uploading data: {e}")
            return None

    def download_file(
        self,
        object_name: str,
        file_path: str
    ) -> bool:
        """Download file from MinIO"""
        if not self.client:
            return False

        try:
            self.client.fget_object(
                self.bucket_name,
                object_name,
                file_path
            )
            logger.info(f"Downloaded: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"Error downloading file: {e}")
            return False

    def get_object(self, object_name: str) -> Optional[bytes]:
        """Get object data"""
        if not self.client:
            return None

        try:
            response = self.client.get_object(
                self.bucket_name,
                object_name
            )
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Error getting object: {e}")
            return None

    def delete_object(self, object_name: str) -> bool:
        """Delete object from MinIO"""
        if not self.client:
            return False

        try:
            self.client.remove_object(
                self.bucket_name,
                object_name
            )
            logger.info(f"Deleted: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"Error deleting object: {e}")
            return False

    def list_objects(self, prefix: Optional[str] = None) -> list:
        """List objects in bucket"""
        if not self.client:
            return []

        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Error listing objects: {e}")
            return []

    def object_exists(self, object_name: str) -> bool:
        """Check if object exists"""
        if not self.client:
            return False

        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except:
            return False

    def get_presigned_url(
        self,
        object_name: str,
        expires_seconds: int = 3600
    ) -> Optional[str]:
        """Get presigned URL for object"""
        if not self.client:
            return None

        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=timedelta(seconds=expires_seconds)
            )
            return url
        except S3Error as e:
            logger.error(f"Error getting presigned URL: {e}")
            return None

    def get_bucket_stats(self) -> dict:
        """Get bucket statistics"""
        if not self.client:
            return {}

        try:
            objects = self.list_objects()
            total_size = 0

            for obj_name in objects:
                stat = self.client.stat_object(self.bucket_name, obj_name)
                total_size += stat.size

            return {
                "bucket": self.bucket_name,
                "object_count": len(objects),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
        except S3Error as e:
            logger.error(f"Error getting stats: {e}")
            return {}
