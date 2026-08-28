# Doc Chatbot

A secure, fully-featured Retrieval-Augmented Generation (RAG) Document Chatbot built with **FastAPI**, **ChromaDB**, and a clean browser-based UI. 

This application allows users to upload PDF and Text documents, embed them into a local vector database, and chat with them using various Large Language Models (LLMs). It seamlessly integrates local models via **Ollama**, or cloud-based models via **Groq** and **Gemini**.

## 🚀 Features

- **Document Ingestion**: Upload PDF or TXT files. The app automatically chunks and vectorizes the text into ChromaDB.
- **Multi-Provider LLM Support**: Seamlessly switch between **Ollama** (local), **Groq** (fast, OpenAI-compatible), and **Gemini** (Google REST API).
- **Web Search Integration**: Automatically fetches real-time context from DuckDuckGo if the document context doesn't contain the answer.
- **Fast-Path Responses**: Instant answers for casual greetings or date/time questions without needing a full RAG cycle.
- **Admin Security**: API key protection for sensitive endpoints like document ingestion and collection deletion.
- **Dynamic Configuration**: Change LLM providers, models, and API keys directly from the UI settings panel. Configurations are persisted dynamically in the `.env` file.
- **Docker Ready**: Includes a `docker-compose.yml` for easy deployment alongside an Ollama instance.

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, Pydantic, LangChain
- **Vector Database**: ChromaDB
- **Frontend**: React (Vite) — component-based UI, npm-managed markdown rendering
- **Embeddings**: Ollama (e.g., `nomic-embed-text`) or Gemini
- **Search**: DuckDuckGo Search API

---

## 🏗️ Architecture & Project Flow

The project follows a standard RAG architecture enhanced with web search and security layers.

### 1. Document Ingestion Flow
1. **Upload**: User uploads a document (PDF/TXT) via the UI, optionally specifying a collection name.
2. **Chunking**: `app/ingestion.py` loads the file and splits it into smaller chunks using LangChain's `RecursiveCharacterTextSplitter`.
3. **Embedding**: Each chunk is embedded into numerical vectors using the configured embedding model (Ollama or Gemini).
4. **Storage**: Vectors and metadata (like source filename) are stored persistently in **ChromaDB** (`app/vectorstore.py`).

### 2. Query (RAG) Flow
1. **Chat Request**: User submits a question via the chat interface.
2. **Fast-Path Check**: `app/retriever.py` checks if it's a casual greeting or a date/time question. If so, it responds immediately without invoking heavy processes.
3. **Web Search**: The app uses DuckDuckGo to fetch real-time web context.
4. **Vector Retrieval**: The app searches ChromaDB for the most relevant document chunks based on semantic similarity.
5. **LLM Generation**: The conversation history, document context, web results, and the user's question are compiled into a prompt and sent to the selected LLM (`app/llm.py`).
6. **Response**: The final answer, along with source document names and web URLs, is returned to the user.

---

## 📂 Directory Structure

```text
.
├── app/
│   ├── main.py           # FastAPI application entry point, routes, and middleware
│   ├── config.py         # Dynamic environment configuration management
│   ├── ingestion.py      # Document loading and chunking logic
│   ├── retriever.py      # RAG orchestration, web search, and prompt building
│   ├── llm.py            # LLM provider integrations (Ollama, Groq, Gemini)
│   ├── embeddings.py     # Embedding logic (Ollama, Gemini)
│   ├── vectorstore.py    # ChromaDB client and connection management
│   ├── schemas.py        # Pydantic models for API validation
│   └── http_utils.py     # Low-level HTTP request helpers
├── frontend_react/
│   ├── src/               # React components, hooks, styles
│   ├── vite.config.js     # Builds to ../frontend_dist
│   └── package.json
├── frontend_dist/         # Built frontend output (generated, served by FastAPI)
├── chroma_data/          # Persistent local storage for the vector database
├── docker-compose.yml    # Docker Compose setup for the app and Ollama
├── Dockerfile            # Docker build instructions
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

---

## 🚦 Getting Started

### Option 1: Run Locally (Native)

1. **Install dependencies**:
   Ensure you have Python 3.10+ and Node 18+ installed.
   ```bash
   pip install -r requirements.txt
   ```

2. **Build the frontend** (one-time, or after any frontend change):
   ```bash
   cd frontend_react
   npm install
   npm run build
   cd ..
   ```
   This produces `frontend_dist/`, which FastAPI serves at `/`. For active frontend
   development, run `npm run dev` inside `frontend_react/` instead — it proxies API
   calls to `localhost:8000` (see `vite.config.js`) so you get hot reload against a
   locally running backend.

3. **Configure Environment**:
   Set up your initial `.env` file or export environment variables. At a minimum, set an admin key to secure your ingestion endpoints.
   ```bash
   # Windows
   set ADMIN_API_KEY=change-me
   
   # Linux/macOS
   export ADMIN_API_KEY=change-me
   ```

4. **Start the server**:
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Access the App**:
   Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

### Option 2: Run via Docker Compose

This is the easiest way to get started, especially if you want to use local models with Ollama.

1. **Start the containers**:
   ```bash
   docker-compose up --build -d
   ```
2. **Access the App**:
   Navigate to [http://localhost:8000](http://localhost:8000).

*(Note: When running via Docker, the Ollama container is mapped to port `11434`. You must pull your desired models into Ollama manually or via the Ollama API before using them).*

---

## ⚙️ Configuration & Environment Variables

The app is highly configurable. You can set these in your `.env` file or change LLM settings directly from the web UI.

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | `ollama`, `groq`, or `gemini` | `ollama` |
| `LLM_MODEL` | The chat model name to use | `qwen2.5:7b` |
| `OLLAMA_BASE_URL` | URL of the Ollama server | `http://localhost:11434` |
| `LLM_API_KEY` | API key for Groq or Gemini | `""` |
| `LLM_API_BASE_URL` | Base URL for OpenAI-compatible APIs (like Groq) | `https://api.x.ai/v1` |
| `GEMINI_API_BASE_URL`| Base URL for Gemini REST API | `https://generativelanguage.googleapis.com/v1beta` |
| `EMBED_PROVIDER` | Backend for embeddings (`ollama` or `gemini`) | `ollama` |
| `EMBED_MODEL` | Embedding model name | `nomic-embed-text` |
| `CHROMA_PATH` | Path to store ChromaDB persistent data | `./chroma_data` |
| `ADMIN_API_KEY` | Protects ingest and delete endpoints | `""` |
| `ALLOWED_ORIGINS` | Comma-separated CORS allowlist | `http://127.0.0.1:8000,http://localhost:8000`|
| `MAX_UPLOAD_MB` | File upload size limit | `20` |
| `RATE_LIMIT_RPM` | Rate limit requests per minute per IP | `30` |

---

## 🔒 Security Features

- **Admin Authentication**: `POST /ingest` and `DELETE /collection/{name}` endpoints are protected by the `X-API-Key` header when `ADMIN_API_KEY` is configured.
- **Rate Limiting**: Built-in sliding window rate limiter protects against abuse.
- **Security Headers**: Middleware injects strict security headers (`X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, etc.).
- **Client-side Safety**: The frontend stores the admin key securely in the session storage (cleared upon closing the tab) and sanitizes Markdown output before rendering it to prevent XSS attacks.
