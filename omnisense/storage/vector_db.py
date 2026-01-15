"""
Vector database management using ChromaDB
For semantic search and similarity matching
"""

import chromadb
from chromadb.config import Settings
from typing import Any, Dict, List, Optional
from pathlib import Path
import numpy as np

from omnisense.config import config
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class VectorDatabase:
    """Vector database for semantic search using ChromaDB"""

    def __init__(self):
        self.client = None
        self.collections = {}
        self._initialize()

    def _initialize(self):
        """Initialize ChromaDB client"""
        try:
            db_path = Path(config.database.chroma_path)
            db_path.mkdir(parents=True, exist_ok=True)

            self.client = chromadb.PersistentClient(
                path=str(db_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            logger.info("ChromaDB initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def get_or_create_collection(self, name: str, metadata: Optional[Dict] = None):
        """Get or create a collection"""
        if name in self.collections:
            return self.collections[name]

        try:
            collection = self.client.get_or_create_collection(
                name=name,
                metadata=metadata or {}
            )
            self.collections[name] = collection
            logger.info(f"Collection '{name}' ready")
            return collection
        except Exception as e:
            logger.error(f"Error with collection '{name}': {e}")
            raise

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None
    ):
        """Add documents to collection"""
        collection = self.get_or_create_collection(collection_name)

        if not ids:
            ids = [f"doc_{i}" for i in range(len(documents))]

        try:
            if embeddings:
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings
                )
            else:
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            logger.info(f"Added {len(documents)} documents to '{collection_name}'")
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise

    def query(
        self,
        collection_name: str,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> Dict:
        """Query collection for similar documents"""
        collection = self.get_or_create_collection(collection_name)

        try:
            if query_embeddings:
                results = collection.query(
                    query_embeddings=query_embeddings,
                    n_results=n_results,
                    where=where,
                    where_document=where_document
                )
            elif query_texts:
                results = collection.query(
                    query_texts=query_texts,
                    n_results=n_results,
                    where=where,
                    where_document=where_document
                )
            else:
                raise ValueError("Must provide either query_texts or query_embeddings")

            return results
        except Exception as e:
            logger.error(f"Error querying collection: {e}")
            raise

    def delete_collection(self, name: str):
        """Delete a collection"""
        try:
            self.client.delete_collection(name)
            if name in self.collections:
                del self.collections[name]
            logger.info(f"Deleted collection '{name}'")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            raise

    def get_collection_stats(self, name: str) -> Dict:
        """Get collection statistics"""
        collection = self.get_or_create_collection(name)

        try:
            count = collection.count()
            return {
                "name": name,
                "count": count
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def semantic_search(
        self,
        collection_name: str,
        query: str,
        top_k: int = 10,
        threshold: float = 0.7
    ) -> List[Dict]:
        """Perform semantic search"""
        results = self.query(
            collection_name=collection_name,
            query_texts=[query],
            n_results=top_k
        )

        matched_results = []
        if results and 'distances' in results:
            for i, distance in enumerate(results['distances'][0]):
                # Convert distance to similarity (assuming cosine distance)
                similarity = 1 - distance
                if similarity >= threshold:
                    matched_results.append({
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'similarity': similarity
                    })

        return matched_results
