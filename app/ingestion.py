"""Document ingestion — load, chunk, and store in the vectorstore."""

import logging
import os
import tempfile
import uuid

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.config import settings
from app.parent_store import save_parents
from app.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)

# Headers pymupdf4llm emits based on font size (#, ##, ###). Splitting on these
# first — before size-based splitting — keeps a chunk from crossing a section
# boundary, and lets us stamp each chunk with the heading it actually belongs to.
_HEADERS_TO_SPLIT_ON = [("#", "h1"), ("##", "h2"), ("###", "h3")]
_HEADER_SPLITTER = MarkdownHeaderTextSplitter(
    headers_to_split_on=_HEADERS_TO_SPLIT_ON, strip_headers=False
)
_SIZE_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP,
    add_start_index=True,
)


def _section_label(header_metadata: dict) -> str | None:
    """Build a single 'section' string from whichever heading levels are present."""
    parts = [header_metadata[key] for _, key in _HEADERS_TO_SPLIT_ON if header_metadata.get(key)]
    return " > ".join(parts) if parts else None


def _split_text_by_section(
    text: str, page_number: int | None
) -> tuple[list[Document], dict[str, str]]:
    """Split *text* on markdown headers first, then to size. Plain text with no
    headers just falls through as one section, so this path works for .txt too.

    Each markdown-header section (before size-splitting) becomes one "parent" —
    every child chunk cut from it carries that parent's id in metadata, so the
    retriever can later swap a matched child for its full parent section.
    Returns ``(child_chunks, {parent_id: parent_text})``.
    """
    section_docs = _HEADER_SPLITTER.split_text(text)
    chunks: list[Document] = []
    parents: dict[str, str] = {}
    for section_doc in section_docs:
        section = _section_label(section_doc.metadata)
        parent_id = str(uuid.uuid4())
        parents[parent_id] = section_doc.page_content
        for chunk in _SIZE_SPLITTER.split_documents([section_doc]):
            if section:
                chunk.metadata["section"] = section
            if page_number is not None:
                chunk.metadata["page_number"] = page_number
            chunk.metadata["parent_id"] = parent_id
            chunks.append(chunk)
    return chunks, parents


async def ingest_file(file_bytes: bytes, filename: str, collection: str) -> int:
    """Write *file_bytes* to a temp file, split into chunks, and add to the vectorstore.

    Small chunks are embedded and indexed for precise similarity search; each
    chunk's full parent section is saved separately (see parent_store.py) so the
    retriever can hand the LLM richer context than a single chunk without
    hurting retrieval precision.

    Returns the number of chunks added.
    """
    is_pdf = filename.lower().endswith(".pdf")
    suffix = ".pdf" if is_pdf else ".txt"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        chunks: list[Document] = []
        all_parents: dict[str, str] = {}

        if is_pdf:
            # pymupdf4llm renders each page to markdown (headings, tables, layout
            # preserved as # / ## / ### and pipe tables) instead of the flat text
            # PyMuPDFLoader/PyPDFLoader produce, so headings survive into metadata.
            import pymupdf4llm

            pages = pymupdf4llm.to_markdown(tmp_path, page_chunks=True)
            for i, page in enumerate(pages):
                page_number = i + 1  # page_chunks is in reading order; trust the index
                page_chunks, page_parents = _split_text_by_section(
                    page.get("text", ""), page_number
                )
                chunks.extend(page_chunks)
                all_parents.update(page_parents)
        else:
            docs = TextLoader(tmp_path).load()
            text = docs[0].page_content if docs else ""
            chunks, all_parents = _split_text_by_section(text, page_number=None)

        for i, chunk in enumerate(chunks):
            chunk.metadata["source_file"] = filename
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(chunks)

        save_parents(collection, all_parents)

        vectorstore = get_vectorstore(collection)
        vectorstore.add_documents(chunks)

        logger.info(
            "Ingested %d chunks (%d parent sections) from %s into collection %s",
            len(chunks),
            len(all_parents),
            filename,
            collection,
        )
        return len(chunks)
    finally:
        os.unlink(tmp_path)
