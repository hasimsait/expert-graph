# ExpertGraph: Immutable Human-Verified Knowledge Graph & MCP-UI System
Here's my beating of the dead horse.

ExpertGraph is a high-integrity, domain-agnostic knowledge graph architecture where the graph acts as an immutable ground truth verified entirely by human domain experts (pathologists, clinicians, legal analysts, financial auditors). 

LLMs are used strictly as extraction utilities at the beginning (**The Ingestion Sieve**) and presentation layers at the end (**The MCP-UI RAG Output**). Fact retrieval is powered by a fast, lightweight **TF-IDF & Cosine Similarity Ranking Engine** (`scikit-learn`), guaranteeing zero context leakage and tamper-proof fact display.

---

## 🏛️ System Architecture

```
[ Raw Unstructured Reports (e.g. Pathology, Financial) ]
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Module A: The Ingestion Sieve                          │
│  • Extractor LLM (Instructor + Entity Resolution)      │
│  • Adversarial Critic LLM (Confidence Validation)      │
│  • Graph Ingester (status: "pending")                  │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Module B: React Annotator Dashboard                    │
│  • High-throughput side-by-side verification UI        │
│  • Hotkeys: (A)pprove / (R)eject / (N)ext              │
│  • Graph Analytics & Impact Traversals                 │
│  • Neo4j Edge Status -> "approved" (Ground Truth)      │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Module C: FastMCP Server & TF-IDF Retrieval Engine     │
│  • TF-IDF & Cosine Similarity Ranking (scikit-learn)   │
│  • Dynamic Similarity Cutoff (Zero Context Leakage)    │
│  • FastMCP Stateless HTTP Endpoint at /mcp             │
│  • Contract Payload (_meta.ui.resourceUri)             │
│  • Dynamic Jinja2 RAG Presentation Widget              │
└────────────────────────────────────────────────────────┘
```

---

## 🤖 Local LLM Support (Gemma, Qwen, Llama, Ollama, vLLM, LM Studio)

ExpertGraph natively supports local GGUF and OpenAI-compatible LLM servers through `instructor` with token loop safeguards:

### 1. Environment Configuration

```bash
# Local OpenAI-Compatible Server (llama.cpp, vLLM, LM Studio, Ollama)
export LLM_PROVIDER="local-openai"   # Hyphenated names are auto-normalized
export LLM_BASE_URL="http://localhost:8080/v1"
export LLM_MODEL="gemma-4-26B-A4B-it-GGUF" # or "Qwen_Qwen3.6-35B-A3B-GGUF"

# Maximum token cap & stop tokens to prevent infinite GGUF loops
export MAX_TOKENS=500
```

### 2. Provider Options
- **`local-openai` / `local_openai`**: Custom local LLM server at `http://localhost:8080/v1` or `http://localhost:11434/v1`.
- **`ollama`**: Ollama local server instance.
- **`openai`**: Official OpenAI API (`gpt-4o`, `gpt-4o-mini`).

---

## 🧬 Bulk Loading Ontologies (UMLS & Custom JSON)

ExpertGraph supports importing external domain ontologies (UMLS RRF files or custom JSON ontologies) into the Neo4j Meta-Graph:

```bash
# Load custom JSON ontology (e.g. Pathology / Medical Domain)
PYTHONPATH=. python3 scripts/load_ontology.py --json scripts/sample_medical_ontology.json

# Load UMLS RRF Metathesaurus files (MRCONSO.RRF, MRREL.RRF)
PYTHONPATH=. python3 scripts/load_ontology.py --umls-dir /path/to/umls/rrf --limit 50000
```

---

## 🧪 RAG Tool Calling with LLMs (Gemma, Qwen, Llama)

You can ask clinical or domain questions to local LLM models using ExpertGraph's MCP tool definition (`retrieve_verified_facts`):

```bash
# Ask a clinical question backed by ExpertGraph MCP tool
PYTHONPATH=. python3 scripts/llama_mcp_rag.py "What genetic mutations were identified in breast cancer tissue samples?"
```

The retrieval engine applies `scikit-learn` **TF-IDF + Cosine Similarity** to score candidate facts by Inverse Document Frequency. Discriminative terms (`"breast"`, `"carcinoma"`, `"HER2"`, `"Acme"`, `"debt"`) score high, while ubiquitous verbs (`"mutation"`, `"detected"`) are downweighted, returning strictly relevant facts without context pollution.

---

## 🧼 Resetting Database & Repository State

To clear all graph data and reset the pending annotator queue cleanly:

```bash
# Reset via CLI script
PYTHONPATH=. python3 scripts/reset_neo4j.py

# Or via REST API
curl -X POST http://localhost:8000/api/reset
```

---

## 🛠️ Technology Stack

- **Backend API & Orchestration**: FastAPI (Python 3.10+)
- **Data Validation & Extraction**: Pydantic v2 + Instructor
- **Retrieval Engine**: `scikit-learn` TF-IDF Vectorizer + Cosine Similarity
- **Graph Database**: Neo4j 5.x (Cypher & Repository Pattern)
- **Protocol**: FastMCP (Stateless HTTP mode mounted at `/mcp`)
- **UI Transport**: `mcp-ui` / MCP Apps standard (`_meta.ui.resourceUri`)
- **Annotation Dashboard**: React 18 (Vite) + TailwindCSS
- **Templating**: Jinja2 + Tailwind CSS

---

## 🚀 Quick Start

### 1. Requirements & Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start Neo4j Database (Optional - System includes in-memory dual graph fallback)
```bash
docker-compose up -d
```

### 3. Build React Annotator Dashboard
```bash
cd dashboard
npm install
npm run build
cd ..
```

### 4. Start ExpertGraph Server (FastAPI + FastMCP)
```bash
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🌐 Endpoints Overview

| Endpoint | Type | Description |
| :--- | :--- | :--- |
| `http://localhost:8000/` | Web Dashboard | High-Throughput React Annotator UI |
| `http://localhost:8000/api/queue` | REST API | Fetch candidate edges awaiting human review |
| `http://localhost:8000/api/approve/{edge_id}` | REST API | Atomically approve pending edge |
| `http://localhost:8000/api/reject/{edge_id}` | REST API | Reject pending edge |
| `http://localhost:8000/api/reset` | REST API | Wipe graph data & reset queue state |
| `http://localhost:8000/api/stats` | REST API | Get live counts of pending, approved, rejected |
| `http://localhost:8000/ui/facts-widget` | MCP-UI Widget | Dynamic Jinja2 RAG presentation widget with concept filter dropdown |
| `http://localhost:8000/mcp` | FastMCP Protocol | FastMCP Stateless HTTP Server endpoint |

---

## 🧪 Testing

ExpertGraph supports dual-mode testing using a repository pattern to isolate unit tests from production data.

### Unit Tests (In-Memory)
By default, all tests use `InMemoryGraphRepository`. This is completely safe and isolated from your Neo4j database:
```bash
PYTHONPATH=. ./venv/bin/pytest
```

### Integration Tests (Live Neo4j)
To run end-to-end integration tests that hit the actual Neo4j database, we use isolated `:TestNode` namespaces that automatically clean up after themselves. Run them using the `integration` marker:
```bash
PYTHONPATH=. ./venv/bin/pytest -m integration
```
