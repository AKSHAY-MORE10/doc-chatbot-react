"""Query orchestration — retrieve context, build prompt, call LLM."""

import logging
import re
from datetime import datetime

from app.config import settings
from app.llm import get_chat_model
from app.parent_store import get_parents
from app.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are a helpful assistant. Answer using the context and web results below.
Format your response clearly using:
- **Bold** for key terms
- Bullet points for lists
- Headers (##) for sections if the answer is long
- Code blocks for any code

Use the conversation history to preserve user-specific details such as names, preferences, and earlier questions.
If the user asks a follow-up question, answer it using the prior conversation first.

If the context doesn't contain the answer, use the web results.
If neither has the answer, say so clearly.

Conversation History:
{history}

Document Context:
{context}

Web Search Results:
{web_results}

Question: {question}

Answer:"""

CASUAL_PATTERNS = (
    r"^\s*(hi|hey|hello|yo|hiya|sup|howdy)\s*!?\s*$",
    r"^\s*(i'?m|im)?\s*(just\s+)?(saying\s+)?(hi|hey|hello|yo|hiya|sup|howdy)\s*!?\s*$",
    r"^\s*(good\s+(morning|afternoon|evening))\s*!?\s*$",
    r"^\s*(thanks|thank you|thx)\s*!?\s*$",
    r"^\s*(how are you|how's it going|what's up)\s*\??\s*$",
)

DATE_TIME_PATTERNS = (
    # Date questions
    r"^\s*(?:what(?:'s|\s+is)?\s+)?(?:the\s+)?(?:current\s+)?date\s*(?:today|now)?\s*\??\s*$",
    r"^\s*what\s+(?:is\s+)?(?:the\s+)?date\s+(?:today|now)\s*\??\s*$",
    r"^\s*what\s+date\s+(?:is\s+)?(?:it\s+)?(?:today|now)?\s*\??\s*$",
    r"^\s*today'?s\s+date\s*(?:and\s+time)?\s*\??\s*$",
    r"^\s*current\s+date\s*(?:and\s+time)?\s*\??\s*$",
    r"^\s*(?:tell\s+me\s+)?(?:the\s+)?date\s*(?:and\s+time)?\s*\??\s*$",
    # Time questions
    r"^\s*(?:what(?:'s|\s+is)?\s+)?(?:the\s+)?(?:current\s+)?time\s*(?:now)?\s*\??\s*$",
    r"^\s*what\s+time\s+is\s+it\s*(?:now)?\s*\??\s*$",
    r"^\s*current\s+time\s*\??\s*$",
    r"^\s*(?:tell\s+me\s+)?(?:the\s+)?time\s*\??\s*$",
    # Day questions
    r"^\s*what\s+day\s+is\s+(?:it\s+)?(?:today)?\s*\??\s*$",
    r"^\s*(?:what(?:'s|\s+is)?\s+)?today\s*\??\s*$",
)


def is_casual_message(question: str) -> bool:
    normalized = question.strip().lower()
    return any(re.match(pattern, normalized) for pattern in CASUAL_PATTERNS)


def is_date_time_question(question: str) -> bool:
    """Detect questions about the current date, time, or day."""
    normalized = question.strip().lower()
    if any(re.match(pattern, normalized) for pattern in DATE_TIME_PATTERNS):
        return True
    # Keyword fallback: contains date/time words with context markers
    date_time_words = ("date", "time", "day")
    context_words = ("today", "now", "current", "what")
    if any(w in normalized for w in date_time_words) and any(
        w in normalized for w in context_words
    ):
        return True
    return False


def web_search(search_query: str) -> tuple[str, list[str]]:
    """Run a web search and return ``(result_text, [source_urls])``."""
    try:
        from langchain_community.tools import DuckDuckGoSearchRun

        result = DuckDuckGoSearchRun().run(search_query)
        return result, ["https://duckduckgo.com"] if result else (result, [])
    except Exception:
        logger.debug("Web search unavailable", exc_info=True)
        return "Web search unavailable.", []


def format_history(history: list[dict] | list) -> str:
    if not history:
        return "No prior conversation."

    recent_turns = history[-10:]
    lines = []
    for turn in recent_turns:
        role = getattr(turn, "role", None) or turn.get("role", "unknown")
        content = getattr(turn, "content", None) or turn.get("content", "")
        if not content.strip():
            continue
        prefix = (
            "User"
            if role == "user"
            else "Assistant" if role == "assistant" else role.title()
        )
        lines.append(f"{prefix}: {content.strip()}")

    return "\n".join(lines) or "No prior conversation."


def query(
    question: str,
    collection: str,
    history: list[dict] | list | None = None,
) -> dict:
    """Answer *question* using RAG (documents + optional web search)."""

    # ── Fast-path: date-time / casual ─────────────────────────
    if is_date_time_question(question):
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")
        return {
            "answer": f"📅 **Date:** {date_str}\n\n🕐 **Time:** {time_str}",
            "sources": [],
            "web_sources": [],
        }

    if is_casual_message(question):
        return {"answer": "Hey! How can I help?", "sources": [], "web_sources": []}

    # ── Web search ──────────────────────────────────────────
    web_results, web_urls = web_search(question)

    # ── Document retrieval ──────────────────────────────────
    vectorstore = get_vectorstore(collection)
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": settings.TOP_K},
    )
    docs = retriever.invoke(question)

    # ── Parent-document resolution ───────────────────────────
    # docs are the small chunks that matched by similarity (precise but narrow).
    # Swap each one for its full parent section (richer context) before handing
    # anything to the LLM, deduping when several matched chunks share a parent.
    parent_ids = list(
        dict.fromkeys(doc.metadata.get("parent_id") for doc in docs if doc.metadata.get("parent_id"))
    )
    parent_texts = get_parents(collection, parent_ids)
    seen_parents: set[str] = set()
    context_parts: list[str] = []
    for doc in docs:
        parent_id = doc.metadata.get("parent_id")
        if parent_id and parent_id in parent_texts:
            if parent_id in seen_parents:
                continue
            seen_parents.add(parent_id)
            context_parts.append(parent_texts[parent_id])
        else:
            # Fallback for chunks ingested before parent-document retrieval existed.
            context_parts.append(doc.page_content)
    context = "\n\n".join(context_parts)

    def _label(doc) -> str:
        name = doc.metadata.get("source_file", "unknown")
        page = doc.metadata.get("page_number")
        section = doc.metadata.get("section")
        location = ", ".join(
            part for part in (f"p. {page}" if page else None, section) if part
        )
        return f"{name} ({location})" if location else name

    sources = list(dict.fromkeys(_label(doc) for doc in docs))

    # ── Build prompt & call LLM ─────────────────────────────
    conversation_history = format_history(history or [])
    llm = get_chat_model()

    prompt = PROMPT_TEMPLATE.format(
        history=conversation_history,
        context=context or "No document context available.",
        web_results=web_results,
        question=question,
    )

    answer = llm(prompt)

    return {
        "answer": answer,
        "sources": sources,
        "web_sources": web_urls,
    }