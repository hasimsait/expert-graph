# ExpertGraph: Immutable Human-Verified Knowledge Graph & MCP-UI System
Here's my beating of the dead horse.
it probably mocked whatever it could getaway with.
idea is:
>What genetic mutations were identified in breast cancer tissue samples?
<details>
<summary>View Raw JSON Response</summary>

```json
{
  "facts": [
    {
      "edge_id": "edge_36a682ffac",
      "subject": "Breast core biopsy",
      "subject_type": "PATHOLOGY_SPECIMEN",
      "relation": "FOUND_IN_SPECIMEN",
      "object": "Invasive Ductal Carcinoma",
      "object_type": "DISEASE_DIAGNOSIS",
      "confidence": 0.94,
      "approved_by": "Dr_Pathologist_Smith",
      "timestamp": 1785927496,
      "chunk_id": "PATH_TEST_001",
      "chunk_text": "SPECIMEN: Breast core biopsy. DIAGNOSIS: Invasive Ductal Carcinoma. BIOMARKERS: Tumor overexpresses HER2 protein (3+ IHC score) and Estrogen Receptor is positive."
    },
    {
      "edge_id": "edge_4e21960e66",
      "subject": "Lung wedge resection",
      "subject_type": "PATHOLOGY_SPECIMEN",
      "relation": "FOUND_IN_SPECIMEN",
      "object": "EGFR-mutant Non-Small Cell Lung Adenocarcinoma",
      "object_type": "DISEASE_DIAGNOSIS",
      "confidence": 0.94,
      "approved_by": "thesis_annotator_1",
      "timestamp": 1785928355,
      "chunk_id": "PATH_TEST_002",
      "chunk_text": "SPECIMEN: Lung wedge resection. DIAGNOSIS: EGFR-mutant Non-Small Cell Lung Adenocarcinoma. MARGINS: Resection margins are clear of tumor cells."
    },
    {
      "edge_id": "edge_d01ec8386e",
      "subject": "Thyroid fine needle aspiration",
      "subject_type": "PATHOLOGY_SPECIMEN",
      "relation": "FOUND_IN_SPECIMEN",
      "object": "Papillary Thyroid Carcinoma with BRAF V600E mutation identified",
      "object_type": "DISEASE_DIAGNOSIS",
      "confidence": 0.94,
      "approved_by": "thesis_annotator_1",
      "timestamp": 1785928358,
      "chunk_id": "PATH_TEST_003",
      "chunk_text": "SPECIMEN: Thyroid fine needle aspiration. DIAGNOSIS: Papillary Thyroid Carcinoma with BRAF V600E mutation identified."
    }
  ]
}
```
</details>
=======================================================
  LLM'S FINAL VERIFIED ANSWER
=======================================================
Based on the retrieved medical records, the following genetic and molecular findings were identified in breast cancer tissue samples:

*   **HER2 Overexpression:** A breast core biopsy diagnosed with **Invasive Ductal Carcinoma** showed protein overexpression of **HER2** (indicated by a 3+ IHC score).
*   **Estrogen Receptor (ER) Status:** The same specimen was identified as **Estrogen Receptor positive**.

No other specific DNA mutations (such as BRCA1/2) were mentioned in the provided clinical data for breast cancer.

For more details, you can view the findings in the [presentation widget](http://localhost:8000/ui/facts-widget?concept=MEDICAL_CONDITION).
*The url would not be the generic "medical condition" but whatever was utilized for the mcp response. Youget to see when it was approved by whom and its source.*

=======================================================

ExpertGraph is a high-integrity graph architecture where the graph acts as an immutable ground truth verified entirely by human domain experts (pathologists, clinicians, legal analysts). 

LLMs are used strictly as extraction utilities at the beginning (**The Ingestion Sieve**) and presentation layers at the end (**The MCP-UI RAG Output**). Fact presentation is controlled via **MCP Apps** (`mcp-ui`) to guarantee tamper-proof, hallucination-free display of human-approved facts.



---

## 🏛️ System Architecture

```
[ Raw Unstructured Reports (e.g. Pathology, Financial) ]
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Module A: The Ingestion Sieve                          │
│  • Extractor LLM (Instructor + Provider Normalization) │
│  • Adversarial Critic LLM (Confidence & Validation)    │
│  • Graph Ingester (status: "pending")                  │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Module B: React Annotator Dashboard                    │
│  • High-throughput side-by-side verification UI        │
│  • Hotkeys: (A)pprove / (R)eject / (N)ext              │
│  • Neo4j Edge Status -> "approved" (Ground Truth)      │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Module C: FastMCP Server & mcp-ui Presentation Layer   │
│  • Stateless HTTP Endpoint at /mcp                     │
│  • Two-Step Cypher Retrieval Engine                    │
│     Step 1: Meta-Graph Subclass & Synonym Expansion    │
│     Step 2: Approved Facts Instance Retrieval           │
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

The script supports both standard OpenAI JSON tool calls and text-based token tool calls (`<|tool_call>...<tool_call|>`) emitted by local GGUF models.

---

## 🧼 Resetting Database & Mock Queue State

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
- **Graph Database**: Neo4j 5.x (Cypher & APOC)
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

Run the automated test suite using `pytest`:
```bash
PYTHONPATH=. ./venv/bin/pytest tests/test_expertgraph.py
```
