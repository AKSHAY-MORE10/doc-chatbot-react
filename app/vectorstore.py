"""ChromaDB vectorstore access with a shared client singleton."""

import logging
import threading

import chromadb
from langchain_community.vectorstores import Chroma

from app.config import settings
from app.embeddings import get_embeddings

logger = logging.getLogger(__name__)

_client: chromadb.ClientAPI | None = None
_client_lock = threading.Lock()


def get_chroma_client() -> chromadb.ClientAPI:
    """Return a shared ChromaDB PersistentClient (thread-safe singleton)."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
                logger.info("ChromaDB client initialised at %s", settings.CHROMA_PATH)
    return _client


def get_vectorstore(collection: str) -> Chroma:
    """Return a Langchain Chroma vectorstore for the given collection."""
    return Chroma(
        client=get_chroma_client(),
        collection_name=collection,
        embedding_function=get_embeddings(),
    )
